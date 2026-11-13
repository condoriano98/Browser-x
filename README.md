# Browser-x

[![CI](https://github.com/condoriano98/Browser-x/actions/workflows/ci.yml/badge.svg)](https://github.com/condoriano98/Browser-x/actions/workflows/ci.yml)

Browser-x is a lightweight, privacy-oriented **portable** web browser for Windows, built on
**Chromium**. It follows the downstream-fork model of
[midori-desktop](https://github.com/goastian/midori-desktop): upstream source is fetched at a
pinned version, and our own files, patches and branding are applied on top. Browser-x is an
independent project. It is not affiliated with Google, the Chromium project, Astian or Midori,
and uses none of their branding.

> **Status: early development.** The repository contains the fork tooling, the portable
> launcher, packaging and CI. No Chromium patches or release builds exist yet. See
> [docs/browser-implementation-plan.md](docs/browser-implementation-plan.md).

## Contents

- [Features](#features)
- [Portable by design](#portable-by-design)
- [Build from source](#build-from-source)
- [Project layout](#project-layout)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)

## Features

Planned for the first release:

- Chromium's tabs, address bar, bookmarks, history, downloads and private windows
- A local-only new-tab page
- Privacy defaults: third-party cookies blocked, HTTPS-first, built-in tracker blocking
- A privacy/status panel and clear site-permission controls
- **No browsing telemetry.** No Google service keys are built in.
- The full Chromium enterprise policy set, under `HKLM\SOFTWARE\Policies\BrowserX`

## Portable by design

Browser-x is **one portable program**. There is no installer and it makes no system changes.

- Download one signed file, choose where to extract it, and start `BrowserX.exe`.
- All browser data stays in the visible `Data\` folder next to it. Delete the folder to remove
  everything.
- **IT stays in control:** the policy `PortableModeAllowed=0` blocks it with a clear message
  pointing to the approved installation. Every file is signed for AppLocker/WDAC publisher
  rules, and the launcher never weakens the Chromium sandbox.

Details: [docs/portable-mode.md](docs/portable-mode.md).

## Build from source

Chromium for Windows is built **on Windows**. Reserve about 250 GB of SSD. A machine with 32+
cores and 64 GB+ RAM is recommended. Full instructions:
[docs/building-windows.md](docs/building-windows.md).

```powershell
git clone https://github.com/condoriano98/Browser-x.git
cd Browser-x
python bx.py doctor              # checks the machine; installs nothing
python bx.py download            # Chromium at the version pinned in browserx.json
python bx.py import              # copy src/ overlay, apply patches/series, apply branding
python bx.py build win-x64       # or: --dev for a fast component build
python bx.py run                 # start it with a throwaway profile
```

Package the portable program (see [packaging/windows/README.md](packaging/windows/README.md)):

```powershell
cmake -S launcher -B build-launcher -A x64
cmake --build build-launcher --config Release
python bx.py package win-x64 --staging <Chrome-bin dir> --launcher build-launcher\Release\BrowserX.exe
```

Repository-level checks run anywhere with Python 3.11+ and CMake:

```bash
python bx.py validate
python -m unittest discover -s tests -t .
cmake -S launcher -B build-launcher && cmake --build build-launcher && ctest --test-dir build-launcher
```

## Project layout

```
browserx.json   product manifest: name, pinned Chromium version, brands, policy key
bx.py, tools/   bx fork tool (download, import, build, package, update, export)
src/            new Browser-x source files copied into chromium/src (overlay)
patches/        ordered Chromium patch series (patches/series)
configs/        GN build args, branding, recommended policies
launcher/       BrowserX.exe portable launcher (C++, CMake)
packaging/      signing and self-extracting download scripts
tests/          repository tests
docs/           plan, build guide, portable mode, policy reference, decisions
chromium/       (not committed) Chromium checkout and build output
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md). Keep changes focused and run
the relevant tests. Do not commit build output, the `chromium/` checkout, or signing material.

## Security

Report vulnerabilities privately. See [SECURITY.md](SECURITY.md).

## License

Browser-x is licensed under the [BSD 3-Clause License](LICENSE), the same license as
Chromium. Release packages include `THIRD_PARTY_NOTICES` for Chromium and its components.
