// Copyright 2026 The Browser-x Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.
//
// BrowserX.exe: the single program users start in the portable package.
//
//  1. Checks administrator policy (PortableModeAllowed) BEFORE writing
//     anything. If portable mode is not allowed it explains why, points to
//     the IT-approved installation, logs the event, and exits.
//  2. Creates the visible Data\ folder next to itself.
//  3. Starts App\<version>\browserx.exe with its profile in Data\User Data.
//
// It never hides, renames or elevates itself, never touches system settings,
// and never forwards switches that weaken the sandbox (see launch_plan.cc).

#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <softpub.h>
#include <wintrust.h>

#include <optional>
#include <string>
#include <vector>

#include "core/launch_plan.h"
#include "launcher_config.h"

namespace {

enum ExitCode : int {
  kOk = 0,
  kPolicyDenied = 3,
  kDataDirNotWritable = 4,
  kAppMissing = 5,
  kSignatureInvalid = 6,
  kLaunchFailed = 7,
};

constexpr wchar_t kPolicyKey[] = BX_POLICY_REGISTRY_KEY;
constexpr wchar_t kProductName[] = BX_PRODUCT_NAME;
constexpr wchar_t kEventSource[] = L"BrowserX";

std::optional<uint32_t> ReadPolicyDword(HKEY hive, const wchar_t* name) {
  HKEY key = nullptr;
  if (RegOpenKeyExW(hive, kPolicyKey, 0, KEY_QUERY_VALUE | KEY_WOW64_64KEY, &key) !=
      ERROR_SUCCESS) {
    return std::nullopt;
  }
  DWORD type = 0;
  DWORD value = 0;
  DWORD size = sizeof(value);
  const LSTATUS status = RegQueryValueExW(key, name, nullptr, &type,
                                          reinterpret_cast<BYTE*>(&value), &size);
  RegCloseKey(key);
  if (status != ERROR_SUCCESS || type != REG_DWORD || size != sizeof(value))
    return std::nullopt;
  return static_cast<uint32_t>(value);
}

std::wstring ReadMachinePolicyString(const wchar_t* name) {
  HKEY key = nullptr;
  if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, kPolicyKey, 0, KEY_QUERY_VALUE | KEY_WOW64_64KEY,
                    &key) != ERROR_SUCCESS) {
    return L"";
  }
  wchar_t buffer[2049] = {};
  DWORD type = 0;
  DWORD size = sizeof(buffer) - sizeof(wchar_t);
  const LSTATUS status = RegQueryValueExW(key, name, nullptr, &type,
                                          reinterpret_cast<BYTE*>(buffer), &size);
  RegCloseKey(key);
  if (status != ERROR_SUCCESS || type != REG_SZ)
    return L"";
  buffer[size / sizeof(wchar_t)] = L'\0';
  return buffer;
}

void LogEvent(WORD type, const std::wstring& message) {
  HANDLE source = RegisterEventSourceW(nullptr, kEventSource);
  if (!source)
    return;
  const wchar_t* strings[] = {message.c_str()};
  ReportEventW(source, type, 0, 1000, nullptr, 1, 0, strings, nullptr);
  DeregisterEventSource(source);
}

void ShowError(const std::wstring& text) {
  MessageBoxW(nullptr, text.c_str(), kProductName, MB_OK | MB_ICONERROR);
}

std::wstring ModulePath() {
  std::wstring path(MAX_PATH, L'\0');
  for (;;) {
    const DWORD n = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (n == 0)
      return L"";
    if (n < path.size()) {
      path.resize(n);
      return path;
    }
    path.resize(path.size() * 2);
  }
}

std::vector<std::wstring> ListSubdirectories(const std::wstring& dir) {
  std::vector<std::wstring> result;
  WIN32_FIND_DATAW data;
  HANDLE find = FindFirstFileW(bx::JoinPath(dir, L"*").c_str(), &data);
  if (find == INVALID_HANDLE_VALUE)
    return result;
  do {
    if ((data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) &&
        !(data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)) {
      result.emplace_back(data.cFileName);
    }
  } while (FindNextFileW(find, &data));
  FindClose(find);
  return result;
}

std::wstring ReadSmallAsciiFile(const std::wstring& path) {
  HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (file == INVALID_HANDLE_VALUE)
    return L"";
  char buffer[128] = {};
  DWORD read = 0;
  ReadFile(file, buffer, sizeof(buffer) - 1, &read, nullptr);
  CloseHandle(file);
  std::wstring out;
  for (DWORD i = 0; i < read; ++i)
    out.push_back(static_cast<wchar_t>(static_cast<unsigned char>(buffer[i])));
  return out;
}

bool HasValidSignature(const std::wstring& path) {
  WINTRUST_FILE_INFO file_info = {};
  file_info.cbStruct = sizeof(file_info);
  file_info.pcwszFilePath = path.c_str();

  GUID action = WINTRUST_ACTION_GENERIC_VERIFY_V2;
  WINTRUST_DATA trust = {};
  trust.cbStruct = sizeof(trust);
  trust.dwUIChoice = WTD_UI_NONE;
  trust.fdwRevocationChecks = WTD_REVOKE_NONE;
  trust.dwUnionChoice = WTD_CHOICE_FILE;
  trust.pFile = &file_info;
  trust.dwStateAction = WTD_STATEACTION_VERIFY;
  const LONG status = WinVerifyTrust(static_cast<HWND>(INVALID_HANDLE_VALUE), &action, &trust);
  trust.dwStateAction = WTD_STATEACTION_CLOSE;
  WinVerifyTrust(static_cast<HWND>(INVALID_HANDLE_VALUE), &action, &trust);
  return status == ERROR_SUCCESS;
}

