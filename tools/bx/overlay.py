# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Copies the src/ overlay (new Browser-x files) into chromium/src.

The overlay may only ADD files. Changes to upstream Chromium files must go
through patches/ so they are reviewable and rebase cleanly. A manifest of
copied files is kept in chromium/src/.bx-overlay so re-imports can replace
our own files without ever overwriting upstream ones.
"""

from __future__ import annotations

import shutil
from pathlib import Path

OVERLAY_MANIFEST = ".bx-overlay"


class OverlayError(RuntimeError):
    pass


def _read_manifest(chromium_src: Path) -> set[str]:
    m = chromium_src / OVERLAY_MANIFEST
    if not m.is_file():
        return set()
    return {l.strip() for l in m.read_text(encoding="utf-8").splitlines() if l.strip()}


def overlay_files(overlay_dir: Path) -> list[str]:
    return sorted(
        p.relative_to(overlay_dir).as_posix()
        for p in overlay_dir.rglob("*")
        if p.is_file() and p.name != ".gitkeep"
    )


def apply_overlay(overlay_dir: Path, chromium_src: Path) -> list[str]:
    if not chromium_src.is_dir():
        raise OverlayError(f"{chromium_src}: Chromium checkout not found (run `bx download`)")
    previous = _read_manifest(chromium_src)
    files = overlay_files(overlay_dir)

    conflicts = [
        rel for rel in files if (chromium_src / rel).exists() and rel not in previous
    ]
    if conflicts:
        raise OverlayError(
            "src/ overlay would overwrite upstream Chromium files; use a patch instead:\n  "
            + "\n  ".join(conflicts)
        )

    # Remove files we copied last time that no longer exist in the overlay.
    for rel in sorted(previous - set(files)):
        target = chromium_src / rel
        if target.is_file():
            target.unlink()

    for rel in files:
        dst = chromium_src / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay_dir / rel, dst)

    (chromium_src / OVERLAY_MANIFEST).write_text(
        "".join(f"{rel}\n" for rel in files), encoding="utf-8"
    )
    return files
