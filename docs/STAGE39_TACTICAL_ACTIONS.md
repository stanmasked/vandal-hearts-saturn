# Stage 39 — one ROM-free action contract for keyboard and Switch gamepad

## Scope and reason

Stage38 successfully ran the native synthetic tactics NRO through three independent NeXium sessions with screenshot-verified Right input and clean exit. That establishes the render/input path but not the correctness of game actions. Previously the SDL layer directly implemented selection, movement, attack and end-turn, so these behaviors could not be tested without SDL and were not shared as a single explicit contract.

## Implementation

- New SDL-free C++17 `include/vh/training_controls.hpp` exports `TrainingAction`, `TrainingEffect`, `TrainingUi`, and `apply_training_action`.
- Cursor movements, selection of a friendly unit, legal/rejected tactical movement, attack, end-turn, cancellation and quit requests go through one function. The same `Battle` core and same map collision/attack rules remain in use. All gameplay changes still call the existing native C++ logic.
- Refactored `src/ui/sdl_main.cpp`: keyboard Enter/Space, Y, X, Backspace, arrows/WASD and SDL gamepad A/Y/X/B/D-pad all dispatch to the **same action function**. The SDL main loop still emits real `VH_STATE` and `VH_CURSOR` on actual state changes; the 64-bit visual state digest is unchanged.
- `tests/training_controls_tests.cpp` verifies selection, cursor motion without battle mutation, accepted Scout move, rejected duplicate move, attack rejection without a nearby target, cancellation, placeholder enemy phase progression, legal melee damage (20 → 14 HP), one-attack-per-turn restriction, invalid target, map edges and quit.
- Registers CTest `training_controls_contract` in Host GCC/Clang workflow. The header uses no SDL2 or original licensed resources, and is compiled as part of the actual SDL source for the Nintendo Switch NRO.

## Verification

Locally compiled the actual Stage01 tactical core and the new action contract on GCC 14 and Clang 17, with **2/2 CTest** (`tactical_core`, `training_controls_contract`) passing under both. These host tests do not claim the latest NRO or actual controller input has passed yet; new-head GitHub Actions must verify that separately.

## Next

Use a real NeXium input sequence to confirm selecting the Scout, moving to tile (2,5), and observing the expected *changed* 64-bit battle fingerprint. Separately test real Joy-Con/Pro Controller events, then continue private identification of the authentic Sega Saturn first mission and assets. Original Saturn BIN/CUE/sprites/music are never committed.
