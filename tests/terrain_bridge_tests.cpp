#include "vh/terrain_bridge.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

namespace {
const std::string kSynthetic =
    "VH_TERRAIN_UNVERIFIED_V1\n"
    "SIZE 2 2\n"
    "CELL 0 0 0 1 1\n"
    "CELL 1 0 0 2 1\n"
    "CELL 0 1 0 1 1\n"
    "CELL 1 1 0 1 1\n";

bool rejects(const std::string& source) {
    try {
        std::istringstream stream(source);
        (void)vh::load_unverified_terrain(stream);
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

void accepts_invented_numeric_geometry_only() {
    std::istringstream stream(kSynthetic);
    vh::Battle battle = vh::load_unverified_terrain(stream);
    assert(battle.width() == 2 && battle.height() == 2);
    assert(battle.units().empty());
    assert(battle.tile({1, 0}).terrain_cost == 2);
    assert(battle.tile({0, 0}).elevation == 0);
    assert(battle.tile({1, 1}).walkable);
    battle.add_unit({1, "synthetic P", vh::Side::Player, {0, 0}, 20, 7, 2, 3, 1});
    battle.add_unit({2, "synthetic E", vh::Side::Enemy, {1, 1}, 20, 7, 2, 3, 1});
    const auto before = vh::battle_fingerprint(battle);
    const auto projected = battle.preview_move(1, {1, 0});
    assert(projected.legal && projected.path_cost == 2 && projected.remaining_points == 1);
    assert(vh::battle_fingerprint(battle) == before);
}

void rejects_untrustworthy_or_incomplete_grid() {
    assert(rejects(""));
    assert(rejects("VH_TERRAIN_V1\nSIZE 2 2\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 129 1\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 0 1\n"));
    assert(rejects(kSynthetic.substr(0, kSynthetic.find("CELL 1 1"))));
    assert(rejects(kSynthetic + "UNTRUSTED_PAYLOAD\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 1 1\nCELL 0 0 0 0 1\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 1 1\nCELL 0 0 0 1 2\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 1 1\nCELL 1 0 0 1 1\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 1 1\nCELL 0 0 100001 1 1\n"));
    assert(rejects("VH_TERRAIN_UNVERIFIED_V1\nSIZE 1 1\nCELL 0 0 0 2147483647 1\n"));
}

} // namespace
int main() {
    accepts_invented_numeric_geometry_only();
    rejects_untrustworthy_or_incomplete_grid();
}
