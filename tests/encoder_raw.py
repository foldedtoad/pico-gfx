# encoder_raw.py - print every CLK/DT change, to see where the encoder rests
#   mpremote run tests/encoder_raw.py        Ctrl-C to stop
#
# Turn the knob ONE click slowly, pause, then another click, pause...
# Each line = one change of the pins. The state printed just before a pause
# is a rest (detent) position.

import time
from machine import Pin

clk = Pin(18, Pin.IN, Pin.PULL_UP)
dt = Pin(19, Pin.IN, Pin.PULL_UP)

irqs = [0]
def count(p):
    irqs[0] += 1
for p in (clk, dt):
    p.irq(count, Pin.IRQ_RISING | Pin.IRQ_FALLING, hard=True)

print("Turn ONE click slowly, pause ~1 s, repeat. Ctrl-C to stop.")
last = None
t_last = time.ticks_ms()
try:
    while True:
        ab = (clk.value() << 1) | dt.value()
        now = time.ticks_ms()
        if ab != last:
            gap = time.ticks_diff(now, t_last)
            if gap > 400 and last is not None:
                print("   ---- pause (rested at CLK=%d DT=%d) ----" % (last >> 1, last & 1))
            print("%7d ms  CLK=%d DT=%d   irqs=%d" % (now, ab >> 1, ab & 1, irqs[0]))
            last = ab
            t_last = now
except KeyboardInterrupt:
    for p in (clk, dt):
        p.irq(None)
    print("done")
