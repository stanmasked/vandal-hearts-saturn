// Deterministic C++17 -> image -> Pillow protocol integration fixture.
// Test-only ROM-free graphics: no SDL, console SDK or Saturn game resources.
#include "vh/battle.hpp"
#include "vh/replay.hpp"
#include "vh/visual_digest.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kWidth = 1280;
constexpr int kHeight = 720;
constexpr std::array<std::uint8_t, 3> kBackground = {14, 19, 32};
constexpr std::array<std::uint8_t, 3> kOn = {66, 220, 132};
constexpr std::array<std::uint8_t, 3> kOff = {40, 53, 69};
constexpr std::array<std::uint8_t, 3> kAnchor = {234, 40, 190};

void rect(std::vector<std::uint8_t>& data, const vh::DigestRect& rect,
          const std::array<std::uint8_t, 3>& rgb) {
    if (rect.x < 0 || rect.y < 0 || rect.w < 1 || rect.h < 1 ||
        rect.x + rect.w > kWidth || rect.y + rect.h > kHeight)
        throw std::out_of_range("visual fixture rectangle outside frame");
    for (int y = rect.y; y < rect.y + rect.h; ++y) {
        for (int x = rect.x; x < rect.x + rect.w; ++x) {
            const auto index = static_cast<std::size_t>(3 * (y * kWidth + x));
            for (int component = 0; component < 3; ++component)
                data[index + component] = rgb[component];
        }
    }
}

void save(const std::string& filename, const vh::Battle& battle) {
    std::vector<std::uint8_t> data(static_cast<std::size_t>(kWidth * kHeight * 3));
    for (std::size_t i = 0; i < data.size(); i += 3)
        for (int c = 0; c < 3; ++c) data[i + c] = kBackground[c];
    const auto fingerprint = vh::battle_fingerprint(battle);
    for (int bit = 0; bit < vh::digest_cells; ++bit)
        rect(data, vh::digest_cell_rect(bit),
             vh::digest_bit(fingerprint, bit) ? kOn : kOff);
    for (int i = 0; i < 3; ++i)
        rect(data, vh::digest_anchor(i), kAnchor);
    std::ofstream out(filename, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot create fixture");
    out << "P6\n" << kWidth << ' ' << kHeight << "\n255\n";
    out.write(reinterpret_cast<const char*>(data.data()),
              static_cast<std::streamsize>(data.size()));
    if (!out) throw std::runtime_error("incomplete fixture image write");
}
}

int main(int argc, char** argv) {
    if (argc != 2 || !argv[1]) {
        std::cerr << "Usage: vh_visual_fixture OUTPUT_DIRECTORY\n";
        return 2;
    }
    try {
        const std::string dir(argv[1]);
        vh::Battle battle = vh::Battle::training();
        const auto initial = vh::battle_fingerprint(battle);
        save(dir + "/initial.ppm", battle);
        if (!battle.move(1, {2, 5})) throw std::runtime_error("training move unexpectedly rejected");
        const auto moved = vh::battle_fingerprint(battle);
        if (initial == moved) throw std::runtime_error("state fingerprint did not change");
        save(dir + "/moved.ppm", battle);
        std::printf("initial=%016llx\nmoved=%016llx\n",
                    static_cast<unsigned long long>(initial),
                    static_cast<unsigned long long>(moved));
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ROM-free visual fixture failed: " << error.what() << '\n';
        return 1;
    }
}
