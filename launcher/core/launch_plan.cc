// Copyright 2026 The Browser-x Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "core/launch_plan.h"

#include <algorithm>
#include <cwctype>

namespace bx {
namespace {

// Switch names (lowercase, without prefix or value) that are never forwarded.
constexpr const wchar_t* kForbiddenSwitches[] = {
    // Sandbox and site-isolation weakening.
    L"no-sandbox",
    L"disable-gpu-sandbox",
    L"disable-setuid-sandbox",
    L"no-zygote",
    L"single-process",
    L"in-process-gpu",
    L"disable-web-security",
    L"disable-site-isolation-trials",
    L"allow-running-insecure-content",
    L"ignore-certificate-errors",
    L"ignore-certificate-errors-spki-list",
    // Remote control of the browser.
    L"remote-debugging-port",
    L"remote-debugging-pipe",
    L"remote-debugging-address",
    L"remote-allow-origins",
    // Bypassing the administrator's extension allowlist.
    L"load-extension",
    L"disable-extensions-except",
    // Data location is fixed to the visible portable Data folder.
    L"user-data-dir",
    L"disk-cache-dir",
    L"profile-directory",
};

std::wstring ToLower(std::wstring s) {
  std::transform(s.begin(), s.end(), s.begin(),
                 [](wchar_t c) { return static_cast<wchar_t>(std::towlower(static_cast<wint_t>(c))); });
  return s;
}

std::wstring Trim(const std::wstring& s) {
  const wchar_t* ws = L" \t\r\n﻿";
  const auto begin = s.find_first_not_of(ws);
  if (begin == std::wstring::npos)
    return L"";
  const auto end = s.find_last_not_of(ws);
  return s.substr(begin, end - begin + 1);
}

std::vector<uint64_t> Components(const std::wstring& v) {
  std::vector<uint64_t> parts;
  uint64_t cur = 0;
  for (wchar_t c : v) {
    if (c == L'.') {
      parts.push_back(cur);
      cur = 0;
    } else {
      cur = cur * 10 + static_cast<uint64_t>(c - L'0');
    }
  }
  parts.push_back(cur);
  return parts;
}

}  // namespace

PortablePolicy DecidePortableMode(std::optional<uint32_t> machine_value,
                                  std::optional<uint32_t> user_value,
                                  bool default_allow) {
  if (machine_value.has_value()) {
    return {*machine_value != 0 ? PolicyDecision::kAllowed : PolicyDecision::kDenied,
            PolicySource::kMachine};
  }
  if (user_value.has_value()) {
    return {*user_value != 0 ? PolicyDecision::kAllowed : PolicyDecision::kDenied,
            PolicySource::kUser};
  }
  return {default_allow ? PolicyDecision::kAllowed : PolicyDecision::kDenied,
          PolicySource::kDefault};
}

bool IsValidVersion(const std::wstring& version) {
  if (version.empty() || version.size() > 64)
    return false;
  int components = 1;
  int digits = 0;
  for (wchar_t c : version) {
    if (c == L'.') {
      if (digits == 0)
        return false;
      ++components;
      digits = 0;
    } else if (c >= L'0' && c <= L'9') {
      if (++digits > 9)
        return false;
    } else {
      return false;
    }
  }
  return digits > 0 && components <= 4;
}

int CompareVersions(const std::wstring& a, const std::wstring& b) {
  std::vector<uint64_t> pa = Components(a);
  std::vector<uint64_t> pb = Components(b);
  const size_t n = std::max(pa.size(), pb.size());
  pa.resize(n, 0);
  pb.resize(n, 0);
  for (size_t i = 0; i < n; ++i) {
    if (pa[i] != pb[i])
      return pa[i] < pb[i] ? -1 : 1;
  }
  return 0;
}

std::optional<std::wstring> SelectVersion(
    const std::wstring& current_txt,
    const std::vector<std::wstring>& installed_dirs) {
  const std::wstring wanted = Trim(current_txt);
  if (IsValidVersion(wanted) &&
      std::find(installed_dirs.begin(), installed_dirs.end(), wanted) !=
          installed_dirs.end()) {
    return wanted;
  }
  std::optional<std::wstring> best;
  for (const auto& dir : installed_dirs) {
    if (!IsValidVersion(dir))
      continue;
    if (!best || CompareVersions(dir, *best) > 0)
      best = dir;
  }
  return best;
}

bool IsForbiddenSwitch(const std::wstring& arg) {
  size_t start = 0;
  if (arg.rfind(L"--", 0) == 0)
    start = 2;
  else if (!arg.empty() && (arg[0] == L'-' || arg[0] == L'/'))
    start = 1;
  else
    return false;
  std::wstring name = arg.substr(start);
  const auto eq = name.find(L'=');
  if (eq != std::wstring::npos)
    name.resize(eq);
  name = ToLower(name);
  for (const wchar_t* forbidden : kForbiddenSwitches) {
    if (name == forbidden)
      return true;
  }
  return false;
}

std::vector<std::wstring> FilterArguments(const std::vector<std::wstring>& args,
                                          std::vector<std::wstring>* removed) {
  std::vector<std::wstring> kept;
  bool switches_ended = false;
  for (const auto& arg : args) {
    if (!switches_ended && arg == L"--") {
      switches_ended = true;
      kept.push_back(arg);
      continue;
    }
    if (!switches_ended && IsForbiddenSwitch(arg)) {
      if (removed)
        removed->push_back(arg);
      continue;
    }
    kept.push_back(arg);
  }
  return kept;
}

std::wstring QuoteArgument(const std::wstring& arg) {
  if (!arg.empty() && arg.find_first_of(L" \t\n\v\"") == std::wstring::npos)
    return arg;
  std::wstring out = L"\"";
  size_t backslashes = 0;
  for (wchar_t c : arg) {
    if (c == L'\\') {
      ++backslashes;
    } else if (c == L'"') {
      out.append(backslashes * 2 + 1, L'\\');
      out.push_back(L'"');
      backslashes = 0;
    } else {
      out.append(backslashes, L'\\');
      out.push_back(c);
      backslashes = 0;
    }
  }
  out.append(backslashes * 2, L'\\');
  out.push_back(L'"');
  return out;
}

std::wstring BuildCommandLine(const std::wstring& exe,
                              const std::vector<std::wstring>& args) {
  std::wstring cmd = QuoteArgument(exe);
  for (const auto& a : args) {
    cmd.push_back(L' ');
    cmd += QuoteArgument(a);
  }
  return cmd;
}

std::wstring JoinPath(const std::wstring& a, const std::wstring& b) {
  if (a.empty())
    return b;
  if (a.back() == L'\\' || a.back() == L'/')
    return a + b;
  return a + L"\\" + b;
}

std::wstring DirName(const std::wstring& path) {
  const auto pos = path.find_last_of(L"\\/");
  if (pos == std::wstring::npos)
    return L".";
  return path.substr(0, pos);
}

bool IsSafeHelpUrl(const std::wstring& url) {
  if (url.size() < 9 || url.size() > 2048)
    return false;
  if (ToLower(url.substr(0, 8)) != L"https://")
    return false;
  for (wchar_t c : url) {
    if (c <= 0x20 || c == L'"' || c == L'<' || c == L'>' || c == 0x7f)
      return false;
  }
  return true;
}

}  // namespace bx
