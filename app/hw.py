# hw.py - Pico 2 + GC9A01 display bring-up for lvgl_micropython (rp2-fix fork)
#
#   import hw
#   display = hw.start()        # guard + SPI + display + LVGL task handler
#   hw.add_button(22)           # optional: GP22 button -> LVGL ENTER key
#   ...
#   hw.stop()                   # call from finally: - hard-resets by default
#
# Pins: SPI0, SCK GP6, MOSI GP7, RST GP10, DC GP11, CS GP12, BL GP13
#       button GP22 -> GND (internal pull-up)

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
_SCRATCH0 = _WDT_BASE + 0x0C
_MAGIC = 0x4C56474C             # "LVGL"

display = None
task_handler = None
_keep = []                      # references LVGL callbacks need kept alive


def _guard():
    """Hard-reset if LVGL was already started since the last hard reset."""
    if machine.mem32[_SCRATCH0] == _MAGIC:
        machine.mem32[_SCRATCH0] = 0
        print("Stale LVGL state from a previous run - hard resetting.")
        print("Wait ~2 s for USB to reconnect, then run again.")
        time.sleep_ms(200)
        machine.reset()
    machine.mem32[_SCRATCH0] = _MAGIC


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


def add_button(pin=22, key=None):
    """Map an active-low push button (pin -> GND) to an LVGL keypad key.

    Call AFTER start() and BEFORE eezui.init(): it creates a default group, so
    every focusable widget EEZ creates (buttons, sliders...) joins it, and the
    button presses ENTER on whichever widget has focus.
    Returns the LVGL group.
    """
    import lvgl as lv
    if key is None:
        key = lv.KEY.ENTER

    pin_obj = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)   # E9-safe

    group = lv.group_create()
    group.set_default()

    def read_cb(indev, data):
        data.key = key
        if pin_obj.value() == 0:
            data.state = lv.INDEV_STATE.PRESSED
        else:
            data.state = lv.INDEV_STATE.RELEASED

    indev = lv.indev_create()
    indev.set_type(lv.INDEV_TYPE.KEYPAD)
    indev.set_read_cb(read_cb)
    indev.set_group(group)

    _keep.extend((pin_obj, group, read_cb, indev))
    return group


def stop(hard_reset=True):
    """Stop drawing, blank the backlight, then hard-reset (LVGL cannot be
    restarted after a soft reboot on this firmware)."""
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
        print("Hard reset - USB reconnects in ~2 s.")
        time.sleep_ms(200)
        machine.reset()
