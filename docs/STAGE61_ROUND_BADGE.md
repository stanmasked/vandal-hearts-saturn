# Stage61 — round indicator in player legend

Base revision is Stage60 `e20ba08`. Stage59 is fully guest-verified
(GCC/Clang 17/17 and Python 406/406 each, NRO, NeXium).
Stage60 runs are separately in progress; this stage is independent and
does not mutate or push to Stage60's branch.

Player-phase round is displayed as a small white bitmap `R 1` / `R 2`
/ `R 4` within a dark badge in unused bottom strip x93..135 and
y675..699. Other HUD regions Stage54 (x145..321), Stage55 (x354..),
Stage56 (x1002..) and game controls stay unchanged. Badge is hidden on
terminal Victory/Defeat, and deliberately hidden for rounds above 99
until the text area can be expanded.

The pure `turn_round_hud(Battle&)` projection reads `Battle::round()`
and `Battle::phase()` only. It never stores pointers, changes actions,
damage, result hashes, movement, or the original ROM-free fixture.

C++ native test validates rounds 1..4 and terminal disappearance,
100x repeated read-only projection and golden battle hashes; 15 Python
synthetic/adversarial image tests check exact whole-glyph pixels,
registration shifts, two-digit rounds and forged/ghost badges.

CI reopens actual NeXium screenshots after independently validating
Stage44/52/54–60, then checks R1 before/after initial attack, R2 after
EndTurn, R4 before final blow, and no panel after victory/defeat.

No Stage61 success claim until the new head passes GCC, Clang,
Nintendo Switch NRO and real NeXium image gates. This remains an
original ROM-free tactics prototype, not a Saturn game data port.
