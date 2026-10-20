#include "vh/battle.hpp"
#include "vh/replay.hpp"

#include <cassert>
#include <cstdint>
#include <iostream>

using namespace vh;

int main() {
    Battle first = Battle::training();
    Battle second = Battle::training();
    const std::uint64_t initial = battle_fingerprint(first);
    assert(initial == battle_fingerprint(second));
    assert(initial == UINT64_C(12553978255608676096));

    const auto left = run_training_replay(first);
    const auto right = run_training_replay(second);
    assert(left.size() == 5 && right.size() == left.size());
    const bool expected[] = {false, true, false, true, true};
    for (size_t i = 0; i < left.size(); ++i) {
        assert(left[i].applied == expected[i]);
        assert(left[i].applied == right[i].applied);
        assert(left[i].fingerprint == right[i].fingerprint);
        assert(left[i].round == right[i].round);
        assert(left[i].phase == right[i].phase);
    }
    assert(left[0].fingerprint == initial);
    assert(left[2].fingerprint == left[1].fingerprint);
    assert(left[1].fingerprint != initial);
    assert(left[3].round == 2);
    assert(left[4].fingerprint != left[3].fingerprint);
    assert(battle_fingerprint(first) == left.back().fingerprint);
    assert(left.back().fingerprint == UINT64_C(3427583621734867608));

    // All fields and tile ordering are actually hashed; no native struct
    // padding, host byte order, or vector insertion order enters the digest.
    Battle changed = Battle::training();
    changed.set_tile({0, 0}, {1, 1, true});
    assert(battle_fingerprint(changed) != initial);
    Battle original = Battle::training();
    Battle reordered(8, 8), renamed(8, 8);
    for (int y = 0; y < 8; ++y) for (int x = 0; x < 8; ++x) {
        const Tile tile = original.tile({x, y});
        reordered.set_tile({x, y}, tile);
        renamed.set_tile({x, y}, tile);
    }
    for (auto it = original.units().rbegin(); it != original.units().rend(); ++it)
        reordered.add_unit(*it);
    for (const Unit& u : original.units()) {
        Unit copy = u;
        if (copy.id == 1) copy.name += "_V2";
        renamed.add_unit(copy);
    }
    assert(battle_fingerprint(original) == battle_fingerprint(reordered));
    assert(battle_fingerprint(original) != battle_fingerprint(renamed));

    std::cout << "ROM-free deterministic replay: initial=" << initial
              << " final=" << left.back().fingerprint
              << " steps=" << left.size() << "\n";
}
