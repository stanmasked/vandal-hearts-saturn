#include "vh/battle.hpp"
#include "vh/replay.hpp"
#include "vh/visual_digest.hpp"
#include <cassert>
#include <cstdint>
#include <stdexcept>

int main() {
    const auto hash = vh::battle_fingerprint(vh::Battle::training());
    assert(hash == UINT64_C(12553978255608676096));
    std::uint64_t rebuilt = 0;
    for (int bit = 0; bit < vh::digest_cells; ++bit) {
        const auto rect = vh::digest_cell_rect(bit);
        assert(rect.x >= 20 && rect.x + rect.w <= 112);
        assert(rect.y >= 20 && rect.y + rect.h <= 112);
        assert(rect.w == 8 && rect.h == 8);
        if (vh::digest_bit(hash, bit)) rebuilt |= (UINT64_C(1) << bit);
    }
    assert(rebuilt == hash);
    assert(vh::digest_anchor(0).x == 8 && vh::digest_anchor(0).y == 8);
    assert(vh::digest_anchor(1).x == 116 && vh::digest_anchor(1).y == 8);
    assert(vh::digest_anchor(2).x == 8 && vh::digest_anchor(2).y == 116);
    for (const int bad : {-1, 64}) {
        bool threw = false;
        try { (void)vh::digest_cell_rect(bad); }
        catch (const std::out_of_range&) { threw = true; }
        assert(threw);
        threw = false;
        try { (void)vh::digest_bit(hash, bad); }
        catch (const std::out_of_range&) { threw = true; }
        assert(threw);
    }
}
