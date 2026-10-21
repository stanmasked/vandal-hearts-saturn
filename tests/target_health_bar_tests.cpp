#include "vh/attack_training.hpp"
#include "vh/target_health_bar.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void hidden(const vh::Battle& battle, vh::Pos p, int selected) {
    const auto hash = vh::battle_fingerprint(battle);
    auto b = vh::target_health_bar(battle, p, selected);
    assert(!b.visible && b.current_hp==0 && b.hp_after==0);
    assert(b.remaining_width==0 && b.damage_width==0);
    assert(vh::battle_fingerprint(battle)==hash);
}
void forecast(const vh::Battle& battle, vh::Pos pos,
              int current,int remaining,int green) {
    const auto hash = vh::battle_fingerprint(battle);
    for(int i=0;i<100;++i) {
        auto b=vh::target_health_bar(battle,pos,1);
        assert(b.visible && b.current_hp==current && b.hp_after==remaining);
        assert(b.remaining_width==green && b.damage_width==vh::kHealthBarWidth-green);
        assert(b.remaining_width+b.damage_width==vh::kHealthBarWidth);
        assert(b.remaining_width>=0 && b.damage_width>=0);
        const auto* enemy=battle.unit_at(pos);
        assert(enemy && enemy->hp==b.current_hp);
        const auto d=battle.preview_attack(1,enemy->id);
        assert(d.legal && d.remaining_hp==b.hp_after);
        assert(d.damage==current-remaining);
        assert(vh::battle_fingerprint(battle)==hash);
    }
}
void duel_and_outcomes() {
    vh::Battle b=vh::stage44_attack_duel();
    assert(vh::battle_fingerprint(b)==UINT64_C(0x9376e23745926630));
    assert(vh::kHealthBarX>=1015 && vh::kHealthBarX+vh::kHealthBarWidth<=1240);
    assert(vh::kHealthBarY>=703 && vh::kHealthBarY+vh::kHealthBarHeight<=711);
    hidden(b,{1,5},1);
    hidden(b,{2,5},-1);
    hidden(b,{2,5},3);
    hidden(b,{2,5},777);
    hidden(b,{-1,5},1);
    const int hp[] = {20,14,8,2};
    const int after[] = {14,8,2,0};
    const int green[] = {154,125,55,0};
    for(int round=0;round<4;++round) {
        forecast(b,{2,5},hp[round],after[round],green[round]);
        assert(b.attack(1,3));
        hidden(b,{2,5},1);
        if(round<3) {
            assert(b.end_player_turn());
            hidden(b,{2,5},-1);
        }
    }
    assert(b.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(b)==UINT64_C(0x6097117b6c951fb6));
    hidden(b,{2,5},1);
}
void unavailable_target_and_defeat() {
    auto b=vh::Battle::training();
    const auto hash=vh::battle_fingerprint(b);
    hidden(b,{6,1},1); // Raider out of range.
    hidden(b,{6,3},1); // Archer out of range.
    hidden(b,{1,6},1); // Allied Guard.
    assert(vh::battle_fingerprint(b)==hash);
    auto d=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) assert(d.end_player_turn());
    assert(d.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(d)==UINT64_C(0x3b0411b006f113c1));
    hidden(d,{2,5},1);
}
}
int main() {
    duel_and_outcomes();
    unavailable_target_and_defeat();
    std::printf("Stage60 projected bar 154/125/55/0 green, 66/95/165/220 red; real preview and terminal hashes unchanged\n");
}
