#include "vh/battle.hpp"
#include "vh/smoke.hpp"
#include "vh/cursor_geometry.hpp"
#include "vh/replay.hpp"
#include "vh/visual_digest.hpp"
#include "vh/training_controls.hpp"
#include "vh/attack_preview_hud.hpp"
#include "vh/selected_unit_hud.hpp"
#include "vh/enemy_hover_hud.hpp"
#include "vh/enemy_attack_cue.hpp"
#include "vh/target_damage_hud.hpp"
#include "vh/target_remaining_hud.hpp"
#include <array>
#include <cctype>
#ifdef VH_STAGE44_DUEL
#include "vh/attack_training.hpp"
#endif
#include <SDL.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {
constexpr int W = 1280;
constexpr int H = 720;
constexpr int TILE_HALF_W = 40;
constexpr int TILE_HALF_H = 20;

using Ui = vh::TrainingUi;

SDL_Point screen_of(vh::Pos p, int elevation) {
    const auto projected = vh::project_training_tile(p, elevation);
    return {projected.x, projected.y};
}

void color(SDL_Renderer* r, int red, int green, int blue, int alpha = 255) {
    SDL_SetRenderDrawColor(r, static_cast<Uint8>(red), static_cast<Uint8>(green),
                           static_cast<Uint8>(blue), static_cast<Uint8>(alpha));
}

void diamond(SDL_Renderer* r, SDL_Point center, SDL_Color fill) {
    SDL_SetRenderDrawBlendMode(r, SDL_BLENDMODE_BLEND);
    color(r, fill.r, fill.g, fill.b, fill.a);
    for (int dy = -TILE_HALF_H; dy <= TILE_HALF_H; ++dy) {
        const int half_width = (TILE_HALF_W * (TILE_HALF_H - std::abs(dy))) / TILE_HALF_H;
        SDL_RenderDrawLine(r, center.x - half_width, center.y + dy,
                          center.x + half_width, center.y + dy);
    }
    color(r, 28, 35, 46);
    SDL_Point outline[5] = {{center.x, center.y - TILE_HALF_H},
                            {center.x + TILE_HALF_W, center.y},
                            {center.x, center.y + TILE_HALF_H},
                            {center.x - TILE_HALF_W, center.y},
                            {center.x, center.y - TILE_HALF_H}};
    SDL_RenderDrawLines(r, outline, 5);
}

bool reachable(const std::vector<vh::Pos>& points, vh::Pos p) {
    return std::find(points.begin(), points.end(), p) != points.end();
}

void render_visual_state_digest(SDL_Renderer* r, const vh::Battle& battle) {
    // ROM-free on-screen checksum works even when guest stderr is not
    // forwarded by the emulator. Never render copyrighted Saturn content.
    const auto checksum = vh::battle_fingerprint(battle);
    for (int bit = 0; bit < vh::digest_cells; ++bit) {
        if (vh::digest_bit(checksum, bit)) color(r, 66, 220, 132);
        else color(r, 40, 53, 69);
        const auto cell = vh::digest_cell_rect(bit);
        SDL_Rect rect{cell.x, cell.y, cell.w, cell.h};
        SDL_RenderFillRect(r, &rect);
    }
    color(r, 234, 40, 190);
    for (int i = 0; i < 3; ++i) {
        const auto anchor = vh::digest_anchor(i);
        SDL_Rect rect{anchor.x, anchor.y, anchor.w, anchor.h};
        SDL_RenderFillRect(r, &rect);
    }
}

// Stage43: a tiny ROM-free receipt in the spare top-right of the window.
// The pixel conveys the LAST processed SDL action, independently of battle
// hash and yellow cursor. Red=Rejected; amber=Cancelled; green=Moved.
void render_action_receipt(SDL_Renderer* r, vh::TrainingEffect effect) {
    SDL_Color value{40, 53, 69, 255};
    switch (effect) {
        case vh::TrainingEffect::Rejected: value = {239, 79, 76, 255}; break;
        case vh::TrainingEffect::Cancelled: value = {251, 220, 90, 255}; break;
        case vh::TrainingEffect::Moved: value = {66, 220, 132, 255}; break;
        case vh::TrainingEffect::Selected: value = {63, 167, 239, 255}; break;
        case vh::TrainingEffect::Attacked: value = {179, 103, 244, 255}; break;
        case vh::TrainingEffect::TurnEnded: value = {76, 222, 230, 255}; break;
        default: break;
    }
    color(r, value.r, value.g, value.b);
    SDL_Rect receipt{1210, 60, 16, 16};
    SDL_RenderFillRect(r, &receipt);
}

