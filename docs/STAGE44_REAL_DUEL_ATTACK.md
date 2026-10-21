# Stage44 — Live attack and repeat-attack rejection in ROM-free NeXium duel

## Why a separate build is necessary

The Stage42–43 default Nintendo Switch NRO uses a synthetic 8×8 tactical
training map where no enemy is immediately within Scout's attack range.
An authentic guest attack on that map would require additional turns,
route finding and unpredictable simple enemy AI. Stage44 therefore builds
an **extra** NRO, without modifying the default scene, by passing
`TARGET=vh_saturn_attack BUILD=switch-attack-build DEFINES=-DVH_STAGE44_DUEL`
to the same devkitPro Makefile. Both builds share the same C++ tactical
engine, SDL input handling, and state digest. All game assets are original
placeholder geometry.

## Duel contract

The attack fixture uses an otherwise empty 8×8 grid, with Scout at
`(1,5)` (HP 22, attack 8, defense 3, range 1) and Raider at `(2,5)`
(HP 20, defense 2, range 1). Scout inflicts exactly `8 - 2 = 6`
damage, reducing Raider from **20 to 14 HP**. A second attack in the
same player round must be rejected without changing state.

The host C++ fingerprint fixture asserts exact canonical FNV-1a digests:

- Initial duel state: `9376e23745926630`.
- After one successful attack: `9a0233cdc1acffdb`.
- Repeated attack: rejected; the fingerprint remains unchanged.

These host values are **not** proof of guest execution.

## Evidence expected from the actual Nintendo Switch guest

An independent fresh Xvfb/NeXium session launches the *duel NRO* after
the established Stage43 NeXium flow has completed. The production pixel
test requires:

1. An initial genuine NeXium PNG encoding the initial full battle hash
   `9376e23745926630`, and a visibly full enemy HP bar.
2. A screenshot-verified return of the yellow cursor to Scout, selection
   with visible yellow actor outline, and a 1-cell aim onto Raider.
3. An actual Y-button key event followed by PNG containing the entire
   attacked hash `9a0233cdc1acffdb` **and** the new purple
   `Attacked` guest receipt and Raider HP-bar pixel reduction.
4. A second Y event followed by PNG containing the same attacked hash,
   the red `Rejected` guest receipt, and *unchanged damaged HP*.
5. An independent verification step decoding the images from the
   artifact directory. A key dispatch, successful exit code, plausible
   screenshot, or host hash by itself cannot satisfy the acceptance gate.

The additional stage runs in `stage44-session/` and preserves Stage43
screenshots, artifacts and reliability checks. The old ROM-free NRO still
must pass its own existing tests.

## What Stage44 does NOT establish

This is **not** a replay of the original Sega Saturn Vandal Hearts battle:
it is an intentionally small ROM-free duel using the shared native engine.
X11 keyboard actions are not physical Switch controller verification.
No original Saturn ROM, CUE/BIN, sprites, soundtrack or maps are uploaded.

Status: The source, CI workflow, and synthetic tests are committed; actual
guest evidence must be judged from the new Actions run, not assumed from
the host fixture.
