# Browser-x: Implementation Plan (Chromium fork, structured like midori-desktop)

Status: **revision 3, decisions D1 (Chromium fork), D5 (BSD-3) and portable-only distribution confirmed.** The repository scaffold exists (see §10). Chromium has not been fetched or built, and nothing has been packaged, installed or deployed.
Target platform: **Windows x64** first. Windows ARM64, Linux and macOS come later, as in the reference.
Date: 2026-11-13

> **Revision 2 change:** The requester asked to model Browser-x on
> [`goastian/midori-desktop`](https://github.com/goastian/midori-desktop) but to use **Chromium** as the engine. midori-desktop is a full
> fork of Firefox. The Chromium equivalent is a **full Chromium fork** (Option A in revision 1), not CEF. This revision replaces the
> CEF recommendation. §3 explains the trade-off and what it costs.

---

## 1. Executive summary

Browser-x will be a **downstream fork of Chromium**. It follows the same layout and workflow as midori-desktop, which follows Firefox:

| midori-desktop (Gecko) | Browser-x (Chromium) |
|---|---|
| Upstream Firefox source downloaded into `engine/` (not committed) | Upstream Chromium fetched at a pinned tag into `chromium/src/` (not committed) via `depot_tools` |
| `amelia.json` holds the product name, vendor, appId, Firefox version, brands, add-ons and update host | `browserx.json` holds the product name, vendor, appId, Chromium version, brands, update host and bundled components |
| Amelia CLI (`download`, `import`, `brand`, `build`, `package`, `update`) | `bx` CLI (Python, in `tools/bx/`) with the same verbs, wrapping `gclient`, `gn` and `autoninja` |
| `src/` overlay of new and changed Firefox files | `src/` overlay of new files, plus `patches/` as an ordered series of `.patch` files for upstream edits |
| `configs/branding/{release,dawn}` | `configs/branding/{stable,beta}` (icons, `BRANDING`, product strings) |
| `configs/{common,windows,…}/mozconfig` | `configs/{common,windows,…}/args.gn` |
| `src/midori/workspace/` (custom features) | `src/browserx/` (custom features, e.g. privacy panel, portable mode) |
| `midori-newtab` add-on, built-in protection extension | Built-in WebUI new-tab page, built-in content blocking |
| `build/AppDir/distribution/policies.json` | Chromium enterprise policies (registry/ADMX) + `initial_preferences` |
| `build/winsign/sign.ps1` + MAR updates + NSIS/7z SFX installer | `packaging/windows/sign.ps1` + **portable-only** 7-Zip GUI SFX + signed update manifest (no installer, ADR 0002) |
| `.github/workflows/{build-windows,patches,update-firefox,release}.yml` | Same set, with `update-chromium.yml` |

**What the fork gives us for free**, compared with CEF:

- the full Chrome browser UI: tabs, omnibox, bookmarks, history, downloads, incognito, settings and site permissions
- the complete Chromium **enterprise policy stack** with ADMX templates
- **Chrome extensions**
- the profile system
- Chromium's own sandbox and download protections

The MVP is mostly about **removing, rebranding and configuring**, plus a small set of new features. It is not about building a browser UI from scratch.

**What it costs:**

- The checkout is about 100 GB, and full builds take hours on large machines. We need **self-hosted Windows build machines**, because GitHub-hosted runners are too small.
- The patch series must be **rebased on every Chromium stable security release (about weekly) and milestone (every 4 weeks)**. This is the dominant ongoing cost. The plan keeps patches small and well named to contain it.

**Identity:** "Like midori-desktop" means the same **structure, workflow and feature direction**: lightweight, privacy-oriented, custom new tab. It does **not** mean using the Midori name, logo, artwork or branding, which belong to Astian. Browser-x ships its own branding. No code is copied from midori-desktop. Its sources are MPL-2.0 Gecko code and do not apply to Chromium anyway.

---

## 2. Repository findings

### 2.1 This repository (`condoriano98/Browser-x`)

| Area | Finding |
|---|---|
| Content | Empty before this plan. The only file is `docs/browser-implementation-plan.md`. There are no commits besides it. |
| `AGENTS.md`, README, CONTRIBUTING, LICENSE | Not present |
| Framework, engine, build system, packaging, CI, tests, policy, signing, updater | None |
| Target OS | Windows (requester) |

There is nothing to preserve or migrate. Phase 0 creates the repo skeleton described in §5.

### 2.2 Reference repository (`goastian/midori-desktop`, inspected at commit `6c78156`)

| Path | What it is | How we mirror it |
|---|---|---|
| `amelia.json` | Product manifest: name, vendor, `appId`, `binaryName`, pinned upstream version (Firefox 159.0.1), brands (`release`, `dawn`), bundled add-ons, `updateHostname`, license type MPL-2.0 | `browserx.json` with the same fields, using a Chromium version |
| `package.json` scripts | `download`, `import`, `bootstrap`, `brand`, `build:win-x64`, `package:win-x64`, `update-ff`, `test`, `lint`, `lc` (license check) | `bx` verbs with the same names (§5.3) |
| `engine/` (gitignored) | Firefox source tree and `obj-*` output | `chromium/src/` and `chromium/src/out/<config>/` |
| `src/` | Overlay of Firefox dirs (`browser/`, `toolkit/`, `netwerk/`, `security/`, `services/`, …) + `src/midori/workspace/` | `src/` overlay of new files in Chromium paths + `src/browserx/` for product features |
| `patches/` | One patch to the Amelia tool itself | `patches/` holds the **ordered Chromium patch series** (`series` file), the Chromium-world norm (ungoogled-chromium, Brave) |
| `configs/branding/release/` | Icons (`.ico`, PNGs 16–1024), installer art, private-browsing icons | `configs/branding/stable/` with Chromium's equivalents (`chrome/app/theme/…`, `BRANDING`, `.ico`, VisualElements) |
| `configs/{common,windows,linux,macos}/mozconfig` | Build flags per platform, branding dir, source repo/changeset, sccache, optional Safe Browsing key file | `configs/{common,windows}/args.gn` (`is_official_build`, `chrome_pgo_phase`, `enable_reporting=false`, no Google API keys, …) |
| `build/AppDir/distribution/policies.json` | Policies baked into the Linux AppImage (disable app update) | Default policies/`initial_preferences` per package type |
| `build/winsign/` | `sign.ps1`, `bootstrap.ps1`, `mar.exe` | `packaging/windows/sign.ps1` + update tooling |
| `scripts/` | `update_ff.py`, `win-installer.sh`, `verify-build-output.sh`, `license-check.mjs`, `run_tests.py`, sync tests | `tools/bx/` commands + `scripts/` equivalents |
| `.github/workflows/` | `build-{windows,linux,macos}.yml`, `ci.yml`, `patches.yml`, `update-firefox.yml`, `release.yml`, `l10n.yml` | Same names; Windows first (§6.7) |
| README "Build from source" | Windows is **cross-compiled from Linux**; native Windows dev not maintained | Browser-x builds **natively on Windows** (Chromium's supported path for non-Google developers; cross-compiling Windows needs a hand-packaged MSVC toolchain) |
| Features listed | Privacy defaults + built-in protection extension, workspaces, custom new tab, custom branding/update config, WebExtensions, sync | Mapped in §4 |

### 2.3 Constraints that follow

1. **Build infrastructure is the gating item.** Chromium for Windows needs Visual Studio 2022 with the pinned Windows SDK, 32+ cores and 64 GB+ RAM recommended, plus about 250 GB of free SSD per checkout. That rules out GitHub-hosted runners (14 GB disk, 6 h limit), so we need **self-hosted runners**. Distributed builds via Siso/RBE need our own RBE service (e.g. BuildBuddy or EngFlow). Google's is not available to forks.
2. **No signing identity exists yet.** We need a code-signing cert (OV/EV or Azure Trusted Signing).
3. **Patch-rebase capacity.** We need at least one engineer who owns weekly rebases (§7.1).
4. **Branding and trademarks.** We must remove Google/Chrome branding (Chromium's non-branded build already does) and must not use Midori/Astian marks.
5. **The project license is not yet chosen.** Chromium is BSD-3-Clause. Our patches should use a compatible license. BSD-3 is the simplest, matching upstream.

---

## 3. Engine decision

| Criterion | **A. Chromium fork (chosen)** | B. CEF + own shell (rev. 1 recommendation) | C. Existing shell in repo |
|---|---|---|---|
| Matches the requested "like midori-desktop" model | **Yes**, the same fork-of-upstream model | No, it is an embedding, not a fork | N/A, the repo is empty |
| Website compatibility | Identical to Chrome | Same engine; some browser-level features missing | N/A |
| Tabs, bookmarks, history, downloads, incognito, settings, permission UI | **Inherited** | Must be built | N/A |
| Extensions | **Full Chrome extension system** | Partial | N/A |
| Enterprise policy | **Full Chromium policy set + ADMX generator** | Subset via `chrome_policy_id` | N/A |
| Security patching | **We rebase and rebuild each stable release (weekly)**, which is heavy | Bump the CEF version, which is light | N/A |
| Build cost | Very high (about 100 GB source, hours per build, self-hosted farm) | Low | N/A |
| Package size | About 120–150 MB installer, similar to Chromium | Similar | N/A |
| Memory | Chromium-like. "Lightweight" comes from disabling background services and features, not from a lighter engine | Similar | N/A |

**Decision: Option A.** It is what the requester asked for. It also gives the strongest result on standards, extensions and enterprise policy, which matter for an IT-approved browser. The cost is accepted on the condition that §7.1 (patch ownership) and §2.3 #1 (build farm) are funded. If they cannot be funded, fall back to CEF (revision 1) rather than shipping an unpatched fork. That fallback is decision D1.

---

## 4. Product scope

### 4.1 MVP (first release)

Most MVP items are **inherited from Chromium and configured**. The "Work" column shows what we actually do.

| Feature | Source | Work |
|---|---|---|
| Tabs, navigation | Inherited | Theme and branding only; optionally a compact "lightweight" toolbar layout patch |
| Address/search bar | Inherited omnibox | Set default search engines in `prepopulated_engines` (no paid deals, decision D2). Turn remote suggestions **off by default** |
| Bookmarks, history, downloads | Inherited | None beyond branding |
| Private windows | Inherited (Incognito) | Rename in strings ("Private window"). Policy `IncognitoModeAvailability` already exists |
| New-tab page | **New**: `src/browserx/webui/new_tab/` (WebUI) | Local-only NTP: search box, local top sites, bookmarks; no remote content. Replaces Chromium's NTP the way `midori-newtab` replaces Firefox's |
| Configurable privacy protections | Mix | Third-party cookie blocking **on** (pref default patch), HTTPS-First/Upgrades **on**, Global Privacy Control header (patch), **built-in tracker blocking** (§4.3) |
| Site permission controls | Inherited | Defaults tightened via `initial_preferences`/policy (notifications ask→block-by-default option) |
| Privacy/status panel | **New** toolbar button + bubble, `src/browserx/privacy_panel/` | Per tab: connection/cert, blocked requests count/list, active permissions, cookies, "managed by your organization" |
| No browsing telemetry | Patch series | Remove or disable UMA/metrics reporting, field trials/variations fetch, Google API keys, translate/spelling/autofill/sync services, Safe Browsing extended reporting, NTP promos, "phone home" endpoints (§7.5) |
| `browserx://version` | Inherited `chrome://version` | Add the Browser-x version, git commit, Chromium version, build ID, portable data path |

### 4.2 Features of the reference repo, and when they arrive

| midori-desktop feature | Browser-x decision | Cost |
|---|---|---|
| Built-in protection extension | **MVP** as built-in tracker blocking (§4.3) | Medium: native engine + list pipeline |
| Custom new tab | **MVP** (WebUI) | Low–medium |
| Custom branding + update config | **MVP** | Low (branding), medium (updates, §6.4) |
| WebExtensions compatibility | **Available in MVP but admin-controlled.** Chromium's extension system is inherited, so the engineering cost is about zero. The cost is **policy and security**: default to `ExtensionInstallBlocklist=*` + an IT `ExtensionInstallAllowlist` in managed deployments. Chrome Web Store access for a non-Google browser is decision D12 | Low engineering, needs a product decision |
| Workspaces (`src/midori/workspace/`) | **Later.** Chromium has tab groups (inherited) as an interim | High: profile/session model changes |
| Sync | **Later.** Chromium sync uses Google servers, which must be disabled | High: server + E2E encryption |
| Linux/macOS builds | **Later.** Windows x64 first, then Windows ARM64 | Each platform adds a build farm and signing |
| Localization (Crowdin, `l10n.yml`) | Inherited Chromium locales. Only our new strings need translation; add Crowdin later | Low |

### 4.3 Built-in tracker blocking (replacing Midori's protection extension)

- **Option 1 (recommended):** a native filter engine in the network stack, as in Brave. For example, embed `adblock-rust` (MPL-2.0, file-level copyleft, compatible with distribution alongside BSD code; needs legal review, decision D8). Lists: EasyList/EasyPrivacy (GPLv3 / CC BY-SA, needs legal review) or a self-curated list. Lists update through a signed component, with the source configurable by policy.
- **Option 2:** a bundled component extension using `declarativeNetRequest`. Easier to maintain across rebases, but capped by the rule limits of Manifest V3.
- Either way: per-site toggle in the privacy panel, on/off/strict modes, and policy `TrackerBlockingMode`.

### 4.4 Explicit exclusions

Workspaces, sync, VPN, bundled search deals, password-manager changes, Widevine/DRM (Chromium builds need a licence from Google), proprietary codecs (`proprietary_codecs=true` / `ffmpeg_branding="Chrome"` need patent licensing, decision D9), Google Safe Browsing API (needs an agreement, decision D10), macOS/Linux.

---

## 5. Architecture and repository layout

### 5.1 Repository layout (mirrors midori-desktop)

```
Browser-x/
├── AGENTS.md                    agent/contributor rules (rebases, no sandbox weakening, no evasion features)
├── README.md  CONTRIBUTING.md  SECURITY.md  CODE_OF_CONDUCT.md  LICENSE (BSD-3, D5)
├── browserx.json                ⇐ amelia.json: name, vendor, appId, binaryName, chromium.version,
│                                   brands{stable,beta}, components, updateHostname, license
├── tools/bx/                    ⇐ amelia: Python CLI (download|import|brand|build|package|run|update|export|test)
├── configs/
│   ├── branding/stable/         icons, BRANDING, product_logo_*, VisualElements, installer art
│   ├── branding/beta/
│   ├── common/args.gn           shared GN args
│   ├── windows/args.gn          Windows GN args
│   └── policies/defaults/       initial_preferences + default managed policy sets per package type
├── patches/
│   ├── series                   ordered list; one topic per patch
│   ├── branding/                product name, policy registry path, user-data-dir name, update URLs
│   ├── privacy/                 telemetry off, API keys off, cookie/HTTPS defaults, GPC
│   ├── browserx/                hooks wiring src/browserx into chrome/ (BUILD.gn deps, toolbar button, NTP)
│   ├── portable/                portable data dir + PortableModeAllowed enforcement
│   └── policy/                  new policy definitions (PortableModeAllowed, TrackerBlockingMode, …)
├── src/                         ⇐ midori src/: NEW files copied into chromium/src at import
│   └── browserx/
│       ├── privacy_panel/       C++ bubble + model
│       ├── content_blocking/    filter engine glue + list component
│       ├── portable/            portable mode detection, marker verification, policy pre-check
│       └── webui/new_tab/       NTP (TS/HTML/CSS, Chromium WebUI conventions)
├── launcher/                    BrowserX.exe portable launcher (C++17, CMake): policy check, Data dir, switch filter
├── packaging/windows/           sign.ps1, make-sfx.ps1 (one-file download), README-PORTABLE.txt
├── scripts/                     update_chromium.py, verify-build-output, license-check, sbom, checksums
├── tests/                       repo-level tests (bx unit tests, patch-apply, policy, portable, network audit)
├── docs/                        this plan, building-windows.md, policy reference, release process
├── .github/workflows/           ci, patches, build-windows, update-chromium, release
└── chromium/                    (gitignored) depot_tools checkout: chromium/src, out/
```

### 5.2 Working model

```mermaid
flowchart LR
  V[browserx.json<br/>upstream.version] --> D[bx download<br/>gclient sync at tag]
  D --> I[bx import<br/>copy src/ overlay<br/>apply patches/series]
  I --> B[bx brand stable|beta<br/>copy configs/branding]
  B --> G[bx build win-x64<br/>gn gen + autoninja]
  G --> P[bx package win-x64<br/>portable folder, zip, SHA256SUMS]
  P --> S[sign + SHA256SUMS + SBOM + provenance]
  U[bx update<br/>new Chromium tag] -->|rebase patches| I
  E[bx export<br/>regen patches from chromium/src edits] --> PS[patches/]
```

- `bx export` turns edits made inside `chromium/src` back into patch files, like `amelia export`.
- `bx update` bumps `upstream.version` in `browserx.json`, re-syncs, and re-applies patches. It stops at the first conflicting patch with a report (like `update_ff.py`).
- **Patch rules:** one topic per patch, smallest diff possible, and new code goes in `src/browserx/` rather than inside upstream files. Upstream files only get thin hooks. This keeps weekly rebases cheap.

### 5.3 `bx` verbs (parity with midori-desktop scripts)

| midori `npm run …` | `bx …` |
|---|---|
| `download` | `bx download` (depot_tools + `gclient sync --with_branch_heads --with_tags` at the pinned tag) |
| `import` | `bx import` |
| `brand` | `bx brand stable` |
| `bootstrap:win` | `bx bootstrap win` (checks VS 2022, SDK, Python, disk/RAM; installs nothing silently) |
| `build:win-x64` / `build:win-arm64` | `bx build win-x64` / `bx build win-arm64` |
| `package:win-x64` | `bx package win-x64` |
| `browser` / `start` | `bx run` (fresh temporary profile) |
| `update-ff` | `bx update [--to <tag>]` |
| `export` | `bx export` |
| `test`, `test:unit` | `bx test` (repo tests + selected Chromium `browser_tests`/`unit_tests` filters) |
| `lc` | `bx license-check` |

### 5.4 Runtime components

The browser runs as Chromium's own process model: browser, sandboxed renderers, GPU, network and utility processes. Browser-x additions live only in the browser process:

- `PortableModeService`: early startup, before the profile is created
- `PrivacyPanelController`
- `ContentBlockingService` (network-request hook + list component)
- the NTP WebUI
- policy definitions registered with Chromium's existing `PolicyService`

---

## 6. Packaging and portable deployment (Windows)

### 6.1 Distribution: one portable program (ADR 0002)

There is **no installer and no MSI**. Each release consists of:

| Artifact | Purpose |
|---|---|
| `BrowserX-<ver>-win-x64-portable.exe` | The one-file download: a signed 7-Zip **GUI** self-extractor (`7z.sfx`). It asks where to extract and runs nothing. |
| `BrowserX-<ver>-win-x64-portable.zip` | The same content, for IT tooling (deterministic zip) |
| `SHA256SUMS` (+ signature, D6) | Checksums of both |

- Users start one program: `BrowserX.exe`.
- There is no default-browser, file-association or registry registration.
- IT can still deploy the folder to managed devices with its own tooling (Intune/ConfigMgr file copy) and control it with AppLocker/WDAC **publisher** rules, because every PE file is signed by the same publisher.
- **Rejected:** a single exe that unpacks about 300 MB to `%TEMP%` on every launch. It is slow, leaves data outside the portable folder, breaks IT path rules, and looks like evasive malware to EDR. See ADR 0002.

### 6.2 Portable layout and data retention (implemented by `bx package` + launcher)

```
BrowserX\
  BrowserX.exe                 signed launcher (launcher/), the only program users start
  App\current.txt              active version (written only by bx / the updater)
  App\<ver>\                   Chromium application files: browserx.exe, <chromium-ver>\ DLLs (signed)
  App\<prev-ver>\              kept for rollback (Phase 5)
  Data\User Data\              created on first run: Chromium profile, visible, normal attributes
  README-PORTABLE.txt, LICENSE, THIRD_PARTY_NOTICES.html
```

- **Launcher (implemented):** `BrowserX.exe`:
  - checks policy **before** writing anything
  - selects `App\<ver>` (validated version names, so a version can never be a path)
  - in release builds, verifies the Authenticode signature of `browserx.exe`
  - creates `Data\User Data`, failing clearly if it is not writable and never falling back elsewhere
  - starts `browserx.exe --user-data-dir=<root>\Data\User Data`
  - drops user-supplied switches that weaken the sandbox or move data, logging an event
- **Chromium side (Phase 4 patch `portable/portable-user-data-dir.patch`):** `browserx.exe` itself:
  - repeats the `PortableModeAllowed` check before creating a profile, so starting `App\<ver>\browserx.exe` directly cannot skip policy
  - defaults the profile to `<root>\Data\User Data`
  - skips shell integration and default-browser checks
  - **Until this patch lands, the launcher check alone can be bypassed by starting the inner exe.** IT's binding control is application control (AppLocker/WDAC), as for any software.
- **No hidden or unexpected storage:** no hidden attributes, no ADS, no registry writes. Remaining writes outside `Data\` (`%TEMP%`, Windows-required caches) are measured in Phase 4 and listed in `docs/portable-mode.md`.
- **Retention:**
  - Chromium's existing settings and policies: `ClearBrowsingDataOnExitList`, `SavingBrowserHistoryDisabled`, `BrowserSignin=0`, `DownloadDirectory`
  - New: `HistoryRetentionDays`
  - Incognito never writes to the profile
- **DPAPI:** Chromium encrypts cookies and passwords with OS-user-bound keys (and app-bound encryption on recent versions). A portable folder moved to another user or machine loses those secrets. This is intended and documented; it is not worked around.

### 6.3 When administrator policy disallows portable mode (implemented in the launcher)

Policy: `PortableModeAllowed` (DWORD) under `HKLM\SOFTWARE\Policies\BrowserX`, then HKCU. HKLM always wins, so HKCU=1 cannot override HKLM=0. It is added to the generated ADMX in Phase 4.

| State | Behaviour |
|---|---|
| `0` | Before creating any file or process, show "Your organization does not allow the portable version of Browser-x on this device. Please use the browser installation approved by your IT department…", offer `PortableBlockedHelpUrl` (https only) if set, write a Warning event (source `BrowserX`, ID 1000), exit code 3. **No files are written.** Verified under Wine. |
| `1` | Runs. |
| Not configured | Runs (`browserx.json` `policy.portableModeDefault`; decision D3 allows organization builds to ship `deny`). |
| Blocked by AppLocker/WDAC/SRP/Defender/EDR | Browser-x does nothing to detect, evade or work around it. Docs say to contact IT. |

**Never implemented:**
- hiding processes or windows
- renamed or alternate executables to dodge allowlists
- ignoring or suppressing HKLM policy
- disabling or tampering with endpoint protection
- suppressing logs
- "stealth" or "boss key" modes
- `--no-sandbox` or other security-weakening flags in any package

The launcher's list of switches it refuses to forward is in `docs/portable-mode.md` and kept in sync by a test.

### 6.4 Updates and rollback

Chromium builds do not include Google Update. Browser-x uses its own update mechanism:

1. When `UpdateCheckEnabled` is not 0, fetch the signed manifest from `update.manifestUrl` in `browserx.json` (or the policy `UpdateSource` mirror).
2. Download the zip and verify its SHA-256 from the manifest and the Authenticode signature of every PE against the pinned publisher.
3. Extract to `App\<new>\` and run `--self-test` (sandbox + resources).
4. Atomically switch `App\current.txt`, keeping N=2 versions. Roll back automatically on failed launch, or manually from `browserx://version`. The launcher already falls back to the newest valid version if `current.txt` is missing or invalid.
5. Back up `Data\User Data\*\` databases before profile-version changes. Chromium refuses to open a profile from a newer version. This is surfaced in the UI and fixed by rolling back.

Additional rules:
- `MinimumVersion` policy: old builds show "no longer approved by your organization".
- No silent self-update unless policy `AutoApplyUpdates=1`.
- Until Phase 5, users update by extracting a newer release over the folder; `Data\` is kept.

### 6.5 IT verification of version and source

- Authenticode signatures (timestamped) on all `.exe`/`.dll` files we ship.
- `SHA256SUMS` + detached signature (Sigstore or minisign, decision D6) per release.
- SLSA build provenance from the release workflow, plus a CycloneDX SBOM listing the Chromium version and `third_party/` components.
- `browserx://version`, `browserx.exe --version`, and Windows file-version resources all agree.
- Source traceability: `browserx.json` `upstream.version` + git commit of this repo + `patches/series` hash, embedded in the build (as midori's mozconfig sets `MOZ_SOURCE_REPO`/`MOZ_SOURCE_CHANGESET`).

### 6.6 Administrator configuration

- The **full Chromium policy set is inherited**. Patch the registry path from `SOFTWARE\Policies\Chromium` to `SOFTWARE\Policies\BrowserX` (`components/policy/...` path constants) and rebrand the generated **ADMX/ADML**, JSON and docs (`components/policy/tools/template_writers`).
- New Browser-x policies:
  - `PortableModeAllowed`, `PortableBlockedHelpUrl`
  - `TrackerBlockingMode`, `TrackerBlockingListUrl`
  - `HistoryRetentionDays`
  - `UpdateCheckEnabled`, `UpdateSource`, `AutoApplyUpdates`, `MinimumVersion`
  - `CrashReportUploadUrl`
- Approved extensions: Chromium's `ExtensionInstallAllowlist`/`ExtensionInstallForcelist`/`ExtensionSettings`. These work in portable mode too because policy is machine-level.
- `configs/policies/managed_defaults.json` lists recommended values for IT. Like midori's `distribution/policies.json`, they are **defaults only**. IT policy always overrides them.
- Host policy honored: system proxy, Windows cert store/enterprise roots, SmartScreen via Mark-of-the-Web, and Windows Firewall. Nothing is disabled.

### 6.7 CI/CD (mirrors midori `.github/workflows`)

| Workflow | Runner | Purpose |
|---|---|---|
| `ci.yml` | GitHub-hosted | Lint, `bx` unit tests, license check, `browserx.json` schema check |
| `patches.yml` | Self-hosted Windows (cached checkout) | Verify `patches/series` applies cleanly to the pinned tag |
| `build-windows.yml` | Self-hosted Windows, 32+ cores / 64 GB+ RAM / 500 GB SSD | `bx build win-x64` + Chromium test subsets + sandbox gate + network audit |
| `update-chromium.yml` | Scheduled daily | Detect new Chromium stable tag, open PR with bump and conflict report |
| `release.yml` | Self-hosted, protected environment | Package, sign (HSM/cloud signing, two-person approval), SBOM, provenance, checksums, publish |

---

## 7. Security, policy, update and licensing

### 7.1 Chromium security cadence and ownership

- **Owner:** a named Release Security Owner plus a backup (decision D7). This is the key staffing commitment for a fork.
- **Cadence:**
  - Track Chromium **stable** (Extended Stable is an option for enterprise, decision D13).
  - `update-chromium.yml` opens a PR within 24 h of a stable tag.
- **SLA:**
  - In-the-wild exploit fixes: shipped within **72 h** of the upstream release
  - Other security releases: within **7 days**
  - Milestones: within **14 days**
  - Never more than one milestone behind
- **Rebase discipline:** patch count and size are tracked in CI. Any patch touching security-sensitive code (sandbox, IPC, net, policy) needs two reviewers.
- **Unsupported builds:** releases more than one milestone behind are marked unsupported, and `MinimumVersion` lets IT enforce this.

### 7.2 Sandbox

- Chromium's sandbox, site isolation and process model stay at **upstream defaults**.
- No patch may weaken them. Code review checklist and AGENTS.md rule.
- CI release gate: launch the built browser and assert renderer integrity level/AppContainer via `chrome://sandbox` data. **A failure blocks the release.**
- The launcher and the policy defaults never pass `--no-sandbox`, `--disable-web-security`, `--disable-site-isolation-trials` or remote-debugging flags.
- `RemoteDebuggingAllowed` defaults to false in managed defaults.

### 7.3 Downloads, permissions, profiles

- **Downloads:** inherited Chromium download protection: Mark-of-the-Web, `DownloadRestrictions` policy, dangerous-file warnings. A Phase 3 test verifies `Zone.Identifier` on downloaded executables.
- **Permissions:** inherited per-origin model. Browser-x tightens defaults (e.g. notifications quieter) and surfaces them in the privacy panel.
- **Profiles:** inherited locking, versioning and encryption. Portable mode changes **only** the location (§6.2).

### 7.4 Dependency and license review

- **Chromium:** BSD-3 + `third_party/` (BSD, MIT, Apache-2.0, LGPL including FFmpeg, MPL, etc.). Generate `about:credits` (`tools/licenses/licenses.py`), ship it as `THIRD_PARTY_NOTICES`, and check it in `bx license-check`.
- **Our additions:** BSD-3 recommended (D5). `adblock-rust` (MPL-2.0) and filter lists (GPL/CC BY-SA) need legal review (D8).
- **No Google API keys** are embedded. Building with Google keys or connecting to Google services (sync, Safe Browsing, translate) has terms that a fork must accept separately.
- **No codecs/DRM** without licensing (D9).
- **No Midori/Astian trademarks or artwork.** Our own branding only.
- Dependabot/Renovate for `tools/bx` deps, and an OSV scan of the SBOM per release.

### 7.5 Crash reporting and telemetry

- **Telemetry off by default and removed where possible:**
  - UMA/metrics upload disabled at build level (`enable_reporting`-related args + patches), with the policy `MetricsReportingEnabled=false` forced in defaults
  - variations/field-trial fetching disabled
  - Google API keys absent
  - promotional and "what's new" fetches removed
- **Network audit test (Phase 4):** a fresh profile on an idle NTP is recorded for 10 minutes. The only allowed requests are the update check (policy-gated), the tracker-list update (policy-gated), and TLS/revocation traffic. Results go in `docs/network-requests.md`.
- **Crash reporting:** Crashpad writes locally, and **uploading is off**. Users can opt in through a dialog that explains dumps may contain page data, or IT can set `CrashReportUploadUrl` to an org-owned server.

### 7.6 Vulnerability reporting and release process

- **`SECURITY.md`:** GitHub private advisories, acknowledgement within 3 business days, 90-day disclosure. Upstream Chromium bugs are reported to crbug.com, following Chromium's security process.
- **Release steps:**
  1. Bump PR
  2. Green `patches` + `build-windows`, including the sandbox gate and network audit
  3. Tag
  4. Clean release build
  5. Sign (protected environment)
  6. SBOM, provenance and checksums
  7. Publish the portable self-extractor, zip, `SHA256SUMS` and update manifest
  8. Release notes linking the Chrome Releases post and CVEs
- **Rollback:** pull the update manifest and republish the previous build. Portable clients can roll back locally.

---

## 8. Phased implementation and acceptance criteria

```
P0 Foundations ─► P1 Unbranded build ─► P2 Branding & de-Googling ─┬─► P3 Privacy features ─┐
                                                                    └─► P4 Policy & portable ─┴─► P5 Packaging/update ─► P6 Release readiness
```

### Phase 0: Foundations

**Depends on:** decisions D1, D5, D7. Build hardware ordered, signing cert procurement started.

**Work:**
- Repo skeleton (§5.1), `AGENTS.md`, `LICENSE`, `SECURITY.md`, `browserx.json` + schema
- `tools/bx` with `download`/`import`/`export`/`build`/`run`
- `ci.yml`
- Self-hosted Windows runner set up
- `docs/building-windows.md`

**Acceptance:**
- `bx download && bx import && bx build win-x64` produces a **plain Chromium** (empty patch series) on the runner, from a clean machine, following the doc only.
- Build time and disk usage are recorded.

### Phase 1: Patch pipeline

**Depends on:** P0.

**Work:**
- `patches/series` mechanism and `bx export`
- `patches.yml`
- `bx update` with conflict reporting
- `update-chromium.yml`
- First trivial patch (version string)

**Acceptance:**
- A drill bumping one Chromium stable tag goes from PR to built binary within 24 h.
- A patch conflict produces a readable report naming the patch and hunk.

### Phase 2: Branding and de-Googling

**Depends on:** P1.

**Work:**
- `configs/branding/stable`
- Product name, user-data dir, policy registry path, and update URLs patched
- Telemetry, variations and API-key services disabled
- Remote search suggestions off
- `browserx://version` additions

**Acceptance:**
- No "Chromium"/"Google Chrome" strings in user-visible UI (string scan).
- Policies are read from `SOFTWARE\Policies\BrowserX`.
- The network audit shows no Google-service traffic on a fresh profile.
- The version page shows the commit and Chromium tag.

### Phase 3: Privacy features

**Depends on:** P2.

**Work:**
- Cookie, HTTPS and GPC defaults
- Content-blocking engine + list component
- Privacy/status panel
- New-tab WebUI
- Permission-default tuning

**Acceptance:**
- The tracker test page blocks the expected requests, with a per-site toggle.
- Third-party cookies are blocked by default.
- The GPC header is sent.
- The panel reflects real state (browser test).
- The NTP makes zero network requests.
- Downloaded `.exe` files have `Zone.Identifier`.

### Phase 4: Policy and portable mode

**Depends on:** P2 (can run alongside P3).

**Work:**
- New policy definitions
- Rebranded ADMX generation
- `PortableModeService` + user-data-dir patch + launcher
- `PortableModeAllowed` enforcement with dialog and event log
- Write-location audit
- Managed default policy sets

**Acceptance:**
- With `PortableModeAllowed=0`, zero files are written and no child process starts (test).
- The ADMX imports into Group Policy, and new and inherited policies apply (policy browser tests).
- A portable run writes only to `Data\` + documented temp paths.
- An extension allowlist works in portable mode.

### Phase 5: Packaging, signing, update

**Depends on:** P3, P4, signing cert.

**Work:**
- Portable self-extractor + zip (scripts exist; needs real build + cert)
- `sign.ps1`
- `SHA256SUMS` + signature, SBOM, provenance
- Update manifest, side-by-side updater, rollback, `MinimumVersion`
- `release.yml`

**Acceptance:**
- `signtool verify /pa` passes on every PE.
- Checksums and provenance verify following the public docs.
- The self-extractor asks for a folder, runs nothing, and the extracted program runs from a standard-user account; an Intune/ConfigMgr file-copy deployment works in a lab.
- Portable update and rollback work, and a tampered zip is rejected.
- `UpdateCheckEnabled=0` produces no update traffic.

### Phase 6: Release readiness

**Depends on:** P5.

**Work:**
- External security review of our patches, updater and portable code
- Accessibility check of the new UI (panel, NTP)
- IT admin guide, policy reference, `README-PORTABLE`
- A full security-release drill against the 72 h SLA

**Acceptance:**
- No open high or critical findings.
- The drill meets the SLA.
- An IT/security stakeholder signs off on the admin guide.
- The Release Security Owner approves 1.0.

---

## 9. Risks, unknowns, and decisions

### Risks

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Weekly rebase burden is underestimated, so security fixes ship late | Named owner and backup, small patches, `src/` overlay over in-place edits, automated bump PRs, SLA drills. Fallback to CEF (D1) |
| R2 | Build farm cost and complexity (Windows runners, ~hours per build) | Persistent incremental checkouts, our own RBE (BuildBuddy/EngFlow) once volume justifies it, release builds on dedicated machines |
| R3 | No Safe Browsing (needs an agreement with Google or Microsoft) | SmartScreen via MOTW meanwhile. D10 sets a timeline. Disclose in docs |
| R4 | Portable mode seen as a shadow-IT vector | Identical signed binaries, HKLM `PortableModeAllowed`, event log, visible data, no evasion features, IT verification docs |
| R5 | "Lightweight" expectation vs. Chromium's real size and RAM | Define lightweight as minimal UI + no background services. Publish measured numbers |
| R6 | Chrome Web Store terms and behaviour for non-Google Chromium builds | D12: allow CWS, allowlist-only via policy, or self-hosted extension catalog |
| R7 | Filter-list and `adblock-rust` licensing | Legal review in P3 (D8). Self-curated list as a fallback |
| R8 | Trademark confusion with Midori/Chrome | Own name and assets (D11). The string scan in P2 catches leftovers |
| R9 | Code-signing cert lead time | Procure in P0 |

### Decisions needed

| ID | Decision |
|---|---|
| D1 | ✅ **Decided:** full Chromium fork (ADR 0001). Still needed: funding the build farm and the rebase owner |
| D2 | Default search engines; remote suggestions on or off |
| D3 | Portable-mode default with no policy: allow or deny |
| D4 | Should organizations get a re-signed build with their own `portableModeDefault`/branding, or only configure through policy? |
| D5 | ✅ **Decided:** BSD-3-Clause (`LICENSE`) |
| D6 | Checksum signing (Sigstore vs minisign/GPG) |
| D7 | Release Security Owner + backup; SLA commitment |
| D8 | Tracker-blocking engine and list licensing |
| D9 | Proprietary codecs / Widevine |
| D10 | Safe Browsing provider and timeline |
| D11 | Product name, branding, and updater approach (own manifest vs Omaha 4) |
| D12 | Extension policy: Chrome Web Store access, allowlist-only, or none in MVP |
| D13 | Stable vs Extended Stable channel |

---

## 10. First implementation tasks and status

Confirmed by the project owner on 2026-11-13: **D1** (full Chromium fork), **portable-only distribution** (ADR 0002), and **D5** (BSD-3-Clause, applied in `LICENSE`; it can still be changed before the first external contribution).

Done in this repository (scaffold, no Chromium fetched or built):

1. ✅ Repo skeleton like midori-desktop:
   - `browserx.json` (+ `schemas/`) pins Chromium **158.0.8127.37** (Windows stable on 2026-11-13)
   - `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `.gitignore`
   - `docs/adr/0001-chromium-fork.md`, `docs/adr/0002-portable-only.md`
2. ✅ `bx` tool (`bx.py`, `tools/bx/`): `validate`, `doctor`, `download`, `import`, `reset`, `brand`, `build`, `run`, `package`, `export`, `patches`, `update`, `checksums`, `verify`, `license-check`. The repository-side logic is unit-tested (22 tests). The Chromium-driving commands (`download`, `build`) are untested until a Windows build machine exists.
3. ✅ `configs/`: layered GN args (common/windows/dev) with forbidden-arg checks, branding `BRANDING` + `map.txt`, recommended managed policies. `patches/series` is empty, with the planned first patches listed.
4. ✅ Portable launcher `launcher/` (C++17, CMake):
   - policy check, version selection, signature check (release), Data folder, switch filter
   - core unit tests pass on Linux, and the Windows executable cross-compiles with `-Werror`
   - Wine smoke test passed: allowed run, HKLM deny (exit 3, nothing written), HKCU unable to override HKLM, missing files (exit 5)
5. ✅ Packaging: `bx package` (portable folder, deterministic zip, `SHA256SUMS`), `packaging/windows/sign.ps1`, `make-sfx.ps1`, `README-PORTABLE.txt`.
6. ✅ CI:
   - `ci.yml` runs on GitHub-hosted runners: bx tests, launcher on Linux, and on Windows with MSVC
   - `patches.yml`, `build-windows.yml` and `release.yml` need a self-hosted runner and are manual
   - `update-chromium.yml` runs daily and opens a bump PR

Next:

1. Provision the self-hosted Windows build runner (§2.3) and start code-signing certificate procurement.
2. Decide D7 (security owner), D11 (final name/branding), D3 (portable default), D6 (checksum signing).
3. Phase 0 exit: `bx download && bx import && bx build win-x64` on the runner, then record time, disk and size. Confirm the GN args and `chrome.7z` staging path against 158.x.
4. First patches: `branding/product-name.patch` (exe name `browserx.exe`), `branding/user-data-dir.patch`, `branding/policy-registry-key.patch`.
5. Phase 4 patch `portable/portable-user-data-dir.patch` (policy re-check inside `browserx.exe`, §6.2), plus the `PortableModeAllowed` policy definition in the ADMX.
