# Stage136 - pinned ROM-free optimized Stage125 tenth-C Yabause export

## Goal
Prepare the REAL emulator executable required by the privately gated
Stage125 tenth-C original-game experiment, without exporting any original
Saturn game media or private diagnostic output.

This new isolated workflow pins the same exact public Yabause and lodepng
upstream commits and lodepng source blob hashes as Stage133. It applies the
existing strict split-CUE CD reader patch and then the **Stage125 guarded
tenth-C patch**, which composes all inherited ninth-C, eighth-C, input,
SH2, video and framebuffer diagnostics on the version-locked upstream source.

Unlike Stage133's Debug binary, this is built in Release mode for a possible
performance improvement. The binary is independently fingerprinted, tested
for headless command-line loadability, and exported as a one-day artifact.
Public CI uses only source code and synthetic tests. The compiled artifact
is open-source emulator code, **never original copyrighted source media**.

## Evidence limits
The binary build does not prove it runs the original Saturn game and does
not validate any tactical gameplay event. Download it into a private host,
rehash against the exact CI artifact, and run a bounded original-game trial
only after full owner-only archive preservation of the new Stage124 pair.
The staged Stage125 runner itself still requires an authenticated private
receipt plus the complete archived Stage124 paired-run structural and
semantic gates before original disc execution.

Any fresh Stage135 capture remains a NEW experiment, not recovery of the
lost historical Stage124 archive. All game files and captures stay exclusively
in owner-only Google Drive and private local working storage. Archive
readback, owner-only permission checks and pinned manifests are mandatory
before cleanup. Release mode may affect runtime speed and should be compared
to Debug on the same short synthetic or private original-media baseline.
