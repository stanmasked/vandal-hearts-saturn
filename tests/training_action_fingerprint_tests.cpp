#include "vh/training_controls.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>

int main() {
    vh::TrainingUi ui;
    const auto initial = vh::battle_fingerprint(ui.battle);
    assert(initial == UINT64_C(12553978255608676096)); // ae38b0b5ab887f00
    assert((ui.cursor == vh::Pos{1, 5}));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm) == vh::TrainingEffect::Selected);
    assert(ui.selected == 1);
    assert(vh::battle_fingerprint(ui.battle) == initial);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Right) == vh::TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{2, 5}));
    assert(vh::battle_fingerprint(ui.battle) == initial);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm) == vh::TrainingEffect::Moved);
    const auto after = vh::battle_fingerprint(ui.battle);
    assert(after == UINT64_C(17265812955270519594)); // ef9c7d67953c9b2a
    assert((ui.battle.find_unit(1)->pos == vh::Pos{2, 5}));
    assert(ui.battle.find_unit(1)->moved);
    assert(ui.selected == 1);
    // Move cursor to an empty tile: the Scout is already marked moved, so
    // a second tactical move in the same round must be rejected.
    assert(vh::apply_training_action(ui, vh::TrainingAction::Down) == vh::TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm) == vh::TrainingEffect::Rejected);
    assert(vh::battle_fingerprint(ui.battle) == after);
    std::cout << std::hex << "training action initial=" << initial << " after=" << after << '\n';
}
