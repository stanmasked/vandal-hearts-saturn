#!/usr/bin/env bash
# Real NeXium GUI capture. All receipts are observations, not simulated success.
set -euo pipefail

: "${NEXIUM_BIN:?NeXium executable path required}"
: "${NEXIUM_WINDOW_ATTEMPTS:=45}"
: "${NEXIUM_POLL_DELAY_SECONDS:=1}"
: "${NEXIUM_SETTLE_DELAY_SECONDS:=12}"
: "${NEXIUM_CLOSE_WAIT_SECONDS:=8}"
for value in "$NEXIUM_WINDOW_ATTEMPTS" "$NEXIUM_POLL_DELAY_SECONDS" \
             "$NEXIUM_SETTLE_DELAY_SECONDS" "$NEXIUM_CLOSE_WAIT_SECONDS"; do
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    echo 'Invalid runtime timing parameter (integer seconds required)' >&2
    exit 4
  fi
done
if (( NEXIUM_WINDOW_ATTEMPTS < 1 || NEXIUM_WINDOW_ATTEMPTS > 60 ||
      NEXIUM_POLL_DELAY_SECONDS > 10 || NEXIUM_SETTLE_DELAY_SECONDS > 60 ||
      NEXIUM_CLOSE_WAIT_SECONDS < 1 || NEXIUM_CLOSE_WAIT_SECONDS > 30 )); then
  echo 'Runtime timing parameter out of range' >&2
  exit 4
fi

test -s nros/vh_saturn_demo.nro
mkdir -p runtime-evidence
record_failure() {
  printf '%s\n' "$1" >runtime-evidence/failure-reason.txt
  printf 'VH_EMU_FAILURE reason=%s\n' "$1" >&2
}

if ! command -v ffmpeg >/dev/null 2>&1; then
  record_failure 'ffmpeg_unavailable'
  exit 1
fi

