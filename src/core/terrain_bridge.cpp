#include "vh/terrain_bridge.hpp"
#include <stdexcept>
#include <string>

namespace vh {
namespace {
constexpr int kMaxElevationMagnitude = 100000;
constexpr int kMaxTerrainCost = 100000;
constexpr const char* kHeader = "VH_TERRAIN_UNVERIFIED_V1";
}

Battle load_unverified_terrain(std::istream& source) {
    std::string tag;
    if (!(source >> tag) || tag != kHeader)
        throw std::invalid_argument("unknown or missing terrain format");
    int width = 0, height = 0;
    if (!(source >> tag >> width >> height) || tag != "SIZE")
        throw std::invalid_argument("missing or malformed terrain dimensions");
    Battle result(width, height); // central native 1..128 grid dimension limit

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int read_x = -1, read_y = -1, elevation = 0;
            int movement_cost = 0, passable = -1;
            if (!(source >> tag >> read_x >> read_y >> elevation >>
                  movement_cost >> passable) ||
                tag != "CELL" || read_x != x || read_y != y ||
                elevation < -kMaxElevationMagnitude ||
                elevation > kMaxElevationMagnitude ||
                movement_cost < 1 || movement_cost > kMaxTerrainCost ||
                (passable != 0 && passable != 1))
                throw std::invalid_argument("invalid or out-of-order terrain cell");
            result.set_tile({x, y}, {elevation, movement_cost, passable == 1});
        }
    }

    if (source >> tag)
        throw std::invalid_argument("unexpected trailing terrain data");
    // If the final read failed for a reason other than EOF, do not accept
    // an invalid trailing token (e.g. a broken input stream).
    if (!source.eof())
        throw std::invalid_argument("terrain stream read error");
    return result;
}
} // namespace vh
