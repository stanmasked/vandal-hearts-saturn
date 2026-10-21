#pragma once

#include "vh/battle.hpp"

#include <cstring>
#include <stdexcept>

namespace vh {

// Zero means regular interactive mode. The diagnostic flag only controls the
// number of rendered frames; it does NOT simulate successful graphics output.
inline int smoke_frames_from_args(int argc, const char* const argv[]) {
    if (argc < 0 || (argc > 0 && !argv)) throw std::invalid_argument("invalid argv");
    constexpr const char* prefix = "--smoke-frames=";
    constexpr size_t prefix_len = 15;
    int frames = 0;
    for (int i = 1; i < argc; ++i) {
        if (!argv[i]) throw std::invalid_argument("null argument");
        if (std::strncmp(argv[i], prefix, prefix_len) != 0) continue;
        if (frames != 0) throw std::invalid_argument("duplicate smoke setting");
        const char* digits = argv[i] + prefix_len;
        if (!*digits) throw std::invalid_argument("empty smoke frame limit");
        int value = 0;
        for (const char* p = digits; *p; ++p) {
            if (*p < '0' || *p > '9') throw std::invalid_argument("invalid smoke frame limit");
            value = value * 10 + (*p - '0');
            if (value > 600) throw std::invalid_argument("smoke frame limit exceeds 600");
        }
        if (!value) throw std::invalid_argument("smoke frame limit must be positive");
        frames = value;
    }
    return frames;
}

// Verifies only the synthetic ROM-free scene used by this native prototype.
inline bool smoke_training_scene_ready(const Battle& battle) {
    if (battle.width() != 8 || battle.height() != 8 ||
        battle.phase() != Phase::Player || battle.round() != 1) return false;
    int allies = 0, enemies = 0;
    for (const auto& u : battle.units()) {
        if (u.hp <= 0 || !battle.in_bounds(u.pos) ||
            !battle.tile(u.pos).walkable || battle.unit_at(u.pos) == nullptr) return false;
        if (u.side == Side::Player) ++allies;
        else ++enemies;
    }
    return allies >= 1 && enemies >= 1;
}

} // namespace vh
