# button_test.py - physical button -> EEZ button -> EEZ action -> Python
#
# Needs firmware rebuilt after adding btn_press + action "on_press" in EEZ.
#   mpremote cp app/hw.py :hw.py
#   mpremote run app/button_test.py     (press the button; Ctrl-C to stop)

import time
import gc
import hw

hw.start()
hw.add_button(22)                  # must come before eezui.init()

import eezui

presses = 0


def on_action(name):
    # Runs via the MicroPython scheduler, not inside LVGL's event handler
    global presses
    if name == "on_press":
        presses += 1
        eezui.set_var("status_text", "Pressed %d" % presses)
        print("action:", name, presses)
    else:
        print("unhandled action:", name)


eezui.on_action(on_action)
eezui.set_var("status_text", "Press the button")
eezui.init()
eezui.load_screen(eezui.SCREEN_MAIN)

gc.collect()
print("ready - free heap:", gc.mem_free())

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nCtrl-C received")
finally:
    hw.stop()
