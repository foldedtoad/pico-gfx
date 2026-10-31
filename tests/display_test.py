# display_test.py - first light for lvgl_micropython (rp2-fix fork) + GC9A01 on Pico 2
# Run with:  mpremote run display_test.py      (Ctrl-C exits cleanly)
#
# EDIT THE PIN NUMBERS to match the wiring from your earlier working test.

import time
import machine
import lvgl as lv
import lcd_bus
import gc9a01
import display_driver_framework as ddf
import task_handler
import sys

# ---------------- fresh-start guard ----------------
# LVGL and the rp2-fix SPI driver keep C-level state that a *soft* reboot
# (Thonny Stop/Run, mpremote, Ctrl-D) does not clear. Re-initialising on top of
# that stale state fails (MemoryError) or hangs. So: if LVGL has already been
# started since the last hard reset, hard-reset now and let the user re-run.
# A watchdog scratch register survives soft reboots but we clear it ourselves.
_WDT_BASE = 0x400D8000 if "RP2350" in sys.implementation._machine else 0x40058000
_SCRATCH0 = _WDT_BASE + 0x0C          # scratch0-3 are free for user code
_MAGIC = 0x4C56474C                   # "LVGL"

if machine.mem32[_SCRATCH0] == _MAGIC:
    machine.mem32[_SCRATCH0] = 0
    print("Stale LVGL state from a previous run - hard resetting.")
    print("Wait ~2 s for USB to reconnect, then run this script again.")
    time.sleep_ms(200)
    machine.reset()
machine.mem32[_SCRATCH0] = _MAGIC

# ---------------- wiring (edit) ----------------
SPI_ID = 0                 # SPI0: SCK 2/6/18/22, MOSI 3/7/19, MISO 0/4/16/20
SCK    = 6
MOSI   = 7
MISO   = 16                # NOT used by the display, but the driver claims a MISO pin.
                           # Pick a valid MISO pin for this SPI that is NOT wired to
                           # anything else (SPI0 options: GP0, GP4, GP16, GP20).
CS     = 12
DC     = 11
RST    = 10
BL     = 13
FREQ   = 40_000_000        # drop to 20_000_000 if you see noise/garbage
# -----------------------------------------------

if not lv.is_initialized():
    lv.init()

spi = machine.SPI(SPI_ID, baudrate=FREQ, sck=SCK, mosi=MOSI, miso=MISO)
bus = lcd_bus.SPIBus(spi_bus=spi, dc=DC, cs=CS, freq=FREQ)

BUF = 240 * 60 * 2         # 60-line partial buffers, 28.8 KB each
fb1 = bus.allocate_framebuffer(BUF, lcd_bus.MEMORY_INTERNAL)
fb2 = bus.allocate_framebuffer(BUF, lcd_bus.MEMORY_INTERNAL)

display = gc9a01.GC9A01(
    data_bus=bus,
    display_width=240,
    display_height=240,
    frame_buffer1=fb1,
    frame_buffer2=fb2,
    reset_pin=RST,
    reset_state=ddf.STATE_LOW,          # RST is active-low on these modules
    backlight_pin=BL,
    backlight_on_state=ddf.STATE_HIGH,  # STATE_PWM for dimming
    color_space=lv.COLOR_FORMAT.RGB565,
    color_byte_order=gc9a01.BYTE_ORDER_BGR,
    rgb565_byte_swap=True,
)
display.set_power(True)
display.init()
display.set_backlight(100)

# ---------------- test screen ----------------
scr = lv.screen_active()
scr.set_style_bg_color(lv.color_hex(0x000000), 0)

arc = lv.arc(scr)
arc.set_size(220, 220)
arc.center()
arc.set_range(0, 100)
arc.set_value(0)

label = lv.label(scr)
label.set_text("Pico 2 + LVGL")
label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
label.center()

# colour check: red / green / blue dots - if red and blue are swapped,
# change BYTE_ORDER_BGR to BYTE_ORDER_RGB (or toggle rgb565_byte_swap)
for i, c in enumerate((0xFF0000, 0x00FF00, 0x0000FF)):
    dot = lv.obj(scr)
    dot.set_size(24, 24)
    dot.set_style_radius(12, 0)
    dot.set_style_bg_color(lv.color_hex(c), 0)
    dot.set_style_border_width(0, 0)
    dot.align(lv.ALIGN.CENTER, (i - 1) * 34, 40)

th = task_handler.TaskHandler()

import gc
gc.collect()
print("LVGL", lv.version_major(), lv.version_minor(), "- free heap:", gc.mem_free())
print("Running - press Ctrl-C to stop")

# After Ctrl-C the board is hard-reset, because LVGL cannot be started again
# after a soft reboot on this firmware. Set False only to inspect state at the
# REPL after stopping (you must then reset before the next run).
HARD_RESET_ON_EXIT = True


def shutdown():
    """Stop LVGL drawing and quiet the display."""
    for name, fn in (
        ("stop task handler", lambda: th.deinit()),          # no more timer callbacks
        ("drain scheduled",   lambda: time.sleep_ms(100)),   # let queued ones finish
        ("backlight off",     lambda: display.set_backlight(0)),
    ):
        try:
            fn()
        except Exception as e:
            print("  shutdown:", name, "failed:", e)
    print("Display stopped.")


v = 0
try:
    while True:
        v = (v + 2) % 101
        arc.set_value(v)
        time.sleep_ms(50)
except KeyboardInterrupt:
    print("\nCtrl-C received - shutting down...")
finally:
    shutdown()
    if HARD_RESET_ON_EXIT:
        machine.mem32[_SCRATCH0] = 0
        print("Hard reset - USB reconnects in ~2 s.")
        time.sleep_ms(200)
        machine.reset()
