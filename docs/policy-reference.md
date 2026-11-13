# Policy reference

Browser-x reads policies from:

1. `HKLM\SOFTWARE\Policies\BrowserX` (machine, set via GPO/Intune with the Browser-x ADMX)
2. `HKCU\SOFTWARE\Policies\BrowserX` (user), only where a machine value is absent

Chromium's own policy names apply unchanged under that key once the branding patch
`branding/policy-registry-key.patch` lands (Phase 2). The ADMX/ADML templates are generated
from Chromium's policy templates with Browser-x branding.

## Browser-x policies

| Policy | Type | Default | Status | Meaning |
|---|---|---|---|---|
| `PortableModeAllowed` | DWORD | allowed (`browserx.json`) | **Enforced by the launcher** | `0` blocks the portable program before it writes any file. HKLM wins over HKCU. See `docs/portable-mode.md` |
| `PortableBlockedHelpUrl` | String (HKLM) | none | **Enforced by the launcher** | `https://` page offered in the "not allowed" dialog |
| `TrackerBlockingMode` | String | `standard` | Planned (Phase 3) | `off`, `standard`, `strict` |
| `TrackerBlockingListUrl` | String | built-in | Planned (Phase 3) | Internal mirror for filter lists |
| `HistoryRetentionDays` | DWORD | unlimited | Planned (Phase 4) | Delete history older than N days |
| `UpdateCheckEnabled` | DWORD | 1 | Planned (Phase 5) | `0` disables update checks |
| `UpdateSource` | String | release host | Planned (Phase 5) | Internal update mirror (https) |
| `AutoApplyUpdates` | DWORD | 0 | Planned (Phase 5) | `1` applies updates without asking |
| `MinimumVersion` | String | none | Planned (Phase 5) | Older versions refuse to start |
| `CrashReportUploadUrl` | String | none (no upload) | Planned (Phase 6) | Organization-owned crash server |

## Recommended Chromium policies

`configs/policies/managed_defaults.json` lists recommended values: metrics off, sign-in and
sync off, search suggestions off, third-party cookies blocked, remote debugging off, and
extensions blocked except an IT allowlist. These are recommendations for IT. Browser-x
never overrides policy that IT sets.
