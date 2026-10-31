# display_diag.py - step-by-step diagnostic for GC9A01 + lvgl_micropython on Pico 2
# Run from a terminal (NOT Thonny):   mpremote run display_diag.py
# Every step prints; the last line you see tells us where it stops.

import sys, time, gc, machine

# ---------------- wiring (edit to YOUR pins) ----------------
SPI_ID = 0
SCK, MOSI, MISO = 6, 7, 16      # MISO unused by display; GP16 must be free
CS, DC, RST, BL = 12, 11, 10, 13
FREQ = 20_000_000          # slower than before, to rule out signal problems
# -------------------------------------------------------------

def step(msg):
    print("[%6d ms] %s" % (time.ticks_ms(), msg))

try:
    step("1 backlight test: OFF 1 s, then ON - watch the screen")
    bl = machine.Pin(BL, machine.Pin.OUT)
    bl.value(0); time.sleep(1); bl.value(1); time.sleep(0.5)

    step("2 import lvgl / lcd_bus / gc9a01")
    import lvgl as lv, lcd_bus, gc9a01
    import display_driver_framework as ddf
    if not lv.is_initialized():
        lv.init()

    step("3 create SPI and SPIBus")
    spi = machine.SPI(SPI_ID, baudrate=FREQ, sck=SCK, mosi=MOSI, miso=MISO)
    print("   ", spi)
    bus = lcd_bus.SPIBus(spi_bus=spi, dc=DC, cs=CS, freq=FREQ)

    step("4 allocate frame buffers")
    BUF = 240 * 60 * 2
    fb1 = bus.allocate_framebuffer(BUF, lcd_bus.MEMORY_INTERNAL)
    fb2 = bus.allocate_framebuffer(BUF, lcd_bus.MEMORY_INTERNAL)
    print("    fb1:", fb1 is not None, " fb2:", fb2 is not None)

    step("5 create GC9A01 driver")
    display = gc9a01.GC9A01(
        data_bus=bus, display_width=240, display_height=240,
        frame_buffer1=fb1, frame_buffer2=fb2,
        reset_pin=RST, reset_state=ddf.STATE_LOW,
        backlight_pin=BL, backlight_on_state=ddf.STATE_HIGH,
        color_space=lv.COLOR_FORMAT.RGB565,
        color_byte_order=gc9a01.BYTE_ORDER_BGR,
        rgb565_byte_swap=True,
    )

    step("6 init panel (reset + init sequence)")
    display.set_power(True)
    display.init()
    display.set_backlight(100)

    step("7 draw full-screen RED and force a render (no task handler)")
    scr = lv.screen_active()
    scr.set_style_bg_color(lv.color_hex(0xFF0000), 0)
    scr.set_style_bg_opa(255, 0)
    lv.refr_now(None)
    step("   render done - is the screen red?")
    time.sleep(2)

    step("8 GREEN then BLUE")
    for c in (0x00FF00, 0x0000FF):
        scr.set_style_bg_color(lv.color_hex(c), 0)
        lv.refr_now(None)
        time.sleep(1.5)

    step("9 label + task handler, then heartbeat every second (Ctrl-C to stop)")
    scr.set_style_bg_color(lv.color_hex(0x000000), 0)
    lbl = lv.label(scr)
    lbl.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    lbl.center()
    import task_handler
    th = task_handler.TaskHandler()
    gc.collect()
    step("   free heap: %d" % gc.mem_free())

    n = 0
    while True:
        n += 1
        lbl.set_text("alive %d" % n)
        print("    heartbeat", n)
        time.sleep(1)

except KeyboardInterrupt:
    step("stopped by user")
except Exception as e:
    step("EXCEPTION:")
    sys.print_exception(e)
