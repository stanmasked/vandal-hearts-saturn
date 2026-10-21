#pragma once
#include "vh/battle.hpp"

#include <algorithm>
#include <string>

namespace vh {

// Stage55: read-only view of the selected LIVE allied fighter. The HUD never
// carries pointers across frames and cannot change the Battle or StateDigest.
struct SelectedUnitHud {
    bool visible = false;
    std::string name;
    int unit_id = 0;
    int hp = 0;
    int attack = 0;
    int defense = 0;
    int range = 0;
    bool moved = false;
    bool acted = false;
};

inline SelectedUnitHud selected_unit_hud(const Battle& battle, int selected) {
    if (selected < 0 || battle.phase() != Phase::Player) return {};
    const Unit* unit = battle.find_unit(selected);
    if (!unit || unit->hp <= 0 || unit->side != Side::Player) return {};
    return {true, unit->name, unit->id, unit->hp, unit->attack, unit->defense,
            unit->range, unit->moved, unit->acted};
}

// All Stage55 samples lie entirely to the RIGHT of the Stage54 damage HUD;
// there is no overlap with actual Stage54 screenshot-based pixel gates or
// the top-right FNV-64 visual fingerprint.
inline constexpr int kUnitHudX = 354;
inline constexpr int kUnitHudY = 670;
inline constexpr int kUnitHudStatusX = 953;
inline constexpr int kUnitHudStatusY = 683;
inline constexpr int kUnitHudMarkerW = 8;
inline constexpr int kUnitHudMarkerH = 34;

} // namespace vh
