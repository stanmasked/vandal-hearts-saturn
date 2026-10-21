#include "vh/attack_training.hpp"
#include "vh/attack_preview_hud.hpp"
#include "vh/replay.hpp"
#include "vh/turn_round_hud.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {
void check(const vh::Battle& battle, int expected) {
    const auto fp=vh::battle_fingerprint(battle);
    for(int i=0;i<100;++i) {
        const auto state=vh::turn_round_hud(battle);
        assert(state.visible && state.round==expected);
        assert(vh::battle_fingerprint(battle)==fp);
    }
}
void hidden(const vh::Battle& battle) {
    const auto fp=vh::battle_fingerprint(battle);
    const auto state=vh::turn_round_hud(battle);
    assert(!state.visible && state.round==0);
    assert(vh::battle_fingerprint(battle)==fp);
}
void duel_and_victory() {
    auto battle=vh::stage44_attack_duel();
    assert(vh::kRoundHudX>85);
    assert(vh::kRoundHudX+vh::kRoundHudWidth<vh::kPreviewBarX);
    assert(vh::kRoundHudY>=660 && vh::kRoundHudY+vh::kRoundHudHeight<=720);
    assert(vh::kRoundDigitX>=110);
    assert(vh::battle_fingerprint(battle)==UINT64_C(0x9376e23745926630));
    for(int round=1;round<=4;++round) {
        check(battle,round);
        assert(battle.attack(1,3));
        if(round<4) {
            check(battle,round); // Attacking does not itself advance a round.
            assert(battle.end_player_turn());
        }
    }
    assert(battle.phase()==vh::Phase::Victory);
    assert(vh::battle_fingerprint(battle)==UINT64_C(0x6097117b6c951fb6));
    hidden(battle);
}
void training_and_defeat() {
    auto training=vh::Battle::training();
    check(training,1);
    auto loss=vh::stage44_attack_duel();
    for(int i=0;i<8;++i) {
        if(loss.phase()==vh::Phase::Player) check(loss,loss.round());
        assert(loss.end_player_turn());
    }
    assert(loss.phase()==vh::Phase::Defeat);
    assert(vh::battle_fingerprint(loss)==UINT64_C(0x3b0411b006f113c1));
    hidden(loss);
}
} // namespace
int main() {
    duel_and_victory();
    training_and_defeat();
    std::printf("Stage61 round badge: 1/2/3/4, terminal hide, phase and replay immutability\n");
}
