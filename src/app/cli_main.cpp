#include "vh/battle.hpp"
#include <iostream>
#include <sstream>
#include <string>

namespace {
void print_map(const vh::Battle& b) {
    std::cout << "\nRound " << b.round() << " | ";
    if (b.phase() == vh::Phase::Victory) std::cout << "VICTORY\n";
    else if (b.phase() == vh::Phase::Defeat) std::cout << "DEFEAT\n";
    else std::cout << "PLAYER TURN\n";
    for (int y = 0; y < b.height(); ++y) {
        for (int x = 0; x < b.width(); ++x) {
            const vh::Pos p{x, y};
            const auto* unit = b.unit_at(p);
            const char ch = unit ? (unit->side == vh::Side::Player ? 'P' : 'E') :
                (!b.tile(p).walkable ? '#' : static_cast<char>('0' + b.tile(p).elevation));
            std::cout << ch << ' ';
        }
        std::cout << '\n';
    }
    for (const auto& u : b.units()) if (u.hp > 0) {
        std::cout << u.id << " " << u.name << " hp=" << u.hp
                  << " pos=" << u.pos.x << ',' << u.pos.y << (u.acted ? " [attacked]" : "") << '\n';
    }
}
}

int main() {
    auto battle = vh::Battle::training();
    std::cout << "Saturn-inspired prototype; NOT original Vandal Hearts game data.\n"
                 "Commands: m ID X Y | a ATTACKER_ID TARGET_ID | end | show | quit\n";
    print_map(battle);
    std::string line;
    while (battle.phase() == vh::Phase::Player && std::getline(std::cin, line)) {
        std::istringstream input(line);
        std::string command;
        input >> command;
        if (command == "quit") break;
        if (command == "m") {
            int id, x, y;
            if (input >> id >> x >> y) std::cout << (battle.move(id, {x, y}) ? "moved" : "illegal move") << '\n';
        } else if (command == "a") {
            int id, target;
            if (input >> id >> target) std::cout << (battle.attack(id, target) ? "attacked" : "illegal attack") << '\n';
        } else if (command == "end") {
            battle.end_player_turn();
        }
        print_map(battle);
    }
    return 0;
}
