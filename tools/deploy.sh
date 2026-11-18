#!/usr/bin/env bash
# tools/deploy.sh - copy the app to the Pico 2.
#
#   tools/deploy.sh          copy files, leave the board at the REPL
#   tools/deploy.sh --run    copy files, then reset so main.py starts the app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/app"
MP="mpremote"

# If the app is running, this first connection stops it: the board hard-resets
# and comes back at the REPL (skip-autostart flag). Give USB time to return.
echo "Connecting (stops the app if it is running)..."
if ! $MP exec "pass" >/dev/null 2>&1; then
    sleep 3
fi

$MP mkdir :screens >/dev/null 2>&1 || true

$MP cp "$APP/hw.py" "$APP/ui.py" "$APP/encoder.py" "$APP/ds3231.py" "$APP/timekeeper.py" "$APP/app_main.py" "$APP/main.py" : \
  + cp "$APP"/screens/*.py :screens/

echo "Files on board:"
$MP ls : + ls :screens

if [ "${1:-}" = "--run" ]; then
    echo "Resetting - app starts via main.py. Ctrl-C in 'mpremote repl' stops it."
    $MP reset
fi
