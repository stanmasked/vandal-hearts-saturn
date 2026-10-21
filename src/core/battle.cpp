#include "vh/battle.hpp"

#include <algorithm>
#include <cstdlib>
#include <limits>
#include <queue>
#include <stdexcept>
#include <utility>

namespace vh {
namespace {
constexpr Pos kDirections[4] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
// This value is a sentinel, never a valid path. Keep arithmetic below it.
constexpr int kUnreachableCost = std::numeric_limits<int>::max() / 4;
int distance(Pos a, Pos b) { return std::abs(a.x - b.x) + std::abs(a.y - b.y); }
}

Battle::Battle(int width, int height) : width_(width), height_(height) {
    if (width <= 0 || height <= 0 || width > 128 || height > 128) {
        throw std::invalid_argument("invalid battle map dimensions");
    }
    tiles_.resize(static_cast<size_t>(width) * static_cast<size_t>(height));
}

bool Battle::in_bounds(Pos p) const {
    return p.x >= 0 && p.y >= 0 && p.x < width_ && p.y < height_;
}

const Tile& Battle::tile(Pos p) const {
    if (!in_bounds(p)) throw std::out_of_range("tile outside map");
    return tiles_.at(static_cast<size_t>(p.y * width_ + p.x));
}

void Battle::set_tile(Pos p, Tile value) {
    if (value.terrain_cost < 1) throw std::invalid_argument("terrain cost must be positive");
    if (!in_bounds(p)) throw std::out_of_range("tile outside map");
    tiles_.at(static_cast<size_t>(p.y * width_ + p.x)) = value;
}

void Battle::add_unit(Unit unit) {
    if (!in_bounds(unit.pos) || !tile(unit.pos).walkable || occupied(unit.pos) ||
        find_unit(unit.id) || unit.hp <= 0 || unit.move_points < 0 || unit.range < 1) {
        throw std::invalid_argument("invalid unit");
    }
    units_.push_back(std::move(unit));
}

const Unit* Battle::find_unit(int id) const {
    for (const auto& u : units_) if (u.id == id) return &u;
    return nullptr;
}
Unit* Battle::mutable_unit(int id) {
    for (auto& u : units_) if (u.id == id) return &u;
    return nullptr;
}
const Unit* Battle::unit_at(Pos pos) const {
    for (const auto& u : units_) if (u.hp > 0 && u.pos == pos) return &u;
    return nullptr;
}
bool Battle::occupied(Pos pos, int excluded_id) const {
    const auto* u = unit_at(pos);
    return u && u->id != excluded_id;
}

int Battle::shortest_cost(const Unit& unit, Pos destination) const {
    constexpr int inf = kUnreachableCost;
    if (!in_bounds(destination) || !tile(destination).walkable ||
        occupied(destination, unit.id)) return inf;
    std::vector<int> dist(static_cast<size_t>(width_ * height_), inf);
    using Step = std::pair<int, int>; // (cost, index)
    std::priority_queue<Step, std::vector<Step>, std::greater<Step>> frontier;
    const int start = unit.pos.y * width_ + unit.pos.x;
    dist[static_cast<size_t>(start)] = 0;
    frontier.emplace(0, start);
    while (!frontier.empty()) {
        const auto [cost, index] = frontier.top();
        frontier.pop();
        if (cost != dist[static_cast<size_t>(index)]) continue;
        const Pos here{index % width_, index / width_};
        if (here == destination) return cost;
        for (const Pos delta : kDirections) {
            const Pos next{here.x + delta.x, here.y + delta.y};
            if (!in_bounds(next) || !tile(next).walkable || occupied(next, unit.id)) continue;
            if (std::abs(tile(next).elevation - tile(here).elevation) > 1) continue;
            // Avoid signed overflow and never relax an unreachable sentinel.
            const int step_cost = tile(next).terrain_cost;
            if (step_cost >= inf - cost) continue;
            const int next_cost = cost + step_cost;
            const int next_index = next.y * width_ + next.x;
            if (next_cost < dist[static_cast<size_t>(next_index)]) {
                dist[static_cast<size_t>(next_index)] = next_cost;
                frontier.emplace(next_cost, next_index);
            }
        }
    }
    return inf;
}

std::vector<Pos> Battle::reachable(int unit_id) const {
    const Unit* u = find_unit(unit_id);
    std::vector<Pos> result;
    if (!u || u->hp <= 0 || u->moved || phase_ != Phase::Player || u->side != Side::Player) return result;
    for (int y = 0; y < height_; ++y) {
        for (int x = 0; x < width_; ++x) {
            const Pos p{x, y};
            if (p != u->pos && shortest_cost(*u, p) <= u->move_points) result.push_back(p);
        }
    }
    return result;
}

MovePreview Battle::preview_move(int id, Pos target) const {
    const Unit* u = find_unit(id);
    if (!u || u->hp <= 0 || u->moved || phase_ != Phase::Player ||
        u->side != Side::Player || u->pos == target) return {};
    const int cost = shortest_cost(*u, target);
    if (cost >= kUnreachableCost || cost > u->move_points) return {};
    return {true, cost, u->move_points - cost};
}

bool Battle::move(int id, Pos target) {
    // One authoritative legality check for preview and committed movement.
    const MovePreview preview = preview_move(id, target);
    if (!preview.legal) return false;
    Unit* u = mutable_unit(id);
    u->pos = target;
    u->moved = true;
    return true;
}

AttackPreview Battle::preview_attack(int attacker_id, int defender_id) const {
    const Unit* from = find_unit(attacker_id);
    const Unit* to = find_unit(defender_id);
    // Exactly the same validity rules govern both forecast and real attack:
    // no friendly fire, duplicate strike, attack on dead units or wrong phase.
    if (!from || !to || from == to || from->hp <= 0 || to->hp <= 0 ||
        from->acted || from->side == to->side ||
        distance(from->pos, to->pos) > from->range ||
        (from->side == Side::Player && phase_ != Phase::Player) ||
        (from->side == Side::Enemy && phase_ != Phase::Enemy))
        return {};

    const int height_bonus = tile(from->pos).elevation > tile(to->pos).elevation ? 2 : 0;
    const int raw_damage = std::max(1, from->attack + height_bonus - to->defense);
    const int dealt = std::min(to->hp, raw_damage);
    bool ends_battle = dealt == to->hp;
    if (ends_battle) {
        for (const Unit& other : units_) {
            if (other.id != to->id && other.side == to->side && other.hp > 0) {
                ends_battle = false;
                break;
            }
        }
    }
    return {true, dealt, to->hp - dealt, ends_battle};
}

bool Battle::attack(int attacker_id, int defender_id) {
    // One source of truth: preview and committed attack can never drift
    // on damage, legal target, overkill or elevation.
    const AttackPreview forecast = preview_attack(attacker_id, defender_id);
    if (!forecast.legal) return false;
    Unit* from = mutable_unit(attacker_id);
    Unit* to = mutable_unit(defender_id);
    to->hp = forecast.remaining_hp;
    from->acted = true;
    update_outcome();
    return true;
}

void Battle::update_outcome() {
    bool players = false;
    bool enemies = false;
    for (const Unit& u : units_) {
        if (u.hp <= 0) continue;
        if (u.side == Side::Player) players = true;
        else enemies = true;
    }
    if (!players) phase_ = Phase::Defeat;
    else if (!enemies) phase_ = Phase::Victory;
}

void Battle::run_enemy_ai() {
    // Deliberately simple placeholder AI; this is NOT Saturn battle logic.
    const std::vector<int> enemy_ids = [&]() {
        std::vector<int> ids;
        for (const auto& u : units_) if (u.side == Side::Enemy && u.hp > 0) ids.push_back(u.id);
        return ids;
    }();
    for (const int id : enemy_ids) {
        Unit* enemy = mutable_unit(id);
        if (!enemy || enemy->hp <= 0 || phase_ != Phase::Enemy) break;
        const Unit* target = nullptr;
        int closest = std::numeric_limits<int>::max();
        for (const auto& u : units_) {
            if (u.side != Side::Player || u.hp <= 0) continue;
            const int d = distance(u.pos, enemy->pos);
            if (d < closest) { closest = d; target = &u; }
        }
        if (!target) break;
        const int target_id = target->id;
        if (closest > enemy->range) {
            const Pos goal = target->pos;
            Pos best = enemy->pos;
            int best_distance = closest;
            for (int y = 0; y < height_; ++y) for (int x = 0; x < width_; ++x) {
                const Pos p{x, y};
                if (p == enemy->pos || distance(p, goal) >= best_distance) continue;
                const int cost = shortest_cost(*enemy, p);
                if (cost < kUnreachableCost && cost <= enemy->move_points) {
                    best = p;
                    best_distance = distance(p, goal);
                }
            }
            enemy->pos = best;
        }
        if (distance(enemy->pos, mutable_unit(target_id)->pos) <= enemy->range)
            attack(id, target_id);
    }
}

bool Battle::end_player_turn() {
    if (phase_ != Phase::Player) return false;
    phase_ = Phase::Enemy;
    for (auto& u : units_) if (u.side == Side::Enemy) { u.acted = false; u.moved = false; }
    run_enemy_ai();
    if (phase_ != Phase::Enemy) return true;
    for (auto& u : units_) if (u.side == Side::Player) { u.acted = false; u.moved = false; }
    phase_ = Phase::Player;
    ++round_;
    return true;
}

Battle Battle::training() {
    Battle battle(8, 8);
    for (int y = 0; y < battle.height(); ++y) for (int x = 0; x < battle.width(); ++x) {
        Tile tile;
        tile.elevation = (x >= 5 && y <= 2) ? 1 : 0;
        tile.walkable = !(x == 3 && y >= 2 && y <= 4);
        tile.terrain_cost = (x == 2 && y == 5) ? 2 : 1;
        battle.set_tile({x, y}, tile);
    }
    battle.add_unit({1, "Scout", Side::Player, {1, 5}, 22, 8, 3, 4, 1});
    battle.add_unit({2, "Guard", Side::Player, {1, 6}, 26, 7, 4, 3, 1});
    battle.add_unit({3, "Raider", Side::Enemy, {6, 1}, 18, 7, 2, 3, 1});
    battle.add_unit({4, "Archer", Side::Enemy, {6, 3}, 14, 6, 2, 3, 2});
    return battle;
}
} // namespace vh
