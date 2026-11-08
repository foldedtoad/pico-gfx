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

BUTTONS = {28: "PREV", 22: "ENTER", 18: "NEXT"}   # left, middle, right
DEBUG_STATS_S = 10                                 # 0 = no periodic stats


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
    hw.start()
    hw.add_buttons(BUTTONS)                        # before the UI is created

    from ui import App
    from screens.counter import CounterScreen
    from screens.watch import WatchScreen

    app = App()
    app.add("watch", WatchScreen)
    app.add("counter", CounterScreen)        # kept for testing; not reachable yet
    app.start("watch")

    gc.collect()
    print("app running - free heap:", gc.mem_free())

    try:
        asyncio.run(app.run_forever(housekeeping()))
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
