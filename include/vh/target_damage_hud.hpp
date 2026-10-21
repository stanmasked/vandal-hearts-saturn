#pragma once
#include "vh/enemy_attack_cue.hpp"

namespace vh {
// Read-only damage HUD. Values come ONLY from the same Battle::preview_attack
// used to commit the actual attack; never calculate an alternate damage rule.
struct TargetDamageHud {
    bool visible = false;
    int damage = 0;
    int remaining_hp = 0;
    bool lethal = false;
};

inline TargetDamageHud target_damage_hud(const Battle& battle, Pos cursor, int selected) {
    const EnemyAttackCue cue = enemy_attack_cue(battle, cursor, selected);
    if (cue.state != EnemyAttackCueState::Ready || cue.damage <= 0) return {};
    return {true, cue.damage, cue.remaining_hp, cue.decisive};
}

// Stage58 text takes the free top center of the Stage56 enemy card.
// Stage57 cue x1242..1265, Stage56 name ends before x1070.
inline constexpr int kDamageHudX = 1090;
inline constexpr int kDamageHudY = 675;
inline constexpr int kDamageDigitX = kDamageHudX + 4 * 8;
inline constexpr int kDamageKoX = 1188;
} // namespace vh
