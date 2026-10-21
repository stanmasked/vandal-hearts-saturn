// Stage69: synthetic host-only inspection of the strict Stage68 terrain format.
// Does not load original Saturn files into CI or expose private scene labels.
#include "vh/terrain_bridge.hpp"
#include <fstream>
#include <iostream>
#include <cstdint>

int main(int argc, char** argv) {
    if (argc != 2 || !argv[1]) {
        std::cerr << "TERRAIN_PROBE_REJECTED\n";
        return 2;
    }
    try {
        std::ifstream source(argv[1], std::ios::binary);
        if (!source) throw std::runtime_error("file cannot be read");
        const vh::Battle battle = vh::load_unverified_terrain(source);
        std::int64_t elevation_sum = 0;
        std::int64_t cost_sum = 0;
        std::uint64_t walkable = 0;
        std::uint64_t blocked = 0;
        for (int y = 0; y < battle.height(); ++y) {
            for (int x = 0; x < battle.width(); ++x) {
                const vh::Tile& t = battle.tile({x, y});
                elevation_sum += static_cast<std::int64_t>(t.elevation);
                cost_sum += static_cast<std::int64_t>(t.terrain_cost);
                if (t.walkable) ++walkable;
                else ++blocked;
            }
        }
        std::cout << "VH_TERRAIN_PROBE size=" << battle.width() << "x"
                  << battle.height() << " cells=" << walkable + blocked
                  << " walkable=" << walkable << " blocked=" << blocked
                  << " cost_sum=" << cost_sum << " elevation_sum=" << elevation_sum
                  << " units=" << battle.units().size() << "\n";
        return 0;
    } catch (...) {
        // Do not echo file paths, private tile records or parser inputs.
        std::cerr << "TERRAIN_PROBE_REJECTED\n";
        return 1;
    }
}
