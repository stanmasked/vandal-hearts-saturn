#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/target_damage_hud.hpp"
#include "vh/training_controls.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void hidden(const vh::Battle& b, vh::Pos p, int selected) {
    const auto before=vh::battle_fingerprint(b);
    const auto h=vh::target_damage_hud(b,p,selected);
    assert(!h.visible && h.damage==0 && h.remaining_hp==0 && !h.lethal);
    assert(vh::battle_fingerprint(b)==before);
}
void legal(const vh::Battle& b, vh::Pos p, int selected,
           int damage,int hp_after,bool lethal) {
    const auto before=vh::battle_fingerprint(b);
    for (int i=0;i<50;++i) {
        const auto h=vh::target_damage_hud(b,p,selected);
        assert(h.visible && h.damage==damage && h.remaining_hp==hp_after);
        assert(h.lethal==lethal);
        const auto* target=b.unit_at(p);
        assert(target && target->hp-h.damage==h.remaining_hp);
        const auto forecast=b.preview_attack(selected,target->id);
        assert(forecast.legal && forecast.damage==h.damage);
        assert(forecast.remaining_hp==h.remaining_hp && forecast.ends_battle==h.lethal);
        assert(vh::battle_fingerprint(b)==before);
    }
}
void full_duel_uses_capped_real_damage() {
    vh::Battle b=vh::stage44_attack_duel();
    assert(vh::battle_fingerprint(b)==UINT64_C(0x9376e23745926630));
    hidden(b,{1,5},1);
    hidden(b,{2,5},-1);
    hidden(b,{2,5},999);
    hidden(b,{2,5},3);  // enemy ID is not allied selection
    hidden(b,{0,0},1);
    assert(vh::kDamageHudX>=1070 && vh::kDamageDigitX+24<vh::kDamageKoX);
    assert(vh::kDamageKoX+16<1242 && vh::kDamageHudY>=668);
    for(int round=0;round<4;++round) {
        const int damage=round==3?2:6;
        const int expected=round==0?14:round==1?8:round==2?2:0;
        legal(b,{2,5},1,damage,expected,round==3);
        assert(b.attack(1,3));
        hidden(b,{2,5},1); // consumed attack or dead enemy
        if(round<3) {
            assert(b.end_player_turn());
            hidden(b,{2,5},-1);
        }
    }
    assert(b.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(b)==UINT64_C(0x6097117b6c951fb6));
    hidden(b,{2,5},1);
}
void out_of_range_and_terminal_hidden() {
    vh::Battle training=vh::Battle::training();
    const auto before=vh::battle_fingerprint(training);
    hidden(training,{6,1},1);
    hidden(training,{6,3},1);
    hidden(training,{1,6},1);
    hidden(training,{-1,1},1);
    assert(vh::battle_fingerprint(training)==before);
    vh::Battle defeat=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(defeat.end_player_turn());
    assert(defeat.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(defeat)==UINT64_C(0x3b0411b006f113c1));
    hidden(defeat,{2,5},1);
}
} // namespace
int main() {
    full_duel_uses_capped_real_damage();
    out_of_range_and_terminal_hidden();
    std::printf("Stage58 damage HUD: 6/6/6/2 capped damage, lethal KO and hidden states are deterministic and read-only\n");
}