// Stage54 forecast HUD is below the battlefield in the existing info strip.
// It is deliberately geometric and font-free so Switch/NRO needs no external
// files. It must NEVER change Battle state or the screen-state hash.
void render_attack_preview(SDL_Renderer* r, const Ui& ui) {
    const vh::AttackPreviewHud h =
        vh::attack_preview_hud(ui.battle, ui.selected, ui.cursor);
    if (!h.visible) return;
    const int x = vh::kPreviewBarX;
    const int y = vh::kPreviewBarY;
    const int w = vh::kPreviewBarWidth;
    const int hh = vh::kPreviewBarHeight;
    color(r, 23, 30, 41);
    SDL_Rect backdrop{x - 4, y - 4, w + 8, hh + 8};
    SDL_RenderFillRect(r, &backdrop);
    if (h.remaining_width > 0) {
        color(r, 117, 221, 109); // surviving HP after strike
        SDL_Rect survivor{x, y, h.remaining_width, hh};
        SDL_RenderFillRect(r, &survivor);
    }
    if (h.damage_width > 0) {
        color(r, 179, 103, 244); // projected HP loss
        SDL_Rect damage{x + h.remaining_width, y, h.damage_width, hh};
        SDL_RenderFillRect(r, &damage);
    }
    if (h.decisive) {
        color(r, 251, 220, 90); // lethal hit ends the entire battle
        SDL_RenderDrawRect(r, &backdrop);
    }
}

// Tiny fixed 3x5 uppercase glyphs: display useful numeric fighter stats
// without a font asset, external SDK font, or copyrighted Saturn resources.
std::array<unsigned char, 5> unit_stat_glyph(char c) {
    switch (c) {
        case '0': return {{7,5,5,5,7}};
        case '1': return {{2,6,2,2,7}};
        case '2': return {{7,1,7,4,7}};
        case '3': return {{7,1,7,1,7}};
        case '4': return {{5,5,7,1,1}};
        case '5': return {{7,4,7,1,7}};
        case '6': return {{7,4,7,5,7}};
        case '7': return {{7,1,1,1,1}};
        case '8': return {{7,5,7,5,7}};
        case '9': return {{7,5,7,1,7}};
        case 'A': return {{2,5,7,5,5}};
        case 'B': return {{6,5,6,5,6}};
        case 'C': return {{3,4,4,4,3}};
        case 'D': return {{6,5,5,5,6}};
        case 'E': return {{7,4,6,4,7}};
        case 'F': return {{7,4,6,4,4}};
        case 'G': return {{3,4,5,5,3}};
        case 'H': return {{5,5,7,5,5}};
        case 'I': return {{7,2,2,2,7}};
        case 'J': return {{3,1,1,5,2}};
        case 'K': return {{5,5,6,5,5}};
        case 'L': return {{4,4,4,4,7}};
        case 'M': return {{5,7,7,5,5}};
        case 'N': return {{5,7,7,7,5}};
        case 'O': return {{2,5,5,5,2}};
        case 'P': return {{6,5,6,4,4}};
        case 'Q': return {{2,5,5,7,3}};
        case 'R': return {{6,5,6,5,5}};
        case 'S': return {{3,4,2,1,6}};
        case 'T': return {{7,2,2,2,2}};
        case 'U': return {{5,5,5,5,7}};
        case 'V': return {{5,5,5,5,2}};
        case 'W': return {{5,5,7,7,5}};
        case 'X': return {{5,5,2,5,5}};
        case 'Y': return {{5,5,2,2,2}};
        case 'Z': return {{7,1,2,4,7}};
        case '-': return {{0,0,7,0,0}};
        default: return {{0,0,0,0,0}}; // space or unsupported
    }
}

