// Stage72: host-side numeric tile-order diagnostic on private-safe format.
// Emits aggregate dimensions and a NON-CRYPTOGRAPHIC ordered digest only.
// Public CI supplies invented numeric data; do not pass real game payloads.
#include "vh/terrain_bridge.hpp"
#include "vh/terrain_order_digest.hpp"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv) {
    if (argc != 2 || !argv[1]) {
        std::cerr << "TERRAIN_ORDER_REJECTED\n";
        return 2;
    }
    try {
        std::ifstream input(argv[1], std::ios::binary);
        if (!input) throw std::runtime_error("unreadable");
        const vh::Battle battle = vh::load_unverified_terrain(input);
        std::cout << "VH_TERRAIN_ORDER_V1 cells="
                  << battle.width() * battle.height()
                  << " digest=" << std::hex << std::setfill('0')
                  << std::setw(16) << vh::ordered_terrain_digest(battle)
                  << std::dec << " units=" << battle.units().size() << "\n";
        return 0;
    } catch (...) {
        // Do not echo user-supplied file paths or original source bytes.
        std::cerr << "TERRAIN_ORDER_REJECTED\n";
        return 1;
    }
}
