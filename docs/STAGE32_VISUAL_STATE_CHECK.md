# Stage 32 — Read a genuine Switch guest battle-state fingerprint from NeXium pixels

## Why this is needed

Stage31 created stable numeric FNV-1a checksums of the ROM-free C++ tactical state and emitted `VH_STATE` on SDL initialization/state changes. NeXium does not necessarily forward Nintendo Switch guest stderr to the host log, so matching a host CLI checksum to the visualized guest's state remained unverified.

## ROM-free visual test marker

The SDL renderer temporarily draws an 8×8 matrix of 64 rectangular cells in the *otherwise unused top-left corner* of the synthetic 1280×720 tactics scene, together with three magenta corner anchors. Each cell is one bit of the **same `vh::battle_fingerprint`** used by host GCC/Clang replay tests; LSB-first, row-major bit index 0–63. An ON cell is RGB (66,220,132), OFF RGB (40,53,69); anchors are RGB (234,40,190). Cell top-left = (20+12×column, 20+12×row), size 8×8, anchor positions (8,8), (116,8), (8,116). All coordinates are *logical output pixels* and do not represent Sega Saturn game data.

Initial ROM-free scene checksum (Stage31 golden) is **`ae38b0b5ab887f00`**. The digest reflects synthetic map tiles, turn, unit IDs/names/stats and statuses; cursor UI position is intentionally not part of the tactical battle fingerprint.

## CI acceptance

New `tools/nexium_visual_digest.py` reads the *actual captured* `runtime-evidence/nexium-window.png`, requiring an exact 1280×720 capture, 3/3 magenta anchors, zero unrecognized cell colors, and the full 64-bit decoded value matching the host golden. A count-only receipt is saved to `runtime-evidence/state-digest.json`. A missing marker or mismatching bit fails the independent frame-state step even when the pawn-color check passes. The strict host-panic and lifecycle audit gates remain unchanged.

## Local independent checks

- Python 9/9 **synthetic screenshot tests passed**: correct golden, one-bit flip, missing anchors, blank image, corrupt pixel, color tolerance, invalid resolution, malformed reference and alternative valid 64-bit reference.
- C++ `visual_digest_contract` CTest **1/1 passed**: uses the actual C++ training scene to derive the 64-bit checksum, iterates all cells, reassembles it from bits, verifies anchors/bounds and rejects out-of-range bit indexes.
- Four source/test Git blobs were hash-checked against the locally tested files before publishing. No original Sega Saturn files, screenshots or artwork are required.

## Limitations and follow-up

**This is a deliberate diagnostic marker visible inside the ROM-free prototype.** Remove or disable it when a genuine first battle is implemented. It confirms that one emulator screenshot visibly encodes the guest-reported *synthetic* state; it does not independently validate the correctness of game rules, keyboard/gamepad input, frame timing, clean NeXium shutdown or any Sega Saturn original assets.

Cross-compilation and full NeXium tests for the new head must still complete. Existing older NRO screenshots cannot pass the new marker check because the previous binary did not render the marker.
