# Stage57 — combat availability cue over enemy

## Goal

Continue from fully verified Stage56 `eba20521`: GCC and Clang 14/14 CTest,
370/370 Python each, Switch NRO and actual Stage56 NeXium screenshots (HP
20/14/8/2 and hidden on ally/Victory/Defeat). Preserve existing combat hashes,
actual attack rules and sample positions.

## Functionality

An asset-free 24x10 status strip at x1242..1265 / y675..684 is drawn in
Stage56's enemy stats panel. It is pure UI and uses the authoritative
`Battle::preview_attack` to distinguish:

- Slate blue: enemy hovered, no valid allied unit selected, inspect only
- Gold: selected allied unit can legally attack the hovered enemy now
- Purple: selected ally has already attacked
- Dusty red: ally selected but attack is currently illegal (e.g. out of range)
- Hidden: empty/allied cursor or terminal Victory/Defeat

Native view `enemy_attack_cue` also exposes the previewed damage and HP
remaining *only* on a legal attack. It never performs an attack, changes
input mapping, stores pointers or modifies any battle/replay fingerprint.

The pixel cue is deliberately outside all Stage54, Stage55 and Stage56
sample positions. The old Stage56 real guest checker remains unchanged.

## Evidence gates

C++ `enemy_attack_cue_contract` checks no-selection, selected, legal preview,
spent action, out of range, dead/terminal, Scout and Raider round progression,
and unchanged golden hashes. Python tests forge incorrect cue colors and
attempt a ghost indicator after terminal phases. The real NeXium auditor
`tools.nexium_enemy_attack_cue.py` requires Stage56 proof first, then
reopens actual registered Stage44/50/52 guest PNGs for
Ready -> Spent -> InspectOnly -> Spent -> Ready -> Hidden states.

**No NeXium success claim until Stage57 workflow passes on the same head.**
Still only an original ROM-free tactics prototype, not the Sega Saturn game.
