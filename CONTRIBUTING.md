# Contributing to Browser-x

Thanks for helping. Please read [AGENTS.md](AGENTS.md) first. Its repository and security
rules apply to every contribution.

## Ways to contribute

- **Bugs:** open an issue with steps to reproduce, the Browser-x version (`browserx://version`)
  and Windows version.
- **Docs:** documentation-only changes need no build.
- **Code:** start with an issue so the approach can be agreed, especially for anything that
  adds a Chromium patch.

## Development setup

- Repository tooling, launcher and tests: Python 3.11+, CMake 3.20+, a C++17 compiler. Works on
  Windows, Linux or macOS.
- Chromium builds: a Windows build machine, see [docs/building-windows.md](docs/building-windows.md).

## Making changes

1. Branch from `main`.
2. Keep changes focused. One topic per Chromium patch.
3. Run `python bx.py validate`, `python -m unittest discover -s tests -t .` and the launcher
   tests.
4. Open a pull request describing what changed and why. Patches touching sandbox, IPC,
   networking, policy, the launcher or the updater need two reviewers.
