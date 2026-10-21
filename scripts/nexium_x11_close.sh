#!/usr/bin/env bash
# Stage36: probe WM_DELETE_WINDOW before asking Openbox to close NeXium.
# This does not suppress or relabel upstream winit/X11 shutdown failures.
set -euo pipefail

window="${1:-}"
: "${NEXIUM_X11_CLOSE_TIMEOUT_SECONDS:=4}"
if ! [[ "$window" =~ ^[0-9]{1,10}$ ]] || [[ "$window" == 0 ]]; then
  printf '%s\n' 'Invalid numeric X11 window ID' >&2
  exit 4
fi
if ! [[ "$NEXIUM_X11_CLOSE_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] ||
    (( NEXIUM_X11_CLOSE_TIMEOUT_SECONDS < 1 || NEXIUM_X11_CLOSE_TIMEOUT_SECONDS > 8 )); then
  printf '%s\n' 'Invalid bounded X11 shutdown timeout' >&2
  exit 4
fi
mkdir -p runtime-evidence
receipt=runtime-evidence/x11-close-status.txt
printf '%s\n' 'method=EWMH_NET_CLOSE_WINDOW' > "$receipt"
if ! timeout --kill-after=1s "${NEXIUM_X11_CLOSE_TIMEOUT_SECONDS}s" \
      xprop -id "$window" WM_PROTOCOLS \
      >runtime-evidence/x11-wm-protocols.txt 2>runtime-evidence/x11-wm-protocols-error.txt; then
  printf '%s\n' 'wm_protocol_query_failed' >> "$receipt"
  exit 2
fi
# xdotool windowclose can fall back to destroying a window when WM_DELETE_WINDOW
# is absent. Fail closed: never destroy a still-owned winit X11 window here.
if ! grep -Eq '(^|[^[:alnum:]_])WM_DELETE_WINDOW([^[:alnum:]_]|$)' \
      runtime-evidence/x11-wm-protocols.txt; then
  printf '%s\n' 'wm_delete_protocol_missing' >> "$receipt"
  exit 2
fi
printf '%s\n' 'wm_delete_protocol_present' >> "$receipt"
if ! timeout --kill-after=1s "${NEXIUM_X11_CLOSE_TIMEOUT_SECONDS}s" \
      wmctrl -ic "$window" 2>runtime-evidence/x11-wm-close-error.txt; then
  printf '%s\n' 'wmctrl_close_request_failed' >> "$receipt"
  exit 3
fi
printf '%s\n' 'wmctrl_close_request_sent' >> "$receipt"
