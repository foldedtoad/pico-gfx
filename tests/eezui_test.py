# eezui_test.py - first EEZ Studio screen on the Pico 2
# Needs: firmware built with tools/build_fw.sh, and hw.py copied to the board.
#
#   mpremote cp app/hw.py :hw.py
#   mpremote run app/eezui_test.py          (Ctrl-C to stop; board then resets)

import time
import gc
import hw

hw.start()

import eezui

eezui.set_var("status_text", "Hello from Python")
eezui.init()                         # builds EEZ screens and loads Main
eezui.load_screen(eezui.SCREEN_MAIN)

gc.collect()
print("eezui running - free heap:", gc.mem_free())
print("status_text =", eezui.get_var("status_text"))

n = 0
try:
    while True:
        time.sleep(1)
        n += 1
        eezui.set_var("status_text", "Count: %d" % n)   # label follows within ~40 ms
except KeyboardInterrupt:
    print("\nCtrl-C received")
finally:
    hw.stop()
