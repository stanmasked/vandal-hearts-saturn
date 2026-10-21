#include "vh/battle.hpp"
#include "vh/cursor_geometry.hpp"
#include <cassert>
#include <iostream>

using namespace vh;

int main() {
    Battle training = Battle::training();
    assert(training.width() == 8 && training.height() == 8);
    Pos initial{1, 5};
    assert(training.in_bounds(initial));
    assert((project_training_tile(initial).x == 480));
    assert((project_training_tile(initial).y == 256));
    Pos next = advance_cursor(initial, CursorStep::Right, training.width(), training.height());
    assert((next == Pos{2, 5}));
    assert(project_training_tile(next).x - project_training_tile(initial).x == 40);
    assert(project_training_tile(next).y - project_training_tile(initial).y == 20);
    assert((advance_cursor(next, CursorStep::Left, 8, 8) == initial));
    assert((advance_cursor(initial, CursorStep::Up, 8, 8) == Pos{1, 4}));
    assert((advance_cursor(initial, CursorStep::Down, 8, 8) == Pos{1, 6}));
    assert((advance_cursor({0, 0}, CursorStep::Left, 8, 8) == Pos{0, 0}));
    assert((advance_cursor({0, 0}, CursorStep::Up, 8, 8) == Pos{0, 0}));
    assert((advance_cursor({7, 7}, CursorStep::Right, 8, 8) == Pos{7, 7}));
    assert((advance_cursor({7, 7}, CursorStep::Down, 8, 8) == Pos{7, 7}));
    assert((project_training_tile({0, 0}).x == 640));
    assert((project_training_tile({0, 0}).y == 136));
    assert(project_training_tile({5, 2}, 1).y == project_training_tile({5, 2}, 0).y - 18);
    assert((advance_cursor(initial, CursorStep::Right, 0, 8) == initial));
    std::cout << "17 ROM-free cursor and projection assertions passed\n";
}
