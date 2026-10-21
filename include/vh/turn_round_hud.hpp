#pragma once
#include "vh/battle.hpp"

namespace vh {

// Stage61: a compact display-only round counter in the existing legend gap.
// The current primitive pixel font/space supports up to two decimal digits.
// Suppress rather than misrepresent unsupported round values or terminal play.
struct TurnRoundHud {
    bool visible = false;
    int round = 0;
};

inline TurnRoundHud turn_round_hud(const Battle& battle) {
    if (battle.phase() != Phase::Player || battle.round() < 1 ||
        battle.round() > 99) return {};
    return {true, battle.round()};
}

inline constexpr int kRoundHudX = 93;
inline constexpr int kRoundHudY = 675;
inline constexpr int kRoundHudWidth = 43;
inline constexpr int kRoundHudHeight = 25;
inline constexpr int kRoundTextX = 97;
inline constexpr int kRoundTextY = 681;
inline constexpr int kRoundDigitX = kRoundTextX + 2 * 8; // "R "

} // namespace vh
