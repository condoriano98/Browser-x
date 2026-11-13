# Building Browser-x on Windows

Browser-x is built natively on Windows, which is Chromium's supported path outside Google.
Verify every version below against the Chromium tag pinned in `browserx.json` and Chromium's
`docs/windows_build_instructions.md` for that tag. They change between milestones.

## Machine

- Windows 11 or Windows Server 2022, x64
- 32+ cores and 64 GB+ RAM recommended (16 GB minimum, with very long builds)
- About 250 GB free on an NTFS SSD per checkout. Put `chromium/` on a dev drive if available.
- Self-hosted CI runner labels: `self-hosted`, `windows`, `chromium` (+ `signing` for releases)

## Tools

1. **Visual Studio 2022** with "Desktop development with C++", the MFC/ATL components, and the
   Windows SDK version Chromium requires (including Debugging Tools for Windows).
2. **Python 3.11+** on PATH.
3. **Git for Windows**, plus `git config --global core.autocrlf false` and
   `git config --global core.filemode false`.
4. **depot_tools**: clone `https://chromium.googlesource.com/chromium/tools/depot_tools.git`,
   put it first on PATH, and set `DEPOT_TOOLS_WIN_TOOLCHAIN=0` (use the local Visual Studio).
5. **CMake 3.20+** for the launcher.

`python bx.py doctor` reports what is missing. It installs nothing.

## Build

```powershell
python bx.py download            # shallow fetch of the pinned tag + gclient sync + hooks
python bx.py import              # overlay + patches + branding (use --reset to start clean)
python bx.py build win-x64       # out\Release-x64: official build, several hours
python bx.py build win-x64 --dev # out\Dev-x64: component build for development
python bx.py run --dev
```

Set `BX_CHROMIUM_DIR` to keep the checkout outside the repository (for example on a dev drive).

## Updating Chromium

```powershell
python bx.py update --check      # show pinned vs. latest stable
python bx.py update              # pin the latest stable in browserx.json
python bx.py download
python bx.py import --reset      # stops at the first patch that no longer applies
```

Fix a conflicting patch inside `chromium\src`, then regenerate it with
`python bx.py export <name>.patch <paths>`.
