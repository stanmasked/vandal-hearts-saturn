#pragma once
#include "vh/battle.hpp"

#include <string>

namespace vh {

// Stage56: read-only, frame-local projection of the living enemy UNDER THE
// tactical cursor. An ally selection is neither required nor modified.
struct EnemyHoverHud {
    bool visible = false;
    std::string name;
    int unit_id = 0;
    int hp = 0;
    int attack = 0;
    int defense = 0;
    int range = 0;
};

// Enemy stats may be inspected before selecting any ally and after spending
// an attack. A terminal phase, empty tile, ally or dead enemy hides the card.
// Never cache Unit* between frames; do not inspect the selected ally's ID.
inline EnemyHoverHud enemy_hover_hud(const Battle& battle, Pos cursor) {
    if (battle.phase() != Phase::Player || !battle.in_bounds(cursor)) return {};
    const Unit* unit = battle.unit_at(cursor);
    if (!unit || unit->side != Side::Enemy || unit->hp <= 0) return {};
    return {true, unit->name, unit->id, unit->hp, unit->attack,
            unit->defense, unit->range};
}

// Panel fits completely between Stage55 x350..993 and the right frame edge.
// It is below all gameplay geometry and outside the digest/action receipt.
inline constexpr int kEnemyHudX = 1002;
inline constexpr int kEnemyHudY = 668;
inline constexpr int kEnemyHudWidth = 272;
inline constexpr int kEnemyHudHeight = 44;

} // namespace vh
