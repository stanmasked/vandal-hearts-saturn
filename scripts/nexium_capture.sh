#!/usr/bin/env bash
# Stage 22: launch the actual NeXium guest under Xvfb and capture evidence.
# Use a standalone launcher so Bash syntax is checked in isolation.
set -euo pipefail

: "${NEXIUM_BIN:?NeXium executable path is required}"
test -s nros/vh_saturn_demo.nro
mkdir -p runtime-evidence

"${NEXIUM_BIN}" nros/vh_saturn_demo.nro >runtime-evidence/nexium.log 2>&1 &
emu_pid=$!
trap 'kill "$emu_pid" 2>/dev/null || true' EXIT

window=""
for attempt in $(seq 1 45); do
  sleep 1
  window="$(xdotool search --onlyvisible --name NeXium 2>/dev/null | tail -n 1 || true)"
  if [ -n "$window" ]; then
    break
  fi
  if ! kill -0 "$emu_pid" 2>/dev/null; then
    cat runtime-evidence/nexium.log
    printf '%s\n' 'Emulator exited before a visible window was created' >&2
    printf '%s\n' 'emulator_terminated_before_window' >runtime-evidence/failure-reason.txt
    exit 1
  fi
done

if [ -z "$window" ]; then
  printf '%s\n' 'NeXium window not found within 45 seconds' >&2
  printf '%s\n' 'window_not_found' >runtime-evidence/failure-reason.txt
  exit 1
fi

sleep 12
if ! kill -0 "$emu_pid" 2>/dev/null; then
  cat runtime-evidence/nexium.log
  printf '%s\n' 'NeXium process exited before screenshot capture' >&2
  printf '%s\n' 'emulator_terminated_before_capture' >runtime-evidence/failure-reason.txt
  exit 1
fi
import -window "$window" runtime-evidence/nexium-window.png
test -s runtime-evidence/nexium-window.png
printf 'captured_window_id=%s\n' "$window" >runtime-evidence/capture-status.txt
