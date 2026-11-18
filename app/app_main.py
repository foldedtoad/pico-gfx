# app_main.py - the application. Started by main.py at power-on, or by hand:
#   mpremote run app/app_main.py
#
# Any exit (Ctrl-C, crash) blanks the display and hard-resets the board;
# the next boot stays at the REPL (see main.py). Crashes are logged to
# /crash.log on the board:   mpremote cat :crash.log

import sys
import gc
import time
import asyncio
import hw

DEBUG_STATS_S = 10                                 # 0 = no periodic stats

# KY-040 rotary encoder = the watch crown (check with tests/encoder_test.py)
ENCODER_CLK, ENCODER_DT, ENCODER_SW = 18, 19, 28   # DT must be CLK + 1 (PIO pin pair)
ENCODER_STEPS = 4                                  # raw steps per click (4 or 2)
ENCODER_REVERSE = False                            # True if clockwise counts down


async def housekeeping():
    """App-wide background task: GC and, optionally, a stats line."""
    import machine
    temp = machine.ADC(4)                          # on-chip temperature sensor
    n = 0
    while True:
        await asyncio.sleep(1)
        gc.collect()
        n += 1
        if DEBUG_STATS_S and n % DEBUG_STATS_S == 0:
            volts = temp.read_u16() * 3.3 / 65535
            celsius = 27 - (volts - 0.706) / 0.001721   # approximate
            print("stats: free heap %d B, chip %.1f C" % (gc.mem_free(), celsius))


def _log_crash(exc):
    try:
        with open("/crash.log", "a") as f:
            f.write("--- crash at ticks_ms %d ---\n" % time.ticks_ms())
            sys.print_exception(exc, f)
    except Exception:
        pass


def run():
    from timekeeper import Timekeeper
    tk = Timekeeper()                              # DS3231 backup clock, if fitted
    tk.sync_at_boot()                              # correct time before the first frame

    hw.start(backlight=0)                          # dark until the dial is drawn

    from ui import App
    from screens.watch import WatchScreen
    from encoder import RotaryEncoder, Button
    import lvgl as lv

    app = App()
    app.encoder = RotaryEncoder(ENCODER_CLK, ENCODER_DT,
                                steps_per_detent=ENCODER_STEPS, reverse=ENCODER_REVERSE)
    app.crown = Button(ENCODER_SW)
    app.timekeeper = tk
    app.add("watch", WatchScreen)                  # screens pick up app.encoder / app.crown
    app.start("watch")

    lv.refr_now(None)                              # draw the first frame now...
    hw.backlight(100)                              # ...then light it up

    gc.collect()
    print("app running - free heap:", gc.mem_free())

    try:
        asyncio.run(app.run_forever(housekeeping(), tk.resync_forever()))
    except KeyboardInterrupt:
        print("\napp stopped (Ctrl-C)")
    except Exception as e:
        print("\napp crashed:")
        sys.print_exception(e)
        _log_crash(e)
    finally:
        hw.stop()                                  # hard reset; next boot -> REPL


if __name__ == "__main__":
    run()
