# Stage106 — genuine original Saturn Vandal Hearts title screen observed

## Verified new visual milestone

The user-owned English-v1.1 Sega Saturn Vandal Hearts original Track1,
Track2 and CUE were independently SHA-256 verified against the immutable
Stage02 pins. The original game is running through genuine pinned
historical open-source Yabause with real C68K, SH2, HLE BIOS and ISOCD.

After the intro movie's final sector was read during the Stage105
10,800-frame run, a new **12,000-frame private original-disc capture**
was made using a temporary local copy of the official Stage104 public
Yabause executable with **only the uniquely disassembled frame bound
changed from 3600 to 12000**. This modified private executable is NOT
a formal Stage106 CI artifact.

The observed process reported:
- 12,000/12,000 actual emulated frames and exit code 0.
- **19,883** genuine numeric ISOCD callback FAD records, **19,438**
  unique addresses.
- Exact original Track1/Track2/CUE and executable SHA-256 preserved
  before and after the process.
- Closed capture gate, protected 0700 workspace, and 100 local-only
  checkpoint screenshots saved.
- Real privately inspected **title graphic** reading
  **VANDAL HEARTS — The Lost Civilization**, **V1.1**,
  and **Press START Button**, with authentic Konami/KCEN copyrights.

This is now evidence of a **visible original title screen**—materially
stronger than merely a KONAMI splash or a black SH2 execution trace.
Frames at 11,760 and 11,880 are black transitions, and the title
is clearly visible at 12,000. The exact first title-rendered
emulated frame is **not** established from 120-frame checkpoints.

The original title is not a usable menu or first tactical battle.
No gamepad START was injected in this run.

## Reproducible public source change

`tools/patch_yabause_original_title_12000.py` chains all earlier
exact pinned historical Yabause source-patching layers and changes
**only the original-private-game frame cap** 10,800→12,000.
The public GCC/Clang CI includes synthetic-only Yabause CD core and
game-free tests, and saves only the GPL public modified Yabause
executable. It does not access, decode, publish or upload original
media, screenshots or numeric original game traces.

The exact new Stage106 CI-produced binary still requires a separate
12,000-frame **private** original-disc reproduction before marking
that executable as fully runtime-verified.

## Next input acceptance

Actual Saturn controller API exists in pinned public Yabause:
`PerPadAdd(&PORTDATA1)`, `PerPadStartPressed(pad)`, and
`PerPadStartReleased(pad)`.

The next independent experiment should register a first-port Saturn
pad, issue **START after frame 12,000** for a bounded interval,
and compare a control (no START) with the input-enabled run on the
same original disc. Keep frame-aligned button press/release metadata
and private frame/CD snapshots. A reported button event alone is
**not** proof the game entered a visible menu.

Continue holding authentic first-battle Issue #11 OPEN until real
visible battle scene and original loader/inputs are independently
verified. Keep all protected assets outside public GitHub.
