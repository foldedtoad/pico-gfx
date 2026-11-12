#!/usr/bin/env python3
"""tools/deploy.py - copy the pico-gfx app to the Pico 2 without mpremote.

Talks to MicroPython's raw REPL over USB serial; needs only pyserial:
    pip install pyserial            (or: sudo apt install python3-serial)

Usage:
    python3 tools/deploy.py              copy files, leave board at the REPL
    python3 tools/deploy.py --run        copy files, then reset to start the app
    python3 tools/deploy.py --port /dev/ttyACM0

Thonny users: click Run > Disconnect in Thonny first (only one program can
use the serial port), then reconnect Thonny with the Stop/Restart button.

Files copied (same set as tools/deploy.sh):
    app/hw.py app/ui.py app/encoder.py app/app_main.py app/main.py  ->  /
    app/screens/*.py                                ->  /screens/
"""

import argparse
import glob
import os
import sys
import time

try:
    import termios                      # POSIX: a vanished port raises termios.error
    _PORT_GONE = (OSError, termios.error)
except ImportError:                     # Windows
    _PORT_GONE = (OSError,)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pyserial is required:  pip install pyserial   (or apt install python3-serial)")

# Every way a port can fail while the board resets or is unplugged
PORT_ERRORS = (serial.SerialException,) + _PORT_GONE


class DeployError(Exception):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
TOP_FILES = ["hw.py", "ui.py", "encoder.py", "app_main.py", "main.py"]
PICO_VID = 0x2E8A                     # Raspberry Pi
CHUNK = 256


# ---------------------------------------------------------------------------
# serial / raw REPL
# ---------------------------------------------------------------------------

def find_port():
    for p in serial.tools.list_ports.comports():
        if p.vid == PICO_VID:
            return p.device
    return None


def open_port(port, wait_s=10):
    """Open the port, waiting for it to (re)appear after a board reset."""
    deadline = time.time() + wait_s
    while True:
        dev = port or find_port()
        if dev:
            try:
                return serial.Serial(dev, 115200, timeout=0.2)
            except PORT_ERRORS:
                pass
        if time.time() > deadline:
            raise DeployError("No Pico found%s. Is it plugged in, and is Thonny disconnected?"
                              % (" on " + port if port else ""))
        time.sleep(0.3)


def read_until(ser, ending, timeout=5):
    data = b""
    deadline = time.time() + timeout
    while not data.endswith(ending):
        chunk = ser.read(1)
        if chunk:
            data += chunk
        elif time.time() > deadline:
            raise TimeoutError("waiting for %r, got %r" % (ending, data[-80:]))
    return data


class Board:
    def __init__(self, port):
        self.port = port
        self.ser = None

    def connect(self):
        """Stop whatever is running and enter the raw REPL.

        If the pico-gfx app is running, Ctrl-C makes it hard-reset the board
        (by design: LVGL cannot restart after a soft reboot). The USB port
        then disappears for ~1-2 s and the board comes back at the REPL, so
        losing the port here is expected: wait and reconnect."""
        for attempt in range(4):
            self.ser = open_port(self.port)
            try:
                self.ser.write(b"\r\x03\x03")          # interrupt anything running
                time.sleep(0.8)                        # let hw.stop() run if it will
                self.ser.reset_input_buffer()
                self.ser.write(b"\r\x01")              # Ctrl-A: raw REPL
                read_until(self.ser, b"raw REPL; CTRL-B to exit\r\n>", timeout=3)
                if attempt:
                    print("  reconnected.")
                return
            except PORT_ERRORS + (TimeoutError,):
                if attempt == 0:
                    print("  app stopped - board is resetting, waiting for it to come back...")
                else:
                    print("  still waiting (attempt %d)..." % (attempt + 1))
                try:
                    self.ser.close()
                except Exception:
                    pass
                time.sleep(2.5)
        raise DeployError(
            "The board did not come back to the REPL.\n"
            "  Try a safe boot: hold the encoder knob pressed, press reset (or\n"
            "  unplug/replug USB), release the knob, then run deploy.py again.")

    def exec(self, code, timeout=10):
        """Run code in the raw REPL; return stdout, raise on a device error."""
        self.ser.write(code.encode() + b"\x04")
        if read_until(self.ser, b"OK", timeout) [-2:] != b"OK":
            raise RuntimeError("raw REPL did not accept code")
        out = read_until(self.ser, b"\x04", timeout)[:-1]
        err = read_until(self.ser, b"\x04", timeout)[:-1]
        read_until(self.ser, b">", timeout)
        if err:
            raise RuntimeError(err.decode(errors="replace").strip())
        return out.decode(errors="replace")

    def mkdir(self, path):
        self.exec("import os\ntry:\n os.mkdir(%r)\nexcept OSError:\n pass" % path)

    def put(self, local, remote):
        with open(local, "rb") as f:
            data = f.read()
        self.exec("f=open(%r,'wb')\nw=f.write" % remote)
        for i in range(0, len(data), CHUNK):
            self.exec("w(%r)" % data[i:i + CHUNK])
        self.exec("f.close()")
        print("  %-28s -> %s (%d bytes)" % (os.path.relpath(local, ROOT), remote, len(data)))

    def listdir(self, path):
        return self.exec("import os\nprint(sorted(os.listdir(%r)))" % path).strip()

    def reset(self):
        try:
            self.ser.write(b"import machine\nmachine.reset()\x04")
            time.sleep(0.5)
        except PORT_ERRORS:
            pass                                       # port vanishes on reset: expected

    def close(self):
        try:
            self.ser.write(b"\x02")                    # Ctrl-B: back to normal REPL
            self.ser.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true", help="reset afterwards so main.py starts the app")
    ap.add_argument("--port", help="serial port (default: auto-detect the Pico)")
    ap.add_argument("--root", default="/", help="target folder on the board (default /)")
    args = ap.parse_args()
    root = args.root if args.root.endswith("/") else args.root + "/"

    files = [(os.path.join(APP, n), root + n) for n in TOP_FILES]
    files += [(p, root + "screens/" + os.path.basename(p))
              for p in sorted(glob.glob(os.path.join(APP, "screens", "*.py")))]
    missing = [l for l, _ in files if not os.path.exists(l)]
    if missing:
        raise DeployError("Missing files: " + ", ".join(missing))

    print("Connecting (stops the app if it is running)...")
    board = Board(args.port)
    board.connect()

    board.mkdir(root + "screens")
    for local, remote in files:
        board.put(local, remote)

    print("On board:  %-9s" % root, board.listdir(root))
    print("           %-9s" % (root + "screens"), board.listdir(root + "screens"))

    if args.run:
        print("Resetting - app starts via main.py.")
        board.reset()
    else:
        board.close()
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except DeployError as e:
        sys.exit("deploy.py: " + str(e))
    except PORT_ERRORS as e:
        sys.exit("deploy.py: lost the connection to the board (%s).\n"
                 "  Was it unplugged or reset mid-copy? Run deploy.py again." % e)
    except KeyboardInterrupt:
        sys.exit("deploy.py: cancelled.")
