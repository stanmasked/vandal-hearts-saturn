# Stage102 — find why the original SH-2 stops progressing visibly

## Verified starting evidence

The user-owned English-v1.1 Saturn Track1, Track2 and CUE match Stage02
SHA-256. Genuine pinned public Yabause executed original-disc-backed SH2
frames and callback FAD reads under HLE BIOS/CDCORE_ISO.

Independent original game runs:

| requested frames | actual FAD count | ending PC |
| ---: | ---: | --- |
| 120 | 305 | `0x06026C08` |
| 240 | 396 | `0x06034198` |
| 360 | 396 | `0x06034198` |
| 600 | 396 | `0x06034198` |

Stage101's real numeric state shows TVMD=33041 (display enabled),
BGON=19, 293 nonzero VDP1 RAM bytes, 6151 nonzero VDP2 RAM bytes
and 19 nonzero palette bytes, but every Titan RGB pixel remains black.
Beyond 240 frames the video state/PC and CD read count stop changing.

These observations are consistent with an SH2 wait loop but do **not**
prove a loop or its specific condition. This is the next constraint.

## Stage102 instrumentation

`tools/patch_yabause_private_sh2_window.py` layers a separate *local*
protected `sh2-window.txt` witness on the exact pinned public Yabause
Stage101 runner without changing its CD access behavior.

At frame 0, each 120-frame checkpoint and the final frame, it records
the observed SH2 PC and registers SR, PR, GBR, R0–R5 and R15; only when
PC lies within mapped high work RAM `0x06000010`–`0x060FFFF0` it
reads at most **nine 16-bit instruction words** around the PC to
identify the type of local branch/wait. The original instruction values
are strictly **private** and must not be copied into PRs, Issues, Actions,
chat-visible logs or screenshots. No file from the user's Saturn disc
or actual decoded opcode is published.

GitHub Actions compiles only the GPL-licensed pinned public Yabause
under GCC/Clang. It reruns synthetic CD and private-mode argument
tests, plus Stage102's fake-only logic checks, and uploads only the
public modified executable artifact (not private captured content).

## Private operator use

On the local Stage02-hash-verified disc:

```bash
VH_SATURN_CAPTURE_GATE=/private/run240/gate \
VH_SATURN_FAD_LOG=/private/run240/fad.vhcdlog \
VH_SATURN_PRIVATE_FRAMES_DIR=/private/run240 \
  /private/pinned-public-yabause vh-private-frame-boot \
  /private/original-saturn-disc.cue 240
```

The directory must be private 0700 and newly empty, and the child must
be run with `umask 077`. Read `sh2-window.txt` **locally** and
classify the instruction type and register progression, reporting
only high-level findings in public text.

A stationary PC could be a legitimate wait loop polling a hardware
register, a stalled game loader or an emulation defect. No inference
about gameplay or the first battle is valid until actual color pixels
and synchronized frame/CD evidence are independently observed.

Issue #11 remains BLOCKED.
