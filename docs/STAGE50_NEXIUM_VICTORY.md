# Stage50 — full four-round victory in actual NeXium (ROM-free)

## Foundation

The preserved [Stage48 NeXium #39496473179](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473179) and [GCC/Clang #39496473185](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473185) both passed on commit `c92073dc`. Three separate emulator starts and actual round 2 attacker/defender HP pixel readings passed, as did cancellation, selection, double-attack rejection, and clean NeXium close. The [Stage48 PNG ZIP](https://github.com/stanmasked/vandal-hearts-saturn/actions/runs/39496473179/artifacts/12298944591) is the untouched baseline.

Stage49 introduced a host-only C++ full four-round `duel_victory_contract`. Stage50 strengthens it with **exact whole-state FNV64 goldens** and a new uninterrupted screenshot-gated continuation of the existing, separate native Switch duel NRO.

## New canonical checkpoints

| Action/checkpoint | Canonical FNV64 | Scout HP | Raider HP |
| --- | --- | ---: | ---: |
| Stage48 second-round hit / rejected retry | `203a8823191e6018` | 19 | 8 |
| X: Raider counterattack, player round 3 | `1b81f3931a165925` | 16 | 8 |
| Select Scout; Y: third-round attack | `7849484ccfd7a0de` | 16 | 2 |
| Y repeat rejected, same state | `7849484ccfd7a0de` | 16 | 2 |
| X: Raider counterattack, player round 4 | `984023d699c803db` | 13 | 2 |
| Select Scout; Y: defeating attack | `6097117b6c951fb6` | 13 | **0** |
| X attempted after Victory; rejected | `6097117b6c951fb6` | 13 | 0 |
| Y attempted after Victory; rejected | `6097117b6c951fb6` | 13 | 0 |

The expected fingerprints are recalculated from the exact native `battle_fingerprint` byte-serialization rules, pinned inside `tests/duel_victory_tests.cpp`. The actual screenshot decoder must read all 64 displayed state cells and the three reference anchors for each accepted action.

## Real X11/NeXium proof requirements

- The live [`tools/nexium_duel_victory.py`](../tools/nexium_duel_victory.py) starts only after Stage44 first hit, Stage45 cancel/reselect and Stage48 authentic second-round hit/rejection succeeded **in the same running native guest**.
- Both end-turn transitions must show the precise subsequent FNV64, visually reduced Scout HP bar (19→16→13), unchanged Raider HP, removed Scout outline, and unchanged cursor. The mutable last-effect square may be cyan TurnEnded or the previously observed red Rejected, but only with all canonical state/HP/selection checks satisfied.
- Each re-selection must show the blue selected-effect square and visible yellow Scout border, following screenshot-confirmed bounded arrow navigation. Each attack must show purple Attacked, correct new FNV64 and Raider bar change (8→2→0).
- Defeat must **remove the Raider pawn and HP bar from the guest screenshot**, alongside the terminal victory state hash. The independent audit checks the two-pixel 2HP bar separately from the absent HP bar at zero. A forged zero-HP receipt with even a still-visible red Raider pawn is rejected.
- Pressing X or Y again after victory must show red Rejected, keep the same full 64-bit state signature, Scout HP13, Raider HP0, and unchanged cursor/selection. No post-victory extra round, repeated kill or phantom damage can be accepted.
- The independent `--verify-dir` command reopens and rechecks **all preceding Stage44–48 real PNG chains** and nine new Stage50 screenshots, including a bounded set of alternative retry filenames. JSON report fields alone can never confirm passing.

## Negative/synthetic suite

`tests/test_nexium_duel_victory.py` covers complete simulated image-chain acceptance, two missed X events, incorrect HP, unknown end-turn receipt, missing selection, unregistered third-round hit, forged living HP bar at 0, defeated Raider sprite still present, incorrect victory hash, invalid post-victory X state change and misreported Y success. Synthetic tests exercise real image readers with generated registered PNGs and are **not guest proof**.

## CI integration and status

`scripts/nexium_capture.sh` gates this probe behind `NEXIUM_VICTORY_PROBE=1` and a successful Stage48 live route. The original default tactical demo stays unchanged. `.github/workflows/switch-nro.yml` extends the separate duel guest time budget from 215 to 320 seconds and requires a fresh independent `python3 -m tools.nexium_duel_victory --verify-dir stage44-session/runtime-evidence` check before NeXium can pass. Failures save the artifact for analysis.

**Never report Stage50 as actual victory verified until a complete real NeXium run is green.** The original Sega Saturn game, its copyrighted sprites/resources, and a physical Switch controller are not part of this ROM-free experiment.
