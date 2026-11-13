# ADR 0002: One portable program, no installer

- Status: Accepted (2026-11-13, confirmed by the project owner)

## Decision

Browser-x ships only as a portable program:

- one signed self-extracting download (7-Zip GUI SFX: asks where to extract, runs nothing)
- plus an equivalent zip and `SHA256SUMS`

Users start `BrowserX.exe`, a small signed launcher. It:

- checks `PortableModeAllowed` before writing anything
- keeps all data in the visible `Data\` folder next to itself
- starts the Chromium application from `App\<version>\`
- never forwards sandbox-weakening or data-relocating switches

## Rejected alternative

A true single `.exe` that unpacks Chromium (about 300 MB, hundreds of files) to `%TEMP%` on every
launch. It is slow, leaves data outside the portable folder, breaks IT path-based rules, and
looks like evasive malware to endpoint protection.

## Consequences

- No MSI, no system-level install, no default-browser or file-association registration.
- Updates are side by side under `App\` with rollback (Phase 5).
- IT can control it with AppLocker/WDAC publisher rules and `PortableModeAllowed`.
