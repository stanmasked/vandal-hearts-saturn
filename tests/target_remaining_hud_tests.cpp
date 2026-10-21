#include "vh/attack_training.hpp"
#include "vh/target_remaining_hud.hpp"
#include "vh/replay.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void hidden(const vh::Battle& battle, vh::Pos pos, int selected) {
    const auto hash=vh::battle_fingerprint(battle);
    const auto h=vh::target_remaining_hud(battle,pos,selected);
    assert(!h.visible && h.hp_after==0);
    assert(vh::battle_fingerprint(battle)==hash);
}
void projected(const vh::Battle& battle, vh::Pos pos, int selected, int hp) {
    const auto hash=vh::battle_fingerprint(battle);
    for (int i=0;i<100;++i) {
        const auto h=vh::target_remaining_hud(battle,pos,selected);
        assert(h.visible && h.hp_after==hp);
        const auto d=vh::target_damage_hud(battle,pos,selected);
        assert(d.visible && d.remaining_hp==h.hp_after);
        const auto* enemy=battle.unit_at(pos);
        assert(enemy && enemy->hp-d.damage==h.hp_after);
        assert(vh::battle_fingerprint(battle)==hash);
    }
}
void full_duel() {
    vh::Battle battle=vh::stage44_attack_duel();
    assert(vh::battle_fingerprint(battle)==UINT64_C(0x9376e23745926630));
    assert(vh::kRemainingHudX>=1134 && vh::kRemainingDigitX+16<1188);
    assert(vh::kRemainingHudY==vh::kDamageHudY);
    hidden(battle,{2,5},-1);
    hidden(battle,{2,5},777);
    hidden(battle,{2,5},3);
    hidden(battle,{1,5},1);
    hidden(battle,{0,0},1);
    for(int round=0;round<4;++round) {
        int remaining=round==0?14:round==1?8:round==2?2:0;
        projected(battle,{2,5},1,remaining);
        assert(battle.attack(1,3));
        hidden(battle,{2,5},1);
        if(round<3) {
            assert(battle.end_player_turn());
            hidden(battle,{2,5},-1);
        }
    }
    assert(battle.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(battle)==UINT64_C(0x6097117b6c951fb6));
    hidden(battle,{2,5},1);
}
void range_and_defeat() {
    vh::Battle training=vh::Battle::training();
    auto fingerprint=vh::battle_fingerprint(training);
    hidden(training,{6,1},1);
    hidden(training,{6,3},1);
    hidden(training,{1,6},1);
    hidden(training,{-1,1},1);
    assert(vh::battle_fingerprint(training)==fingerprint);
    vh::Battle defeat=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(defeat.end_player_turn());
    assert(defeat.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(defeat)==UINT64_C(0x3b0411b006f113c1));
    hidden(defeat,{2,5},1);
}
}
int main() {
    full_duel();
    range_and_defeat();
    std::printf("Stage59 remaining enemy HP: 14/8/2/0 projected, hidden spent/illegal/terminal, immutable hashes\n");
}
