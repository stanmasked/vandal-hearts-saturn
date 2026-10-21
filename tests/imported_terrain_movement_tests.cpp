// Stage70: the private-geometry format must feed the *actual* native tactics
// core without changing preview/move legality. All geometry is invented.
#include "vh/terrain_bridge.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

std::string terrain_text(int central_cost = 9, int top_elevation = 0,
                         bool central_walkable = true) {
    std::ostringstream out;
    out << "VH_TERRAIN_UNVERIFIED_V1\nSIZE 3 3\n";
    for (int y = 0; y < 3; ++y) {
        for (int x = 0; x < 3; ++x) {
            const int elevation = x == 1 && y == 0 ? top_elevation : 0;
            const int cost = x == 1 && y == 1 ? central_cost : 1;
            const int walkable = x == 1 && y == 1 ? central_walkable : 1;
            out << "CELL " << x << ' ' << y << ' ' << elevation << ' '
                << cost << ' ' << walkable << '\n';
        }
    }
    return out.str();
}

vh::Battle import_grid(int central_cost = 9, int top_elevation = 0,
                       bool central_walkable = true) {
    std::istringstream input(terrain_text(central_cost, top_elevation,
                                         central_walkable));
    return vh::load_unverified_terrain(input);
}

vh::Battle manual_grid(int central_cost = 9, int top_elevation = 0,
                       bool central_walkable = true) {
    vh::Battle reference(3, 3);
    for (int y = 0; y < 3; ++y) {
        for (int x = 0; x < 3; ++x) {
            reference.set_tile(
                {x, y},
                {x == 1 && y == 0 ? top_elevation : 0,
                 x == 1 && y == 1 ? central_cost : 1,
                 x == 1 && y == 1 ? central_walkable : true});
        }
    }
    return reference;
}

void add_test_units(vh::Battle& battle, int move_points = 4) {
    // The bridge deliberately does not import *any* units. These entirely
    // invented combat attributes are injected only by the host tests.
    assert(battle.units().empty());
    battle.add_unit({101, "invented ally", vh::Side::Player,
                     {0, 1}, 20, 8, 2, move_points, 1});
    battle.add_unit({102, "invented foe", vh::Side::Enemy,
                     {2, 2}, 20, 7, 2, 4, 1});
}

void compare_grid(const vh::Battle& actual, const vh::Battle& expected) {
    assert(actual.width() == expected.width());
    assert(actual.height() == expected.height());
    for (int y = 0; y < actual.height(); ++y) {
        for (int x = 0; x < actual.width(); ++x) {
            const auto a = actual.tile({x, y});
            const auto b = expected.tile({x, y});
            assert(a.elevation == b.elevation);
            assert(a.terrain_cost == b.terrain_cost);
            assert(a.walkable == b.walkable);
        }
    }
}

void compare_native_preview_contract(vh::Battle& actual, vh::Battle& expected) {
    compare_grid(actual, expected);
    assert(vh::battle_fingerprint(actual) == vh::battle_fingerprint(expected));
    const auto baseline = vh::battle_fingerprint(actual);
    assert(actual.reachable(101) == expected.reachable(101));
    for (int y = 0; y < actual.height(); ++y) {
        for (int x = 0; x < actual.width(); ++x) {
            const vh::Pos dest{x, y};
            const auto a = actual.preview_move(101, dest);
            const auto b = expected.preview_move(101, dest);
            assert(a.legal == b.legal && a.path_cost == b.path_cost &&
                   a.remaining_points == b.remaining_points);
        }
    }
    assert(vh::battle_fingerprint(actual) == baseline);
    assert(vh::battle_fingerprint(expected) == baseline);
}

void costly_direct_route_uses_cheaper_detour() {
    auto imported = import_grid();
    auto reference = manual_grid();
    add_test_units(imported);
    add_test_units(reference);
    compare_native_preview_contract(imported, reference);

    // Direct route through (1,1) costs 9. The upper 4-step detour wins.
    const auto forecast = imported.preview_move(101, {2, 1});
    assert(forecast.legal && forecast.path_cost == 4 &&
           forecast.remaining_points == 0);
    assert(imported.preview_move(101, {2, 2}).legal == false); // foe occupied
    assert(imported.move(101, {2, 1}));
    assert(reference.move(101, {2, 1}));
    assert(vh::battle_fingerprint(imported) ==
           vh::battle_fingerprint(reference));
    assert(imported.find_unit(101)->moved);
    assert(!imported.preview_move(101, {1, 1}).legal);
    assert(!imported.move(101, {1, 1}));
}

void observed_cost_change_alters_tactics_without_fake_stats() {
    auto imported = import_grid(1);
    auto reference = manual_grid(1);
    add_test_units(imported);
    add_test_units(reference);
    compare_native_preview_contract(imported, reference);
    const auto direct = imported.preview_move(101, {2, 1});
    assert(direct.legal && direct.path_cost == 2 &&
           direct.remaining_points == 2);
    assert(imported.move(101, {2, 1}));
}

void cliff_excludes_upper_route_and_occupied_enemy_blocks_lower() {
    auto imported = import_grid(9, 2);
    auto reference = manual_grid(9, 2);
    add_test_units(imported);
    add_test_units(reference);
    compare_native_preview_contract(imported, reference);
    assert(!imported.preview_move(101, {2, 1}).legal);
    assert(!imported.move(101, {2, 1}));
    assert((imported.find_unit(101)->pos == vh::Pos{0, 1}));
}

void blocked_center_forces_upper_path() {
    auto imported = import_grid(1, 0, false);
    auto reference = manual_grid(1, 0, false);
    add_test_units(imported);
    add_test_units(reference);
    compare_native_preview_contract(imported, reference);
    assert(!imported.preview_move(101, {1, 1}).legal);
    const auto detour = imported.preview_move(101, {2, 1});
    assert(detour.legal && detour.path_cost == 4);
}

void insufficient_budget_hides_detour() {
    auto imported = import_grid();
    auto reference = manual_grid();
    add_test_units(imported, 3);
    add_test_units(reference, 3);
    compare_native_preview_contract(imported, reference);
    assert(!imported.preview_move(101, {2, 1}).legal);
}

void failed_import_cannot_produce_a_partial_battle() {
    std::string corrupt = terrain_text();
    const auto marker = corrupt.find("CELL 1 2 ");
    assert(marker != std::string::npos);
    corrupt.erase(marker);
    std::istringstream input(corrupt);
    bool rejected = false;
    try {
        (void)vh::load_unverified_terrain(input);
    } catch (const std::invalid_argument&) {
        rejected = true;
    }
    assert(rejected);
}

} // namespace

int main() {
    costly_direct_route_uses_cheaper_detour();
    observed_cost_change_alters_tactics_without_fake_stats();
    cliff_excludes_upper_route_and_occupied_enemy_blocks_lower();
    blocked_center_forces_upper_path();
    insufficient_budget_hides_detour();
    failed_import_cannot_produce_a_partial_battle();
}
