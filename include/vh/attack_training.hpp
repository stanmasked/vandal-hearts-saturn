#pragma once
#include "vh/battle.hpp"

namespace vh {
// Stage44 opt-in duel: a deliberately ORIGINAL ROM-free training fixture.
// Built into a separate NRO, never replacing the established Stage43 scene.
inline Battle stage44_attack_duel() {
    Battle battle(8, 8);
    battle.add_unit({1, "Scout", Side::Player, {1, 5}, 22, 8, 3, 4, 1});
    battle.add_unit({3, "Raider", Side::Enemy, {2, 5}, 20, 6, 2, 3, 1});
    return battle;
}
}  // namespace vh
