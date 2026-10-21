#include "vh/battle.hpp"
#include "vh/replay.hpp"

#include <cassert>
#include <cstdio>
#include <limits>

namespace {

void costs_and_invariants() {
    const vh::Battle battle = vh::Battle::training();
    const auto before = vh::battle_fingerprint(battle);

    const auto terrain = battle.preview_move(1, {2, 5});
    assert(terrain.legal && terrain.path_cost == 2 && terrain.remaining_points == 2);

    const auto plain = battle.preview_move(1, {0, 5});
    assert(plain.legal && plain.path_cost == 1 && plain.remaining_points == 3);

    const auto guard = battle.preview_move(2, {2, 6});
    assert(guard.legal && guard.path_cost == 1 && guard.remaining_points == 2);

    // Unwalkable tile, occupied ally, unchanged position, off-map, unknown
    // unit and enemy never yield a legal player movement projection.
    assert(!battle.preview_move(1, {3, 3}).legal);
    assert(!battle.preview_move(1, {1, 6}).legal);
    assert(!battle.preview_move(1, {1, 5}).legal);
    assert(!battle.preview_move(1, {-1, 5}).legal);
    assert(!battle.preview_move(999, {2, 5}).legal);
    assert(!battle.preview_move(3, {5, 1}).legal);
    for (int i = 0; i < 100; ++i) {
        assert(battle.preview_move(1, {2, 5}).path_cost == 2);
        assert(vh::battle_fingerprint(battle) == before);
    }
}

void detours_and_cliffs() {
    vh::Battle battle(3, 3);
    battle.add_unit({1, "P", vh::Side::Player, {0, 1}, 20, 8, 1, 4, 1});
    battle.add_unit({2, "E", vh::Side::Enemy, {2, 2}, 20});
    battle.set_tile({1, 1}, {0, 1, false});
    const auto detour = battle.preview_move(1, {2, 1});
    assert(detour.legal && detour.path_cost == 4 && detour.remaining_points == 0);

    battle.set_tile({1, 0}, {2, 1, true}); // impassable upward cliff
    assert(!battle.preview_move(1, {2, 1}).legal);
}

void huge_budgets_must_not_teleport_or_overflow() {
    vh::Battle battle(4, 1);
    battle.add_unit({1, "P", vh::Side::Player, {0, 0}, 20, 7, 2,
                     std::numeric_limits<int>::max(), 1});
    battle.add_unit({2, "E", vh::Side::Enemy, {3, 0}, 20});
    battle.set_tile({1, 0}, {0, 1, false});
    // Prior code used an INF sentinel smaller than INT_MAX, allowing a
    // high-budget actor to cross a completely blocked tile.
    assert(!battle.preview_move(1, {2, 0}).legal);
    assert(!battle.move(1, {2, 0}));
    assert((battle.find_unit(1)->pos == vh::Pos{0, 0}));

    battle.set_tile({1, 0}, {0, std::numeric_limits<int>::max(), true});
    assert(!battle.preview_move(1, {1, 0}).legal);
    assert(!battle.preview_move(1, {2, 0}).legal);
    assert(!battle.move(1, {2, 0})); // no signed-integer cost overflow

    battle.set_tile({1, 0}, {0, 1, true});
    const auto valid = battle.preview_move(1, {2, 0});
    assert(valid.legal && valid.path_cost == 2);
    assert(battle.move(1, {2, 0}));
    assert(!battle.preview_move(1, {1, 0}).legal);
    assert(!battle.move(1, {1, 0})); // spent movement cannot be reused
}

void terminal_projection_is_hidden() {
    vh::Battle battle(2, 1);
    battle.add_unit({1, "P", vh::Side::Player, {0, 0}, 20, 99, 2, 4, 1});
    battle.add_unit({2, "E", vh::Side::Enemy, {1, 0}, 5});
    assert(battle.attack(1, 2) && battle.phase() == vh::Phase::Victory);
    const auto fingerprint = vh::battle_fingerprint(battle);
    const auto unavailable = battle.preview_move(1, {1, 0});
    assert(!unavailable.legal && unavailable.path_cost == 0 &&
           unavailable.remaining_points == 0);
    assert(vh::battle_fingerprint(battle) == fingerprint);
}

} // namespace

int main() {
    costs_and_invariants();
    detours_and_cliffs();
    huge_budgets_must_not_teleport_or_overflow();
    terminal_projection_is_hidden();
    std::puts("Stage63 move preview: path costs, immutable reads, blocked paths, overflow-safe");
}
