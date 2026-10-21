#pragma once

#include "vh/battle.hpp"
#include <algorithm>

namespace vh {

// These coordinates describe only the synthetic ROM-free 8x8 tactics demo.
// They do not imply known Sega Saturn map or graphical-resource coordinates.
struct Pixel { int x; int y; };
enum class CursorStep { Left, Right, Up, Down };

inline Pos advance_cursor(Pos current, CursorStep direction, int width, int height) {
    if (width < 1 || height < 1) return current;
    switch (direction) {
        case CursorStep::Left: current.x = std::max(0, current.x - 1); break;
        case CursorStep::Right: current.x = std::min(width - 1, current.x + 1); break;
        case CursorStep::Up: current.y = std::max(0, current.y - 1); break;
        case CursorStep::Down: current.y = std::min(height - 1, current.y + 1); break;
    }
    return current;
}

inline Pixel project_training_tile(Pos p, int elevation = 0) {
    constexpr int base_x = 640;
    constexpr int base_y = 136;
    constexpr int tile_half_width = 40;
    constexpr int tile_half_height = 20;
    constexpr int elevation_height = 18;
    return {base_x + (p.x - p.y) * tile_half_width,
            base_y + (p.x + p.y) * tile_half_height - elevation * elevation_height};
}

} // namespace vh
