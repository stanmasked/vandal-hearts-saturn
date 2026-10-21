cmake_minimum_required(VERSION 3.16)
project(vandal_hearts_saturn_remake LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(vh_core src/core/battle.cpp)
target_include_directories(vh_core PUBLIC include)
if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(vh_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(vh_cli src/app/cli_main.cpp)
target_link_libraries(vh_cli PRIVATE vh_core)

find_package(SDL2 QUIET)
if(SDL2_FOUND)
  add_executable(vh_sdl src/ui/sdl_main.cpp)
  target_link_libraries(vh_sdl PRIVATE vh_core)
  if(TARGET SDL2::SDL2)
    target_link_libraries(vh_sdl PRIVATE SDL2::SDL2)
  else()
    target_include_directories(vh_sdl PRIVATE ${SDL2_INCLUDE_DIRS})
    target_link_libraries(vh_sdl PRIVATE ${SDL2_LIBRARIES})
  endif()
  if(TARGET SDL2::SDL2main)
    target_link_libraries(vh_sdl PRIVATE SDL2::SDL2main)
  endif()
  message(STATUS "SDL2 found: building playable 2D/iso demo")
else()
  message(STATUS "SDL2 not installed: building CLI and tests only")
endif()

enable_testing()
add_executable(vh_tests tests/battle_tests.cpp)
target_link_libraries(vh_tests PRIVATE vh_core)
add_test(NAME tactical_core COMMAND vh_tests)

# ROM-free startup/smoke invariants tested on host without SDL or Switch SDK.
add_executable(vh_smoke_tests tests/smoke_tests.cpp)
target_link_libraries(vh_smoke_tests PRIVATE vh_core)
add_test(NAME startup_smoke_contract COMMAND vh_smoke_tests)

# C++17 training-scene cursor math shared by SDL and host tests.
add_executable(vh_cursor_geometry_tests tests/cursor_geometry_tests.cpp)
target_link_libraries(vh_cursor_geometry_tests PRIVATE vh_core)
add_test(NAME cursor_geometry_contract COMMAND vh_cursor_geometry_tests)

# Deterministic ROM-free tactical replay and host/Switch state fingerprint contract.
add_executable(vh_replay_tests tests/replay_tests.cpp)
target_link_libraries(vh_replay_tests PRIVATE vh_core)
add_test(NAME deterministic_replay_contract COMMAND vh_replay_tests)
add_executable(vh_replay_cli src/app/replay_main.cpp)
target_link_libraries(vh_replay_cli PRIVATE vh_core)

# Verify a framebuffer-readable ROM-free state fingerprint contract without SDL.
add_executable(vh_visual_digest_tests tests/visual_digest_tests.cpp)
target_link_libraries(vh_visual_digest_tests PRIVATE vh_core)
add_test(NAME visual_digest_contract COMMAND vh_visual_digest_tests)

# Host-only synthetic C++ image source for cross-language visual digest tests.
add_executable(vh_visual_fixture src/app/visual_fixture_main.cpp)
target_link_libraries(vh_visual_fixture PRIVATE vh_core)

# SDL-independent gameplay actions shared by keyboard, controller and host tests.
add_executable(vh_training_controls_tests tests/training_controls_tests.cpp)
target_link_libraries(vh_training_controls_tests PRIVATE vh_core)
add_test(NAME training_controls_contract COMMAND vh_training_controls_tests)

# Host golden state for actual NeXium Select → Right → Confirm input trace.
add_executable(vh_training_action_fingerprint_tests tests/training_action_fingerprint_tests.cpp)
target_link_libraries(vh_training_action_fingerprint_tests PRIVATE vh_core)
add_test(NAME training_action_fingerprint COMMAND vh_training_action_fingerprint_tests)

# Isolated ROM-free combat fixture: authentic attack requires NeXium pixel proof.
add_executable(vh_attack_training_fingerprint_tests tests/attack_training_fingerprint_tests.cpp)
target_link_libraries(vh_attack_training_fingerprint_tests PRIVATE vh_core)
add_test(NAME attack_training_fingerprint COMMAND vh_attack_training_fingerprint_tests)

# Stage49: ROM-free complete duel, deterministic victory and irreversible outcome.
add_executable(vh_duel_victory_tests tests/duel_victory_tests.cpp)
target_link_libraries(vh_duel_victory_tests PRIVATE vh_core)
add_test(NAME duel_victory_contract COMMAND vh_duel_victory_tests)

# Stage51: opposite end-state, eight unopposed Raider attacks and terminal Defeat.
add_executable(vh_duel_defeat_tests tests/duel_defeat_tests.cpp)
target_link_libraries(vh_duel_defeat_tests PRIVATE vh_core)
add_test(NAME duel_defeat_contract COMMAND vh_duel_defeat_tests)

# Stage53: read-only damage forecast, shared with actual attacks and both
# previously guest-verified Victory/Defeat terminal states.
add_executable(vh_attack_preview_tests tests/attack_preview_tests.cpp)
target_link_libraries(vh_attack_preview_tests PRIVATE vh_core)
add_test(NAME attack_preview_contract COMMAND vh_attack_preview_tests)

# Stage54: forecast HUD is deterministic, read-only, and hidden outside legal aim.
add_executable(vh_attack_preview_hud_tests tests/attack_preview_hud_tests.cpp)
target_link_libraries(vh_attack_preview_hud_tests PRIVATE vh_core)
add_test(NAME attack_preview_hud_contract COMMAND vh_attack_preview_hud_tests)

# Stage55: selected-unit informational overlay without tactical mutation.
add_executable(vh_selected_unit_hud_tests tests/selected_unit_hud_tests.cpp)
target_link_libraries(vh_selected_unit_hud_tests PRIVATE vh_core)
add_test(NAME selected_unit_hud_contract COMMAND vh_selected_unit_hud_tests)

# Stage56: enemy-hover attributes; side-effect-free, no new controls or ROM assets.
add_executable(vh_enemy_hover_hud_tests tests/enemy_hover_hud_tests.cpp)
target_link_libraries(vh_enemy_hover_hud_tests PRIVATE vh_core)
add_test(NAME enemy_hover_hud_contract COMMAND vh_enemy_hover_hud_tests)

# Stage57: independent attack availability cue tied to real combat preview rules.
add_executable(vh_enemy_attack_cue_tests tests/enemy_attack_cue_tests.cpp)
target_link_libraries(vh_enemy_attack_cue_tests PRIVATE vh_core)
add_test(NAME enemy_attack_cue_contract COMMAND vh_enemy_attack_cue_tests)

# Stage58: display exact predicted HP loss and lethal result; no rule changes.
add_executable(vh_target_damage_hud_tests tests/target_damage_hud_tests.cpp)
target_link_libraries(vh_target_damage_hud_tests PRIVATE vh_core)
add_test(NAME target_damage_hud_contract COMMAND vh_target_damage_hud_tests)

# Stage59: projected enemy HP after the next legal strike, same battle rules.
add_executable(vh_target_remaining_hud_tests tests/target_remaining_hud_tests.cpp)
target_link_libraries(vh_target_remaining_hud_tests PRIVATE vh_core)
add_test(NAME target_remaining_hud_contract COMMAND vh_target_remaining_hud_tests)

# Stage60: projected HP bar, two-color read-only split of current enemy HP.
add_executable(vh_target_health_bar_tests tests/target_health_bar_tests.cpp)
target_link_libraries(vh_target_health_bar_tests PRIVATE vh_core)
add_test(NAME target_health_bar_contract COMMAND vh_target_health_bar_tests)