int HandlePolicyDenied(bx::PolicySource source) {
  const std::wstring scope = source == bx::PolicySource::kMachine ? L"device"
                             : source == bx::PolicySource::kUser  ? L"user account"
                                                                  : L"build";
  LogEvent(EVENTLOG_WARNING_TYPE,
           L"Browser-x portable mode was not started because administrator policy "
           L"PortableModeAllowed does not allow it (" + scope + L" policy).");

  std::wstring text =
      L"Your organization does not allow the portable version of Browser-x on this "
      L"device.\n\nPlease use the browser installation approved by your IT department, "
      L"or contact IT for help.";
  const std::wstring help_url = ReadMachinePolicyString(L"PortableBlockedHelpUrl");
  if (bx::IsSafeHelpUrl(help_url)) {
    text += L"\n\nOpen your IT help page now?\n" + help_url;
    if (MessageBoxW(nullptr, text.c_str(), kProductName, MB_YESNO | MB_ICONWARNING) == IDYES)
      ShellExecuteW(nullptr, L"open", help_url.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
  } else {
    MessageBoxW(nullptr, text.c_str(), kProductName, MB_OK | MB_ICONWARNING);
  }
  return kPolicyDenied;
}

}  // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
  // 1. Policy check, before any file is created or child process started.
  const bx::PortablePolicy policy = bx::DecidePortableMode(
      ReadPolicyDword(HKEY_LOCAL_MACHINE, L"PortableModeAllowed"),
      ReadPolicyDword(HKEY_CURRENT_USER, L"PortableModeAllowed"),
      BX_PORTABLE_DEFAULT_ALLOW);
  if (policy.decision == bx::PolicyDecision::kDenied)
    return HandlePolicyDenied(policy.source);

  const std::wstring root = bx::DirName(ModulePath());
  const std::wstring app_dir = bx::JoinPath(root, L"App");

  // 2. Locate the application version.
  const std::optional<std::wstring> version = bx::SelectVersion(
      ReadSmallAsciiFile(bx::JoinPath(app_dir, L"current.txt")), ListSubdirectories(app_dir));
  if (!version) {
    ShowError(L"Browser-x files are incomplete (no application version found in the App "
              L"folder).\n\nExtract the portable package again from the original download.");
    return kAppMissing;
  }
  const std::wstring version_dir = bx::JoinPath(app_dir, *version);
  const std::wstring browser_exe = bx::JoinPath(version_dir, BX_BROWSER_EXE);
  if (GetFileAttributesW(browser_exe.c_str()) == INVALID_FILE_ATTRIBUTES) {
    ShowError(L"Browser-x files are incomplete:\n" + browser_exe +
              L"\n\nExtract the portable package again from the original download.");
    return kAppMissing;
  }
#if BX_REQUIRE_SIGNED
  if (!HasValidSignature(browser_exe)) {
    LogEvent(EVENTLOG_ERROR_TYPE, L"Browser-x was not started: invalid signature on " + browser_exe);
    ShowError(L"Browser-x was not started because its files are not validly signed:\n" +
              browser_exe + L"\n\nDownload the portable package again from the official source.");
    return kSignatureInvalid;
  }
#else
  (void)&HasValidSignature;
#endif

  // 3. Visible data folder next to the program. Never fall back elsewhere.
  const std::wstring user_data = bx::JoinPath(bx::JoinPath(root, L"Data"), L"User Data");
  const int mk = SHCreateDirectoryExW(nullptr, user_data.c_str(), nullptr);
  if (mk != ERROR_SUCCESS && mk != ERROR_ALREADY_EXISTS && mk != ERROR_FILE_EXISTS) {
    ShowError(L"Browser-x cannot write its data folder:\n" + user_data +
              L"\n\nThe portable version keeps all data next to the program and does not "
              L"store it anywhere else. Move the Browser-x folder to a location where you "
              L"can write files, as approved by IT.");
    return kDataDirNotWritable;
  }

  // 4. Forward the user's arguments, minus forbidden switches.
  std::vector<std::wstring> user_args;
  int argc = 0;
  if (LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc)) {
    for (int i = 1; i < argc; ++i)
      user_args.emplace_back(argv[i]);
    LocalFree(argv);
  }
  std::vector<std::wstring> removed;
  std::vector<std::wstring> args = {L"--user-data-dir=" + user_data};
  for (auto& a : bx::FilterArguments(user_args, &removed))
    args.push_back(std::move(a));
  if (!removed.empty()) {
    std::wstring list;
    for (const auto& r : removed)
      list += L"\n  " + r;
    LogEvent(EVENTLOG_INFORMATION_TYPE,
             L"Browser-x ignored command-line switches that are not allowed:" + list);
  }

  std::wstring command_line = bx::BuildCommandLine(browser_exe, args);
  STARTUPINFOW si = {};
  si.cb = sizeof(si);
  PROCESS_INFORMATION pi = {};
  if (!CreateProcessW(browser_exe.c_str(), command_line.data(), nullptr, nullptr, FALSE, 0,
                      nullptr, version_dir.c_str(), &si, &pi)) {
    ShowError(L"Browser-x could not be started (error " + std::to_wstring(GetLastError()) +
              L").");
    return kLaunchFailed;
  }
  CloseHandle(pi.hThread);
  CloseHandle(pi.hProcess);
  return kOk;
}
