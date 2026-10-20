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
