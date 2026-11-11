# hw.py - Pico 2 + GC9A01 display bring-up for lvgl_micropython (rp2-fix fork)
#
#   import hw
#   display = hw.start()        # guard + SPI + display + LVGL task handler
#   hw.backlight(100)           # once the first frame is drawn
#   ...
#   hw.stop()                   # call from finally: - hard-resets by default
#
# Pins: SPI0, SCK GP6, MOSI GP7, RST GP10, DC GP11, CS GP12, BL GP13
#       KY-040 encoder: CLK GP18, DT GP22, SW GP28 (module powered from 3V3)

import sys
import time
import machine

# ---------------- wiring ----------------
SPI_ID = 0
SCK, MOSI, MISO = 6, 7, 16      # MISO is not wired; GP16 must stay free
CS, DC, RST, BL = 12, 11, 10, 13
FREQ = 40_000_000
WIDTH = HEIGHT = 240
BUF_LINES = 60
# ----------------------------------------

# Watchdog scratch0 survives soft reboots: used to detect stale LVGL state.
_WDT_BASE = 0x400D8000 if "RP2350" in sys.implementation._machine else 0x40058000
_SCRATCH0 = _WDT_BASE + 0x0C   # "LVGL started since last hard reset"
_SCRATCH1 = _WDT_BASE + 0x10   # "skip autostart once" (survives machine.reset)
_MAGIC = 0x4C56474C             # "LVGL"
_SKIP = 0x534B4950              # "SKIP"

display = None
task_handler = None


def _guard():
    """Hard-reset if LVGL was already started since the last hard reset."""
    if machine.mem32[_SCRATCH0] == _MAGIC:
        machine.mem32[_SCRATCH0] = 0
        print("Stale LVGL state from a previous run - hard resetting.")
        print("Wait ~2 s for USB to reconnect, then run again.")
        time.sleep_ms(200)
        machine.reset()
    machine.mem32[_SCRATCH0] = _MAGIC


def skip_autostart_requested():
    """True (once) if the previous run asked main.py not to auto-start.
    Cleared by reading it, and by any power cycle."""
    if machine.mem32[_SCRATCH1] == _SKIP:
        machine.mem32[_SCRATCH1] = 0
        return True
    return False


def start(backlight=100):
    global display, task_handler
    _guard()

    import lvgl as lv
    import lcd_bus
    import gc9a01
    import display_driver_framework as ddf
    import task_handler as th_mod

    if not lv.is_initialized():
        lv.init()

    spi = machine.SPI(SPI_ID, baudrate=FREQ, sck=SCK, mosi=MOSI, miso=MISO)
    bus = lcd_bus.SPIBus(spi_bus=spi, dc=DC, cs=CS, freq=FREQ)

    size = WIDTH * BUF_LINES * 2
    fb1 = bus.allocate_framebuffer(size, lcd_bus.MEMORY_INTERNAL)
    fb2 = bus.allocate_framebuffer(size, lcd_bus.MEMORY_INTERNAL)

    display = gc9a01.GC9A01(
        data_bus=bus,
        display_width=WIDTH,
        display_height=HEIGHT,
        frame_buffer1=fb1,
        frame_buffer2=fb2,
        reset_pin=RST,
        reset_state=ddf.STATE_LOW,
        backlight_pin=BL,
        backlight_on_state=ddf.STATE_HIGH,
        color_space=lv.COLOR_FORMAT.RGB565,
        color_byte_order=gc9a01.BYTE_ORDER_BGR,
        rgb565_byte_swap=True,
    )
    display.set_power(True)
    display.init()
    display.set_backlight(backlight)

    task_handler = th_mod.TaskHandler()
    return display


def backlight(level):
    """Backlight 0-100. start(backlight=0) + backlight(100) after the first
    frame is drawn avoids showing a half-initialised screen at power-up."""
    display.set_backlight(level)


def stop(hard_reset=True, skip_autostart=True):
    """Stop drawing, blank the backlight, then hard-reset (LVGL cannot be
    restarted after a soft reboot on this firmware).

    skip_autostart=True: the next boot stays at the REPL instead of running
    main.py again, so Ctrl-C / mpremote / a crash never cause a reset loop."""
    for name, fn in (
        ("stop task handler", lambda: task_handler.deinit()),
        ("drain scheduled",   lambda: time.sleep_ms(100)),
        ("backlight off",     lambda: display.set_backlight(0)),
    ):
        try:
            fn()
        except Exception as e:
            print("  stop:", name, "failed:", e)
    if hard_reset:
        machine.mem32[_SCRATCH0] = 0
        machine.mem32[_SCRATCH1] = _SKIP if skip_autostart else 0
        print("Hard reset - USB reconnects in ~2 s.")
        time.sleep_ms(200)
        machine.reset()
