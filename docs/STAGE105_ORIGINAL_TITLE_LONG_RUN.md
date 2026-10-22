# Stage105 — observe original Saturn title transition after real intro movie

## Evidence verified so far

The user-owned original English v1.1 Saturn Track1, Track2 and CUE
are full-SHA-256 matched against Stage02. Historical pinned Yabause
was instrumented to use actual C68K instead of dummy M68K and executed
the original game correctly past the previous black-screen state.

Stage104 private original-disc 3600-frame session completed with 5891
genuine ISOCD callbacks (5821 unique), 30 private screenshots,
24 distinct PNGs and visually confirmed:
- Frame 600: KONAMI splash.
- Frame 1200: KONAMI Computer Entertainment Nagoya logo.
- Frame 1800: original forest cinematic with a character.
- Frame 2400: continuing movie.
- Frame 3600: original forest/tree/sword cinematic.

The actual title/menu and first tactical encounter were not observed.

## This stage

Stage105 increases **only** the opt-in original game frame bound
from 3600 to 9000 (max 150 seconds of guest frames at 60 Hz).
The same pinned Yabause C68K, SH2 interpreter, HLE BIOS, CDCORE_ISO,
software renderer and 120-frame private screenshots remain unchanged.
No controller input is synthesized in this stage.

Public GitHub CI uses only synthetic game-free tests and publishes only
its reproducible public GPL Yabause executable. All real Saturn BIN/CUE,
private PNGs, numerical FAD logs and SH2 instruction windows stay
outside GitHub in a 0700 local environment. The child runs with
umask 077 and an external bounded timeout.

The private result is considered useful only when independently
inspected PNGs show actual scene evolution and a visible
titled menu can be distinguished from logos or FMV. A fully
visible title screen is not a reconstructed first tactical
battle, and does not prove map or combat mechanics.

Issue #11 remains OPEN until original first-battle frames and
their loader/FAD attribution are actually captured.
