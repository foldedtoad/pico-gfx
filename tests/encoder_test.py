# encoder_test.py - check the KY-040 wiring, direction and steps per click
# (no LVGL; any firmware). Needs app/encoder.py on the board:
#   mpremote cp app/encoder.py :encoder.py
#   mpremote run tests/encoder_test.py        Ctrl-C to stop
#
# Turn ONE click clockwise: expect exactly one "detents +1", printed as the
# knob settles into the click. Counter-clockwise: "detents -1".
#   - shows -1 for clockwise  -> set ENCODER_REVERSE = True in app_main.py
#   - only every 2nd click counts, or 2 per click -> try ENCODER_STEPS = 2

import time
from encoder import RotaryEncoder, Button

STEPS = 4
enc = RotaryEncoder(clk=18, dt=19, steps_per_detent=STEPS)
btn = Button(28)

print("CLK GP18 / DT GP19 / SW GP28 - turn the knob and press it. Ctrl-C to stop.")
print("idle levels: CLK=%d DT=%d SW=%d (expect 1 1 1, or 0 0 1 at some detents)"
      % (enc._clk.value(), enc._dt.value(), btn._p.value()))
pos = 0
try:
    while True:
        d = enc.take()
        if d:
            pos += d
            print("detents %+d   position %d" % (d, pos))
        ev = btn.poll()
        if ev:
            print("button:", ev)
        time.sleep_ms(20)
except KeyboardInterrupt:
    enc.deinit()
    print("done")
