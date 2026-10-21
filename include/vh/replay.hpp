#pragma once

#include "vh/battle.hpp"

#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace vh {

// Stable across host/Switch C++17 compilers: canonical little-endian integers
// and FNV-1a over the entire ROM-free gameplay state, never native struct bytes.
class StateDigest {
public:
    void byte(std::uint8_t b) { hash_ = (hash_ ^ b) * UINT64_C(1099511628211); }
    void integer(int value) {
        std::uint32_t x = static_cast<std::uint32_t>(value);
        for (int i = 0; i < 4; ++i) byte(static_cast<std::uint8_t>((x >> (8 * i)) & 255u));
    }
    void text(const std::string& name) {
        if (name.size() > UINT32_MAX) throw std::length_error("unit name too long");
        integer(static_cast<int>(name.size()));
        for (unsigned char c : name) byte(c);
    }
    std::uint64_t value() const { return hash_; }
private:
    std::uint64_t hash_ = UINT64_C(14695981039346656037);
};

inline std::uint64_t battle_fingerprint(const Battle& battle) {
    StateDigest digest;
    for (unsigned char c : {'V','H','S','1'}) digest.byte(c);
    digest.integer(battle.width());
    digest.integer(battle.height());
    digest.integer(battle.round());
    digest.integer(static_cast<int>(battle.phase()));
    for (int y = 0; y < battle.height(); ++y) {
        for (int x = 0; x < battle.width(); ++x) {
            const Tile& t = battle.tile({x, y});
            digest.integer(t.elevation);
            digest.integer(t.terrain_cost);
            digest.integer(t.walkable ? 1 : 0);
        }
    }
    std::vector<const Unit*> units;
    units.reserve(battle.units().size());
    for (const Unit& u : battle.units()) units.push_back(&u);
    std::sort(units.begin(), units.end(), [](const Unit* a, const Unit* b) {
        return a->id < b->id;
    });
    digest.integer(static_cast<int>(units.size()));
    for (const Unit* u : units) {
        digest.integer(u->id);
        digest.text(u->name);
        digest.integer(static_cast<int>(u->side));
        digest.integer(u->pos.x); digest.integer(u->pos.y);
        digest.integer(u->hp); digest.integer(u->attack); digest.integer(u->defense);
        digest.integer(u->move_points); digest.integer(u->range);
        digest.integer(u->moved ? 1 : 0); digest.integer(u->acted ? 1 : 0);
    }
    return digest.value();
}

enum class ReplayOp { Move, Attack, EndTurn };
struct ReplayCommand {
    ReplayOp op;
    int unit_id = 0;
    Pos destination{};
    int defender_id = 0;
};
struct ReplayReceipt {
    bool applied = false;
    std::uint64_t fingerprint = 0;
    int round = 0;
    Phase phase = Phase::Player;
};

inline ReplayReceipt apply_replay_command(Battle& battle, const ReplayCommand& command) {
    bool applied = false;
    switch (command.op) {
        case ReplayOp::Move: applied = battle.move(command.unit_id, command.destination); break;
        case ReplayOp::Attack: applied = battle.attack(command.unit_id, command.defender_id); break;
        case ReplayOp::EndTurn: applied = battle.end_player_turn(); break;
    }
    return {applied, battle_fingerprint(battle), battle.round(), battle.phase()};
}

// Script contains intentionally rejected actions to verify they don't mutate
// state. This is synthetic tactics, NOT a transcript from Sega Saturn game data.
inline std::vector<ReplayCommand> training_replay_script() {
    return {
        {ReplayOp::Attack, 1, {}, 4}, // too far away -> reject
        {ReplayOp::Move, 1, {2, 5}},   // move through 2-cost terrain
        {ReplayOp::Move, 1, {2, 6}},   // already moved -> reject
        {ReplayOp::EndTurn},            // enemy placeholder AI advances round
        {ReplayOp::Move, 2, {2, 6}},   // guard moves in new round
    };
}

inline std::vector<ReplayReceipt> run_training_replay(Battle& battle) {
    std::vector<ReplayReceipt> result;
    for (const ReplayCommand& command : training_replay_script())
        result.push_back(apply_replay_command(battle, command));
    return result;
}

} // namespace vh
