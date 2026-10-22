# Stage105 — original Saturn intro across 10800 emulated frames

## Verified source and runtime background

User-owned Vandal Hearts Saturn English-v1.1 two-BIN/CUE original media
were privately reconstructed and checked against exact Stage02 SHA-256
hashes. Pinned historical real Yabause with C68K enabled now renders
original KONAMI branding and a multi-scene introductory film.

Stage104's **official public-only GitHub Actions Clang executable** was
downloaded and used on the real original disc at 3600 frames. Results:
5891 naturally generated ISOCD callbacks (5821 distinct) and real
private film images featuring forest and sword scenes. Those FAD
events and six selected PNGs were byte-identical to the preliminary
single-immediate patched diagnostic binary. No title/menu appeared.

## What Stage105 adds

`tools/patch_yabause_private_title_10800.py` extends exactly the
same pinned public Stage104/Yabause/C68K original-game mode from
3600 to **10800 bounded frames**. The only source change is the
opt-in frame bound: SH2/HLE BIOS, genuine ISOCD source reader,
C68K sound CPU, Titan renderer, 120-frame video snapshots,
local-only SH2 instruction samples and numerical CD callback gate
are preserved.

The public GitHub Actions workflow builds only licensed upstream
Yabause source, runs fabricated CUE/ISO tests under GCC/Clang
and uploads only the public executable. It receives no original
BIN/CUE, DVD/CD tracks, audio, artwork or frames.

## Early private 10800-frame observation

Before the Stage105 public compilation could finish, a separate
**private interim diagnostic copy** was derived from the official
Stage104 executable. Its exact compiled 3600-frame comparison
instruction was uniquely identified and **only its immediate
frame-limit value was changed to 10800**. The modified binary
and its hash are not distributed or called official Stage105 CI.

On the existing Stage02-hash-matched original CUE, this private
diagnostic completed exactly **10800/10800** frames with status 0,
18,467 numeric ISOCD callbacks (**18,397 distinct**), closed
manual FAD gate, all source/executable hashes unchanged and
90 private PNG checkpoints.

Direct visual examination of privately saved frames at 7200,
9000 and 10800 shows the original introductory film continuing,
including city buildings and a silhouetted warrior against
red skies. The **original title/menu and first battle were not
observed at these sampled points**. A frame from the intro must
not be described as a playable title screen.

This result must be reproduced on the exact Stage105 CI executable
before being labeled an official-build runtime pass. Note that
a handful of sampled checkpoints cannot prove a title screen did
not appear between frames.

## Acceptance and next goal

Confirm the pinned GCC+Clang public-code-only build and rerun
the 10800 original frames on the CI-produced executable.
If the title is still not observed, investigate whether the FMV
runs until a later time or requires a controller input to skip.
Any controller intervention must be captured with an actual
frame-indexed guest input trace, not merely assumed.

Keep original media/screenshots/private FAD and SH2 opcode
windows out of public GitHub. First-battle source authenticity
Issue #11 stays open.
