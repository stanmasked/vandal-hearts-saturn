#pragma once

#include "vh/battle.hpp"

namespace vh {

// Stage64: read-only destination-cost display. It only exposes a legal move
// for the currently selected ally; it never mutates Battle or consumes action.
// The tiny built-in SDL font can show "COST 999 LEFT 999" in 18 glyph cells,
// so larger values are suppressed instead of being silently truncated.
struct MovePreviewHud {
    bool visible = false;
    int path_cost = 0;
    int remaining_points = 0;
};

inline constexpr int kMovePreviewHudX = 500;
inline constexpr int kMovePreviewHudY = 670;

inline MovePreviewHud move_preview_hud(const Battle& battle, int selected, Pos cursor) {
    if (selected < 0 || battle.phase() != Phase::Player) return {};
    const MovePreview move = battle.preview_move(selected, cursor);
    if (!move.legal || move.path_cost > 999 || move.remaining_points > 999) return {};
    return {true, move.path_cost, move.remaining_points};
}

} // namespace vh
