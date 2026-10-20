#pragma once

#include <cstdint>
#include <stdexcept>

namespace vh {

// ROM-free debug overlay. These 1280x720 logical coords are intentionally
// separate from the unknown original Sega Saturn screen/map geometry.
constexpr int digest_cells = 64;
constexpr int digest_columns = 8;
constexpr int digest_cell_size = 8;
constexpr int digest_pitch = 12;
constexpr int digest_x = 20;
constexpr int digest_y = 20;
constexpr int digest_anchor_size = 8;

struct DigestRect { int x, y, w, h; };

inline DigestRect digest_cell_rect(int bit_index) {
    if (bit_index < 0 || bit_index >= digest_cells)
        throw std::out_of_range("invalid visual digest bit");
    return {digest_x + (bit_index % digest_columns) * digest_pitch,
            digest_y + (bit_index / digest_columns) * digest_pitch,
            digest_cell_size, digest_cell_size};
}

constexpr DigestRect digest_anchor(int which) {
    return which == 0 ? DigestRect{8, 8, digest_anchor_size, digest_anchor_size} :
           which == 1 ? DigestRect{116, 8, digest_anchor_size, digest_anchor_size} :
           DigestRect{8, 116, digest_anchor_size, digest_anchor_size};
}

inline bool digest_bit(std::uint64_t fingerprint, int bit_index) {
    if (bit_index < 0 || bit_index >= digest_cells)
        throw std::out_of_range("invalid visual digest bit");
    return ((fingerprint >> bit_index) & UINT64_C(1)) != 0;
}

}  // namespace vh