void unit_stat_text(SDL_Renderer* r, const std::string& words,
                    int start_x, int top_y) {
    const size_t length = std::min(words.size(), static_cast<size_t>(18));
    for (size_t i = 0; i < length; ++i) {
        const char letter = static_cast<char>(
            std::toupper(static_cast<unsigned char>(words[i])));
        const auto bits = unit_stat_glyph(letter);
        for (int y = 0; y < 5; ++y) for (int x = 0; x < 3; ++x) {
            if ((bits[static_cast<size_t>(y)] & (1u << (2 - x))) == 0) continue;
            SDL_Rect px{start_x + static_cast<int>(i)*8 + x*2, top_y + y*2, 2, 2};
            SDL_RenderFillRect(r, &px);
        }
    }
}

// The stat panel occupies logical x350..993 and never overlaps Stage54's
// x141..324 projected attack bar nor the top-right gameplay fingerprint.
// No actual battle mutation occurs during this rendering pass.
void render_selected_unit_info(SDL_Renderer* r, const Ui& ui) {
    const vh::SelectedUnitHud info = vh::selected_unit_hud(ui.battle, ui.selected);
    if (!info.visible) return;
    color(r, 23, 30, 41);
    SDL_Rect bg{350, 668, 644, 44};
    SDL_RenderFillRect(r, &bg);
    color(r, 63, 167, 239);
    SDL_Rect marker{vh::kUnitHudX, vh::kUnitHudY + 3,
                    vh::kUnitHudMarkerW, vh::kUnitHudMarkerH};
    SDL_RenderFillRect(r, &marker);
    color(r, 220, 233, 238);
    unit_stat_text(r, info.name.substr(0, 14), 374, 677);
    unit_stat_text(r, "HP " + std::to_string(info.hp), 500, 683);
    unit_stat_text(r, "ATK " + std::to_string(info.attack), 603, 683);
    unit_stat_text(r, "DEF " + std::to_string(info.defense), 724, 683);
    unit_stat_text(r, "RNG " + std::to_string(info.range), 839, 683);
    // Cyan = action still available, purple = already attacked this round.
    if (info.acted) color(r, 179, 103, 244);
    else color(r, 76, 222, 230);
    SDL_Rect acted{vh::kUnitHudStatusX, vh::kUnitHudStatusY, 14, 14};
    SDL_RenderFillRect(r, &acted);
    // Gold = already moved this round, grey-blue = movement still possible.
    if (info.moved) color(r, 251, 220, 90);
    else color(r, 74, 94, 111);
    SDL_Rect moved{976, vh::kUnitHudStatusY, 12, 14};
    SDL_RenderFillRect(r, &moved);
}

// Stage56: independent enemy-hover information card. Its x1002..1273 region
// does not touch Stage55 x350..993 or Stage54 x141..324.
// Read-only: does not affect tactical state, replay or action receipts.
void render_enemy_hover_info(SDL_Renderer* r, const Ui& ui) {
    const vh::EnemyHoverHud info = vh::enemy_hover_hud(ui.battle, ui.cursor);
    if (!info.visible) return;
    color(r, 23, 30, 41);
    SDL_Rect bg{vh::kEnemyHudX, vh::kEnemyHudY, vh::kEnemyHudWidth, vh::kEnemyHudHeight};
    SDL_RenderFillRect(r, &bg);
    color(r, 239, 79, 76);
    SDL_Rect marker{1008, 674, 6, 33};
    SDL_RenderFillRect(r, &marker);
    color(r, 220, 233, 238);
    unit_stat_text(r, info.name.substr(0, 18), 1020, 675);
    unit_stat_text(r, "HP " + std::to_string(info.hp), 1022, 690);
    unit_stat_text(r, "ATK " + std::to_string(info.attack), 1077, 690);
    unit_stat_text(r, "DEF " + std::to_string(info.defense), 1140, 690);
    unit_stat_text(r, "RNG " + std::to_string(info.range), 1204, 690);
}

