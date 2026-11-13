# Portable mode

Browser-x is distributed **only** as one portable program: no installer, no MSI, no registry
or system changes. This page is the reference for users and IT.

## What you download

| File | What it is |
|---|---|
| `BrowserX-<version>-win-x64-portable.exe` | Signed self-extracting archive. It asks **where** to extract and does nothing else. |
| `BrowserX-<version>-win-x64-portable.zip` | Same content as a zip, for IT tooling. |
| `SHA256SUMS`, `SHA256SUMS.sig` | Checksums and their signature (see "Verifying a download"). |

The self-extractor never runs the browser from a temporary folder. It never starts anything
automatically, and it never extracts to a hidden location.

## Folder layout after extraction

```
BrowserX\
  BrowserX.exe            <- the one program you start
  App\current.txt         active application version
  App\<version>\          Chromium-based application files (signed)
  Data\                   created on first run: ALL your browser data
    User Data\            profile: history, bookmarks, cookies, cache, settings
  README-PORTABLE.txt
  LICENSE, THIRD_PARTY_NOTICES.html
```

- `Data\` is a normal, visible folder. Nothing is hidden, and no alternate data streams are used.
- Browser-x does not write to the registry, Start menu, file associations, or default-browser
  settings. Windows itself may use `%TEMP%`. Phase 4 measures any other writes outside the
  folder and lists them here.
- **Deleting the `BrowserX` folder removes the program and all its data.**
- Private windows never write browsing data to `Data\`.

### Moving the folder

Chromium protects cookies and saved passwords with Windows DPAPI, which is tied to your
Windows user account. If you copy the folder to another user or computer, bookmarks,
history and settings still work, but **cookies and saved passwords will not**. You will need
to sign in to websites again. This is intended. Browser-x does not weaken that protection.

## What BrowserX.exe does

1. **Checks administrator policy first**, before it writes any file or starts any process
   (see below).
2. Finds the application version named in `App\current.txt`. If that is missing, it uses the
   newest valid `App\<version>\` folder.
3. In release builds, it refuses to start an application file without a valid Authenticode
   signature.
4. Creates `Data\User Data` next to itself. If the folder is not writable, it shows an error
   and stops. It never falls back to another location.
5. Starts `App\<version>\browserx.exe` with `--user-data-dir=<folder>\Data\User Data`.

It runs as the current user (`asInvoker`) and never asks for elevation.

### Command-line switches that are never forwarded

These switches would weaken the sandbox, allow remote control, bypass the administrator's
extension controls, or move data out of `Data\`. The launcher drops them, whether written
with a `--`, `-` or `/` prefix, and records an Information event in the Windows Application
log:

`--no-sandbox`, `--disable-gpu-sandbox`, `--disable-setuid-sandbox`, `--no-zygote`,
`--single-process`, `--in-process-gpu`, `--disable-web-security`,
`--disable-site-isolation-trials`, `--allow-running-insecure-content`,
`--ignore-certificate-errors`, `--ignore-certificate-errors-spki-list`,
`--remote-debugging-port`, `--remote-debugging-pipe`, `--remote-debugging-address`,
`--remote-allow-origins`, `--load-extension`, `--disable-extensions-except`,
`--user-data-dir`, `--disk-cache-dir`, `--profile-directory`.

Arguments after a bare `--` are treated as URLs or files, as Chromium does.
`launcher/core/launch_plan.cc` holds the list, and `tests/bx/test_launcher_policy_doc.py`
keeps this page in sync with it.

## Administrator control

Policies are read from `HKLM\SOFTWARE\Policies\BrowserX`, or from `HKCU\...` when no machine
value exists. See `docs/policy-reference.md`.

| `PortableModeAllowed` (DWORD) | Result |
|---|---|
| HKLM = `0` | **Blocked.** This applies even if HKCU says `1`. |
| HKLM = `1` | Allowed. |
| No HKLM value, HKCU = `0` / `1` | Blocked / allowed. |
| Not configured | Allowed. Set by `policy.portableModeDefault` in `browserx.json`; an organization build may ship with `deny`. |

When blocked, BrowserX.exe:

- shows: *"Your organization does not allow the portable version of Browser-x on this device.
  Please use the browser installation approved by your IT department, or contact IT for help."*
- offers to open `PortableBlockedHelpUrl` (HKLM, `https://` only) if IT set one
- writes a Warning event (source `BrowserX`, event ID 1000) to the Application log
- exits with code **3** without creating `Data\` or starting the browser

Other exit codes: `4` data folder not writable, `5` application files missing, `6` invalid
signature, `7` the browser process could not be started.

Browser-x respects Windows application control. If AppLocker, WDAC, Smart App Control,
Defender or another EDR blocks it, it does not try to detect, evade or work around that. The
message Windows shows is the result. Ask IT for an approved installation.

Because every file is Authenticode-signed with the same publisher certificate, IT can
allow or block Browser-x with a single publisher rule.

## Verifying a download

1. Check the signature: in PowerShell, `Get-AuthenticodeSignature .\BrowserX-*.exe` must
   report `Valid` with the Browser-x publisher. Every `.exe` and `.dll` inside is signed too.
2. Check the checksum: `Get-FileHash .\BrowserX-*-portable.zip -Algorithm SHA256` must match
   `SHA256SUMS`. Then verify `SHA256SUMS.sig` as described in the release notes (decision D6).
3. In the browser, `browserx://version` (after Phase 2) shows the Browser-x version, Chromium
   version and source commit.

## Updates and rollback

Planned in Phase 5. The updater installs new versions side by side in `App\<new-version>\`,
checks the signature and checksum, then switches `App\current.txt`. The previous version is
kept so you can roll back. IT can turn update checks off or point them at an internal
mirror by policy. Until then, update by extracting a newer release over the folder. `Data\`
is kept.
