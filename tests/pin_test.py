# pin_test.py - check the GP22 button wiring (no LVGL, works on any firmware)
#   mpremote run app/pin_test.py      then press the button; Ctrl-C to stop
import time
from machine import Pin

btn = Pin(22, Pin.IN, Pin.PULL_UP)
last = btn.value()
print("GP22 idle value:", last, "(expect 1)")
try:
    while True:
        v = btn.value()
        if v != last:
            print("PRESSED" if v == 0 else "released")
            last = v
        time.sleep_ms(10)
except KeyboardInterrupt:
    print("done")
