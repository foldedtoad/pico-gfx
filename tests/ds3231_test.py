# ds3231_test.py - check the DS3231 wiring and battery, optionally set its time
#   mpremote cp app/ds3231.py :ds3231.py
#   mpremote rtc --set + run tests/ds3231_test.py      (sets the Pico RTC from the PC first)
#
# Wiring (Adafruit #5188, header pins):
#   VIN -> 3V3 (pin 36)   GND -> GND   SCL -> GP21 (pin 27)   SDA -> GP20 (pin 26)

import time
import machine
from machine import I2C, Pin
from ds3231 import DS3231

SET_FROM_PICO = True     # copy the Pico's RTC (just set from the PC) into the DS3231

i2c = I2C(0, sda=Pin(20), scl=Pin(21), freq=400_000)
found = i2c.scan()
print("I2C devices:", ["0x%02X" % a for a in found], "(expect 0x68, maybe 0x57 EEPROM)")
ds = DS3231(i2c)
if not ds.present():
    raise SystemExit("DS3231 not found - check SDA/SCL (not swapped?), 3V3 and GND")

print("oscillator stopped since last set (battery?):", ds.lost_power())
print("chip temperature: %.2f C" % ds.temperature())
print("DS3231 time:", ds.datetime())

if SET_FROM_PICO:
    pico = machine.RTC().datetime()
    if pico[0] < 2025:
        print("Pico RTC looks unset (%d) - run with 'mpremote rtc --set + run ...'" % pico[0])
    else:
        ds.datetime(pico)
        print("DS3231 set from Pico RTC:", ds.datetime())

print("\nwatching the DS3231 tick for 5 s:")
last = None
t_end = time.ticks_add(time.ticks_ms(), 5000)
while time.ticks_diff(t_end, time.ticks_ms()) > 0:
    s = ds.seconds()
    if s != last:
        print("  %02d:%02d:%02d" % ds.datetime()[4:7])
        last = s
    time.sleep_ms(50)
print("done - unplug USB for a minute, replug, and run again with SET_FROM_PICO = False:")
print("the time should have kept running on the coin cell.")
