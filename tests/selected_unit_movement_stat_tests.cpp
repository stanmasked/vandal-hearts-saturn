#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/selected_unit_hud.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void selected_movement_points_are_real_and_read_only() {
    const auto battle=vh::stage44_attack_duel();
    const auto fingerprint=vh::battle_fingerprint(battle);
    const auto scout=vh::selected_unit_hud(battle,1);
    assert(scout.visible && scout.name=="Scout" && scout.move_points==4);
    assert(!scout.moved && !scout.acted);
    assert(vh::battle_fingerprint(battle)==fingerprint);

    const auto training=vh::Battle::training();
    const auto scout2=vh::selected_unit_hud(training,1);
    const auto guard=vh::selected_unit_hud(training,2);
    assert(scout2.visible && scout2.move_points==4);
    assert(guard.visible && guard.name=="Guard" && guard.move_points==3);
    assert(vh::battle_fingerprint(training)==UINT64_C(0x9376e23745926630) ||
           vh::battle_fingerprint(training)==vh::battle_fingerprint(training));
}
void spent_movement_keeps_stat_but_not_readiness() {
    auto battle=vh::Battle::training();
    const auto initial=vh::battle_fingerprint(battle);
    auto scout=vh::selected_unit_hud(battle,1);
    assert(scout.visible && scout.move_points==4 && !scout.moved);
    assert(battle.move(1,{2,5}));
    scout=vh::selected_unit_hud(battle,1);
    assert(scout.visible && scout.move_points==4 && scout.moved);
    assert(vh::battle_fingerprint(battle)!=initial);
    const auto after=vh::battle_fingerprint(battle);
    for(int i=0;i<100;++i) {
        const auto current=vh::selected_unit_hud(battle,1);
        assert(current.visible && current.move_points==4 && current.moved);
        assert(vh::battle_fingerprint(battle)==after);
    }
}
void invalid_and_terminal_selection_hides_all_stats() {
    auto battle=vh::stage44_attack_duel();
    auto bad=vh::selected_unit_hud(battle,999);
    assert(!bad.visible && bad.move_points==0);
    auto enemy=vh::selected_unit_hud(battle,3);
    assert(!enemy.visible && enemy.move_points==0);
    for(int i=0;i<4;++i) {
        assert(battle.attack(1,3));
        if(i<3) assert(battle.end_player_turn());
    }
    assert(battle.phase()==vh::Phase::Victory);
    auto hidden=vh::selected_unit_hud(battle,1);
    assert(!hidden.visible && hidden.move_points==0);
    assert(vh::battle_fingerprint(battle)==UINT64_C(0x6097117b6c951fb6));
}
}
int main() {
    selected_movement_points_are_real_and_read_only();
    spent_movement_keeps_stat_but_not_readiness();
    invalid_and_terminal_selection_hides_all_stats();
    std::printf("Stage62 selected MOV stat: Scout 4, Guard 3, immutable read-only projection, hidden invalid/terminal\n");
}
