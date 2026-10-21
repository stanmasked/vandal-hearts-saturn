#include "vh/attack_training.hpp"
#include "vh/replay.hpp"
#include "vh/training_controls.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>

int main() {
    using vh::TrainingAction;
    using vh::TrainingEffect;

    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1, 5};
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x9376e23745926630));
    assert(ui.battle.phase() == vh::Phase::Player);
    const std::array<int, 8> remaining_hp{{19,16,13,10,7,4,1,0}};
    const std::array<int, 8> expected_round{{2,3,4,5,6,7,8,8}};
    const std::array<std::uint64_t, 8> golden{{
        UINT64_C(0xcbda1f619741fbf5), UINT64_C(0x63612b72203eb079),
        UINT64_C(0x66070dc6b67566ad), UINT64_C(0xcdeb89c69e09b7e9),
        UINT64_C(0x413b700b4a1466e5), UINT64_C(0xa6cd3306a9d5b5e1),
        UINT64_C(0x11c830508d90884d), UINT64_C(0x3b0411b006f113c1)
    }};

    // No player attacks: surviving Raider deals precisely 3 HP every round.
    // The eighth incoming hit causes defeat without creating round 9.
    for (size_t index = 0; index < remaining_hp.size(); ++index) {
        const auto before = vh::battle_fingerprint(ui.battle);
        if (index == 7) {
            // A valid selection must be cleared on defeat, just as on victory.
            assert(vh::apply_training_action(ui, TrainingAction::Confirm)
                   == TrainingEffect::Selected);
            assert(ui.selected == 1);
            assert(vh::battle_fingerprint(ui.battle) == before);
        } else {
            assert(ui.selected == -1);
        }
        assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
               == TrainingEffect::TurnEnded);
        assert(ui.selected == -1);
        assert(ui.battle.find_unit(1)->hp == remaining_hp[index]);
        assert(ui.battle.find_unit(3)->hp == 20);
        assert(ui.battle.round() == expected_round[index]);
        assert(vh::battle_fingerprint(ui.battle) == golden[index]);
        if (index < 7) {
            assert(ui.battle.phase() == vh::Phase::Player);
            assert(ui.status == "New player round.");
            assert(ui.battle.find_unit(1)->hp > 0);
        }
    }
    assert(ui.battle.phase() == vh::Phase::Defeat);
    assert(ui.status == "Defeat.");
    assert(ui.battle.unit_at({1, 5}) == nullptr);
    assert(ui.battle.unit_at({2, 5}) != nullptr);
    assert(ui.battle.find_unit(1)->hp == 0);
    assert(ui.battle.find_unit(3)->hp == 20);
    assert(ui.battle.reachable(1).empty());
    const auto defeat_hash = vh::battle_fingerprint(ui.battle);
    assert(defeat_hash == UINT64_C(0x3b0411b006f113c1));

    // No extra player turn, attacker resurrection or HP mutation after Defeat.
    assert(vh::apply_training_action(ui, TrainingAction::EndTurn)
           == TrainingEffect::Rejected);
    assert(vh::apply_training_action(ui, TrainingAction::Attack)
           == TrainingEffect::Rejected);
    assert(vh::apply_training_action(ui, TrainingAction::Confirm)
           == TrainingEffect::Rejected);
    assert(!ui.battle.end_player_turn());
    assert(!ui.battle.move(1, {1, 4}));
    assert(!ui.battle.attack(1, 3));
    assert(!ui.battle.attack(3, 1));
    assert(ui.battle.phase() == vh::Phase::Defeat);
    assert(ui.battle.round() == 8);
    assert(ui.battle.find_unit(1)->hp == 0);
    assert(ui.battle.find_unit(3)->hp == 20);
    assert(vh::battle_fingerprint(ui.battle) == defeat_hash);

    std::printf("Stage51 ROM-free defeat=true round=8 ScoutHP=0 RaiderHP=20 state=%016llx terminal_rejections=true\n",
                static_cast<unsigned long long>(defeat_hash));
}
