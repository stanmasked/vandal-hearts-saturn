# Stage88 — actual public Yabause CUE/BIN open through the private wrapper

## Goal

Stage87 bound an arbitrary executable hash and a declaration of a local
CUE path to a private numeric-read session, but did not prove that the
executable opened that CUE. Stage88 tests the missing link by running
the **real linked historical Yabause ISOCD backend** from our pinned
public source under the Stage87 private wrapper, on exclusively
**invented nonbootable** CUE/BIN fixtures.

## Real code path

1. Fetch the exact upstream Yabause and LodePNG revisions used by
   Stage78–87; enforce both source file Git-object pins.
2. Apply the Stage79 primary sector read accounting and Stage77 manual
   numeric FAD gate to original `cdbase.c`.
3. Build the real linked Yabause runner with GCC and Clang. The Stage88
   source instrumenter accepts only the pinned upstream original
   `yui.cpp`, extending the Stage82/83/84 test modes.
4. Stage88's new opt-in `vh-exact-cue-read` mode requires a **three-item**
   argv (runner, mode, absolute CUE path). It calls the original
   `ISOCD.Init(argv[2])`; the old Yabause CUE parser locates the
   quoted BIN file through CUE-relative file resolution.
5. Open the manual trace gate, call the original
   `ISOCD.ReadSectorFAD` for invented FADs 150, 151 and synthetic EOF
   152, and verify distinct marker bytes in sectors 150 and 151.
6. Close the gate, release the real ISO backend and Yabause core, then
   exit without creating any other output.
7. A separate Python verifier creates all its inputs outside Git:
   an invented two-sector 4,704-byte MODE1/2352 BIN, an unrelated
   fake Track2 file and a tiny CUE referencing Track1.
8. The Stage87 private wrapper verifies all three invented source
   digests plus the locally pinned actual runner executable before and
   after its process run; it requires exact CUE argv identity and
   accepts only the numeric-only local FAD log.
9. **Negative control:** change a separately generated fake CUE to
   refer to a missing BIN, re-pin only this fake CUE, and require the
   real process to fail without producing a success receipt.

Expected synthetic numeric log:
```text
VHCD_FAD 150
VHCD_FAD 151
```

## Evidence boundary

A pass confirms the **real original public Yabause CUE parser opened
a CUE and its associated BIN and read actual file bytes** with the
instrumented CD callback, under the existing private wrapper. It is
stronger than Stage84's bare fabricated ISO access and Stage87's
argv-only CUE declaration.

It does not prove that the user's English v1.1 Saturn disc or an
unpatched Japanese master was opened, that Saturn BIOS/game code was
booted, or that a specific menu/first-battle scene was active.
It does not authenticate unit placement, combat mechanics, game
maps or source-loader identity. Those remain Issue #11.

The Stage88 receipt explicitly sets `real_game_media_used=false`,
`original_game_boot_verified=false`, and
`first_battle_loader_verified=false`. Public CI never receives the
user's original BIN/CUE, screens, assets, audio or private logs.
All generated test files live in ephemeral private directories and
are destroyed; no binaries or synthetic media are uploaded as
artifacts. See Stage86/87 for the separate operator procedure once
the existing private media are available.
