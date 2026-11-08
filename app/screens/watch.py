# screens/watch.py - FoldedToad railroad pocket watch
#
# EEZ screen "Watch", widgets in this order (back to front):
#   img_dial    dial_face.png    X 0,   Y 0
#   img_second  hand_second.png  X 114, Y 140   pivot 6, 28
#   img_hour    hand_hour.png    X 110, Y 62    pivot 10, 58
#   img_minute  hand_minute.png  X 111, Y 18    pivot 9, 102
#
# Time comes from the Pico's RTC (machine.RTC). Thonny sets it when it
# connects; with mpremote:  mpremote rtc --set.  Without either, the clock
# starts at midnight on power-up (no backup battery).

import time
import machine
import asyncio
import eezui
from ui import Screen

# Railroad watches typically beat 18,000 times an hour: 5 steps per second.
# 1 = one jump per second (cheapest to draw).
BEATS_PER_SECOND = 5

# Pivots are also set in EEZ; setting them here keeps the two in step even
# if the EEZ properties are left at their defaults.
PIVOTS = {
    "img_second": (6, 28),
    "img_hour": (10, 58),
    "img_minute": (9, 102),
}


class WatchScreen(Screen):
    screen_id = eezui.SCREEN_WATCH

    def __init__(self, app):
        super().__init__(app)
        self.rtc = machine.RTC()
        self._angle = {}
        self._last_s = None
        self._s_tick = 0             # ticks_ms when the RTC second last changed
        self._pivots_set = False

    # ---- helpers ----
    def _rotate(self, name, tenths):
        tenths %= 3600
        if self._angle.get(name) != tenths:     # only redraw hands that moved
            self._angle[name] = tenths
            eezui.set_rotation(name, tenths)

    def _now(self):
        """(h, m, s, fraction of second). The RTC has no sub-seconds, so the
        fraction is measured from the moment the seconds value changed."""
        dt = self.rtc.datetime()                # (y, mo, d, wd, h, m, s, sub)
        h, m, s = dt[4], dt[5], dt[6]
        now = time.ticks_ms()
        if s != self._last_s:
            self._last_s = s
            self._s_tick = now
        frac = min(999, time.ticks_diff(now, self._s_tick)) / 1000
        return h, m, s, frac

    def update(self):
        h, m, s, frac = self._now()
        beat = int(frac * BEATS_PER_SECOND) / BEATS_PER_SECOND
        # angles in 0.1 degree units
        self._rotate("img_second", int((s + beat) * 60))           # 6 deg / s
        self._rotate("img_minute", m * 60 + s)                     # 0.1 deg / s
        self._rotate("img_hour", ((h % 12) * 3600 + m * 60 + s) // 12)

    # ---- lifecycle ----
    def enter(self):
        if not self._pivots_set:
            for name, (x, y) in PIVOTS.items():
                eezui.set_pivot(name, x, y)
            self._pivots_set = True
        self.update()

    async def run(self):
        # Poll quickly so the beat lines up with the RTC's second boundary;
        # hands are only redrawn when their angle actually changes.
        while True:
            self.update()
            await asyncio.sleep_ms(40)
