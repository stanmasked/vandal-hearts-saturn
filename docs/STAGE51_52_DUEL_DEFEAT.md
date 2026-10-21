# Stages 51–52 — defeat and immutable terminal outcome (ROM-free)

## Baseline and scope

[Stage50 fully green NeXium #39502774414](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39502774414) and [native GCC/Clang #39502774119](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39502774119) on `b160fa56` remain the pinned original homebrew **Victory** baseline. The separate [real guest PNG artifact #12305597502](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39502774414/artifacts/12305597502) is unaffected by the new test route.

Stages 51–52 check the **opposite** terminal outcome with the identical isolated ROM-free `stage44_attack_duel()` fixture: Scout has 22 HP, Raider has 20 HP and deals 3 HP at the end of each player's round. Scout never attacks, so the Raider wins on the eighth enemy turn. This is an original tactical prototype, not authentic Sega Saturn gameplay or a port of original assets.

## Stage51: native C++ negative-outcome regression

A separate CTest `duel_defeat_contract` in `tests/duel_defeat_tests.cpp` drives eight native `TrainingAction::EndTurn` actions through the real `Battle` enemy AI and end-turn reducer. It enforces: HP22→19→16→13→10→7→4→1→0, exactly eight enemy attacks, **Phase::Defeat on battle round 8**, no round 9, Raider HP20 unchanged, `Defeat.` UI status, no Scout pawn returned by `unit_at`, and the selection cleared on the fatal turn. After defeat, both UI input actions and direct core attacks, moves and end turns must return rejection without mutating the full battle FNV64 fingerprint. Earlier round goldens and final death hash are independently pinned.

## Stage52: separate genuine NeXium defeat route

A new `NEXIUM_DEFEAT_PROBE=1` switch in `scripts/nexium_capture.sh` drives `tools/nexium_duel_defeat.py` **without the victory probe**, in an isolated `stage52-session` guest. The main Stage50 guest still runs and must pass independently before the workflow is green.

Each of eight X key actions must have its own screenshot confirming the exact 64-bit state fingerprint, corresponding visually shortened Scout HP green bar, *unchanged* Raider full 20HP bar and living red pawn, unchanged cursor and no Scout selection border. Only a genuine end-turn fingerprint transition allows a red overwritten last-effect receipt; otherwise cyan TurnEnded is expected. A single retry is allowed only from a frame with the exact unchanged previous battle fingerprint and unchanged HP.

| End-turn number | Battle round | Scout HP | Expected entire guest state |
| ---: | ---: | ---: | --- |
| 0 | 1 | 22 | `9376e23745926630` |
| 1 | 2 | 19 | `cbda1f619741fbf5` |
| 2 | 3 | 16 | `63612b72203eb079` |
| 3 | 4 | 13 | `66070dc6b67566ad` |
| 4 | 5 | 10 | `cdeb89c69e09b7e9` |
| 5 | 6 | 7 | `413b700b4a1466e5` |
| 6 | 7 | 4 | `a6cd3306a9d5b5e1` |
| 7 | 8 | 1 | `11c830508d90884d` |
| 8 | 8, **Defeat** | **0** | `3b0411b006f113c1` |

After the eighth strike, registered pixels must show **no Scout HP bar, no blue Scout pawn**, but continued full Raider HP20 and a living red Raider. New X, Y and Return inputs must each show a red Rejected receipt and preserve the **same** final battle checksum. The independent `--verify-dir` audit reopens the baseline screenshot and all eight real round PNGs plus three post-defeat screenshots; JSON success fields alone cannot override any failed frame check. Images are archived even after failure.

Twelve independent synthetic image adversarial regressions guard missed X events, false hashes, forged HP/sprites, unknown receipts, an extra round and missing post-defeat rejections. They are **not** substitute for real guest proof.

**Stage52 remains unverified until an actual green NeXium job produces all these guest PNGs.** A real Switch Joy-Con controller or original Saturn game data are not exercised.
