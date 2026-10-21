#include "vh/movement_preview_hud.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdio>
#include <limits>
namespace {
void legal_destination_displays_cost_and_remaining_points() {
    const vh::Battle battle = vh::Battle::training();
    const auto before = vh::battle_fingerprint(battle);
    const auto costly = vh::movement_preview_hud(battle, 1, {2, 5});
    assert(costly.visible && costly.unit_id == 1);
    assert(costly.path_cost == 2 && costly.remaining_points == 2);
    const auto ordinary = vh::movement_preview_hud(battle, 1, {1, 4});
    assert(ordinary.visible && ordinary.path_cost == 1 && ordinary.remaining_points == 3);
    const auto guard = vh::movement_preview_hud(battle, 2, {1, 7});
    assert(guard.visible && guard.unit_id == 2);
    assert(guard.path_cost == 1 && guard.remaining_points == 2);
    for (int i = 0; i < 100; ++i) {
        assert(vh::movement_preview_hud(battle, 1, {2, 5}).path_cost == 2);
        assert(vh::battle_fingerprint(battle) == before);
    }
}
void illegal_destinations_never_show_a_cost() {
    const vh::Battle battle = vh::Battle::training();
    assert(!vh::movement_preview_hud(battle, -1, {1, 4}).visible);
    assert(!vh::movement_preview_hud(battle, 999, {1, 4}).visible);
    assert(!vh::movement_preview_hud(battle, 3, {5, 1}).visible);
    assert(!vh::movement_preview_hud(battle, 1, {1, 5}).visible);
    assert(!vh::movement_preview_hud(battle, 1, {1, 6}).visible);
    assert(!vh::movement_preview_hud(battle, 1, {6, 1}).visible);
    assert(!vh::movement_preview_hud(battle, 1, {3, 3}).visible);
    assert(!vh::movement_preview_hud(battle, 1, {0, 0}).visible);
}
void moved_or_terminal_units_do_not_leave_ghost_preview() {
    vh::Battle moved = vh::Battle::training();
    assert(moved.move(1, {1, 4}));
    assert(!vh::movement_preview_hud(moved, 1, {2, 4}).visible);
    vh::Battle victory(2, 1);
    victory.add_unit({1, "P", vh::Side::Player, {0, 0}, 20, 99, 2, 4, 1});
    victory.add_unit({2, "E", vh::Side::Enemy, {1, 0}, 5});
    assert(victory.attack(1, 2));
    assert(victory.phase() == vh::Phase::Victory);
    assert(!vh::movement_preview_hud(victory, 1, {1, 0}).visible);
}
void unsupported_wide_values_are_hidden_not_truncated() {
    vh::Battle battle(3, 1);
    battle.add_unit({1, "P", vh::Side::Player, {0, 0}, 20, 7, 2,
                     std::numeric_limits<int>::max(), 1});
    battle.add_unit({2, "E", vh::Side::Enemy, {2, 0}, 20});
    const auto preview = battle.preview_move(1, {1, 0});
    assert(preview.legal && preview.remaining_points > 99);
    assert(!vh::movement_preview_hud(battle, 1, {1, 0}).visible);
}
}
int main() {
    legal_destination_displays_cost_and_remaining_points();
    illegal_destinations_never_show_a_cost();
    moved_or_terminal_units_do_not_leave_ghost_preview();
    unsupported_wide_values_are_hidden_not_truncated();
    std::puts("Stage64 movement preview HUD: exact cost/remaining, legal-only, read-only, no stale/overflow text");
}
