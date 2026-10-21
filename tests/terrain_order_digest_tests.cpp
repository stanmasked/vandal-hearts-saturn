// Stage72: zero-original-media, order-sensitive tile identity contract.
#include "vh/terrain_order_digest.hpp"
#include "vh/replay.hpp"
#include <cassert>
#include <cstdint>

namespace {
void read_only_digest_and_swapped_tiles() {
    vh::Battle a(2, 2);
    a.set_tile({0, 0}, {-3, 5, true});
    a.set_tile({1, 0}, {9, 2, false});
    a.set_tile({0, 1}, {0, 1, true});
    a.set_tile({1, 1}, {-1, 4, true});
    const auto fingerprint = vh::battle_fingerprint(a);
    const auto ordered = vh::ordered_terrain_digest(a);
    for (int i = 0; i < 100; ++i) {
        assert(vh::ordered_terrain_digest(a) == ordered);
        assert(vh::battle_fingerprint(a) == fingerprint);
    }
    vh::Battle swapped = a;
    const vh::Tile first = swapped.tile({0, 0});
    const vh::Tile second = swapped.tile({1, 0});
    swapped.set_tile({0, 0}, second);
    swapped.set_tile({1, 0}, first);
    // The global sums are unchanged by a tile swap. The ordered digest is not.
    assert(vh::ordered_terrain_digest(swapped) != ordered);
    swapped.set_tile({0, 0}, first);
    swapped.set_tile({1, 0}, second);
    assert(vh::ordered_terrain_digest(swapped) == ordered);
}
void every_field_changes_digest() {
    vh::Battle initial(1, 2);
    initial.set_tile({0, 0}, {-5, 7, true});
    initial.set_tile({0, 1}, {2, 3, false});
    const auto digest = vh::ordered_terrain_digest(initial);
    auto a = initial;
    a.set_tile({0, 0}, {-4, 7, true});
    assert(vh::ordered_terrain_digest(a) != digest);
    a = initial;
    a.set_tile({0, 0}, {-5, 8, true});
    assert(vh::ordered_terrain_digest(a) != digest);
    a = initial;
    a.set_tile({0, 0}, {-5, 7, false});
    assert(vh::ordered_terrain_digest(a) != digest);
}
void dimensions_are_part_of_identity() {
    vh::Battle one_by_four(1, 4);
    vh::Battle two_by_two(2, 2);
    assert(vh::ordered_terrain_digest(one_by_four) !=
           vh::ordered_terrain_digest(two_by_two));
}
} // namespace
int main() {
    read_only_digest_and_swapped_tiles();
    every_field_changes_digest();
    dimensions_are_part_of_identity();
}
