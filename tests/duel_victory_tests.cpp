#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/training_controls.hpp"

#include <cassert>
#include <cstdio>

namespace {
void check_hp(const vh::TrainingUi& ui, int scout, int raider, int round) {
    assert(ui.battle.find_unit(1) != nullptr);
    assert(ui.battle.find_unit(3) != nullptr);
    assert(ui.battle.find_unit(1)->hp == scout);
    assert(ui.battle.find_unit(3)->hp == raider);
    assert(ui.battle.round() == round);
}

void scout_attack(vh::TrainingUi& ui, int expected_raider_hp) {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    assert(ui.battle.phase() == vh::Phase::Player);
    assert(ui.selected == -1);
    assert((ui.cursor == vh::Pos{2, 5}));
    assert(vh::apply_training_action(ui, TrainingAction::Left)
           == TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{1, 5}));
    assert(vh::apply_training_action(ui, TrainingAction::Confirm)
           == TrainingEffect::Selected);
    assert(ui.selected == 1);
    assert(vh::apply_training_action(ui, TrainingAction::Right)
           == TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{2, 5}));
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Attacked);
    assert(ui.battle.find_unit(3)->hp == expected_raider_hp);
}
}

int main() {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1, 5};

    // Round 1: one legal attack, then exactly one enemy counterstrike.
    assert(vh::apply_training_action(ui, TrainingAction::Confirm)
           == TrainingEffect::Selected);
    assert(vh::apply_training_action(ui, TrainingAction::Right)
           == TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Attacked);
    check_hp(ui, 22, 14, 1);
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Rejected);
    assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
           == TrainingEffect::TurnEnded);
    check_hp(ui, 19, 14, 2);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0xb633fd92746c41cf));

    // Round 2: stage48 guest-verified attack 14 -> 8 and AI response.
    scout_attack(ui, 8);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x203a8823191e6018));
    assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
           == TrainingEffect::TurnEnded);
    check_hp(ui, 16, 8, 3);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x1b81f3931a165925));
    assert(ui.selected == -1);

    // Round 3: enemy survives with exactly two HP.
    scout_attack(ui, 2);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x7849484ccfd7a0de));
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Rejected);
    check_hp(ui, 16, 2, 3);
    assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
           == TrainingEffect::TurnEnded);
    check_hp(ui, 13, 2, 4);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x984023d699c803db));
    assert(ui.selected == -1);

    // Round 4: fatal hit clamps remaining HP to zero and freezes victory.
    scout_attack(ui, 0);
    check_hp(ui, 13, 0, 4);
    assert(ui.battle.phase() == vh::Phase::Victory);
    assert(ui.status == "Victory!");
    assert(ui.battle.unit_at({2, 5}) == nullptr);
    const auto victory_hash = vh::battle_fingerprint(ui.battle);
    assert(victory_hash == UINT64_C(0x6097117b6c951fb6));

    // A completed battle cannot be replayed into another round/attack.
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Rejected);
    assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
           == TrainingEffect::Rejected);
    assert(vh::apply_training_action(ui, TrainingAction::Confirm)
           == TrainingEffect::Rejected);
    assert(!ui.battle.attack(1, 3));
    assert(!ui.battle.attack(3, 1));
    assert(!ui.battle.move(1, {1, 4}));
    assert(!ui.battle.end_player_turn());
    assert(vh::battle_fingerprint(ui.battle) == victory_hash);
    assert(ui.battle.phase() == vh::Phase::Victory);
    check_hp(ui, 13, 0, 4);

    // Cancel may remove local UI selection, but cannot change victory state.
    assert(vh::apply_training_action(ui, TrainingAction::Cancel)
           == TrainingEffect::Cancelled);
    assert(ui.selected == -1);
    assert(vh::battle_fingerprint(ui.battle) == victory_hash);
    std::printf("Stage49 ROM-free duel victory=true round=4 ScoutHP=13 RaiderHP=0 state=%016llx terminal_rejections=true\n",
                static_cast<unsigned long long>(victory_hash));
}
