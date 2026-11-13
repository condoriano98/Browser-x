# Instructions for contributors and coding agents

Browser-x is a downstream **Chromium fork** distributed **only as a portable program** for
Windows. Read `docs/browser-implementation-plan.md` before larger changes.

## Repository rules

- `browserx.json` is the single source of truth for the product name, pinned Chromium version,
  brands and policy key. Do not duplicate these values elsewhere. Read them from the manifest
  (bx, CMake).
- New Chromium-side code goes in `src/browserx/` (overlay, add-only). Edits to upstream
  Chromium files go in `patches/` as small, single-topic patches listed in `patches/series`.
  Create them with `python bx.py export <topic>/<name>.patch <paths>`.
- Never commit `chromium/`, build output, `dist/`, or any signing keys or certificates.
- Every source file we own starts with the BSD license header
  (`python bx.py license-check`).
- Run before pushing: `python bx.py validate`, `python -m unittest discover -s tests -t .`,
  and the launcher tests (`ctest`).

## Security rules (non-negotiable)

- Never disable or weaken the Chromium sandbox, site isolation, or certificate checks, in
  code, GN args, launcher arguments, or packaging. The launcher's forbidden-switch list
  (`launcher/core/launch_plan.cc`) may only grow, and `docs/portable-mode.md` must list it.
- Portable mode must **honor administrator policy**. Never add stealth or evasion features:
  no hidden processes, windows or storage, no renamed or alternate executables to avoid
  allowlisting, no ignoring or suppressing HKLM policy, no disabling or interfering with
  endpoint protection or monitoring, no log suppression.
- Data stays in the visible `Data\` folder. Never add silent fallbacks to other locations.
- No telemetry or new outbound network requests without a documented decision and policy
  control.
- No Google API keys, proprietary codecs or Widevine (decision D9), and no Midori, Astian,
  Google or Chrome branding or artwork.

## Style

- Python: stdlib only in `tools/bx`, typed, 4-space indent.
- C++: Chromium style (`launcher/` uses C++17, no exceptions needed, `-Werror` / `/WX`).
- Commit messages: imperative summary line, body explaining why.
