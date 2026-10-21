#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/selected_unit_hud.hpp"
#include "vh/training_controls.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void hidden(const vh::Battle& b, int selected) {
    const auto hash = vh::battle_fingerprint(b);
    const auto u = vh::selected_unit_hud(b, selected);
    assert(!u.visible && u.name.empty() && u.unit_id == 0);
    assert(u.hp == 0 && u.attack == 0 && u.defense == 0 && u.range == 0);
    assert(!u.acted && !u.moved);
    assert(vh::battle_fingerprint(b) == hash);
}

void selected_ally_shows_real_stats_and_readiness() {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1,5};
    hidden(ui.battle, ui.selected);
    hidden(ui.battle, 3);  // Enemy cannot be displayed as *selected ally*.
    hidden(ui.battle, 999);
    const auto start = vh::battle_fingerprint(ui.battle);
    assert(start == UINT64_C(0x9376e23745926630));
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    auto i=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(i.visible && i.name=="Scout" && i.unit_id==1);
    assert(i.hp==22 && i.attack==8 && i.defense==3 && i.range==1);
    assert(!i.moved && !i.acted);
    for(int k=0;k<100;++k) {
        i=vh::selected_unit_hud(ui.battle,ui.selected);
        assert(i.visible && i.hp==22 && !i.acted && !i.moved);
        assert(vh::battle_fingerprint(ui.battle)==start);
    }
    assert(vh::apply_training_action(ui,TrainingAction::Right)==TrainingEffect::CursorMoved);
    i=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(i.visible && i.hp==22 && !i.acted);
    assert(vh::apply_training_action(ui,TrainingAction::Attack)==TrainingEffect::Attacked);
    i=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(i.visible && i.name=="Scout" && i.hp==22 && i.acted && !i.moved);
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0x9a0233cdc1acffdb));
    assert(vh::apply_training_action(ui,TrainingAction::EndTurn)==TrainingEffect::TurnEnded);
    hidden(ui.battle,ui.selected); // Selection automatically reset each round.
    assert(vh::battle_fingerprint(ui.battle)==UINT64_C(0xb633fd92746c41cf));
    // The next valid selection reflects real HP after enemy counterattack.
    assert(vh::apply_training_action(ui,TrainingAction::Left)==TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    i=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(i.visible && i.hp==19 && !i.acted && !i.moved);
    assert(vh::apply_training_action(ui,TrainingAction::Cancel)==TrainingEffect::Cancelled);
    hidden(ui.battle,ui.selected);
}

void used_movement_is_displayed_with_unchanged_tactics() {
    using vh::TrainingAction;
    using vh::TrainingEffect;
    vh::TrainingUi ui;
    const auto start=vh::battle_fingerprint(ui.battle);
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Selected);
    auto p=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(p.visible && p.name=="Scout" && !p.moved && !p.acted);
    assert(vh::battle_fingerprint(ui.battle)==start);
    assert(vh::apply_training_action(ui,TrainingAction::Right)==TrainingEffect::CursorMoved);
    assert(vh::apply_training_action(ui,TrainingAction::Confirm)==TrainingEffect::Moved);
    p=vh::selected_unit_hud(ui.battle,ui.selected);
    assert(p.visible && p.name=="Scout" && p.moved && !p.acted);
    assert(p.hp==22 && p.attack==8 && p.defense==3 && p.range==1);
    assert(vh::apply_training_action(ui,TrainingAction::Cancel)==TrainingEffect::Cancelled);
    hidden(ui.battle,ui.selected);
}

void terminal_states_do_not_show_ghost_selection() {
    vh::Battle victory=vh::stage44_attack_duel();
    for(int i=0;i<4;++i) {
        assert(victory.attack(1,3));
        if(i<3) assert(victory.end_player_turn());
    }
    assert(victory.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(victory)==UINT64_C(0x6097117b6c951fb6));
    hidden(victory,1);
    hidden(victory,3);

    vh::Battle defeat=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(defeat.end_player_turn());
    assert(defeat.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(defeat)==UINT64_C(0x3b0411b006f113c1));
    hidden(defeat,1);
    hidden(defeat,3);
}

void multiple_allies_do_not_inherit_each_others_stats() {
    vh::Battle b=vh::Battle::training();
    const auto before=vh::battle_fingerprint(b);
    auto scout=vh::selected_unit_hud(b,1);
    auto guard=vh::selected_unit_hud(b,2);
    assert(scout.visible && scout.name=="Scout" && scout.hp==22 && scout.attack==8);
    assert(guard.visible && guard.name=="Guard" && guard.hp==26 && guard.attack==7);
    assert(guard.defense==4 && guard.range==1);
    assert(b.units().size()==4);
    assert(vh::battle_fingerprint(b)==before);
}

} // namespace

int main() {
    selected_ally_shows_real_stats_and_readiness();
    used_movement_is_displayed_with_unchanged_tactics();
    terminal_states_do_not_show_ghost_selection();
    multiple_allies_do_not_inherit_each_others_stats();
    std::printf("Stage55 selected ally HUD: accurate HP/ATK/DEF/RNG, read-only readiness, movement, cancel, Victory and Defeat protections passed\n");
}
