#!/usr/bin/env bash
# Real NeXium guest window probe; preserves failure receipts for GitHub Actions.
# This launcher is exercised with mock executables in CI before emulator use.
set -euo pipefail

: "${NEXIUM_BIN:?NeXium executable path is required}"
: "${NEXIUM_WINDOW_ATTEMPTS:=45}"
: "${NEXIUM_POLL_DELAY_SECONDS:=1}"
: "${NEXIUM_SETTLE_DELAY_SECONDS:=12}"
for config_value in "$NEXIUM_WINDOW_ATTEMPTS" "$NEXIUM_POLL_DELAY_SECONDS" "$NEXIUM_SETTLE_DELAY_SECONDS"; do
  if ! [[ "$config_value" =~ ^[0-9]+$ ]]; then
    echo 'Invalid runtime timing parameter (integer seconds required)' >&2
    exit 4
  fi
done
if (( NEXIUM_WINDOW_ATTEMPTS < 1 || NEXIUM_WINDOW_ATTEMPTS > 60 || NEXIUM_POLL_DELAY_SECONDS > 10 || NEXIUM_SETTLE_DELAY_SECONDS > 60 )); then
  echo 'Runtime timing parameter out of range' >&2
  exit 4
fi

test -s nros/vh_saturn_demo.nro
mkdir -p runtime-evidence
record_failure() {
  printf '%s\n' "$1" >runtime-evidence/failure-reason.txt
  printf 'VH_EMU_FAILURE reason=%s\n' "$1" >&2
}

"$NEXIUM_BIN" nros/vh_saturn_demo.nro >runtime-evidence/nexium.log 2>&1 &
emu_pid=$!
trap 'kill "$emu_pid" 2>/dev/null || true; wait "$emu_pid" 2>/dev/null || true' EXIT

window=''
for ((attempt=1; attempt<=NEXIUM_WINDOW_ATTEMPTS; attempt++)); do
  sleep "$NEXIUM_POLL_DELAY_SECONDS"
  window="$(xdotool search --onlyvisible --name NeXium 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
  if ! kill -0 "$emu_pid" 2>/dev/null; then
    record_failure 'emulator_terminated_before_window'
    cat runtime-evidence/nexium.log >&2
    exit 1
  fi
done
if [[ -z "$window" ]]; then
  record_failure 'window_not_found'
  exit 1
fi

sleep "$NEXIUM_SETTLE_DELAY_SECONDS"
if ! kill -0 "$emu_pid" 2>/dev/null; then
  record_failure 'emulator_terminated_before_capture'
  cat runtime-evidence/nexium.log >&2
  exit 1
fi
if ! import -window "$window" runtime-evidence/nexium-window.png; then
  record_failure 'window_capture_command_failed'
  exit 1
fi
if [[ ! -s runtime-evidence/nexium-window.png ]]; then
  record_failure 'window_capture_empty'
  exit 1
fi
printf 'captured_window_id=%s\n' "$window" >runtime-evidence/capture-status.txt
printf '%s\n' 'VH_EMU_CAPTURE screenshot=ready' >&2

# Optional input probe, not part of the boot-success criterion. In some NeXium
# builds X11 window keys may be handled by emulator UI rather than the guest.
# Save evidence for independent review instead of claiming control success.
if xdotool windowactivate --sync "$window" 2>/dev/null && \
   xdotool key --clearmodifiers --window "$window" Right 2>/dev/null; then
  sleep 1
  if import -window "$window" runtime-evidence/nexium-after-right.png && \
     [[ -s runtime-evidence/nexium-after-right.png ]]; then
    printf '%s\n' 'input_attempted=Right screenshot=ready' >runtime-evidence/input-probe-status.txt
  else
    printf '%s\n' 'input_attempted=Right screenshot=failed' >runtime-evidence/input-probe-status.txt
  fi
else
  printf '%s\n' 'input_attempted=Right dispatch=failed' >runtime-evidence/input-probe-status.txt
fi