// Stage57: status cue in the upper-right of the existing Stage56 card.
// No new game logic: legality is derived from Battle::preview_attack.
void render_enemy_attack_cue(SDL_Renderer* r, const Ui& ui) {
    const auto cue = vh::enemy_attack_cue(ui.battle, ui.cursor, ui.selected);
    if (cue.state == vh::EnemyAttackCueState::Hidden) return;
    switch (cue.state) {
        case vh::EnemyAttackCueState::InspectOnly: color(r, 74, 94, 111); break;
        case vh::EnemyAttackCueState::Ready: color(r, 251, 220, 90); break;
        case vh::EnemyAttackCueState::Spent: color(r, 179, 103, 244); break;
        case vh::EnemyAttackCueState::Blocked: color(r, 116, 77, 88); break;
        case vh::EnemyAttackCueState::Hidden: return;
    }
    SDL_Rect marker{vh::kEnemyCueX, vh::kEnemyCueY,
                    vh::kEnemyCueWidth, vh::kEnemyCueHeight};
    SDL_RenderFillRect(r, &marker);
}

// Stage58: precise capped HP damage readout shares Stage53 preview authority.
// The text occupies unused Stage56 enemy-card area, not Stage54-57 samples.
void render_target_damage(SDL_Renderer* r, const Ui& ui) {
    const auto forecast = vh::target_damage_hud(ui.battle, ui.cursor, ui.selected);
    if (!forecast.visible) return;
    color(r, 220, 233, 238);
    unit_stat_text(r, "DMG " + std::to_string(forecast.damage),
                   vh::kDamageHudX, vh::kDamageHudY);
    if (forecast.lethal) {
        color(r, 251, 220, 90);
        unit_stat_text(r, "KO", vh::kDamageKoX, vh::kDamageHudY);
    }
}

// Stage59: projected ENEMY HP after the legal next hit, read-only.
// The label uses the free gap between Stage58 DMG and KO in the enemy card.
void render_target_remaining(SDL_Renderer* r, const Ui& ui) {
    const auto predicted = vh::target_remaining_hud(ui.battle, ui.cursor, ui.selected);
    if (!predicted.visible) return;
    color(r, 220, 233, 238);
    unit_stat_text(r, "HP " + std::to_string(predicted.hp_after),
                   vh::kRemainingHudX, vh::kRemainingHudY);
}

void render(SDL_Renderer* r, const Ui& ui) {
    color(r, 14, 19, 32);
    SDL_RenderClear(r);
    const auto selected_points = ui.selected >= 0 ? ui.battle.reachable(ui.selected) : std::vector<vh::Pos>{};
    for (int y = 0; y < ui.battle.height(); ++y) for (int x = 0; x < ui.battle.width(); ++x) {
        const vh::Pos p{x, y};
        const auto& tile = ui.battle.tile(p);
        const SDL_Point center = screen_of(p, tile.elevation);
        SDL_Color c = !tile.walkable ? SDL_Color{60, 54, 58, 255} :
                     tile.elevation ? SDL_Color{96, 112, 84, 255} : SDL_Color{70, 92, 105, 255};
        if (reachable(selected_points, p)) c = {44, 139, 125, 255};
        if (p == ui.cursor) c = {220, 178, 68, 255};
        diamond(r, center, c);
        if (tile.elevation > 0) {
            color(r, 49, 60, 51);
            SDL_RenderDrawLine(r, center.x, center.y + TILE_HALF_H,
                               center.x, center.y + TILE_HALF_H + tile.elevation * 14);
        }
        const auto* unit = ui.battle.unit_at(p);
        if (unit) {
            const SDL_Color pawn = unit->side == vh::Side::Player ?
                SDL_Color{63, 167, 239, 255} : SDL_Color{239, 79, 76, 255};
            color(r, 15, 22, 29, 180);
            SDL_Rect shadow{center.x - 17, center.y - 12, 34, 14};
            SDL_RenderFillRect(r, &shadow);
            color(r, pawn.r, pawn.g, pawn.b);
            SDL_Rect body{center.x - 12, center.y - 39, 24, 30};
            SDL_RenderFillRect(r, &body);
            color(r, 225, 219, 184);
            SDL_Rect head{center.x - 7, center.y - 49, 14, 14};
            SDL_RenderFillRect(r, &head);
            if (unit->id == ui.selected) {
                color(r, 251, 220, 90);
                SDL_Rect border{center.x - 16, center.y - 53, 32, 49};
                SDL_RenderDrawRect(r, &border);
            }
            color(r, 31, 32, 32);
            SDL_Rect hp_bg{center.x - 17, center.y - 61, 34, 5};
            SDL_RenderFillRect(r, &hp_bg);
            color(r, 117, 221, 109);
            SDL_Rect hp{center.x - 17, center.y - 61,
                        std::max(1, std::min(34, unit->hp * 34 / 26)), 5};
            SDL_RenderFillRect(r, &hp);
        }
    }
    // Two colored information strips are deliberately text-free so that Switch
    // can render this prototype without an external font or game assets.
    color(r, 45, 64, 83);
    SDL_Rect help{0, H - 60, W, 60};
    SDL_RenderFillRect(r, &help);
    color(r, 63, 167, 239);
    SDL_Rect allies{16, H - 43, 30, 20};
    SDL_RenderFillRect(r, &allies);
    color(r, 239, 79, 76);
    SDL_Rect enemies{55, H - 43, 30, 20};
    SDL_RenderFillRect(r, &enemies);
    render_attack_preview(r, ui);
    render_selected_unit_info(r, ui);
    render_enemy_hover_info(r, ui);
    render_enemy_attack_cue(r, ui);
    render_target_damage(r, ui);
    render_target_remaining(r, ui);
    render_visual_state_digest(r, ui.battle);
    render_action_receipt(r, ui.last_effect);
    SDL_RenderPresent(r);
}

