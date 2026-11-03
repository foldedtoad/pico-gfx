# nav_test.py - three-button navigation: PREV / ENTER / NEXT
#
# Switches (left to right): GP28 = PREV, GP22 = ENTER, GP18 = NEXT
# EEZ screen: lbl_status + buttons btn_minus (on_minus), btn_press (on_press),
#             btn_plus (on_plus), created in that order.
#
#   mpremote cp app/hw.py :hw.py
#   mpremote run app/nav_test.py      (Ctrl-C to stop; board then resets)

import time
import gc
import hw

hw.start()
group = hw.add_buttons({28: "PREV", 22: "ENTER", 18: "NEXT"})   # before eezui.init()

import eezui

value = 0


def show():
    eezui.set_var("status_text", "Value: %d" % value)


def on_action(name):
    global value
    if name == "on_minus":
        value -= 1
    elif name == "on_plus":
        value += 1
    elif name == "on_press":          # middle on-screen button = reset
        value = 0
    else:
        print("unhandled action:", name)
        return
    print(name, "->", value)
    show()


eezui.on_action(on_action)
show()
eezui.init()
eezui.load_screen(eezui.SCREEN_MAIN)

gc.collect()
print("focusable widgets in group:", group.get_obj_count(), "(expect 3)")
print("ready - free heap:", gc.mem_free())
print("Left/right switches move focus, middle switch clicks.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nCtrl-C received")
finally:
    hw.stop()
