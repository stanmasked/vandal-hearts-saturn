#pragma once

#include "vh/battle.hpp"

namespace vh {

// Original, ROM-free display model: no SDL dependency or Battle mutation.
// The previous green section survives the predicted strike; the purple
// section will be lost. Both are scaled to the *current* defender HP because
// this training engine does not yet have a maximum-HP stat.
inline constexpr int kPreviewBarWidth = 176;
inline constexpr int kPreviewBarX = 145;
inline constexpr int kPreviewBarY = 680;
inline constexpr int kPreviewBarHeight = 14;

struct AttackPreviewHud {
    bool visible = false;
    bool decisive = false;
    int hp_before = 0;
    int hp_after = 0;
    int damage = 0;
    int remaining_width = 0;
    int damage_width = 0;
};

inline AttackPreviewHud attack_preview_hud(const Battle& battle,
                                          int selected, Pos cursor) {
    if (selected < 0 || battle.phase() != Phase::Player) return {};
    const Unit* attacker = battle.find_unit(selected);
    const Unit* defender = battle.unit_at(cursor);
    if (!attacker || !defender || attacker->side != Side::Player) return {};
    const AttackPreview p = battle.preview_attack(selected, defender->id);
    if (!p.legal || defender->hp <= 0) return {};
    // 64-bit intermediate avoids overflow for unusual legal unit HP values.
    const int remains = static_cast<int>(
        (static_cast<long long>(p.remaining_hp) * kPreviewBarWidth) / defender->hp);
    return {true, p.ends_battle, defender->hp, p.remaining_hp, p.damage,
            remains, kPreviewBarWidth - remains};
}
} // namespace vh
