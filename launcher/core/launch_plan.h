// Copyright 2026 The Browser-x Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// Platform-independent decisions made by the BrowserX.exe portable launcher.
// Kept free of Windows APIs so it is unit-tested on every CI platform.

#ifndef BROWSERX_LAUNCHER_CORE_LAUNCH_PLAN_H_
#define BROWSERX_LAUNCHER_CORE_LAUNCH_PLAN_H_

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace bx {

enum class PolicyDecision { kAllowed, kDenied };
enum class PolicySource { kMachine, kUser, kDefault };

struct PortablePolicy {
  PolicyDecision decision;
  PolicySource source;
};

// Decides whether portable mode may run.
//  - A machine policy (HKLM) always wins, in either direction.
//  - Without a machine policy, a user policy (HKCU) applies.
//  - With neither, `default_allow` applies (browserx.json policy default).
// A value of 0 means "not allowed"; any other value means "allowed".
PortablePolicy DecidePortableMode(std::optional<uint32_t> machine_value,
                                  std::optional<uint32_t> user_value,
                                  bool default_allow);

// True for "1", "0.1.0", "158.0.8127.37": 1 to 4 dot-separated numbers of
// 1-9 digits. Anything else (paths, "..", spaces) is rejected, so a version
// is always safe to use as a single directory name.
bool IsValidVersion(const std::wstring& version);

// Returns -1, 0 or 1. Both arguments must be valid versions.
int CompareVersions(const std::wstring& a, const std::wstring& b);

// Picks the application version to start: the one named in App\current.txt if
// it is valid and installed, otherwise the highest valid installed version.
std::optional<std::wstring> SelectVersion(
    const std::wstring& current_txt,
    const std::vector<std::wstring>& installed_dirs);

// True if `arg` is a Chromium switch the launcher never forwards because it
// weakens security, bypasses administrator control, or would move user data
// out of the portable Data folder. Recognizes Chromium's Windows switch
// prefixes "--", "-" and "/", case-insensitively, with or without "=value".
bool IsForbiddenSwitch(const std::wstring& arg);

// Drops forbidden switches. Everything after a bare "--" is treated as a
// non-switch argument (as Chromium does) and kept. Removed arguments are
// appended to `removed` when it is non-null.
std::vector<std::wstring> FilterArguments(const std::vector<std::wstring>& args,
                                          std::vector<std::wstring>* removed);

// Quotes one argument so CommandLineToArgvW / the MSVC CRT parse it back
// unchanged.
std::wstring QuoteArgument(const std::wstring& arg);

std::wstring BuildCommandLine(const std::wstring& exe,
                              const std::vector<std::wstring>& args);

// Joins Windows path components with a single backslash.
std::wstring JoinPath(const std::wstring& a, const std::wstring& b);

// Returns the directory part of a Windows path ("C:\a\b.exe" -> "C:\a").
std::wstring DirName(const std::wstring& path);

// Only plain https:// URLs without whitespace or quotes may be opened from
// the "portable mode not allowed" dialog.
bool IsSafeHelpUrl(const std::wstring& url);

}  // namespace bx

#endif  // BROWSERX_LAUNCHER_CORE_LAUNCH_PLAN_H_
