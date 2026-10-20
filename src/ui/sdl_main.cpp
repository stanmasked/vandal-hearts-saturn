#include "vh/battle.hpp"
#include "vh/smoke.hpp"
#include "vh/cursor_geometry.hpp"
#include "vh/replay.hpp"
#include "vh/visual_digest.hpp"
#include "vh/training_controls.hpp"
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
        default: break;
    }
    color(r, value.r, value.g, value.b);
    SDL_Rect receipt{1210, 60, 16, 16};
    SDL_RenderFillRect(r, &receipt);
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
    if (!vh::smoke_training_scene_ready(ui.battle)) {
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
