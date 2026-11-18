# timekeeper.py - keeps the Pico's RTC in step with the DS3231 backup clock
#
#   tk = Timekeeper()                 # finds the DS3231 on I2C0 (GP20 SDA, GP21 SCL)
#   tk.sync_at_boot()                 # DS3231 -> Pico RTC, aligned to the second
#   tk.save(datetime_tuple)           # crown set: Pico RTC -> DS3231
#   await tk.resync_forever()         # hourly DS3231 -> Pico RTC (drift correction)
#
# Without a DS3231 (not fitted, unplugged, battery flat) everything falls back
# to the Pico's own RTC, exactly as before.

import time
import machine
import asyncio
from machine import I2C, Pin
from ds3231 import DS3231

I2C_ID, SDA, SCL = 0, 20, 21
RESYNC_S = 3600


class Timekeeper:
    def __init__(self):
        self.rtc = machine.RTC()
        self.ext = None
        try:
            ds = DS3231(I2C(I2C_ID, sda=Pin(SDA), scl=Pin(SCL), freq=400_000))
            if ds.present():
                self.ext = ds
        except Exception as e:
            print("timekeeper: no DS3231 (%s)" % e)
        if self.ext is None:
            print("timekeeper: DS3231 not found - using the Pico RTC only")
        self.busy = lambda: False            # set by the watch: True while setting

    # ---- helpers ----
    def _aligned_copy_blocking(self):
        """Wait for the DS3231's seconds to tick over, then copy it at once, so
        the Pico RTC starts its second within a few ms of the DS3231's."""
        s0 = self.ext.seconds()
        t_end = time.ticks_add(time.ticks_ms(), 1200)
        while self.ext.seconds() == s0 and time.ticks_diff(t_end, time.ticks_ms()) > 0:
            time.sleep_ms(2)
        self.rtc.datetime(self.ext.datetime())

    async def _aligned_copy(self):
        s0 = self.ext.seconds()
        t_end = time.ticks_add(time.ticks_ms(), 1200)
        while self.ext.seconds() == s0 and time.ticks_diff(t_end, time.ticks_ms()) > 0:
            await asyncio.sleep_ms(5)
        self.rtc.datetime(self.ext.datetime())

    # ---- API ----
    def sync_at_boot(self):
        if self.ext is None:
            return False
        try:
            if self.ext.lost_power():
                print("timekeeper: DS3231 lost power (battery?) - time not set, "
                      "set it with the crown")
                return False
            self._aligned_copy_blocking()
            print("timekeeper: time from DS3231: %04d-%02d-%02d %02d:%02d:%02d"
                  % (self.rtc.datetime()[0:3] + self.rtc.datetime()[4:7]))
            return True
        except OSError as e:
            print("timekeeper: DS3231 read failed (%s)" % e)
            return False

    def save(self, dt):
        """Store a newly set time in the DS3231 as well."""
        if self.ext is None:
            return
        try:
            self.ext.datetime(dt)
        except OSError as e:
            print("timekeeper: DS3231 write failed (%s)" % e)

    async def resync_forever(self):
        if self.ext is None:
            return
        while True:
            await asyncio.sleep(RESYNC_S)
            if self.busy():
                continue                     # never fight the crown
            try:
                if not self.ext.lost_power():
                    await self._aligned_copy()
            except OSError as e:
                print("timekeeper: resync failed (%s)" % e)