void status_title(SDL_Window* window, const Ui& ui) {
    std::string name = "Vandal Hearts Saturn-inspired native prototype | round " +
                       std::to_string(ui.battle.round()) + " | " + ui.status;
    SDL_SetWindowTitle(window, name.c_str());
}

void issue(Ui& ui, vh::TrainingAction action, bool& running) {
    ui.last_effect = vh::apply_training_action(ui, action);
    if (ui.last_effect == vh::TrainingEffect::QuitRequested)
        running = false;
}
void key(Ui& ui, SDL_Keycode code, bool& running) {
    switch (code) {
        case SDLK_ESCAPE: issue(ui, vh::TrainingAction::Quit, running); break;
        case SDLK_LEFT: case SDLK_a: issue(ui, vh::TrainingAction::Left, running); break;
        case SDLK_RIGHT: case SDLK_d: issue(ui, vh::TrainingAction::Right, running); break;
        case SDLK_UP: case SDLK_w: issue(ui, vh::TrainingAction::Up, running); break;
        case SDLK_DOWN: case SDLK_s: issue(ui, vh::TrainingAction::Down, running); break;
        case SDLK_RETURN: case SDLK_SPACE: issue(ui, vh::TrainingAction::Confirm, running); break;
        case SDLK_y: issue(ui, vh::TrainingAction::Attack, running); break;
        case SDLK_x: issue(ui, vh::TrainingAction::EndTurn, running); break;
        case SDLK_BACKSPACE: issue(ui, vh::TrainingAction::Cancel, running); break;
        default: break;
    }
}
void controller(Ui& ui, Uint8 button, bool& running) {
    switch (button) {
        case SDL_CONTROLLER_BUTTON_DPAD_LEFT: issue(ui, vh::TrainingAction::Left, running); break;
        case SDL_CONTROLLER_BUTTON_DPAD_RIGHT: issue(ui, vh::TrainingAction::Right, running); break;
        case SDL_CONTROLLER_BUTTON_DPAD_UP: issue(ui, vh::TrainingAction::Up, running); break;
        case SDL_CONTROLLER_BUTTON_DPAD_DOWN: issue(ui, vh::TrainingAction::Down, running); break;
        case SDL_CONTROLLER_BUTTON_A: issue(ui, vh::TrainingAction::Confirm, running); break;
        case SDL_CONTROLLER_BUTTON_B: issue(ui, vh::TrainingAction::Cancel, running); break;
        case SDL_CONTROLLER_BUTTON_Y: issue(ui, vh::TrainingAction::Attack, running); break;
        case SDL_CONTROLLER_BUTTON_X: issue(ui, vh::TrainingAction::EndTurn, running); break;
        case SDL_CONTROLLER_BUTTON_START: issue(ui, vh::TrainingAction::Quit, running); break;
        default: break;
    }
}
}

