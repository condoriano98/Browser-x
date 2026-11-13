# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# BrowserX.exe portable launcher. Builds the platform-independent core and
# its tests everywhere; the launcher executable itself only on Windows.

cmake_minimum_required(VERSION 3.20)
project(BrowserXLauncher LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(BX_REQUIRE_SIGNED "Refuse to start an unsigned browser executable (release builds)" OFF)

# Product values come from browserx.json, the single source of truth.
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/../browserx.json" BX_MANIFEST)
string(JSON BX_NAME GET "${BX_MANIFEST}" name)
string(JSON BX_VENDOR GET "${BX_MANIFEST}" vendor)
string(JSON BX_BINARY GET "${BX_MANIFEST}" binaryName)
string(JSON BX_VERSION GET "${BX_MANIFEST}" displayVersion)
string(JSON BX_POLICY_KEY GET "${BX_MANIFEST}" policy registryKey)
string(JSON BX_PORTABLE_DEFAULT GET "${BX_MANIFEST}" policy portableModeDefault)
string(REPLACE "\\" "\\\\" BX_POLICY_KEY_ESCAPED "${BX_POLICY_KEY}")
string(REPLACE "." ";" BX_VERSION_PARTS "${BX_VERSION}")
list(GET BX_VERSION_PARTS 0 BX_VERSION_MAJOR)
list(GET BX_VERSION_PARTS 1 BX_VERSION_MINOR)
list(GET BX_VERSION_PARTS 2 BX_VERSION_PATCH)
if(BX_PORTABLE_DEFAULT STREQUAL "allow")
  set(BX_PORTABLE_DEFAULT_ALLOW true)
else()
  set(BX_PORTABLE_DEFAULT_ALLOW false)
endif()
if(BX_REQUIRE_SIGNED)
  set(BX_REQUIRE_SIGNED_VALUE 1)
else()
  set(BX_REQUIRE_SIGNED_VALUE 0)
endif()
configure_file(launcher_config.h.in "${CMAKE_CURRENT_BINARY_DIR}/launcher_config.h" @ONLY)

if(MSVC)
  add_compile_options(/W4 /WX /permissive- /utf-8 /guard:cf /sdl)
else()
  add_compile_options(-Wall -Wextra -Werror)
endif()

add_library(bx_launcher_core STATIC core/launch_plan.cc)
target_include_directories(bx_launcher_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")

enable_testing()
add_executable(launcher_core_tests tests/launch_plan_test.cc)
target_link_libraries(launcher_core_tests PRIVATE bx_launcher_core)
add_test(NAME launcher_core_tests COMMAND launcher_core_tests)

if(WIN32)
  enable_language(RC)
  configure_file(win/launcher.rc.in "${CMAKE_CURRENT_BINARY_DIR}/launcher.rc" @ONLY)
  add_executable(BrowserX WIN32 win/main.cc "${CMAKE_CURRENT_BINARY_DIR}/launcher.rc")
  target_include_directories(BrowserX PRIVATE "${CMAKE_CURRENT_BINARY_DIR}" "${CMAKE_CURRENT_SOURCE_DIR}/win")
  target_compile_definitions(BrowserX PRIVATE UNICODE _UNICODE NOMINMAX WIN32_LEAN_AND_MEAN)
  target_link_libraries(BrowserX PRIVATE bx_launcher_core advapi32 shell32 user32 wintrust)
  if(MSVC)
    target_link_options(BrowserX PRIVATE /guard:cf /DYNAMICBASE /NXCOMPAT /CETCOMPAT /MANIFEST:NO)
  else()
    target_link_options(BrowserX PRIVATE -municode -static)
  endif()
endif()
