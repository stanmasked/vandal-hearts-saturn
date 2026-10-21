#include "vh/training_controls.hpp"
#include <cassert>
#include <iostream>

using namespace vh;

int main() {
    TrainingUi ui;
    const auto same = [](const Battle& a, const Battle& b) {
        // Test the underlying immutable tactical fields directly, without relying
        // on native padding or on the rendering environment.
        assert(a.round() == b.round() && a.phase() == b.phase());
        assert(a.units().size() == b.units().size());
        for (size_t i = 0; i < a.units().size(); ++i) {
            const Unit& x = a.units()[i], &y = b.units()[i];
            assert(x.id == y.id && x.pos == y.pos && x.hp == y.hp &&
                   x.moved == y.moved && x.acted == y.acted);
        }
    };
    Battle untouched = ui.battle;
    assert(apply_training_action(ui, TrainingAction::Confirm) == TrainingEffect::Selected);
    assert(ui.selected == 1);
    same(ui.battle, untouched);
    assert(apply_training_action(ui, TrainingAction::Right) == TrainingEffect::CursorMoved);
    assert((ui.cursor == Pos{2, 5}));
    same(ui.battle, untouched); // movement of the cursor is not a tactical move
    assert(apply_training_action(ui, TrainingAction::Attack) == TrainingEffect::Rejected);
    same(ui.battle, untouched); // can't attack an empty tile
    assert(apply_training_action(ui, TrainingAction::Confirm) == TrainingEffect::Moved);
    assert((ui.battle.find_unit(1)->pos == Pos{2, 5}));
    assert(ui.battle.find_unit(1)->moved);
    Battle moved = ui.battle;
    assert(apply_training_action(ui, TrainingAction::Down) == TrainingEffect::CursorMoved);
    assert(apply_training_action(ui, TrainingAction::Confirm) == TrainingEffect::Rejected);
    same(ui.battle, moved); // second move in same turn rejected
    assert(apply_training_action(ui, TrainingAction::Cancel) == TrainingEffect::Cancelled);
    assert(ui.selected == -1);
    assert(apply_training_action(ui, TrainingAction::Cancel) == TrainingEffect::NoChange);
    assert(apply_training_action(ui, TrainingAction::EndTurn) == TrainingEffect::TurnEnded);
    assert(ui.battle.round() == 2 && ui.battle.phase() == Phase::Player);
    assert(!ui.battle.find_unit(1)->moved);
    assert(ui.selected == -1);
    assert(apply_training_action(ui, TrainingAction::Quit) == TrainingEffect::QuitRequested);

    // Verify attack and its single-use limit with a close synthetic opponent.
    TrainingUi duel;
    duel.battle = Battle(4, 4);
    duel.cursor = {1, 1};
    duel.battle.add_unit({1, "Hero", Side::Player, {1, 1}, 20, 8, 2, 4, 1});
    duel.battle.add_unit({3, "Enemy", Side::Enemy, {2, 1}, 20, 6, 2, 3, 1});
    assert(apply_training_action(duel, TrainingAction::Confirm) == TrainingEffect::Selected);
    assert(apply_training_action(duel, TrainingAction::Right) == TrainingEffect::CursorMoved);
    assert(apply_training_action(duel, TrainingAction::Attack) == TrainingEffect::Attacked);
    assert(duel.battle.find_unit(3)->hp == 14);
    assert(duel.battle.find_unit(1)->acted);
    Battle attacked = duel.battle;
    assert(apply_training_action(duel, TrainingAction::Attack) == TrainingEffect::Rejected);
    same(duel.battle, attacked);
    assert(apply_training_action(duel, TrainingAction::Confirm) == TrainingEffect::Rejected);
    same(duel.battle, attacked);

    TrainingUi edges;
    edges.cursor = {0, 0};
    assert(apply_training_action(edges, TrainingAction::Left) == TrainingEffect::NoChange);
    assert(apply_training_action(edges, TrainingAction::Up) == TrainingEffect::NoChange);
    assert((edges.cursor == Pos{0, 0}));
    std::cout << "ROM-free action contract passed: select/move/reject/attack/end-turn/cancel\n";
}
