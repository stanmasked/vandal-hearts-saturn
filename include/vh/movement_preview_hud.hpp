#pragma once
#include "vh/battle.hpp"
namespace vh {
struct MovementPreviewHud {
    bool visible = false;
    int unit_id = 0;
    int path_cost = 0;
    int remaining_points = 0;
};
inline MovementPreviewHud movement_preview_hud(const Battle& battle,
                                                int selected, Pos cursor) {
    if (selected < 0 || battle.phase() != Phase::Player) return {};
    const Unit* unit = battle.find_unit(selected);
    if (!unit || unit->hp <= 0 || unit->side != Side::Player || unit->moved)
        return {};
    const MovePreview preview = battle.preview_move(selected, cursor);
    if (!preview.legal || preview.path_cost < 1 ||
        preview.path_cost > 99 || preview.remaining_points < 0 ||
        preview.remaining_points > 99) return {};
    return {true, selected, preview.path_cost, preview.remaining_points};
}
inline constexpr int kMovementPreviewX = 16;
inline constexpr int kMovementPreviewY = 600;
inline constexpr int kMovementPreviewWidth = 190;
inline constexpr int kMovementPreviewHeight = 42;
inline constexpr int kMovementPreviewTextX = 36;
inline constexpr int kMovementPreviewTextY = 610;
} // namespace vh
