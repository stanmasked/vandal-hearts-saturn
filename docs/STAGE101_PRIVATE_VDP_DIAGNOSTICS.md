# Stage101 — determine why original Yabause frames are black

## Grounded starting point

Stages97–98 independently established matching full SHA-256 values for
the user-owned English-v1.1 Track1/Track2/CUE and showed genuine Yabause
ISOCD reads from the original disc. Stage99 ran actual historical Yabause
SH-2/HLE-BIOS emulation for up to 600 frames, with 396 naturally observed
numeric CD reads. Nevertheless every private PNG through frame 600 was
completely **black**. Stage100 correlated these numeric reads to real
ISO9660 file extents without claiming a visible first battle.

We cannot conclude from black screenshots alone whether VDP registers
are disabled, whether video RAM contains tile/sprite data, or whether
the software-renderer's Titan framebuffer is failing to composite it.

## New read-only instrumentation

Stage101 wraps exactly the same pinned public Yabause runner as Stage99
but introduces one additional **private numeric-only file**
`video-state.txt` under the protected screenshot directory.

Snapshots occur at frame 0, 120, 240, 360, 480 and 600 (and the final
frame if it is not already a checkpoint). Each record contains only:

- actual emulated SH-2 program counter;
- VDP2 TVMD, BGON and RAMCTL register values;
- VDP1 TVMR, PTMR and EDSR register values;
- count of nonzero bytes in VDP1 VRAM (512 KiB), VDP2 VRAM (512 KiB),
  and VDP2 color RAM (4 KiB);
- count of nonblack RGB pixels from the `TitanRender()` output buffer;
- numerical video dimensions and instrumented frame number.

**No** original VRAM, CD sectors, tile contents, image pixels, original
game code, sound, ZIP parts or screenshot hashes are exported to GitHub.
The source binaries and all captures stay only in a private 0700 local
workspace; the subprocess is launched under umask 077, so the new file
is private. GitHub Actions compiles only public pinned Yabause and tests
synthetic samples, never accesses the user's game image.

`tools/saturn_private_video_state_audit.py` validates strict record
order/ranges and private 0600 permissions and prints a sanitized Boolean
diagnostic. A matching video register does **not** establish a working
Saturn menu or battlefield.

## How to interpret

| Evidence | Interpretation |
| --- | --- |
| TVMD display bit disabled, BGON=0 | Blank video may be genuine guest/VDP configuration |
| VDP VRAM populated but Titan RGB pixels all zero | Suspect video mode, layers, palette or compositing; investigate rather than claiming game visible |
| Nonblack Titan pixels | Renderer produces some color, but still not proof that the game title/first battle is displayed |
| SH-2 PC and CD reads advancing | Guest execution activity, not a proof of correct game or framebuffer |

A private example after all Stage02 original disc identity checks:

```bash
VH_SATURN_CAPTURE_GATE=/private/run600/control.gate \
VH_SATURN_FAD_LOG=/private/run600/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/run600 \
  /private/pinned-public-yabause vh-private-frame-boot \
  /private/original-vandal-hearts.cue 600

python3 -m tools.saturn_private_video_state_audit \
  --video-state /private/run600/video-state.txt
```

These paths are placeholders. No original content is to be sent
through public CI or GitHub issues. The audit deliberately keeps
`actual_original_game_title_visible_verified=false`,
`original_first_battle_visible_verified=false`, and
`frame_to_cd_reads_synchronized_verified=false` even when valid
numeric records exist.

## Real private original-disc results (22 October 2026)

A complete private copy of the original English-v1.1 Track1, Track2 and
CUE was reassembled from the user's uploaded split ZIP volumes in a
0700 temporary workspace and **each file's full SHA-256 matched Stage02**.
The pinned Stage101 public-only Clang Yabause executable, successfully
built in GitHub Actions, ran the **actual original disc** for 600 frames
and produced its local numeric state evidence and screenshots.

| Sample | SH2 PC | VDP2 TVMD | BGON | nonzero VDP1 VRAM | nonzero VDP2 VRAM | nonzero color RAM | nonblack Titan RGB |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0x06002E00 | 32768 | 1 | 0 | 0 | 0 | 0 |
| 120 | 0x06026C08 | 33041 | 19 | 293 | 6151 | 19 | 0 |
| 240 | 0x06034198 | 33041 | 19 | 293 | 6151 | 19 | 0 |
| 360 | 0x06034198 | 33041 | 19 | 293 | 6151 | 19 | 0 |
| 480 | 0x06034198 | 33041 | 19 | 293 | 6151 | 19 | 0 |
| 600 | 0x06034198 | 33041 | 19 | 293 | 6151 | 19 | 0 |

All 7 saved private PNGs (before, five checkpoints and after) had **zero
nonblack RGB pixels**. Exactly 396 naturally generated CD FAD callbacks
were recorded, with 370 distinct addresses.

Separate real-disc processes at 120/240/360 frames reproduce that
progression: **305 FADs at frame 120; 396 by frame 240; no further
reads by frames 360 or 600**. The SH2 PC remains at
`0x06034198` at the latter three sampling points.

These findings rule out a completely empty VDP2 RAM and disabled VDP2
TVMD display as the simple explanation. They do **not** isolate a
renderer defect, because the game may be waiting on another emulated
system or a video event. The next diagnostic must inspect the bounded
SH2 instruction/register state near `0x06034198` privately, without
publishing original game code, and distinguish repeated waiting loops
from an emulation problem. Original screens and RAM contents stay only
in the private workspace.

## Acceptance criteria

1. GCC and Clang compile/link the pinned real Yabause source with the
   Stage101 instrumentation, retaining all Stage82–99 regressions.
2. Public no-disc test matrix rejects incorrect inputs and malformed
   sample VDP reports; no original media tracked.
3. A private original-disc 600-frame run yields the six bounded numeric
   checkpoints and unchanged Track1/Track2/CUE hashes.
4. Only after understanding actual VDP/Titan and obtaining visible
   images should the first-battle authenticity gate (Issue #11) advance.
