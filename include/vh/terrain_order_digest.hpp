#pragma once

#include "vh/battle.hpp"
#include <cstdint>

namespace vh {

// Stage72: deterministic FNV-1a-64 of every tile IN ROW-MAJOR ORDER.
// The hash encodes dimensions as LE32, then for each (x,y): signed elevation
// modulo 2^32 encoded LE32, cost LE32 and walkability as one byte.
// Not cryptographic and emphatically NOT proof of a genuine Saturn asset.
// There are no source identifiers, private paths or game bytes in this API.
inline std::uint64_t ordered_terrain_digest(const Battle& battle) {
    std::uint64_t state = UINT64_C(14695981039346656037);
    constexpr std::uint64_t prime = UINT64_C(1099511628211);
    const auto byte = [&](std::uint8_t input) {
        state ^= input;
        state *= prime; // unsigned arithmetic wraps modulo 2^64
    };
    const auto le32 = [&](std::uint32_t input) {
        for (int i = 0; i != 4; ++i)
            byte(static_cast<std::uint8_t>((input >> (i * 8)) & 255u));
    };

    le32(static_cast<std::uint32_t>(battle.width()));
    le32(static_cast<std::uint32_t>(battle.height()));
    for (int y = 0; y != battle.height(); ++y) {
        for (int x = 0; x != battle.width(); ++x) {
            const Tile& tile = battle.tile({x, y});
            le32(static_cast<std::uint32_t>(tile.elevation));
            le32(static_cast<std::uint32_t>(tile.terrain_cost));
            byte(static_cast<std::uint8_t>(tile.walkable ? 1 : 0));
        }
    }
    return state;
}

} // namespace vh
