#pragma once

#include "vh/battle.hpp"
#include "vh/cursor_geometry.hpp"

#include <string>

namespace vh {

// One ROM-free action contract for SDL keyboard, Switch gamepad, and host tests.
// The original Saturn's tactical/UI rules are not inferred by this module.
enum class TrainingAction {
    Left, Right, Up, Down, Confirm, Attack, EndTurn, Cancel, Quit
};
enum class TrainingEffect {
    NoChange, CursorMoved, Selected, Moved, Attacked, TurnEnded,
    Cancelled, Rejected, QuitRequested
};

struct TrainingUi {
    Battle battle = Battle::training();
    Pos cursor{1, 5};
    int selected = -1;
    std::string status = "Select ally: A / Enter. Move: D-pad. Attack: Y. End round: X";
};

inline TrainingEffect apply_training_action(TrainingUi& ui, TrainingAction action) {
    const Pos before = ui.cursor;
    switch (action) {
        case TrainingAction::Left:
            ui.cursor = advance_cursor(before, CursorStep::Left, ui.battle.width(), ui.battle.height());
            return ui.cursor != before ? TrainingEffect::CursorMoved : TrainingEffect::NoChange;
        case TrainingAction::Right:
            ui.cursor = advance_cursor(before, CursorStep::Right, ui.battle.width(), ui.battle.height());
            return ui.cursor != before ? TrainingEffect::CursorMoved : TrainingEffect::NoChange;
        case TrainingAction::Up:
            ui.cursor = advance_cursor(before, CursorStep::Up, ui.battle.width(), ui.battle.height());
            return ui.cursor != before ? TrainingEffect::CursorMoved : TrainingEffect::NoChange;
        case TrainingAction::Down:
            ui.cursor = advance_cursor(before, CursorStep::Down, ui.battle.width(), ui.battle.height());
            return ui.cursor != before ? TrainingEffect::CursorMoved : TrainingEffect::NoChange;
        case TrainingAction::Confirm: {
            if (ui.battle.phase() != Phase::Player) return TrainingEffect::Rejected;
            const Unit* hovered = ui.battle.unit_at(ui.cursor);
            if (hovered && hovered->side == Side::Player) {
                ui.selected = hovered->id;
                ui.status = "Ally selected. Move to green tile; Y attacks enemy; X ends round.";
                return TrainingEffect::Selected;
            }
            if (ui.selected >= 0 && ui.battle.move(ui.selected, ui.cursor)) {
                ui.status = "Moved. Aim at enemy then press Y to attack.";
                return TrainingEffect::Moved;
            }
            ui.status = "No valid allied unit or move at the cursor.";
            return TrainingEffect::Rejected;
        }
        case TrainingAction::Attack: {
            if (ui.battle.phase() != Phase::Player || ui.selected < 0)
                return TrainingEffect::Rejected;
            const Unit* hovered = ui.battle.unit_at(ui.cursor);
            if (hovered && ui.battle.attack(ui.selected, hovered->id)) {
                ui.status = ui.battle.phase() == Phase::Victory ? "Victory!" : "Hit confirmed.";
                return TrainingEffect::Attacked;
            }
            ui.status = "Illegal target or attacker already acted.";
            return TrainingEffect::Rejected;
        }
        case TrainingAction::EndTurn:
            if (ui.battle.end_player_turn()) {
                ui.selected = -1;
                ui.status = ui.battle.phase() == Phase::Defeat ? "Defeat." : "New player round.";
                return TrainingEffect::TurnEnded;
            }
            return TrainingEffect::Rejected;
        case TrainingAction::Cancel:
            if (ui.selected < 0) return TrainingEffect::NoChange;
            ui.selected = -1;
            ui.status = "Selection cancelled.";
            return TrainingEffect::Cancelled;
        case TrainingAction::Quit:
            return TrainingEffect::QuitRequested;
    }
    return TrainingEffect::NoChange;
}

} // namespace vh
