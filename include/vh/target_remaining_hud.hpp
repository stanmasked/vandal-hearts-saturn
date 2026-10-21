#pragma once
#include "vh/target_damage_hud.hpp"

namespace vh {

// Read-only view of HP remaining after the next *legal* attack.
// Its only source is Stage58's already battle-backed damage forecast.
struct TargetRemainingHud {
    bool visible = false;
    int hp_after = 0;
};

inline TargetRemainingHud target_remaining_hud(const Battle& battle, Pos cursor, int selected) {
    const TargetDamageHud projected = target_damage_hud(battle, cursor, selected);
    if (!projected.visible) return {};
    return {true, projected.remaining_hp};
}

// Occupies the 40px gap after DMG6, before KO; all Stage56-58 glyphs stay put.
inline constexpr int kRemainingHudX = 1140;
inline constexpr int kRemainingHudY = 675;
inline constexpr int kRemainingDigitX = kRemainingHudX + 3 * 8; // "HP "
} // namespace vh
