# Stage80 — build the real pinned Yabause core with the CD diagnostic

## Scope

This stage moves beyond Stage78/79's standalone compiled callback:
the full public Yabause emulation **core library** is compiled against
the patched original `cdbase.c` with independent GCC/Clang CI matrix.

It does NOT launch a Saturn emulator binary, boot a BIOS, mount any
game, or verify the original first battle. A static library build is
strictly weaker than a full executable/run.

## Reproducible inputs

- Public repository: https://github.com/Yabause/yabause
- Immutable upstream commit: `7e38821dbac265490f115e163c523a939acda759`
- Only instrumented upstream path: `yabause/src/cdbase.c`
- Expected original Git blob: `d56d5dd1941b553c0ede111a83fcf8e50dbecb45`
- Patch logic: `tools/patch_yabause_full_cdbase.py`
- Reuses Stage79's manually window-gated, **primary sector payload only**
  read receipt across original five `fread` sites.

CI checks the exact upstream commit, independently checks the Git blob
before patching, refuses patch drift, and confirms all changes outside
the ISO CD callback are forbidden.

## CI build

Workflow: `.github/workflows/yabause-pinned-core.yml`.

Clone the fixed public source temporarily, generate the patched source
in a fresh file, replace the temporary checkout's `cdbase.c`,
configure the historical CMake project, and compile its `yabause`
target. The core library includes dozens of real Yabause translation
units; it is not a test-specific C stub.

The build disables optional OpenGL, SDL, OpenAL, SSF, Musashi, Play JIT
and MPEG configurations to focus on a minimal Linux core. The `runner`
port is configured but is missing third-party `lodepng` source in
this pinned revision; it is **not assumed to produce a runnable binary**.

This baseline stage does not instrument an SH2 loader or capture scenes;
the CD numeric hook records successfully read primary sector payloads
only when the exact manually controlled ASCII `1\n` gate exists.

## Boundaries / privacy

- No original ISO/BIN/CUE/CHD image, BIOS, CD sectors, save states,
  screenshots or proprietary scripts are downloaded, built or uploaded.
- The public GPL Yabause source is fetched transiently, never stored in
  this game repository or in published build artifacts.
- A core library build demonstrates API/translation-unit compatibility,
  not that the executable works or that any authentic first-battle
  resource was identified. See Issue #11.
- This project records the English v1.1 translation-patched Saturn
  source separately; that is not proof of original Japanese authenticity.

## Next genuine runtime milestone

Create an explicit full emulator executable integration and a
disc-free smoke test first, with a verifiable command-line receipt.
Then, only in a private authenticated workspace, verify the user's
already supplied disc against its prior local metadata and collect
independent menu and battle-entry captures. Do not ship the user media
or capture artifacts through public CI.
