#include "vh/attack_training.hpp"
#include "vh/battle.hpp"
#include "vh/replay.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>

namespace {

void invalid(const vh::Battle& battle, int attacker, int defender) {
    const auto before = vh::battle_fingerprint(battle);
    const vh::AttackPreview p = battle.preview_attack(attacker, defender);
    assert(!p.legal && p.damage == 0 && p.remaining_hp == 0 && !p.ends_battle);
    assert(vh::battle_fingerprint(battle) == before);
}

void duel_forecast_matches_four_real_rounds() {
    vh::Battle b = vh::stage44_attack_duel();
    const std::array<int, 4> enemy_hp{{14, 8, 2, 0}};
    const std::array<std::uint64_t, 4> hit_hash{{
        UINT64_C(0x9a0233cdc1acffdb), UINT64_C(0x203a8823191e6018),
        UINT64_C(0x7849484ccfd7a0de), UINT64_C(0x6097117b6c951fb6)
    }};
    const std::array<std::uint64_t, 3> next_hash{{
        UINT64_C(0xb633fd92746c41cf), UINT64_C(0x1b81f3931a165925),
        UINT64_C(0x984023d699c803db)
    }};
    invalid(b, 3, 1); // Enemy cannot attack during player's turn.
    invalid(b, 1, 1);
    invalid(b, 1, 99);
    invalid(b, 99, 3);

    for (int round = 0; round < 4; ++round) {
        const auto before = vh::battle_fingerprint(b);
        for (int retry = 0; retry < 20; ++retry) {
            const vh::AttackPreview f = b.preview_attack(1, 3);
            assert(f.legal && f.damage == (round == 3 ? 2 : 6));
            assert(f.remaining_hp == enemy_hp[static_cast<size_t>(round)]);
            assert(f.ends_battle == (round == 3));
            assert(vh::battle_fingerprint(b) == before);
        }
        assert(b.attack(1, 3));
        assert(b.find_unit(3)->hp == enemy_hp[static_cast<size_t>(round)]);
        assert(vh::battle_fingerprint(b) == hit_hash[static_cast<size_t>(round)]);
        invalid(b, 1, 3); // Once-per-turn attack cannot be forecast as legal.
        if (round < 3) {
            assert(b.end_player_turn());
            assert(vh::battle_fingerprint(b) == next_hash[static_cast<size_t>(round)]);
        }
    }
    assert(b.round() == 4 && b.phase() == vh::Phase::Victory);
    invalid(b, 1, 3);
    invalid(b, 3, 1);
    const auto victory = vh::battle_fingerprint(b);
    assert(!b.attack(1, 3));
    assert(!b.end_player_turn());
    assert(vh::battle_fingerprint(b) == victory);
}

void two_allies_and_two_enemies_have_correct_last_enemy_condition() {
    vh::Battle b(2,2);
    b.add_unit({1, "Hero", vh::Side::Player, {0,0}, 20, 20, 2});
    b.add_unit({2, "Guard", vh::Side::Player, {0,1}, 20, 20, 2});
    b.add_unit({3, "Raider", vh::Side::Enemy, {1,0}, 5, 3, 1});
    b.add_unit({4, "Archer", vh::Side::Enemy, {1,1}, 5, 3, 1});
    const auto before = vh::battle_fingerprint(b);
    const vh::AttackPreview first = b.preview_attack(1,3);
    assert(first.legal && first.damage == 5 && first.remaining_hp == 0);
    assert(!first.ends_battle); // One other living enemy remains.
    assert(vh::battle_fingerprint(b) == before);
    assert(b.attack(1,3));
    assert(b.phase() == vh::Phase::Player);
    assert(b.unit_at({1,0}) == nullptr);
    invalid(b,1,4); // Hero has used this turn's attack.
    const auto second = b.preview_attack(2,4);
    assert(second.legal && second.damage == 5 && second.remaining_hp == 0);
    assert(second.ends_battle); // Last enemy death must end encounter.
    assert(b.attack(2,4) && b.phase() == vh::Phase::Victory);
    invalid(b,2,4);
}

void height_advantage_minimum_damage_and_range() {
    vh::Battle height(2,1);
    height.set_tile({0,0},{1,1,true});
    height.add_unit({1,"High",vh::Side::Player,{0,0},20,5,2});
    height.add_unit({3,"Low",vh::Side::Enemy,{1,0},20,2,4});
    const auto f = height.preview_attack(1,3);
    assert(f.legal && f.damage == 3 && f.remaining_hp == 17 && !f.ends_battle);
    assert(height.attack(1,3) && height.find_unit(3)->hp == f.remaining_hp);

    vh::Battle minimum(2,1);
    minimum.add_unit({1,"Weak",vh::Side::Player,{0,0},20,1,1});
    minimum.add_unit({3,"Tank",vh::Side::Enemy,{1,0},3,1,99});
    const auto floor = minimum.preview_attack(1,3);
    assert(floor.legal && floor.damage == 1 && floor.remaining_hp == 2);
    assert(minimum.attack(1,3) && minimum.find_unit(3)->hp == 2);

    vh::Battle distance(3,1);
    distance.add_unit({1,"Archer",vh::Side::Player,{0,0},20,8,1,3,2});
    distance.add_unit({3,"Target",vh::Side::Enemy,{2,0},20,3,1});
    assert(distance.preview_attack(1,3).legal);
    assert(distance.attack(1,3) && distance.find_unit(3)->hp == 13);
    vh::Battle melee(3,1);
    melee.add_unit({1,"Melee",vh::Side::Player,{0,0},20,8,1,3,1});
    melee.add_unit({3,"Far",vh::Side::Enemy,{2,0},20,3,1});
    invalid(melee,1,3);
    assert(!melee.attack(1,3));
}

void defeated_player_has_no_legal_preview() {
    vh::Battle b = vh::stage44_attack_duel();
    for (int i=0;i<8;++i) assert(b.end_player_turn());
    assert(b.round() == 8 && b.phase() == vh::Phase::Defeat);
    assert(vh::battle_fingerprint(b) == UINT64_C(0x3b0411b006f113c1));
    invalid(b,1,3);
    invalid(b,3,1);
}

} // namespace

int main() {
    duel_forecast_matches_four_real_rounds();
    two_allies_and_two_enemies_have_correct_last_enemy_condition();
    height_advantage_minimum_damage_and_range();
    defeated_player_has_no_legal_preview();
    std::printf("Stage53 ROM-free attack preview: 4-round golden parity, 2v2 last enemy, terrain, overkill, range, Defeat and Victory protections passed\n");
}
