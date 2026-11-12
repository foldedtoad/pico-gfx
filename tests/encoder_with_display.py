# encoder_with_display.py - does the encoder still count once the display,
# LVGL and its task handler are running? (isolates display vs. app logic)
#   mpremote run tests/encoder_with_display.py      turn the knob; Ctrl-C to stop
# Needs hw.py and encoder.py on the board (tools/deploy.py puts them there).

import time
import hw
from encoder import RotaryEncoder, Button

STAGES = ("before display", "after hw.start()")
enc = None


def watch_encoder(label, seconds=10):
    print("\n[%s] turn the knob a few clicks within %d s..." % (label, seconds))
    r0 = enc._raw()
    t_end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    total = 0
    while time.ticks_diff(t_end, time.ticks_ms()) > 0:
        d = enc.take()
        if d:
            total += d
            print("   detents %+d   total %+d" % (d, total))
        time.sleep_ms(40)
    print("   PIO raw step count: %d -> %d, net clicks %+d" % (r0, enc._raw(), total))


enc = RotaryEncoder(18, 19, steps_per_detent=4)
try:
    watch_encoder(STAGES[0])
    hw.start()
    print("display + LVGL + task handler running")
    watch_encoder(STAGES[1])
except KeyboardInterrupt:
    pass
finally:
    enc.deinit()
    hw.stop()            # hard reset (LVGL cannot restart after a soft reboot)
