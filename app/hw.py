# hw.py - Pico 2 + GC9A01 display bring-up for lvgl_micropython (rp2-fix fork)
#
#   import hw
#   display = hw.start()        # guard + SPI + display + LVGL task handler
#   hw.add_buttons({28: "PREV", 22: "ENTER", 18: "NEXT"})   # optional buttons
#   ...
#   hw.stop()                   # call from finally: - hard-resets by default
#
# Pins: SPI0, SCK GP6, MOSI GP7, RST GP10, DC GP11, CS GP12, BL GP13
#       buttons GP28 (prev), GP22 (enter), GP18 (next) -> GND, internal pull-ups

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


def add_buttons(mapping):
    """Map active-low push buttons (GPIO -> GND) to LVGL keypad keys.

        hw.add_buttons({28: "PREV", 22: "ENTER", 18: "NEXT"})

    Keys are lv.KEY names: PREV/NEXT move focus, ENTER clicks the focused
    widget, LEFT/RIGHT/UP/DOWN adjust sliders, arcs, rollers...
    Call AFTER start() and BEFORE eezui.init(): it creates a default group,
    so every focusable widget EEZ creates joins it (in creation order).
    Returns the LVGL group.
    """
    import lvgl as lv

    pins = []
    for gpio, key in mapping.items():
        if isinstance(key, str):
            key = getattr(lv.KEY, key)
        pins.append((machine.Pin(gpio, machine.Pin.IN, machine.Pin.PULL_UP), key))

    group = lv.group_create()
    group.set_default()

    last_key = [pins[0][1]]

    def read_cb(indev, data):
        # A keypad reports one key at a time: the first pressed button wins.
        for pin_obj, key in pins:
            if pin_obj.value() == 0:
                last_key[0] = key
                data.key = key
                data.state = lv.INDEV_STATE.PRESSED
                return
        data.key = last_key[0]          # release must report the same key
        data.state = lv.INDEV_STATE.RELEASED

    indev = lv.indev_create()
    indev.set_type(lv.INDEV_TYPE.KEYPAD)
    indev.set_read_cb(read_cb)
    indev.set_group(group)

    _keep.extend((pins, group, read_cb, indev))
    return group


def add_button(pin=22, key="ENTER"):
    """Single button shortcut (kept for button_test.py)."""
    return add_buttons({pin: key})


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
