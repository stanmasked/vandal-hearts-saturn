# Stage 24 — Optional NeXium right-key input evidence

## Goal

Stage 22/23's NeXium smoke job has not yet returned an authenticated guest screenshot. In addition to verifying a *first* tactics scene frame, save a separate **post-input** screenshot after sending the X11 `Right` key. This may help determine whether the game UI receives keyboard navigation once NeXium displays the ROM-free demo.

## Implementation

- The original `scripts/nexium_capture.sh` still requires a valid initial screenshot and writes a capture receipt.
- After initial capture, it **attempts** `xdotool windowactivate` then sends `Right` to the same X11 window; it captures `runtime-evidence/nexium-after-right.png` if possible and records `input-probe-status.txt`.
- This is **optional evidence**, not a condition for the baseline framebuffer gate. Keyboard injection might be interpreted by NeXium's host UI rather than delivered to the guest.
- `tools/nexium_cursor_motion.py` compares the largest yellow highlight components in the two images, checks for a plausible rightward offset, and writes `runtime-evidence/cursor-motion.json`. Absence of the second screenshot is clearly noted. An unverified input result is **never accepted as success automatically**.
- The existing Stage 21 two-blue/two-red visual test remains the mandatory early gate; any failed NeXium run still uploads evidence.

## Test validation

Seven **synthetic-only** Python screenshot tests passed: rightward yellow cursor movement, no movement, left movement, legend-only image, disappearing cursor, mismatched image dimensions, and undersized images. Six earlier mocked launch tests also passed after changing the Bash capture script (13/13 combined). Bash syntax check passed.

## Limits

No actual NeXium screenshot or guest input result is claimed here. The new visual comparison applies to the ROM-free 8×8 isometric tactics demo only, not the Sega Saturn game's original battle. It cannot prove keyboard delivery, controller support, or pixel-exact rendering. Authentic Saturn resources remain outside GitHub.
