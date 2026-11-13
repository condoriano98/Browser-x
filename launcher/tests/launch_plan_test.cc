// Copyright 2026 The Browser-x Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// Dependency-free unit tests for launcher/core. Run via ctest.

#include <cstdio>
#include <string>
#include <vector>

#include "core/launch_plan.h"

namespace {

int g_failures = 0;

#define EXPECT(cond)                                                  \
  do {                                                                \
    if (!(cond)) {                                                    \
      std::fprintf(stderr, "%s:%d: EXPECT(%s) failed\n", __FILE__,    \
                   __LINE__, #cond);                                  \
      ++g_failures;                                                   \
    }                                                                 \
  } while (0)

using bx::PolicyDecision;
using bx::PolicySource;

void TestPolicy() {
  // Machine policy wins in both directions.
  auto p = bx::DecidePortableMode(0u, 1u, true);
  EXPECT(p.decision == PolicyDecision::kDenied && p.source == PolicySource::kMachine);
  p = bx::DecidePortableMode(1u, 0u, false);
  EXPECT(p.decision == PolicyDecision::kAllowed && p.source == PolicySource::kMachine);
  // User policy applies only without machine policy.
  p = bx::DecidePortableMode(std::nullopt, 0u, true);
  EXPECT(p.decision == PolicyDecision::kDenied && p.source == PolicySource::kUser);
  p = bx::DecidePortableMode(std::nullopt, 7u, false);
  EXPECT(p.decision == PolicyDecision::kAllowed && p.source == PolicySource::kUser);
  // Default.
  p = bx::DecidePortableMode(std::nullopt, std::nullopt, true);
  EXPECT(p.decision == PolicyDecision::kAllowed && p.source == PolicySource::kDefault);
  p = bx::DecidePortableMode(std::nullopt, std::nullopt, false);
  EXPECT(p.decision == PolicyDecision::kDenied && p.source == PolicySource::kDefault);
}

void TestVersions() {
  EXPECT(bx::IsValidVersion(L"1"));
  EXPECT(bx::IsValidVersion(L"0.1.0"));
  EXPECT(bx::IsValidVersion(L"158.0.8127.37"));
  EXPECT(!bx::IsValidVersion(L""));
  EXPECT(!bx::IsValidVersion(L".."));
  EXPECT(!bx::IsValidVersion(L"1..2"));
  EXPECT(!bx::IsValidVersion(L"1.2."));
  EXPECT(!bx::IsValidVersion(L"..\\evil"));
  EXPECT(!bx::IsValidVersion(L"1.2.3.4.5"));
  EXPECT(!bx::IsValidVersion(L"1 .2"));
  EXPECT(!bx::IsValidVersion(L"1234567890"));

  EXPECT(bx::CompareVersions(L"0.10.0", L"0.9.9") == 1);
  EXPECT(bx::CompareVersions(L"1.0", L"1.0.0") == 0);
  EXPECT(bx::CompareVersions(L"1.2.3", L"1.2.4") == -1);

  const std::vector<std::wstring> installed = {L"0.1.0", L"0.2.0", L"junk", L"..", L"0.10.0"};
  EXPECT(bx::SelectVersion(L"0.2.0\r\n", installed) == std::wstring(L"0.2.0"));
  EXPECT(bx::SelectVersion(L"\uFEFF0.1.0", installed) == std::wstring(L"0.1.0"));
  // Missing or invalid current.txt falls back to the highest valid version.
  EXPECT(bx::SelectVersion(L"9.9.9", installed) == std::wstring(L"0.10.0"));
  EXPECT(bx::SelectVersion(L"..", installed) == std::wstring(L"0.10.0"));
  EXPECT(!bx::SelectVersion(L"", {L"junk"}).has_value());
}

void TestSwitchFilter() {
  EXPECT(bx::IsForbiddenSwitch(L"--no-sandbox"));
  EXPECT(bx::IsForbiddenSwitch(L"--NO-SANDBOX"));
  EXPECT(bx::IsForbiddenSwitch(L"-no-sandbox"));
  EXPECT(bx::IsForbiddenSwitch(L"/no-sandbox"));
  EXPECT(bx::IsForbiddenSwitch(L"--user-data-dir=C:\\elsewhere"));
  EXPECT(bx::IsForbiddenSwitch(L"--remote-debugging-port=9222"));
  EXPECT(bx::IsForbiddenSwitch(L"--load-extension=C:\\x"));
  EXPECT(!bx::IsForbiddenSwitch(L"--incognito"));
  EXPECT(!bx::IsForbiddenSwitch(L"--no-sandboxing-is-not-a-switch"));
  EXPECT(!bx::IsForbiddenSwitch(L"https://example.com/--no-sandbox"));

  std::vector<std::wstring> removed;
  const auto kept = bx::FilterArguments(
      {L"--incognito", L"--no-sandbox", L"https://example.com", L"--",
       L"--no-sandbox"},
      &removed);
  EXPECT(kept.size() == 4);
  EXPECT(kept[0] == L"--incognito");
  EXPECT(kept[1] == L"https://example.com");
  EXPECT(kept[2] == L"--");
  EXPECT(kept[3] == L"--no-sandbox");  // after "--" it is a URL/file argument
  EXPECT(removed.size() == 1 && removed[0] == L"--no-sandbox");
}

void TestQuoting() {
  EXPECT(bx::QuoteArgument(L"simple") == L"simple");
  EXPECT(bx::QuoteArgument(L"") == L"\"\"");
  EXPECT(bx::QuoteArgument(L"C:\\Program Files\\x") == L"\"C:\\Program Files\\x\"");
  EXPECT(bx::QuoteArgument(L"a\"b") == L"\"a\\\"b\"");
  EXPECT(bx::QuoteArgument(L"C:\\dir with space\\") == L"\"C:\\dir with space\\\\\"");
  EXPECT(bx::BuildCommandLine(L"C:\\B X\\b.exe", {L"--a", L"x y"}) ==
         L"\"C:\\B X\\b.exe\" --a \"x y\"");
}

void TestPaths() {
  EXPECT(bx::JoinPath(L"C:\\a", L"b") == L"C:\\a\\b");
  EXPECT(bx::JoinPath(L"C:\\a\\", L"b") == L"C:\\a\\b");
  EXPECT(bx::DirName(L"D:\\Apps\\BrowserX\\BrowserX.exe") == L"D:\\Apps\\BrowserX");
  EXPECT(bx::DirName(L"BrowserX.exe") == L".");
}

void TestHelpUrl() {
  EXPECT(bx::IsSafeHelpUrl(L"https://it.example.com/browser"));
  EXPECT(bx::IsSafeHelpUrl(L"HTTPS://it.example.com/"));
  EXPECT(!bx::IsSafeHelpUrl(L"http://it.example.com/"));
  EXPECT(!bx::IsSafeHelpUrl(L"file:///C:/x"));
  EXPECT(!bx::IsSafeHelpUrl(L"https://a b"));
  EXPECT(!bx::IsSafeHelpUrl(L"https://a\"b"));
  EXPECT(!bx::IsSafeHelpUrl(L"https://"));
}

}  // namespace

int main() {
  TestPolicy();
  TestVersions();
  TestSwitchFilter();
  TestQuoting();
  TestPaths();
  TestHelpUrl();
  if (g_failures) {
    std::fprintf(stderr, "%d failure(s)\n", g_failures);
    return 1;
  }
  std::printf("all launcher core tests passed\n");
  return 0;
}
