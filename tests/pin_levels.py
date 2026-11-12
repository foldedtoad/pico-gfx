# pin_levels.py - do CLK/DT still change after the display starts?
# Prints live pin levels and pad settings while you turn the knob.
#   mpremote run tests/pin_levels.py
import sys
import time
import machine
from machine import Pin

RP2350 = "RP2350" in sys.implementation._machine
PADS = 0x40038000 if RP2350 else 0x4001C000
PINS = (18, 19, 28)
for g in PINS:
    Pin(g, Pin.IN, Pin.PULL_UP)


def pad(g):
    v = machine.mem32[PADS + 4 + 4 * g]
    return "IE=%d PUE=%d PDE=%d OD=%d%s" % ((v >> 6) & 1, (v >> 3) & 1, (v >> 2) & 1,
                                           (v >> 7) & 1, (" ISO=%d" % ((v >> 8) & 1)) if RP2350 else "")


def watch(label, seconds=8):
    print("\n[%s] turn the knob slowly for %d s" % (label, seconds))
    for g in PINS:
        print("   GP%d pad: %s" % (g, pad(g)))
    pins = [Pin(g) for g in PINS]
    seen = set()
    changes = 0
    last = None
    t_end = time.ticks_add(time.ticks_ms(), seconds * 1000)
    while time.ticks_diff(t_end, time.ticks_ms()) > 0:
        lv = tuple(p.value() for p in pins)
        if lv != last:
            changes += 1
            seen.add(lv[:2])
            last = lv
        time.sleep_ms(2)
    print("   CLK/DT states seen: %s   changes: %d" % (sorted(seen), changes))
    print("   -> %s" % ("pins respond to the knob" if len(seen) >= 3
                         else "pins STUCK - not following the knob"))


watch("without display")
import hw
hw.start()
watch("display running")
hw.stop()
