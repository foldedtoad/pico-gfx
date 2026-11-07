# main.py - runs automatically at power-on.
#
# Stays at the REPL instead of starting the app when:
#   * the previous run was stopped (Ctrl-C, mpremote, crash) - one boot only
#   * the middle button (GP22) is held during power-up / reset
# A power cycle always starts the app again.

import machine
import hw

SAFE_BOOT_PIN = 22


def _autostart_allowed():
    if hw.skip_autostart_requested():
        print("main.py: app was stopped last time - staying at REPL.")
        print("         machine.reset() or power-cycle to start it again.")
        return False
    if machine.Pin(SAFE_BOOT_PIN, machine.Pin.IN, machine.Pin.PULL_UP).value() == 0:
        print("main.py: middle button held - safe boot, staying at REPL.")
        return False
    return True


if _autostart_allowed():
    import app_main
    app_main.run()
