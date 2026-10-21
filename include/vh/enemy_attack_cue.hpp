#pragma once
#include "vh/enemy_hover_hud.hpp"

namespace vh {

// Stage57: independent, read-only interpretation of Battle::preview_attack
// for the ENEMY currently under the cursor. Does not give legal attack
// permission: the existing battle engine is the only source of truth.
enum class EnemyAttackCueState { Hidden, InspectOnly, Ready, Spent, Blocked };
struct EnemyAttackCue {
    EnemyAttackCueState state = EnemyAttackCueState::Hidden;
    int damage = 0;
    int remaining_hp = 0;
    bool decisive = false;
};

inline EnemyAttackCue enemy_attack_cue(const Battle& battle, Pos cursor, int selected) {
    const EnemyHoverHud hovered = enemy_hover_hud(battle, cursor);
    if (!hovered.visible) return {};
    if (selected < 0) return {EnemyAttackCueState::InspectOnly};
    const Unit* attacker = battle.find_unit(selected);
    if (!attacker || attacker->side != Side::Player || attacker->hp <= 0)
        return {EnemyAttackCueState::InspectOnly};
    if (attacker->acted) return {EnemyAttackCueState::Spent};
    const AttackPreview projected = battle.preview_attack(selected, hovered.unit_id);
    if (!projected.legal) return {EnemyAttackCueState::Blocked};
    return {EnemyAttackCueState::Ready, projected.damage,
            projected.remaining_hp, projected.ends_battle};
}

// Entirely inside Stage56 card, away from old name, digits and auditor pixels.
inline constexpr int kEnemyCueX = 1242;
inline constexpr int kEnemyCueY = 675;
inline constexpr int kEnemyCueWidth = 24;
inline constexpr int kEnemyCueHeight = 10;

} // namespace vh
