#!/usr/bin/env bash
# Bounded X11 Right-input probe with a screenshot-confirmed second attempt.
# A key-dispatch receipt is not proof of guest input. No original ROM assets.
set -euo pipefail
window="${1:-}"
if ! [[ "$window" =~ ^[0-9]{1,10}$ ]] || [[ "$window" == 0 ]]; then
  echo 'Invalid X11 window ID for optional input probe' >&2
  exit 4
fi
mkdir -p runtime-evidence
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
receipts=runtime-evidence/input-probe-attempts.txt
probe_python="${NEXIUM_PROBE_PYTHON:-python3}"
printf '%s\n' 'probe=bounded_right_v1' > "$receipts"
check_motion() {
  local image="$1" attempt="$2"
  PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" "$probe_python" -m tools.nexium_cursor_motion \
    runtime-evidence/nexium-window.png "$image" \
    --output "runtime-evidence/input-motion-attempt-${attempt}.json" \
    > /dev/null 2> "runtime-evidence/input-motion-attempt-${attempt}.stderr"
}
if ! timeout --kill-after=1s 4s xdotool key --clearmodifiers --window "$window" Right 2>/dev/null; then
  printf '%s\n' 'input_attempted=Right dispatch=failed' >runtime-evidence/input-probe-status.txt
  printf '%s\n' 'attempt1=dispatch_failed' >> "$receipts"
  exit 0
fi
sleep 1
if ! timeout --kill-after=1s 8s import -window "$window" runtime-evidence/nexium-after-right.png ||
   [[ ! -s runtime-evidence/nexium-after-right.png ]]; then
  printf '%s\n' 'input_attempted=Right screenshot=failed' >runtime-evidence/input-probe-status.txt
  printf '%s\n' 'attempt1=capture_failed' >> "$receipts"
  exit 0
fi
printf '%s\n' 'input_attempted=Right screenshot=ready' >runtime-evidence/input-probe-status.txt
if check_motion runtime-evidence/nexium-after-right.png 1; then
  printf '%s\n' 'attempt1=visible_movement' 'selected_attempt=1' >> "$receipts"
  exit 0
fi
printf '%s\n' 'attempt1=no_verified_movement' >> "$receipts"
# Bare Xvfb/Openbox may ignore window activation; never use --sync here.
if timeout --kill-after=1s 2s xdotool windowfocus "$window" 2>/dev/null; then
  printf '%s\n' 'focus_request=sent' >> "$receipts"
else
  printf '%s\n' 'focus_request=failed' >> "$receipts"
fi
if ! timeout --kill-after=1s 4s xdotool key --clearmodifiers --window "$window" Right 2>/dev/null; then
  printf '%s\n' 'attempt2=dispatch_failed' 'selected_attempt=1' >> "$receipts"
  exit 0
fi
sleep 1
if ! timeout --kill-after=1s 8s import -window "$window" runtime-evidence/nexium-after-right-retry.png ||
   [[ ! -s runtime-evidence/nexium-after-right-retry.png ]]; then
  printf '%s\n' 'attempt2=capture_failed' 'selected_attempt=1' >> "$receipts"
  exit 0
fi
if check_motion runtime-evidence/nexium-after-right-retry.png 2; then
  cp runtime-evidence/nexium-after-right-retry.png runtime-evidence/nexium-after-right.png
  printf '%s\n' 'attempt2=visible_movement' 'selected_attempt=2' >> "$receipts"
else
  printf '%s\n' 'attempt2=no_verified_movement' 'selected_attempt=1' >> "$receipts"
fi
