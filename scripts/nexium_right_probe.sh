#!/usr/bin/env bash
# Stage46: bounded screenshot-confirmed Right input for Xvfb/NeXium.
# Never treat a dispatched key as successful motion; preserve each receipt.
set -euo pipefail
window="${1:-}"
if ! [[ "$window" =~ ^[0-9]{1,10}$ ]] || [[ "$window" == 0 ]]; then
  echo 'Invalid X11 window ID for optional input probe' >&2
  exit 4
fi
: "${NEXIUM_PROBE_MAX_ATTEMPTS:=8}"
if ! [[ "$NEXIUM_PROBE_MAX_ATTEMPTS" =~ ^[1-8]$ ]]; then
  echo 'Probe max attempts must be an integer from 1 to 8' >&2
  exit 4
fi
mkdir -p runtime-evidence
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
receipts=runtime-evidence/input-probe-attempts.txt
probe_python="${NEXIUM_PROBE_PYTHON:-python3}"
printf 'probe=bounded_right_v2\nmax_attempts=%s\n' "$NEXIUM_PROBE_MAX_ATTEMPTS" > "$receipts"
check_motion() {
  local image="$1" attempt="$2"
  PYTHONPATH="$source_root${PYTHONPATH:+:$PYTHONPATH}" "$probe_python" -m tools.nexium_cursor_motion \
    runtime-evidence/nexium-window.png "$image" \
    --output "runtime-evidence/input-motion-attempt-${attempt}.json" \
    > /dev/null 2> "runtime-evidence/input-motion-attempt-${attempt}.stderr"
}
for ((attempt=1; attempt<=NEXIUM_PROBE_MAX_ATTEMPTS; ++attempt)); do
  frame="runtime-evidence/nexium-after-right-attempt-${attempt}.png"
  if ! timeout --kill-after=1s 4s xdotool key --clearmodifiers --window "$window" Right 2>/dev/null; then
    # Fail fast on a hung or failed xdotool invocation: repeating timeouts
    # would delay emulator teardown and risk orphaning the guest process.
    # This is distinct from a successfully delivered but visually ignored key.
    printf 'attempt%s=dispatch_failed\nselected_attempt=none\n' "$attempt" >> "$receipts"
    printf 'input_attempted=Right dispatch=failed\n' >runtime-evidence/input-probe-status.txt
    exit 0
  else
    sleep 1
    if ! timeout --kill-after=1s 8s import -window "$window" "$frame" 2>/dev/null || [[ ! -s "$frame" ]]; then
      printf 'attempt%s=capture_failed\n' "$attempt" >> "$receipts"
    elif check_motion "$frame" "$attempt"; then
      # Promoting ONLY a screenshot which was actually classified as moved.
      cp "$frame" runtime-evidence/nexium-after-right.png
      printf 'attempt%s=visible_movement\nselected_attempt=%s\n' "$attempt" "$attempt" >> "$receipts"
      # Preserve the exact v1 receipt expected by the independent guest gate;
      # the v2 attempt/JSON files carry the separate motion proof.
      printf 'input_attempted=Right screenshot=ready\n' >runtime-evidence/input-probe-status.txt
      exit 0
    else
      printf 'attempt%s=no_verified_movement\n' "$attempt" >> "$receipts"
    fi
  fi
  if (( attempt < NEXIUM_PROBE_MAX_ATTEMPTS )); then
    # Focus only after the captured frame failed to show input, never blindly.
    if timeout --kill-after=1s 2s xdotool windowfocus "$window" 2>/dev/null; then
      printf 'focus_after_attempt_%s=sent\n' "$attempt" >> "$receipts"
    else
      printf 'focus_after_attempt_%s=failed\n' "$attempt" >> "$receipts"
    fi
  fi
done
# No synthetic evidence and no arbitrary fallback to the first frame.
printf 'selected_attempt=none\n' >> "$receipts"
printf 'input_attempted=Right motion=unverified max_attempts=%s\n' "$NEXIUM_PROBE_MAX_ATTEMPTS" \
  >runtime-evidence/input-probe-status.txt
# Keep the surrounding launcher alive to audit teardown, but strict workflow
# validators MUST fail the sample without a real verified motion screenshot.
exit 0
