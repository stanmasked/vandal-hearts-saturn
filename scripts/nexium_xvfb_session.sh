#!/usr/bin/env bash
# Run the NeXium launch/capture probe with a real X11 window manager alive.
# The Xvfb display is provided by the outer GitHub Actions xvfb-run command.
set -euo pipefail
: "${DISPLAY:?An Xvfb DISPLAY is required}"
: "${NEXIUM_WM_WAIT_ATTEMPTS:=40}"
: "${NEXIUM_WM_POLL_SECONDS:=0.1}"
if ! [[ "$NEXIUM_WM_WAIT_ATTEMPTS" =~ ^[0-9]+$ ]] ||
   (( NEXIUM_WM_WAIT_ATTEMPTS < 1 || NEXIUM_WM_WAIT_ATTEMPTS > 100 )); then
  echo 'Invalid window-manager readiness attempt limit' >&2
  exit 4
fi
mkdir -p runtime-evidence
openbox >runtime-evidence/window-manager.log 2>&1 &
wm_pid=$!
cleanup_wm() {
  local result=$?
  trap - EXIT
  local forced=0
  if kill -0 "$wm_pid" 2>/dev/null; then
    kill -TERM "$wm_pid" 2>/dev/null || true
    for ((n=0; n<20; n++)); do
      if ! kill -0 "$wm_pid" 2>/dev/null; then break; fi
      sleep 0.1
    done
    if kill -0 "$wm_pid" 2>/dev/null; then
      forced=1
      kill -KILL "$wm_pid" 2>/dev/null || true
    fi
  fi
  wait "$wm_pid" 2>/dev/null || true
  if (( forced == 1 )); then
    printf '%s\n' 'window_manager_forced_sigkill' >runtime-evidence/window-manager-shutdown.txt
    if (( result == 0 )); then result=1; fi
  else
    printf '%s\n' 'window_manager_reaped' >runtime-evidence/window-manager-shutdown.txt
  fi
  exit "$result"
}
trap cleanup_wm EXIT
ready=0
for ((i=0; i<NEXIUM_WM_WAIT_ATTEMPTS; i++)); do
  wm_description="$(timeout --kill-after=1s 2s wmctrl -m 2>/dev/null || true)"
  if [[ "$wm_description" == *'Name: Openbox'* ]]; then
    ready=1
    break
  fi
  if ! kill -0 "$wm_pid" 2>/dev/null; then
    echo 'Openbox terminated before window-manager readiness' >&2
    printf '%s\n' 'window_manager_terminated' >runtime-evidence/window-manager-failure.txt
    exit 1
  fi
  sleep "$NEXIUM_WM_POLL_SECONDS"
done
if (( ready == 0 )); then
  echo 'Timed out waiting for the Openbox X11 window manager' >&2
  printf '%s\n' 'window_manager_not_ready' >runtime-evidence/window-manager-failure.txt
  exit 1
fi
printf '%s\n' 'window_manager=Openbox ready=true' >runtime-evidence/window-manager-status.txt
# A normal WM allows xdotool windowclose to deliver WM_DELETE_WINDOW rather than
# destroying a raw X11 window while winit is still managing it.
# Keep the WM alive until the actual emulator capture and graceful close finish.
# If the WM unexpectedly dies during the guest session, do not call it stable.
guest_status=0
bash scripts/nexium_capture.sh || guest_status=$?
if ! kill -0 "$wm_pid" 2>/dev/null; then
  printf '%s\n' 'window_manager_died_during_capture' >runtime-evidence/window-manager-failure.txt
  if (( guest_status == 0 )); then guest_status=1; fi
fi
exit "$guest_status"
