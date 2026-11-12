# pin_owner.py - which peripheral owns each GPIO, before and after the display
# starts? Reads the RP2350 IO_BANK0 FUNCSEL fields directly.
#   mpremote run tests/pin_owner.py
import sys
import machine

BASE = 0x40028000 if "RP2350" in sys.implementation._machine else 0x40014000
NAMES = {0: "JTAG/HSTX", 1: "SPI", 2: "UART", 3: "I2C", 4: "PWM", 5: "SIO(gpio)",
         6: "PIO0", 7: "PIO1", 8: "PIO2", 9: "QMI/clk", 10: "USB", 11: "UART-aux",
         0x1F: "none"}
PINS = {6: "display SCK", 7: "display MOSI", 16: "MISO (reserved)", 17: "SPI0 CSn default",
        18: "encoder CLK", 19: "encoder DT", 20: "free", 21: "free", 22: "free",
        28: "encoder SW"}


def funcsel(gpio):
    return machine.mem32[BASE + 4 + 8 * gpio] & 0x1F


def snapshot():
    return {g: funcsel(g) for g in PINS}


before = snapshot()
from encoder import RotaryEncoder             # claims 18/19 for PIO 2
enc = RotaryEncoder(18, 19)
with_enc = snapshot()
import hw
hw.start()
after = snapshot()

print("GPIO  role                 before   +encoder   +display")
for g, role in PINS.items():
    flag = "   <-- changed by display" if after[g] != with_enc[g] else ""
    print("GP%-3d %-20s %-9s %-10s %-10s%s" % (g, role, NAMES.get(before[g], before[g]),
          NAMES.get(with_enc[g], with_enc[g]), NAMES.get(after[g], after[g]), flag))
enc.deinit()
hw.stop()
