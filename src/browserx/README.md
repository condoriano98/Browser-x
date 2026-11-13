# src/browserx

New Browser-x code, copied into `chromium/src/browserx/` by `bx import`
(like midori-desktop's `src/midori/`). This overlay may only **add** files;
edits to upstream Chromium files go in `patches/`.

Planned components (see `docs/browser-implementation-plan.md` §5):

| Directory | Purpose |
|---|---|
| `portable/` | Portable-mode service: confirms the launcher's policy decision before profile creation |
| `privacy_panel/` | Toolbar privacy/status bubble |
| `content_blocking/` | Tracker blocking engine glue and list component |
| `webui/new_tab/` | Local-only new-tab page |

Code here follows Chromium style (`//styleguide`) and is built by GN.
