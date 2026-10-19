#pragma once

#include <string>
#include <vector>

namespace vh {

struct Pos {
    int x = 0;
    int y = 0;
};

inline bool operator==(Pos a, Pos b) { return a.x == b.x && a.y == b.y; }
inline bool operator!=(Pos a, Pos b) { return !(a == b); }

enum class Side { Player, Enemy };
enum class Phase { Player, Enemy, Victory, Defeat };

struct Tile {
    int elevation = 0;
    int terrain_cost = 1;
    bool walkable = true;
};

struct Unit {
    int id = 0;
    std::string name;
    Side side = Side::Player;
    Pos pos{};
    int hp = 20;
    int attack = 7;
    int defense = 2;
    int move_points = 4;
    int range = 1;
    bool moved = false;
    bool acted = false;
};

class Battle {
public:
    Battle(int width, int height);
    static Battle training();

    int width() const { return width_; }
    int height() const { return height_; }
    Phase phase() const { return phase_; }
    int round() const { return round_; }
    const std::vector<Unit>& units() const { return units_; }

    bool in_bounds(Pos p) const;
    const Tile& tile(Pos p) const;
    void set_tile(Pos p, Tile tile);
    void add_unit(Unit unit);
    const Unit* unit_at(Pos p) const;
    const Unit* find_unit(int id) const;
    std::vector<Pos> reachable(int unit_id) const;
    bool move(int unit_id, Pos dest);
    bool attack(int attacker_id, int defender_id);
    bool end_player_turn(); // Synthetic enemy AI and start of next player round.

private:
    int width_;
    int height_;
    int round_ = 1;
    Phase phase_ = Phase::Player;
    std::vector<Tile> tiles_;
    std::vector<Unit> units_;

    Unit* mutable_unit(int id);
    int shortest_cost(const Unit& unit, Pos destination) const;
    bool occupied(Pos pos, int excluded_id = -1) const;
    void update_outcome();
    void run_enemy_ai();
};

} // namespace vh
