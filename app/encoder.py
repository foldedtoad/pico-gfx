# encoder.py - KY-040 style rotary encoder with push switch
#
#   enc = RotaryEncoder(clk=18, dt=19)        # counted by PIO hardware
#   btn = Button(28)                          # push switch, polled
#
#   enc.take()   -> clicks turned since the last call (+ clockwise, - counter)
#   btn.poll()   -> None, "click" (on release) or "long" (while held >= long_ms)
#
# Wiring: module + to 3V3 (NOT 5 V), GND to GND. DT must be on the GPIO right
# after CLK (PIO reads them as a pin pair). CLK/DT have 10k pull-ups on the
# KY-040 board; SW usually has none, so internal pull-ups are enabled on all
# three (also the safe choice with RP2350 erratum E9).
#
# Why PIO: a PIO state machine samples both pins millions of times a second
# and keeps the quadrature count itself - no CPU interrupts involved, so the
# display, LVGL and garbage collection cannot make it miss steps. (Pin IRQs
# stopped working once the display was running on this firmware.)
#
# The PIO program is the quadrature counter from the Raspberry Pi pico-examples
# (16-entry jump table indexed by previous+current pin state, count kept in Y).
# Its jump table must sit at PIO address 0; MicroPython loads programs at the
# highest free address, so the program is padded to all 32 instructions.

import time
import rp2
from machine import Pin


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_LEFT, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def _quadrature():
    # jump table: index = (previous AB << 2) | current AB
    jmp("update")          # 0  00 -> 00
    jmp("decrement")       # 1  00 -> 01
    jmp("increment")       # 2  00 -> 10
    jmp("update")          # 3  00 -> 11 (invalid)
    jmp("increment")       # 4  01 -> 00
    jmp("update")          # 5  01 -> 01
    jmp("update")          # 6  01 -> 10 (invalid)
    jmp("decrement")       # 7  01 -> 11
    jmp("decrement")       # 8  10 -> 00
    jmp("update")          # 9  10 -> 01 (invalid)
    jmp("update")          # 10 10 -> 10
    jmp("increment")       # 11 10 -> 11
    jmp("update")          # 12 11 -> 00 (invalid)
    jmp("increment")       # 13 11 -> 01
    label("decrement")
    jmp(y_dec, "update")   # 14 11 -> 10: Y-- (falls through to update)
    wrap_target()
    label("update")
    mov(isr, y)            # 15 11 -> 11
    push(noblock)          # latest count always in the RX FIFO
    out(isr, 2)            # previous AB (low 2 bits of OSR) into ISR
    in_(pins, 2)           # ISR = previous AB << 2 | current AB
    mov(osr, isr)          # remember for next time
    mov(pc, isr)           # jump into the table
    label("increment")
    mov(y, invert(y))      # Y++ done as ~(~Y - 1)
    jmp(y_dec, "inc_cont")
    label("inc_cont")
    mov(y, invert(y))
    wrap()
    # padding: fills instruction memory so the program loads at address 0
    nop()
    nop()
    nop()
    nop()
    nop()
    nop()
    nop()
    nop()


def _signed(v):
    return v - (1 << 32) if v & 0x80000000 else v


class RotaryEncoder:
    PIO_ID = 2              # RP2350 has PIO 0..2; PIO 2 is unused by the display

    def __init__(self, clk, dt, steps_per_detent=4, reverse=False):
        if dt != clk + 1:
            raise ValueError("DT must be on GPIO %d (the pin after CLK)" % (clk + 1))
        self._clk = Pin(clk, Pin.IN, Pin.PULL_UP)
        self._dt = Pin(dt, Pin.IN, Pin.PULL_UP)
        self._spd = steps_per_detent
        # The PIO counts down when CLK leads (CLK falls first); on the KY-040
        # that is clockwise, so invert to make clockwise positive.
        self._sign = 1 if reverse else -1

        pio = rp2.PIO(self.PIO_ID)
        pio.remove_program()                         # free all 32 instruction slots
        sm_id = self.PIO_ID * 4
        # 2 MHz: samples the pins every ~3 us - far faster than any hand turn
        self._sm = rp2.StateMachine(sm_id, _quadrature, freq=2_000_000, in_base=self._clk)
        self._sm.exec("set(y, 0)")
        self._sm.active(1)

        self._last_raw = 0
        self._base = self._raw()                     # count at the last rest position
        self._clicks = 0
        self._taken = 0

    def _raw(self):
        """Current step count from the PIO.

        The PIO pushes its count every few microseconds with push(noblock).
        When the 4-entry RX FIFO is full, new pushes are DROPPED, so whatever
        sits in the FIFO dates from just after the previous read - up to a
        whole poll old. Discard those, then wait for the next push (a few
        microseconds away) to get the count as of now."""
        sm = self._sm
        for _ in range(sm.rx_fifo()):
            sm.get()
        self._last_raw = _signed(sm.get())
        return self._last_raw

    def _update(self):
        raw = self._raw()
        # Count clicks only when the knob rests (CLK = DT = 1): steps since the
        # previous rest, rounded to whole clicks. Re-basing at every rest means
        # a stray step can never accumulate into a false click.
        if self._clk.value() and self._dt.value():
            delta = raw - self._base
            if delta:
                half = self._spd // 2
                n = (delta + half) // self._spd if delta > 0 else -((-delta + half) // self._spd)
                self._clicks += n
                self._base = raw

    def position(self):
        """Total clicks since start."""
        self._update()
        return self._clicks * self._sign

    def take(self):
        """Clicks since the last call. Call regularly (every 10-50 ms)."""
        pos = self.position()
        d = pos - self._taken
        self._taken = pos
        return d

    def flush(self):
        self._taken = self.position()

    def deinit(self):
        self._sm.active(0)


class Button:
    def __init__(self, pin, long_ms=900):
        self._p = Pin(pin, Pin.IN, Pin.PULL_UP)
        self._long_ms = long_ms
        self._raw = self._stable = self._p.value()
        self._down_at = None
        self._long_sent = False

    def is_down(self):
        return self._stable == 0

    def poll(self):
        """Call every 10-50 ms. A level must be seen on two consecutive polls
        before it counts (debounce). Returns None, 'click' or 'long'."""
        raw = self._p.value()
        now = time.ticks_ms()
        if raw != self._raw:                  # changed since last poll: wait one more
            self._raw = raw
            return None
        if raw != self._stable:               # confirmed edge
            self._stable = raw
            if raw == 0:                      # pressed
                self._down_at = now
                self._long_sent = False
                return None
            was_long = self._long_sent        # released
            self._down_at = None
            return None if was_long else "click"
        if (raw == 0 and self._down_at is not None and not self._long_sent
                and time.ticks_diff(now, self._down_at) >= self._long_ms):
            self._long_sent = True
            return "long"
        return None
