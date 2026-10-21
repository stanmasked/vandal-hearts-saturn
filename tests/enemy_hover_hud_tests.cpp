#include "vh/attack_training.hpp"
#include "vh/enemy_hover_hud.hpp"
#include "vh/replay.hpp"
#include "vh/selected_unit_hud.hpp"
#include "vh/training_controls.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void hidden(const vh::Battle& battle, vh::Pos cursor) {
    const auto before = vh::battle_fingerprint(battle);
    const auto panel = vh::enemy_hover_hud(battle, cursor);
    assert(!panel.visible && panel.unit_id == 0 && panel.name.empty());
    assert(panel.hp == 0 && panel.attack == 0 && panel.defense == 0 && panel.range == 0);
    assert(vh::battle_fingerprint(battle) == before);
}

void hovering_without_selection_is_read_only() {
    vh::Battle duel = vh::stage44_attack_duel();
    const auto before = vh::battle_fingerprint(duel);
    assert(before == UINT64_C(0x9376e23745926630));
    hidden(duel,{1,5});   // Allied Scout.
    hidden(duel,{0,0});   // Empty.
    hidden(duel,{-1,5});  // Off-map.
    hidden(duel,{8,5});   // Off-map.
    for (int i=0; i<100; ++i) {
        const auto h=vh::enemy_hover_hud(duel,{2,5});
        assert(h.visible && h.name=="Raider" && h.unit_id==3);
        assert(h.hp==20 && h.attack==6 && h.defense==2 && h.range==1);
        assert(vh::battle_fingerprint(duel)==before);
    }
    assert(vh::kEnemyHudX >= 994);
    assert(vh::kEnemyHudX+vh::kEnemyHudWidth <= 1280);
    assert(vh::kEnemyHudY >= 660);
    assert(vh::kEnemyHudY+vh::kEnemyHudHeight <= 720);
}

void hover_survives_attack_and_selection_changes() {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    vh::TrainingUi ui;
    ui.battle=vh::stage44_attack_duel();
    ui.cursor={1,5};
    assert(vh::apply_training_action(ui,TrainingAction::Right)==TrainingEffect::CursorMoved);
    auto h=vh::enemy_hover_hud(ui.battle,ui.cursor);
    assert(h.visible && h.hp==20 && ui.selected==-1); // Hover without selection.
    assert(vh::apply_training_action(ui,TrainingAction::Left)==TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    assert(vh::selected_unit_hud(ui.battle,ui.selected).visible);
    assert(vh::apply_training_action(ui,TrainingAction::Right)==TrainingEffect::CursorMoved);
    h=vh::enemy_hover_hud(ui.battle,ui.cursor);
    assert(h.visible && h.hp==20);
    assert(vh::apply_training_action(ui,TrainingAction::Attack)==TrainingEffect::Attacked);
    h=vh::enemy_hover_hud(ui.battle,ui.cursor);
    assert(h.visible && h.hp==14 && h.attack==6 && h.defense==2);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x9a0233cdc1acffdb));
    assert(vh::apply_training_action(ui,TrainingAction::EndTurn)==TrainingEffect::TurnEnded);
    h=vh::enemy_hover_hud(ui.battle,ui.cursor);
    assert(h.visible && h.hp==14); // Cursor still on Raider, Scout HP now 19.
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0xb633fd92746c41cf));
    assert(vh::apply_training_action(ui,TrainingAction::Left)==TrainingEffect::CursorMoved);
    hidden(ui.battle,ui.cursor); // Cursor returned to Scout.
    assert(vh::selected_unit_hud(ui.battle,ui.selected).visible==false);
}

void multiple_enemies_show_their_own_stats() {
    vh::Battle training=vh::Battle::training();
    const auto start=vh::battle_fingerprint(training);
    const auto raider=vh::enemy_hover_hud(training,{6,1});
    const auto archer=vh::enemy_hover_hud(training,{6,3});
    assert(raider.visible && raider.name=="Raider" && raider.hp==18);
    assert(raider.attack==7 && raider.defense==2 && raider.range==1);
    assert(archer.visible && archer.name=="Archer" && archer.hp==14);
    assert(archer.attack==6 && archer.defense==2 && archer.range==2);
    hidden(training,{1,6}); // Guard, not enemy.
    assert(vh::battle_fingerprint(training)==start);
}

void dead_and_terminal_enemies_never_appear() {
    vh::Battle win=vh::stage44_attack_duel();
    for(int round=0;round<4;++round) {
        assert(win.attack(1,3));
        if(round<3) assert(win.end_player_turn());
    }
    assert(win.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(win)==UINT64_C(0x6097117b6c951fb6));
    hidden(win,{2,5}); // Dead enemy, even while cursor remains at target.
    vh::Battle lose=vh::stage44_attack_duel();
    for(int round=0;round<8;++round) assert(lose.end_player_turn());
    assert(lose.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(lose)==UINT64_C(0x3b0411b006f113c1));
    hidden(lose,{2,5}); // Living enemy must not leak into terminal screen.
}
}
int main() {
    hovering_without_selection_is_read_only();
    hover_survives_attack_and_selection_changes();
    multiple_enemies_show_their_own_stats();
    dead_and_terminal_enemies_never_appear();
    std::printf("Stage56 enemy hover HUD: exact Raider/Archer stats, no selection, live HP, independent panels, terminal protection\n");
}
