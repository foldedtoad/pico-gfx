#!/usr/bin/env bash
# tools/build_fw.sh - build MicroPython + LVGL + eezui firmware for the Pico 2
#
# Usage (from anywhere):   ~/micropython_projects/pico-gfx/tools/build_fw.sh
# Output:                  firmware/pico-gfx.uf2   and   build.log
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIND="$ROOT/firmware/lvgl_micropython"
EXT_CMAKE="$BIND/ext_mod/micropython.cmake"
MODULE="$ROOT/firmware/modules/eezui/micropython.cmake"

# 1. The rp2 build in lvgl_micropython ignores USER_C_MODULE on the command
#    line, so add a hook that includes our module when EEZUI_MODULE is set.
#    Idempotent: re-added automatically after a submodule reset.
if ! grep -q 'EEZUI_MODULE' "$EXT_CMAKE"; then
    printf '\n# pico-gfx hook (added by tools/build_fw.sh)\nif(DEFINED ENV{EEZUI_MODULE})\n    include($ENV{EEZUI_MODULE})\nendif()\n' >> "$EXT_CMAKE"
    echo "Added EEZUI_MODULE hook to $EXT_CMAKE"
fi

# 2. Sanity check: EEZ output must be in place.
if [ ! -f "$ROOT/firmware/modules/eezui/ui/ui.c" ]; then
    echo "ERROR: firmware/modules/eezui/ui/ui.c not found - build the EEZ project first." >&2
    exit 1
fi

# 3. Build.
export EEZUI_MODULE="$MODULE"
cd "$BIND"
python3 make.py rp2 BOARD=RPI_PICO2 DISPLAY=gc9a01 "$@" 2>&1 | tee "$ROOT/build.log"

# 4. Copy the result somewhere stable.
UF2="$BIND/build/lvgl_micropy_RPI_PICO2.uf2"
if [ -f "$UF2" ]; then
    cp "$UF2" "$ROOT/firmware/pico-gfx.uf2"
    echo
    echo "Firmware: $ROOT/firmware/pico-gfx.uf2"
    grep -q "usermod_eezui" "$ROOT/build.log" && echo "eezui module: included" \
        || echo "WARNING: 'usermod_eezui' not seen in build.log - check the hook"
fi
