#include "vh/attack_training.hpp"
#include "vh/enemy_attack_cue.hpp"
#include "vh/replay.hpp"
#include "vh/training_controls.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
using vh::EnemyAttackCueState;
void check(const vh::Battle& battle, vh::Pos pos, int selected,
           EnemyAttackCueState state, int damage=0, int remaining=0) {
    const auto before = vh::battle_fingerprint(battle);
    for (int i=0;i<50;++i) {
        const auto c=vh::enemy_attack_cue(battle,pos,selected);
        assert(c.state==state && c.damage==damage && c.remaining_hp==remaining);
        if (state!=EnemyAttackCueState::Ready) assert(!c.decisive);
        assert(vh::battle_fingerprint(battle)==before);
    }
}

void real_duel_states_use_single_attack_source_of_truth() {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    vh::TrainingUi ui;
    ui.battle=vh::stage44_attack_duel();
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x9376e23745926630));
    check(ui.battle,{1,5},-1,EnemyAttackCueState::Hidden);
    check(ui.battle,{2,5},-1,EnemyAttackCueState::InspectOnly);
    check(ui.battle,{2,5},777,EnemyAttackCueState::InspectOnly);
    check(ui.battle,{2,5},3,EnemyAttackCueState::InspectOnly); // enemy is not an ally
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    assert(ui.selected==1);
    check(ui.battle,{1,5},1,EnemyAttackCueState::Hidden);
    check(ui.battle,{2,5},1,EnemyAttackCueState::Ready,6,14);
    const auto before=vh::battle_fingerprint(ui.battle);
    const auto real=ui.battle.preview_attack(1,3);
    const auto cue=vh::enemy_attack_cue(ui.battle,{2,5},1);
    assert(real.legal && cue.damage==real.damage && cue.remaining_hp==real.remaining_hp);
    assert(vh::battle_fingerprint(ui.battle)==before);
    assert(vh::apply_training_action(ui,TrainingAction::Right)==TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui,TrainingAction::Attack)==TrainingEffect::Attacked);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x9a0233cdc1acffdb));
    check(ui.battle,{2,5},1,EnemyAttackCueState::Spent);
    assert(vh::apply_training_action(ui,TrainingAction::EndTurn)==TrainingEffect::TurnEnded);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0xb633fd92746c41cf));
    check(ui.battle,{2,5},-1,EnemyAttackCueState::InspectOnly);
    assert(vh::apply_training_action(ui,TrainingAction::Left)==TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    check(ui.battle,{2,5},1,EnemyAttackCueState::Ready,6,8);
}

void range_and_life_cycle_are_never_forged() {
    vh::Battle training=vh::Battle::training();
    const auto start=vh::battle_fingerprint(training);
    // Scout (1,5) is too far from Raider (6,1) or Archer (6,3).
    check(training,{6,1},1,EnemyAttackCueState::Blocked);
    check(training,{6,3},1,EnemyAttackCueState::Blocked);
    check(training,{6,3},-1,EnemyAttackCueState::InspectOnly);
    check(training,{-1,5},1,EnemyAttackCueState::Hidden);
    check(training,{1,6},1,EnemyAttackCueState::Hidden);
    assert(vh::battle_fingerprint(training)==start);
    assert(vh::kEnemyCueX>=1240 && vh::kEnemyCueX+vh::kEnemyCueWidth<=1274);
    assert(vh::kEnemyCueY>=668 && vh::kEnemyCueY+vh::kEnemyCueHeight<690);
    vh::Battle victory=vh::stage44_attack_duel();
    for(int i=0;i<4;++i) {
        assert(victory.attack(1,3));
        if(i<3) assert(victory.end_player_turn());
    }
    assert(victory.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(victory)==UINT64_C(0x6097117b6c951fb6));
    check(victory,{2,5},1,EnemyAttackCueState::Hidden);
    vh::Battle defeat=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(defeat.end_player_turn());
    assert(defeat.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(defeat)==UINT64_C(0x3b0411b006f113c1));
    check(defeat,{2,5},1,EnemyAttackCueState::Hidden);
}
}
int main() {
    real_duel_states_use_single_attack_source_of_truth();
    range_and_life_cycle_are_never_forged();
    std::printf("Stage57 attack cue: Ready/Spent/Blocked/InspectOnly/Hidden states, live preview and terminal fingerprints verified\n");
}
