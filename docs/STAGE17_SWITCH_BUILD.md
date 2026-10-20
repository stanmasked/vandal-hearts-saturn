# Stage 17 — Verified Nintendo Switch NRO build gate

## Goal

Compile the existing ROM-free C++17 8x8 tactics demo for Nintendo Switch
with libnx and switch-SDL2. This is **not yet Vandal Hearts Saturn gameplay**.

## Build environment

- GitHub Actions container: devkitpro/devkita64:20260219.
- Existing root Makefile uses devkitPro/libnx switch_rules and SDL2.
- Workflow: .github/workflows/switch-nro.yml.
- The binary vh_saturn_demo.nro should be created by the devkitPro toolchain;
  any build failure must remain visible. There is no fake NRO fallback.

## Independent acceptance tests

tools/nro_verify.py inspects the NRO0 signature at byte offset 0x10,
checks declared executable size, segment bounds and the optional ASET region;
it also computes SHA-256. This only proves a well-formed binary **header**.
Eight synthetic unit tests exercise valid and damaged fixtures, and require
no Switch SDK or original game media.

On a successful Actions run, the artifact vh-saturn-prototype-nro should
contain a NRO, its NACP metadata and verification JSON. Do not claim it
exists or runs until the workflow completes successfully. Artifact filenames
contain **no original Saturn assets**.

## How to reproduce with an installed devkitPro

Set DEVKITPRO to /opt/devkitpro (or its actual installed location), install
devkitA64, libnx and switch-sdl2, then run make -j2 in the project root.
Run python3 -m tools.nro_verify vh_saturn_demo.nro to inspect the output.

## Remaining validation

A successful native compilation does not establish successful runtime in
NeXium or on a Nintendo Switch console. Runtime input, frame pacing,
visual output and controls must be tested separately. The Saturn .MAP A/B
candidate arrays still have unknown semantics and there is no authentic
first mission imported into this prototype.
