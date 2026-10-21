# Stage96 — private frame-file witness integrity bound to four numeric FAD captures

## Objective

Stage95 validates a quartet of privately stored, operator-declared FAD
read sessions (two menu controls and two first-battle entries) against the
Stage94 original-media hash/ISO and runner-session integrity receipts.
But it knows **nothing about screenshots**. A numeric FAD log labeled
`first_battle_entry` does not establish that the emulator was actually
showing the first battle.

Stage96 adds a **local private image-file witness preflight**. It checks
that the files associated with each of the four Stage95 sessions exist,
are structurally valid PNGs, and have not been accidentally substituted.
It does **not** classify frame pixels as Vandal Hearts, infer a game
state, or pretend the operator's frame counters were captured by the
Yabause CD callback.

## Operator input

Keep the original Stage95 capture workspaces unchanged. For each, create
a **separate new 0700 private witness folder** containing exactly:

- `frame-witness.json`: schema_version 1, session_id from that
  capture's Stage86 receipt, phase, SHA-256 of the **exact numeric
  `fad.vhcdlog` bytes** and two declared frame records.
- `before.png`: private frame image recorded before opening the
  intended CD-read gate.
- `after.png`: private frame image recorded after closing the
  intended CD-read gate.

Each manifest frame entry must use the corresponding filename,
`when: before_gate` or `when: after_gate`,
`declared_frame_counter` (a monotonically increasing nonnegative
integer) and the SHA-256 of the actual private PNG file. The screenshot
files and JSON manifest must be regular single-link files with 0600
permissions, not symlinks, and must be no larger than the tool's bounds.
PNG framing, IHDR dimensions and chunk CRCs are verified without
decoding or exporting copyrighted pixels.

Example **placeholder** command when four full Stage94 captures and
their independently stored images are already available locally:

```bash
python3 -m tools.saturn_private_frame_witness \
  --menu-capture /private/saturn/menu-one \
  --menu-capture /private/saturn/menu-two \
  --menu-witness /private/saturn/images-menu-one \
  --menu-witness /private/saturn/images-menu-two \
  --battle-capture /private/saturn/battle-one \
  --battle-capture /private/saturn/battle-two \
  --battle-witness /private/saturn/images-battle-one \
  --battle-witness /private/saturn/images-battle-two
```

The tool first repeats the entire Stage95 cohort validation, including
all original Stage94 source-integrity receipts and FAD-to-Track1 LBA
checks. Next it checks the declared screenshot/session association,
actual FAD-log SHA-256 match, monotonically ordered declared frame
counters, same PNG dimensions and eight independent file identities.

Its standard output is **only a sanitized summary** of counts and
Boolean checks. No PNG payload, extracted image content, private file
path, screenshot digest, original disc bytes, CD log values or session ID
appears in that summary. Unlike the screenshot bytes themselves, the
summary alone is safe to review.

## Important interpretation boundaries

A valid PNG CRC and a matching hash show file integrity, **not** that a
Yabause frame corresponds to an original Saturn game scene.

The manifest's `before_gate` and `after_gate` labels and its frame
counters are *operator declarations*, not instrumented emulator events.
In particular, a passing Stage96 receipt MUST keep:

- `actual_emulator_frame_counters_independently_verified=false`
- `frame_capture_synchronized_to_fad_gate_verified=false`
- `actual_original_saturn_game_boot_observed=false`
- `original_first_battle_scene_identified=false`
- `source_loader_to_map_relationship_verified=false`

Repeated identical screenshots before and after a gate are **allowed**
and counted, because unchanged UIs or loading screens are legitimate;
equality does not prove duplicate frame capture. Scene-level evidence
will require human review of real frames and an independently
instrumented, monotonically increasing frame counter that shares a
time base with CD callback reads.

Public CI fabricates a 22-sector test Saturn image, a fake executable
and eight one-pixel PNGs. The 13 focused tests verify success and
corrupted/changed frames, CRCs, hashes, session identities, relative
frame ordering, unsafe file permissions, reused witnesses and FAD
mismatch. All original game assets and private screenshots remain
outside GitHub CI.

## Original media access

The English v1.1 private Track1 was found in the user's Drive, but the
621,755,904-byte file exceeds this chat's raw Drive download limit.
Stage92's separately authorized local Range method and full Stage02
SHA-256 recheck are prerequisites before any true original game boot.
No genuine first battle was observed or reconstructed here. Continue
to treat Issue #11 as BLOCKED.
