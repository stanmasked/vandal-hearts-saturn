# Stage 33 — Actual C++ -> PPM -> Python visual-digest interoperability

## Reason

Stage32's C++ tests verified the bit-position layout and Python's synthetic pixel tests verified screenshot color recognition, independently. That did not yet prove that the native C++ state fingerprint can pass through a real image file and be decoded by the exact NeXium Python checker.

## Implemented

New host-only vh_visual_fixture (src/app/visual_fixture_main.cpp) creates two ROM-free 1280x720 binary PPM (P6) images. Each image is drawn by C++ using the exact vh::battle_fingerprint, vh::digest_bit, vh::digest_cell_rect and vh::digest_anchor functions. It writes the initial synthetic training scene and the post-Scout-move-to-(2,5) scene; all image pixels are synthetic colors, no original game graphics. The CLI prints two numeric receipts.

New tools/check_visual_bridge.py invokes the native binary via subprocess in a temporary folder, opens actual generated PPM files with Pillow, and verifies them with the same tools.nexium_visual_digest.decode used by the NeXium CI. It checks the golden initial checksum, the changed checksum, both directions of stale-reference rejection, all three anchors, and denial of a single white corruption pixel. Output is a compact JSON report without original art or emulator screenshots.

Host CMakeLists.txt builds the fixture, while .github/workflows/host.yml runs the cross-language test after installing Pillow, once for GCC and once for Clang. Only host CI runs the fixture; it is not linked into the Switch NRO and does not affect the actual game renderer.

## Local verified outputs

GCC and Clang both compiled the fixture and passed the bridge checks. Initial checksum: ae38b0b5ab887f00; after move: ef9c7d67953c9b2a. The preexisting Stage31 deterministic replay CTest also passed for both compilers. The fixture/decoder Python logic is unchanged from Stage32, except the new bridge executable/script.

## Limitations

This proves cross-language compatibility for a C++-generated test image, not actual Nintendo Switch execution. Real NeXium pixels on Stage32/33 remain a separate CI check. It cannot prove gamepad/keyboard delivery, NeXium/X11 shutdown stability, or authenticity to the original Sega Saturn first mission. No copyrighted game content is included.