#include "vh/battle.hpp"
#include "vh/replay.hpp"

#include <cinttypes>
#include <cstdio>

int main() {
    vh::Battle battle = vh::Battle::training();
    std::printf("VHS_REPLAY version=1 scene=synthetic_training steps=5 initial=%016" PRIx64 "\n",
                vh::battle_fingerprint(battle));
    const auto commands = vh::training_replay_script();
    for (std::size_t i = 0; i < commands.size(); ++i) {
        const auto outcome = vh::apply_replay_command(battle, commands[i]);
        std::printf("VHS_REPLAY step=%zu applied=%d round=%d phase=%d state=%016" PRIx64 "\n",
                    i + 1, outcome.applied ? 1 : 0, outcome.round,
                    static_cast<int>(outcome.phase), outcome.fingerprint);
    }
    return 0;
}
