#include "vh/attack_training.hpp"
#include "vh/training_controls.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>

int main() {
    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1,5};
    assert(ui.battle.units().size() == 2);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x9376e23745926630));
    assert(ui.battle.find_unit(3)->hp == 20);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm)
        == vh::TrainingEffect::Selected);
    assert(ui.selected == 1);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Right)
        == vh::TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{2,5}));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Attacked);
    const auto moved_hash = vh::battle_fingerprint(ui.battle);
    assert(moved_hash == UINT64_C(0x9a0233cdc1acffdb));
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(ui.battle.find_unit(1)->acted);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Rejected);
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(vh::battle_fingerprint(ui.battle) == moved_hash);
    // Stage45: cancellation may clear the UI selection, but cannot clear
    // the durable per-round 'acted' bit of the native Scout.
    assert(vh::apply_training_action(ui, vh::TrainingAction::Cancel)
        == vh::TrainingEffect::Cancelled);
    assert(ui.selected == -1);
    assert(vh::battle_fingerprint(ui.battle) == moved_hash);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Left)
        == vh::TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{1,5}));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm)
        == vh::TrainingEffect::Selected);
    assert(ui.selected == 1);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Right)
        == vh::TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Rejected);
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(ui.battle.find_unit(1)->acted);
    assert(vh::battle_fingerprint(ui.battle) == moved_hash);
    // Stage47: the end-of-turn enemy attacks adjacent Scout for 3 HP.
    // Returning to a new player round restores Scout's ability to attack,
    // without undoing earlier Raider damage or resetting the UI cursor.
    assert(vh::apply_training_action(ui, vh::TrainingAction::EndTurn)
        == vh::TrainingEffect::TurnEnded);
    assert(ui.selected == -1);
    assert(ui.battle.round() == 2);
    assert(ui.battle.phase() == vh::Phase::Player);
    assert(ui.battle.find_unit(1)->hp == 19);
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(!ui.battle.find_unit(1)->acted);
    assert(ui.battle.find_unit(3)->acted);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0xb633fd92746c41cf));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Rejected); // cannot attack without selection
    assert(vh::apply_training_action(ui, vh::TrainingAction::Left)
        == vh::TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm)
        == vh::TrainingEffect::Selected);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Right)
        == vh::TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Attacked);
    assert(ui.battle.find_unit(3)->hp == 8);
    assert(ui.battle.find_unit(1)->hp == 19);
    assert(ui.battle.find_unit(1)->acted);
    const auto second_round_fingerprint = vh::battle_fingerprint(ui.battle);
    assert(second_round_fingerprint != moved_hash);
    assert(second_round_fingerprint == UINT64_C(0x203a8823191e6018));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Rejected);
    assert(vh::battle_fingerprint(ui.battle) == second_round_fingerprint);
    assert(ui.battle.find_unit(3)->hp == 8);
    std::printf("Stage44 duel initial=%016llx attacked=%016llx HP=20->14 second_rejected=true\n",
        static_cast<unsigned long long>(UINT64_C(0x9376e23745926630)),
        static_cast<unsigned long long>(moved_hash));
}
