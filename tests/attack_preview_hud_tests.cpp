#include "vh/attack_preview_hud.hpp"
#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/training_controls.hpp"

#include <array>
#include <cassert>
#include <cstdio>
#include <cstdint>

int main() {
    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1,5};
    const auto start = vh::battle_fingerprint(ui.battle);
    assert(!vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).visible);
    assert(!vh::attack_preview_hud(ui.battle,1,ui.cursor).visible);
    assert(!vh::attack_preview_hud(ui.battle,3,{1,5}).visible);

    assert(vh::apply_training_action(ui,vh::TrainingAction::Confirm)
           == vh::TrainingEffect::Selected);
    assert(!vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).visible);
    assert(vh::apply_training_action(ui,vh::TrainingAction::Right)
           == vh::TrainingEffect::CursorMoved);
    auto h=vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor);
    assert(h.visible && !h.decisive && h.hp_before==20 && h.hp_after==14);
    assert(h.damage==6 && h.remaining_width==123 && h.damage_width==53);
    assert(h.remaining_width+h.damage_width==vh::kPreviewBarWidth);
    for(int i=0;i<50;++i) {
        assert(vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).remaining_width==123);
        assert(vh::battle_fingerprint(ui.battle)==start);
    }
    // Stage44 visually-selected aim must show forecast, after hit it disappears.
    assert(vh::apply_training_action(ui,vh::TrainingAction::Attack)
           == vh::TrainingEffect::Attacked);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x9a0233cdc1acffdb));
    assert(!vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).visible);
    assert(vh::apply_training_action(ui,vh::TrainingAction::Attack)
           == vh::TrainingEffect::Rejected);

    // Stage50 canonical 4-round Victory; last 2HP is visibly lethal.
    const std::array<int,3> hp{{8,2,0}};
    for(int round=0;round<3;++round) {
        assert(vh::apply_training_action(ui,vh::TrainingAction::EndTurn)
               == vh::TrainingEffect::TurnEnded);
        assert(!vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).visible);
        assert(vh::apply_training_action(ui,vh::TrainingAction::Left)
               == vh::TrainingEffect::CursorMoved);
        assert(vh::apply_training_action(ui,vh::TrainingAction::Confirm)
               == vh::TrainingEffect::Selected);
        assert(vh::apply_training_action(ui,vh::TrainingAction::Right)
               == vh::TrainingEffect::CursorMoved);
        const auto before=vh::battle_fingerprint(ui.battle);
        h=vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor);
        assert(h.visible && h.damage==(round==2?2:6));
        assert(h.hp_after==hp[static_cast<size_t>(round)]);
        assert(h.decisive==(round==2));
        assert(h.remaining_width+h.damage_width==vh::kPreviewBarWidth);
        if(round==2) assert(h.remaining_width==0 && h.damage_width==176);
        assert(vh::battle_fingerprint(ui.battle)==before);
        assert(vh::apply_training_action(ui,vh::TrainingAction::Attack)
               == vh::TrainingEffect::Attacked);
        assert(!vh::attack_preview_hud(ui.battle,ui.selected,ui.cursor).visible);
    }
    assert(ui.battle.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x6097117b6c951fb6));
    assert(!vh::attack_preview_hud(ui.battle,1,{2,5}).visible);

    // Repeat for Defeat: no forecast for a dead player even when selected
    // is maliciously left pointing to a stale unit id.
    vh::Battle dead=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(dead.end_player_turn());
    const auto fingerprint=vh::battle_fingerprint(dead);
    assert(dead.phase()==vh::Phase::Defeat);
    assert(!vh::attack_preview_hud(dead,1,{2,5}).visible);
    assert(fingerprint==UINT64_C(0x3b0411b006f113c1));

    // Two opponents: a lethal hit to one does not mean the battle is over.
    vh::Battle multi(3,2);
    multi.add_unit({1,"Hero",vh::Side::Player,{0,0},20,20,2});
    multi.add_unit({3,"Raider",vh::Side::Enemy,{1,0},2,5,1});
    multi.add_unit({4,"Archer",vh::Side::Enemy,{2,0},2,5,1});
    h=vh::attack_preview_hud(multi,1,{1,0});
    assert(h.visible && !h.decisive && h.hp_before==2 && h.hp_after==0);
    assert(h.damage==2 && h.remaining_width==0);
    assert(vh::battle_fingerprint(multi)==vh::battle_fingerprint(multi));

    std::printf("Stage54 ROM-free non-mutating forecast HUD: 4-round parity, show/hide, lethal 2HP, 2v2 and terminal rejection passed\n");
}
