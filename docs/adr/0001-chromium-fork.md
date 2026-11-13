# ADR 0001: Full Chromium fork, structured like midori-desktop

- Status: Accepted (2026-11-13, confirmed by the project owner)
- Supersedes: the CEF recommendation in plan revision 1

## Decision

Browser-x is a downstream fork of Chromium, managed like midori-desktop manages Firefox:

- a product manifest (`browserx.json`)
- a fork tool (`bx`)
- an add-only source overlay (`src/`)
- an ordered patch series (`patches/`)
- branding and GN-args configs (`configs/`)
- per-task CI workflows

## Consequences

- Inherited: the full browser UI, extensions, the enterprise policy stack and the sandbox.
- Required:
  - a self-hosted Windows build farm
  - a named owner for weekly Chromium security rebases, with SLAs in `SECURITY.md`
  - small, single-topic patches
- Fallback, if the rebase and build capacity cannot be funded: CEF (plan revision 1), rather
  than shipping an unpatched fork.