int main(int argc, char** argv) {
    int smoke_frames = 0;
    try { smoke_frames = vh::smoke_frames_from_args(argc, argv); }
    catch (const std::invalid_argument& e) {
        std::fprintf(stderr, "VH_SMOKE argument_error=%s\n", e.what());
        return 4;
    }
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_GAMECONTROLLER) != 0) {
        std::fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    SDL_Window* window = SDL_CreateWindow("Saturn tactics prototype", SDL_WINDOWPOS_CENTERED,
                                           SDL_WINDOWPOS_CENTERED, W, H, SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (!window) { SDL_Quit(); return 2; }
    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!renderer) renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_SOFTWARE);
    if (!renderer) { SDL_DestroyWindow(window); SDL_Quit(); return 3; }
    SDL_RenderSetLogicalSize(renderer, W, H);
    std::fprintf(stderr, "VH_SMOKE sdl=ready renderer=ready\n");
    std::fflush(stderr);
    SDL_GameController* pad = nullptr;
    for (int i = 0; i < SDL_NumJoysticks(); ++i) {
        if (SDL_IsGameController(i)) { pad = SDL_GameControllerOpen(i); break; }
    }
    Ui ui;
#ifdef VH_STAGE44_DUEL
    ui.battle = vh::stage44_attack_duel();
    ui.cursor = {1, 5};
    const bool scene_ready = ui.battle.units().size() == 2 &&
                             ui.battle.unit_at({1, 5}) != nullptr &&
                             ui.battle.unit_at({2, 5}) != nullptr;
#else
    const bool scene_ready = vh::smoke_training_scene_ready(ui.battle);
#endif
    if (!scene_ready) {
        std::fprintf(stderr, "VH_SMOKE scene=failed\n");
        if (pad) SDL_GameControllerClose(pad);
        SDL_DestroyRenderer(renderer);
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 5;
    }
    std::fprintf(stderr, "VH_SMOKE scene=ready width=8 height=8 units=%zu\n",
                 ui.battle.units().size());
    std::fflush(stderr);
    std::fprintf(stderr, "VH_STATE scene=training version=1 state=%016llx\n",
                 static_cast<unsigned long long>(vh::battle_fingerprint(ui.battle)));
    std::fflush(stderr);
    unsigned int rendered_frames = 0;
    bool running = true;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            const auto before_state = vh::battle_fingerprint(ui.battle);
            const vh::Pos before_cursor = ui.cursor;
            if (event.type == SDL_QUIT) running = false;
            else if (event.type == SDL_KEYDOWN && !event.key.repeat) key(ui, event.key.keysym.sym, running);
            else if (event.type == SDL_CONTROLLERBUTTONDOWN) controller(ui, event.cbutton.button, running);
            const auto after_state = vh::battle_fingerprint(ui.battle);
            if (before_state != after_state) {
                std::fprintf(stderr, "VH_STATE scene=training version=1 round=%d state=%016llx\n",
                             ui.battle.round(), static_cast<unsigned long long>(after_state));
                std::fflush(stderr);
            }
            if (before_cursor != ui.cursor) {
                std::fprintf(stderr, "VH_CURSOR x=%d y=%d\n", ui.cursor.x, ui.cursor.y);
                std::fflush(stderr);
            }
        }
        status_title(window, ui);
        render(renderer, ui);
        ++rendered_frames;
        if (rendered_frames == 1) {
            std::fprintf(stderr, "VH_SMOKE first_frame=rendered\n");
            std::fflush(stderr);
        }
        if (smoke_frames > 0 && rendered_frames >= static_cast<unsigned int>(smoke_frames)) {
            std::fprintf(stderr, "VH_SMOKE completed_frames=%u round=%d phase=%d\n",
                         rendered_frames, ui.battle.round(), static_cast<int>(ui.battle.phase()));
            std::fflush(stderr);
            running = false;
        }
        if (running) SDL_Delay(8);
    }
    if (pad) SDL_GameControllerClose(pad);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
