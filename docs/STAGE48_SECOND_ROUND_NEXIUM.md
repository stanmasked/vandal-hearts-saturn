# Stage48 — Guest-verified second round with enemy retaliation (ROM-free)

This stage extends the **same, already verified** duel-NRO session used for
Stage44–45, without changing the default tactical training scene.

## Preconditions

- Stage47 C++ host test passed [GCC/Clang #39489547914](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39489547914), and existing Switch/NeXium CI #39489547694 passed.
- The stage-44 duel Scout hit leaves Raider HP14 and state `9a0233cdc1acffdb`.
- Stage45 cancelled and reselected Scout, but the next attempted same-round Y was rejected; Scout remained selected and the cursor was on Raider's tile.
- All images come from an **actual NeXium guest NRO**, not simulated Python gameplay.

## Canonical state transitions

| Event | Battle fingerprint | Scout HP | Raider HP |
| --- | --- | ---: | ---: |
| Stage45 finished (same player turn) | `9a0233cdc1acffdb` | 22 | 14 |
| Press X / EndTurn; enemy Raider hits Scout; round becomes 2 | `b633fd92746c41cf` | 19 | 14 |
| Try Y with no unit selected | `b633fd92746c41cf` (reject) | 19 | 14 |
| Re-select Scout, press Y on Raider | `203a8823191e6018` | 19 | 8 |
| Try Y again in round 2 | `203a8823191e6018` (reject) | 19 | 8 |

These hex values come from the canonical state hash, pinned by the Stage48
C++ regression (`tests/attack_training_fingerprint_tests.cpp`). They include
round number, phase, movement/attack state, HP and all unit stats.

## Actual emulator evidence required

The [`tools/nexium_second_round.py`](../tools/nexium_second_round.py)
input driver is permitted to start **only if** the Stage44 attack and Stage45
cancel/reselect/third-attack probes have passed **in the same session**.

An independent workflow step reopens the full PNG chain and revalidates
Stage44–45. Stage48 must additionally prove:

1. After X, screenshot hash `b633fd92746c41cf`, Scout HP bar
   change **22 → 19**, Raider HP14, no yellow Scout selection outline
   and cursor still on Raider. The volatile last-effect pixel is independently
   inspected: cyan **TurnEnded** is normal, but a subsequent red **Rejected**
   is accepted ONLY with the exact round-2 hash and both expected HP bars.
   An arbitrary effect color, unchanged hash or unchanged HP is rejected.
2. A Y action with no selected unit is **Rejected** (red receipt), with
   the same hash and both HP bars unchanged.
3. Bounded, screenshot-observed Left/Right keys return to Scout. Return
   (or one Space fallback) must produce an observed blue **Selected**
   receipt and the yellow Scout outline, with identical battle hash.
4. Bounded return of cursor to Raider, then Y: `203a8823191e6018`,
   purple **Attacked** receipt, Raider HP **14 → 8**, Scout HP19.
5. Repeated Y produces an observed red **Rejected** receipt, unchanged
   second-round hash and unchanged both HP bars. A screenshot or JSON
   receipt alone cannot imply success.

Each HP bar assertion samples multiple registered guest pixels, not only a
host-side number, using the magenta registration markers. Every accepted
input is corroborated by the post-input rendered frame. A missing screenshot,
unexpected state transition, invalid proof filename or transient focus loss
fails the independent verifier. Navigation allows at most twelve observed
attempts per direction; no blind passing due to key dispatch.

## Scope and limitations

This is an original minimal **ROM-free** tactical training scenario using
the native homebrew engine. The enemy AI is a deliberately simplified
placeholder, not reverse-engineered Saturn combat rules. NeXium uses
X11 keyboard events; this does not validate a physical Nintendo Switch
controller. The original Saturn game files, maps, scripts and sprites are
not part of this repository.

Status must only be marked **guest verified** after a real passing
GitHub Actions NeXium job and an archived screenshot receipt.

## First real emulator failure and strict correction

[NeXium #39493124899](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39493124899) successfully built both Switch NROs, passed GCC/Clang elsewhere, completed three independently valid NeXium launches, and passed the entire Stage44/Stage45 duel continuation. The first real X screenshot also decoded the exact second-round checksum `b633fd92746c41cf` (the enemy has taken its turn). However, the separate last-effect square was red `Rejected`, not the cyan `TurnEnded` assumed by the initial Stage48 script, and the live script correctly reported `second_round_passed=false`. The independent verifier also correctly declined to endorse missing later frames.

The [saved guest artifact #12297348087](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39493124899/artifacts/12297348087) contains `stage44-session/runtime-evidence/action-round2-ended.png` and `round2-evidence.json`. The last-effect square is mutable UI state and should not be treated as an immutable acknowledgment of an earlier action after the actual game state has advanced. Rather than dropping the safeguard entirely, the new gate permits only cyan or red at the end-turn checkpoint, *after* exact state fingerprint, separately sampled Scout/ Raider HP bars, cleared selection and unchanged cursor have been checked. The next explicit Y-with-no-selection step must still produce red `Rejected` and no state or HP change.

Two additional host screenshot regressions cover this observed red-overwrite shape, reject unknown colors, and require the canonical battle checksum even when a red receipt appears. **Real Stage48 acceptance remains pending the next complete NeXium run.**
