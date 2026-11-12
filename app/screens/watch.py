# screens/watch.py - FoldedToad railroad pocket watch
#
# EEZ screen "Watch", widgets in this order (back to front):
#   img_dial    dial_face.png    X 0,   Y 0
#   img_second  hand_second.png  X 114, Y 140   pivot 6, 28
#   img_hour    hand_hour.png    X 110, Y 62    pivot 10, 58
#   img_minute  hand_minute.png  X 111, Y 18    pivot 9, 102
#
# Time comes from the Pico's RTC (machine.RTC). Thonny sets it when it
# connects; with mpremote:  mpremote rtc --set.  Or set it with the crown:
#
#   click knob   "pull the crown": seconds hand stops at 0, set mode
#   turn knob    move the minute hand (fast turning = bigger steps)
#   click again  "push the crown in": new time stored, watch restarts at :00
#   hold ~1 s    (in set mode) cancel, keep the old time

import time
import machine
import asyncio
import eezui
from ui import Screen

# Railroad watches typically beat 18,000 times an hour: 5 steps per second.
# 1 = one jump per second (cheapest to draw).
BEATS_PER_SECOND = 5

PIVOTS = {
    "img_second": (6, 28),
    "img_hour": (10, 58),
    "img_minute": (9, 102),
}

POLL_MS = 40


class WatchScreen(Screen):
    screen_id = eezui.SCREEN_WATCH

    def __init__(self, app):
        super().__init__(app)
        self.rtc = machine.RTC()
        self.encoder = getattr(app, "encoder", None)     # optional hardware
        self.crown = getattr(app, "crown", None)
        self._angle = {}
        self._last_s = None
        self._s_tick = 0
        self._pivots_set = False
        self.setting = False
        self.set_minutes = 0                             # 0..1439 while setting

    # ---- hands ----
    def _rotate(self, name, tenths):
        tenths %= 3600
        if self._angle.get(name) != tenths:              # only redraw hands that moved
            self._angle[name] = tenths
            eezui.set_rotation(name, tenths)

    def _show(self, h, m, s, beat=0.0):
        # angles in 0.1 degree units
        self._rotate("img_second", int((s + beat) * 60))           # 6 deg / s
        self._rotate("img_minute", m * 60 + s)                     # 0.1 deg / s
        self._rotate("img_hour", ((h % 12) * 3600 + m * 60 + s) // 12)

    def _now(self):
        """(h, m, s, fraction of second). The RTC has no sub-seconds, so the
        fraction is measured from the moment the seconds value changed."""
        dt = self.rtc.datetime()                         # (y, mo, d, wd, h, m, s, sub)
        h, m, s = dt[4], dt[5], dt[6]
        now = time.ticks_ms()
        if s != self._last_s:
            self._last_s = s
            self._s_tick = now
        frac = min(999, time.ticks_diff(now, self._s_tick)) / 1000
        return h, m, s, frac

    def update(self):
        if self.setting:
            h, m = divmod(self.set_minutes, 60)
            self._show(h, m, 0)
        else:
            h, m, s, frac = self._now()
            self._show(h, m, s, int(frac * BEATS_PER_SECOND) / BEATS_PER_SECOND)

    # ---- crown (encoder) ----
    def _pull_crown(self):
        dt = self.rtc.datetime()
        self.set_minutes = dt[4] * 60 + dt[5]
        self.setting = True
        if self.encoder:
            self.encoder.flush()                         # ignore turns made before
        print("watch: set mode (%02d:%02d)" % divmod(self.set_minutes, 60))

    def _push_crown(self):
        y, mo, d, wd = self.rtc.datetime()[:4]
        h, m = divmod(self.set_minutes, 60)
        self.rtc.datetime((y, mo, d, wd, h, m, 0, 0))
        self._last_s = None                              # restart the beat cleanly
        self.setting = False
        print("watch: time set to %02d:%02d:00" % (h, m))

    def _cancel(self):
        self.setting = False
        self._last_s = None
        print("watch: setting cancelled")

    @staticmethod
    def _step(detents):
        """Acceleration: detents seen in one 40 ms poll -> minutes per detent."""
        n = abs(detents)
        return 1 if n <= 1 else (5 if n <= 3 else 15)

    def _handle_crown(self):
        if self.crown:
            ev = self.crown.poll()
            if ev == "click":
                if self.setting:
                    self._push_crown()
                else:
                    self._pull_crown()
            elif ev == "long" and self.setting:
                self._cancel()
        if self.encoder:
            d = self.encoder.take()
            if d and self.setting:
                self.set_minutes = (self.set_minutes + d * self._step(d)) % 1440

    # ---- lifecycle ----
    def enter(self):
        if not self._pivots_set:
            for name, (x, y) in PIVOTS.items():
                eezui.set_pivot(name, x, y)
            self._pivots_set = True
        self.update()

    async def run(self):
        # Poll quickly so the beat lines up with the RTC's second boundary and
        # the crown feels immediate; hands redraw only when their angle changes.
        while True:
            self._handle_crown()
            self.update()
            await asyncio.sleep_ms(POLL_MS)
