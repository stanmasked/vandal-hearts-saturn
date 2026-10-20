#include "vh/attack_training.hpp"
#include "vh/training_controls.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdint>
#include <cstdio>

int main() {
    vh::TrainingUi ui;
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1,5};
    assert(ui.battle.units().size() == 2);
    assert(vh::battle_fingerprint(ui.battle) == UINT64_C(0x9376e23745926630));
    assert(ui.battle.find_unit(3)->hp == 20);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Confirm)
        == vh::TrainingEffect::Selected);
    assert(ui.selected == 1);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Right)
        == vh::TrainingEffect::CursorMoved);
    assert((ui.cursor == vh::Pos{2,5}));
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Attacked);
    const auto moved_hash = vh::battle_fingerprint(ui.battle);
    assert(moved_hash == UINT64_C(0x9a0233cdc1acffdb));
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(ui.battle.find_unit(1)->acted);
    assert(vh::apply_training_action(ui, vh::TrainingAction::Attack)
        == vh::TrainingEffect::Rejected);
    assert(ui.battle.find_unit(3)->hp == 14);
    assert(vh::battle_fingerprint(ui.battle) == moved_hash);
    std::printf("Stage44 duel initial=%016llx attacked=%016llx HP=20->14 second_rejected=true\n",
        static_cast<unsigned long long>(UINT64_C(0x9376e23745926630)),
        static_cast<unsigned long long>(moved_hash));
}
