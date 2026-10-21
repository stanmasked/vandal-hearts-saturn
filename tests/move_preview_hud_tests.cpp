#include "vh/move_preview_hud.hpp"
#include "vh/replay.hpp"

#include <cassert>
#include <cstdio>
#include <limits>

namespace {

void legal_cost_and_budget_are_read_only() {
    const vh::Battle battle = vh::Battle::training();
    const auto before = vh::battle_fingerprint(battle);

    const auto scout = vh::move_preview_hud(battle, 1, {2, 5});
    assert(scout.visible && scout.path_cost == 2 && scout.remaining_points == 2);

    const auto plain = vh::move_preview_hud(battle, 1, {0, 5});
    assert(plain.visible && plain.path_cost == 1 && plain.remaining_points == 3);

    const auto guard = vh::move_preview_hud(battle, 2, {2, 6});
    assert(guard.visible && guard.path_cost == 1 && guard.remaining_points == 2);

    for (int i = 0; i < 100; ++i) {
        assert(vh::move_preview_hud(battle, 1, {2, 5}).path_cost == 2);
        assert(vh::battle_fingerprint(battle) == before);
    }
}

void illegal_or_unavailable_moves_hide_the_hud() {
    const auto battle = vh::Battle::training();
    assert(!vh::move_preview_hud(battle, -1, {2, 5}).visible);
    assert(!vh::move_preview_hud(battle, 999, {2, 5}).visible);
    assert(!vh::move_preview_hud(battle, 3, {5, 1}).visible); // enemy is not a player actor
    assert(!vh::move_preview_hud(battle, 1, {1, 5}).visible); // current tile
    assert(!vh::move_preview_hud(battle, 1, {1, 6}).visible); // occupied by Guard
    assert(!vh::move_preview_hud(battle, 1, {3, 3}).visible); // blocked terrain

    auto spent = vh::Battle::training();
    assert(spent.move(1, {2, 5}));
    const auto spent_hash = vh::battle_fingerprint(spent);
    assert(!vh::move_preview_hud(spent, 1, {3, 5}).visible);
    assert(vh::battle_fingerprint(spent) == spent_hash);
}

void terminal_battle_hides_hud() {
    vh::Battle battle(2, 1);
    battle.add_unit({1, "Hero", vh::Side::Player, {0, 0}, 20, 99, 0, 4, 1});
    battle.add_unit({2, "Enemy", vh::Side::Enemy, {1, 0}, 5});
    assert(battle.attack(1, 2));
    assert(battle.phase() == vh::Phase::Victory);
    const auto terminal_hash = vh::battle_fingerprint(battle);
    assert(!vh::move_preview_hud(battle, 1, {1, 0}).visible);
    assert(vh::battle_fingerprint(battle) == terminal_hash);
}

void font_boundaries_never_truncate_values() {
    vh::Battle battle(3, 1);
    battle.add_unit({1, "Hero", vh::Side::Player, {0, 0}, 20, 8, 2, 1998, 1});
    battle.add_unit({2, "Enemy", vh::Side::Enemy, {2, 0}, 20});
    battle.set_tile({1, 0}, {0, 999, true});
    auto visible = vh::move_preview_hud(battle, 1, {1, 0});
    assert(visible.visible && visible.path_cost == 999 && visible.remaining_points == 999);

    battle.set_tile({1, 0}, {0, 1000, true});
    assert(!vh::move_preview_hud(battle, 1, {1, 0}).visible);

    vh::Battle huge_budget(3, 1);
    huge_budget.add_unit({1, "Hero", vh::Side::Player, {0, 0}, 20, 8, 2,
                          std::numeric_limits<int>::max(), 1});
    huge_budget.add_unit({2, "Enemy", vh::Side::Enemy, {2, 0}, 20});
    assert(!vh::move_preview_hud(huge_budget, 1, {1, 0}).visible);
}

} // namespace

int main() {
    legal_cost_and_budget_are_read_only();
    illegal_or_unavailable_moves_hide_the_hud();
    terminal_battle_hides_hud();
    font_boundaries_never_truncate_values();
    std::puts("Stage64 movement preview HUD: exact cost/budget, hide invalid states, immutable read-only projection");
}