"$NEXIUM_BIN" nros/vh_saturn_demo.nro >runtime-evidence/nexium.log 2>&1 &
emu_pid=$!
cleanup() {
  if kill -0 "$emu_pid" 2>/dev/null; then
    kill -TERM "$emu_pid" 2>/dev/null || true
    wait "$emu_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
window=''
for ((attempt=1; attempt<=NEXIUM_WINDOW_ATTEMPTS; ++attempt)); do
  sleep "$NEXIUM_POLL_DELAY_SECONDS"
  window="$(xdotool search --onlyvisible --name NeXium 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
  if ! kill -0 "$emu_pid" 2>/dev/null; then
    record_failure 'emulator_terminated_before_window'
    cat runtime-evidence/nexium.log >&2
    exit 1
  fi
done
if [[ -z "$window" ]]; then record_failure 'window_not_found'; exit 1; fi
sleep "$NEXIUM_SETTLE_DELAY_SECONDS"
if ! kill -0 "$emu_pid" 2>/dev/null; then
  record_failure 'emulator_terminated_before_capture'
  cat runtime-evidence/nexium.log >&2
  exit 1
fi
geometry="$(xdotool getwindowgeometry --shell "$window")" || {
  record_failure 'window_geometry_unavailable'
  exit 1
}
width="$(printf '%s\n' "$geometry" | sed -n 's/^WIDTH=//p')"
height="$(printf '%s\n' "$geometry" | sed -n 's/^HEIGHT=//p')"
if ! [[ "$width" =~ ^[1-9][0-9]*$ && "$height" =~ ^[1-9][0-9]*$ ]]; then
  record_failure 'window_geometry_invalid'
  exit 1
fi
if ! timeout --kill-after=2s 15s ffmpeg -hide_banner -loglevel error -y \
    -f x11grab -window_id "$window" -video_size "${width}x${height}" \
    -framerate 1 -draw_mouse 0 -i "$DISPLAY" \
    -frames:v 1 -update 1 runtime-evidence/nexium-window.png; then
  record_failure 'window_capture_command_failed'
  exit 1
fi
if [[ ! -s runtime-evidence/nexium-window.png ]]; then
  record_failure 'window_capture_empty'
  exit 1
fi
printf 'captured_window_id=%s\n' "$window" >runtime-evidence/capture-status.txt
printf '%s\n' 'VH_EMU_CAPTURE screenshot=ready' >&2

# Try Right at most twice; a second attempt is permitted only when the first
# actual screenshot fails to demonstrate cursor movement. The guest visual CI
# gate remains authoritative and can still reject an unresponsive cursor.
input_helper="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/nexium_right_probe.sh"
if ! bash "$input_helper" "$window"; then
  printf '%s\n' 'input_attempted=Right helper=failed' >runtime-evidence/input-probe-status.txt
fi

# Optional Stage40 real tactical trace; the strict independent workflow gate
# checks actual screenshot pixels and rejects an unsuccessful action sequence.
if [[ "${NEXIUM_ACTION_PROBE:-0}" == "1" ]]; then
  if python3 -m tools.nexium_tactical_action --window "$window" --folder runtime-evidence; then
    if [[ "${NEXIUM_POST_MOVE_PROBE:-0}" == "1" ]]; then
      if ! python3 -m tools.nexium_post_move --window "$window" --folder runtime-evidence; then
        printf '%s\n' 'post_move=unverified' >runtime-evidence/post-move-probe-status.txt
      fi
    fi
  else
    printf '%s\n' 'tactical_action=unverified' >runtime-evidence/action-probe-status.txt
    # Do not attempt follow-on actions without genuine observed Scout movement.
  fi
fi

# Stage44 uses a distinct ROM-free NRO in a separate Xvfb working folder.
# Only the actual guest PNG plus a decoded host checksum can pass its gate.
if [[ "${NEXIUM_ATTACK_PROBE:-0}" == "1" ]]; then
  if python3 -m tools.nexium_attack_action --window "$window" --folder runtime-evidence; then
    # Never run follow-on actions when the first real guest attack failed.
    if [[ "${NEXIUM_RESELECT_PROBE:-0}" == "1" ]]; then
      if python3 -m tools.nexium_duel_reselect --window "$window" --folder runtime-evidence; then
        # Stage48 only continues from a real validated Stage45 re-selection.
        if [[ "${NEXIUM_SECOND_ROUND_PROBE:-0}" == "1" ]]; then
          if python3 -m tools.nexium_second_round --window "$window" --folder runtime-evidence; then
            # Stage50 only begins after the complete real Stage48 duel.
            if [[ "${NEXIUM_VICTORY_PROBE:-0}" == "1" ]]; then
              if ! python3 -m tools.nexium_duel_victory --window "$window" --folder runtime-evidence; then
                printf '%s\n' 'victory=unverified' >runtime-evidence/victory-probe-status.txt
              fi
            fi
          else
            printf '%s\n' 'round2=unverified' >runtime-evidence/round2-probe-status.txt
          fi
        fi
      else
        printf '%s\n' 'duel_reselect=unverified' >runtime-evidence/reselect-probe-status.txt
      fi
    fi
  else
    printf '%s\n' 'attack=unverified' >runtime-evidence/attack-probe-status.txt
  fi
fi

# Stage52: a separate unmodified ROM-free duel NRO instance. This route
# intentionally skips all player attacks until the Raider defeats Scout.
# Do not couple its acceptance to the independent Stage50 victory session.
if [[ "${NEXIUM_DEFEAT_PROBE:-0}" == "1" ]]; then
  if ! python3 -m tools.nexium_duel_defeat --window "$window" --folder runtime-evidence; then
    printf '%s\n' 'defeat=unverified' >runtime-evidence/defeat-probe-status.txt
  fi
fi

# This snapshot predates the shutdown request. A panic observed here cannot be
# explained by a subsequent Xvfb/WM_DELETE teardown.
cp runtime-evidence/nexium.log runtime-evidence/nexium-log-before-close.log
printf '%s\n' 'capture_done shutdown_requested' >runtime-evidence/lifecycle-status.txt
if ! kill -0 "$emu_pid" 2>/dev/null; then
  record_failure 'emulator_terminated_before_shutdown'
  exit 1
fi

# Check the X11 WM_DELETE_WINDOW protocol first. Do not destroy a live
# winit-owned window when it lacks this protocol; fail the stability gate.
close_helper="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/nexium_x11_close.sh"
if bash "$close_helper" "$window"; then
  printf '%s\n' 'windowclose_sent' >>runtime-evidence/lifecycle-status.txt
  printf '%s\n' 'close_method=EWMH' >>runtime-evidence/lifecycle-status.txt
else
  printf '%s\n' 'windowclose_unavailable' >>runtime-evidence/lifecycle-status.txt
fi
for ((second=0; second<NEXIUM_CLOSE_WAIT_SECONDS; ++second)); do
  if ! kill -0 "$emu_pid" 2>/dev/null; then break; fi
  sleep 1
done
forced=0
if kill -0 "$emu_pid" 2>/dev/null; then
  forced=1
  printf '%s\n' 'forced_sigterm' >>runtime-evidence/lifecycle-status.txt
  kill -TERM "$emu_pid" 2>/dev/null || true
  # Do not leave a guest process running when xvfb-run tears down the X server.
  for ((second=0; second<3; ++second)); do
    if ! kill -0 "$emu_pid" 2>/dev/null; then break; fi
    sleep 1
  done
  if kill -0 "$emu_pid" 2>/dev/null; then
    printf '%s\n' 'forced_sigkill' >>runtime-evidence/lifecycle-status.txt
    kill -KILL "$emu_pid" 2>/dev/null || true
  fi
fi
if wait "$emu_pid"; then
  exit_code=0
else
  exit_code=$?
fi
trap - EXIT
printf 'emulator_exit_code=%s\n' "$exit_code" >>runtime-evidence/lifecycle-status.txt
if (( forced != 0 )); then
  record_failure 'forced_termination_after_capture'
  exit 1
fi
if (( exit_code != 0 )); then
  record_failure 'emulator_nonzero_exit_after_capture'
  exit 1
fi
printf '%s\n' 'VH_EMU_LIFECYCLE close=complete' >&2
