# ds3231.py - minimal MicroPython driver for the DS3231 precision RTC
# (Adafruit #5188 / #3013, ChronoDot, ZS-042 ...). I2C address 0x68.
#
#   from machine import I2C, Pin
#   rtc = DS3231(I2C(0, sda=Pin(20), scl=Pin(21), freq=400_000))
#   rtc.datetime()                  -> (y, mo, d, weekday, h, m, s, 0)  machine.RTC format
#   rtc.datetime((2026, 11, 20, 4, 9, 41, 0, 0))
#   rtc.lost_power()                -> True if the oscillator stopped (time not valid)
#   rtc.temperature()               -> deg C (0.25 resolution)
#   rtc.sqw_1hz(True)               -> 1 Hz square wave on the SQW pin
#
# weekday follows machine.RTC: 0 = Monday ... 6 = Sunday.

_ADDR = 0x68
_REG_TIME = 0x00
_REG_CONTROL = 0x0E
_REG_STATUS = 0x0F
_REG_TEMP = 0x11


def _bcd(b):
    return (b >> 4) * 10 + (b & 0x0F)


def _tobcd(d):
    return ((d // 10) << 4) | (d % 10)


class DS3231:
    def __init__(self, i2c, addr=_ADDR):
        self.i2c = i2c
        self.addr = addr

    def present(self):
        try:
            return self.addr in self.i2c.scan()
        except OSError:
            return False

    def _read(self, reg, n):
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _write(self, reg, data):
        self.i2c.writeto_mem(self.addr, reg, bytes(data))

    def datetime(self, dt=None):
        if dt is None:
            b = self._read(_REG_TIME, 7)
            s = _bcd(b[0] & 0x7F)
            m = _bcd(b[1] & 0x7F)
            hr = b[2]
            if hr & 0x40:                                  # 12-hour mode (not used by us)
                h = _bcd(hr & 0x1F) % 12 + (12 if hr & 0x20 else 0)
            else:
                h = _bcd(hr & 0x3F)
            wd = ((b[3] & 0x07) - 1) % 7                   # DS3231 1..7 -> 0..6
            d = _bcd(b[4] & 0x3F)
            mo = _bcd(b[5] & 0x1F)
            y = 2000 + _bcd(b[6]) + (100 if b[5] & 0x80 else 0)
            return (y, mo, d, wd, h, m, s, 0)
        y, mo, d, wd, h, m, s = dt[:7]
        self._write(_REG_TIME, (_tobcd(s), _tobcd(m), _tobcd(h), (wd % 7) + 1,
                                _tobcd(d), _tobcd(mo), _tobcd(y % 100)))
        st = self._read(_REG_STATUS, 1)[0]
        self._write(_REG_STATUS, (st & 0x7F,))             # clear "oscillator stopped" flag

    def seconds(self):
        return _bcd(self._read(_REG_TIME, 1)[0] & 0x7F)

    def lost_power(self):
        """True if the oscillator stopped (battery flat/missing) since the time
        was last set - the stored time is then not trustworthy."""
        return bool(self._read(_REG_STATUS, 1)[0] & 0x80)

    def temperature(self):
        b = self._read(_REG_TEMP, 2)
        t = b[0] - 256 if b[0] & 0x80 else b[0]
        return t + (b[1] >> 6) * 0.25

    def sqw_1hz(self, on=True):
        """on: 1 Hz square wave on SQW (INTCN=0, RS=00). off: SQW used as alarm INT."""
        c = self._read(_REG_CONTROL, 1)[0]
        c = (c & ~0x1C) if on else (c | 0x04)
        self._write(_REG_CONTROL, (c,))
