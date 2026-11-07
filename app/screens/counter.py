# screens/counter.py - the Main EEZ screen: "-" / Reset / "+" counter
#
# EEZ: lbl_status (Text = variable status_text)
#      btn_minus -> on_minus, btn_press -> on_press, btn_plus -> on_plus

import asyncio
import eezui
from ui import Screen

IDLE_RESET_S = 30          # reset the value after this long without input


class CounterScreen(Screen):
    screen_id = eezui.SCREEN_MAIN

    def __init__(self, app):
        super().__init__(app)
        self.value = 0
        self.idle = 0

    def show(self):
        self.set("status_text", "Value: %d" % self.value)

    # ---- lifecycle ----
    def enter(self):
        self.show()

    async def run(self):
        # Background task while this screen is active: idle auto-reset.
        while True:
            await asyncio.sleep(1)
            self.idle += 1
            if self.idle == IDLE_RESET_S and self.value != 0:
                self.value = 0
                self.show()
                print("counter: idle reset")

    # ---- EEZ actions ----
    def on_minus(self):
        self.idle = 0
        self.value -= 1
        self.show()

    def on_plus(self):
        self.idle = 0
        self.value += 1
        self.show()

    def on_press(self):          # middle on-screen button = Reset
        self.idle = 0
        self.value = 0
        self.show()
