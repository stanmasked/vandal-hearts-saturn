#include "vh/battle.hpp"
#include <cassert>
#include <iostream>
#include <stdexcept>

using namespace vh;

void test_path_and_height() {
    Battle b(4, 3);
    b.add_unit({1, "P", Side::Player, {0, 1}, 20, 8, 1, 3});
    b.add_unit({2, "E", Side::Enemy, {3, 1}, 20});
    b.set_tile({1, 1}, {0, 1, false});
    assert(!b.move(1, {1, 1}));
    assert(!b.move(1, {2, 1})); // detour would cost 4
    assert(b.move(1, {0, 2}));
    assert(!b.move(1, {0, 0})); // once per turn
}

void test_cliffs_and_costs() {
    Battle b(3, 1);
    b.add_unit({1, "P", Side::Player, {0, 0}, 20, 5, 0, 4});
    b.add_unit({2, "E", Side::Enemy, {2, 0}, 20});
    b.set_tile({1, 0}, {2, 1, true});
    assert(!b.move(1, {1, 0}));
    b.set_tile({1, 0}, {1, 5, true});
    assert(!b.move(1, {1, 0}));
    b.set_tile({1, 0}, {1, 2, true});
    assert(b.move(1, {1, 0}));
}

void test_victory() {
    Battle b(2, 1);
    b.add_unit({1, "P", Side::Player, {0, 0}, 20, 99, 0, 0});
    b.add_unit({2, "E", Side::Enemy, {1, 0}, 10});
    assert(!b.attack(1, 1));
    assert(b.attack(1, 2));
    assert(b.phase() == Phase::Victory);
    assert(b.find_unit(2)->hp == 0);
    assert(!b.end_player_turn());
}

void test_attack_rules() {
    Battle b(3, 1);
    b.add_unit({1, "P", Side::Player, {0, 0}, 20, 6, 1, 2});
    b.add_unit({2, "P2", Side::Player, {1, 0}, 20});
    b.add_unit({3, "E", Side::Enemy, {2, 0}, 20, 6, 1});
    assert(!b.attack(1, 2)); // no friendly fire
    assert(!b.attack(3, 2)); // enemy cannot act during player turn
    assert(!b.attack(1, 3)); // out of range
    assert(b.attack(2, 3));
    assert(!b.attack(2, 3)); // at most one attack per turn
    assert(b.end_player_turn());
    assert(b.round() == 2 || b.phase() == Phase::Defeat);
}

void test_occupied_movement_and_bounds() {
    Battle b(3, 2);
    b.add_unit({1, "P", Side::Player, {0, 0}, 20, 8, 1, 4});
    b.add_unit({2, "E", Side::Enemy, {1, 0}, 20});
    assert(!b.move(1, {-1, 0}));
    assert(!b.move(1, {3, 1}));
    assert(!b.move(1, {1, 0}));
    assert(b.move(1, {1, 1}));
}

void test_invalid_data() {
    bool caught = false;
    try { Battle broken(0, 4); } catch (const std::invalid_argument&) { caught = true; }
    assert(caught);
    Battle b(2, 1);
    b.add_unit({1, "P", Side::Player, {0, 0}});
    caught = false;
    try { b.add_unit({2, "Duplicate", Side::Enemy, {0, 0}}); }
    catch (const std::invalid_argument&) { caught = true; }
    assert(caught);
}

int main() {
    test_path_and_height();
    test_cliffs_and_costs();
    test_victory();
    test_attack_rules();
    test_occupied_movement_and_bounds();
    test_invalid_data();
    std::cout << "6 tactical-core tests passed\n";
}
