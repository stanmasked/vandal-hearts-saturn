#pragma once
#include "vh/target_remaining_hud.hpp"

namespace vh {

// Stage60: a pure visual split of the target's CURRENT hit points.
// Green = HP still present after next legal hit; red = HP that hit removes.
// The ROM-free Unit intentionally has no max-HP field. Using current HP
// as denominator makes this a within-next-hit split, NOT total-health meter.
struct TargetHealthBar {
    bool visible = false;
    int current_hp = 0;
    int hp_after = 0;
    int remaining_width = 0;
    int damage_width = 0;
};

inline constexpr int kHealthBarX = 1020;
inline constexpr int kHealthBarY = 705;
inline constexpr int kHealthBarWidth = 220;
inline constexpr int kHealthBarHeight = 5;

inline TargetHealthBar target_health_bar(const Battle& battle, Pos cursor, int selected) {
    const TargetRemainingHud forecast = target_remaining_hud(battle, cursor, selected);
    if (!forecast.visible) return {};
    const Unit* target = battle.unit_at(cursor);
    if (!target || target->side != Side::Enemy || target->hp <= 0 ||
        forecast.hp_after < 0 || forecast.hp_after > target->hp) return {};
    const int green = static_cast<int>(
        static_cast<long long>(forecast.hp_after) * kHealthBarWidth / target->hp);
    return {true, target->hp, forecast.hp_after, green, kHealthBarWidth - green};
}

} // namespace vh
