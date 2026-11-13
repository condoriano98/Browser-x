# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""The ordered Chromium patch series in patches/series.

Each non-comment line of patches/series names a .patch file relative to
patches/. Patches are applied in order with `git apply` inside chromium/src.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_PATCH_NAME = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)*\.patch$")


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class Patch:
    name: str
    path: Path


def read_series(patches_dir: Path) -> list[Patch]:
    series = patches_dir / "series"
    if not series.is_file():
        raise PatchError(f"{series}: not found")
    patches: list[Patch] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(series.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not _PATCH_NAME.match(line):
            raise PatchError(f"{series}:{lineno}: invalid patch name {line!r}")
        if line in seen:
            raise PatchError(f"{series}:{lineno}: duplicate patch {line!r}")
        seen.add(line)
        path = patches_dir / line
        if not path.is_file():
            raise PatchError(f"{series}:{lineno}: {line} does not exist")
        patches.append(Patch(name=line, path=path))
    return patches


def unlisted_patches(patches_dir: Path) -> list[str]:
    """Patch files on disk that are not referenced by the series file."""
    listed = {p.name for p in read_series(patches_dir)}
    on_disk = {
        p.relative_to(patches_dir).as_posix() for p in patches_dir.rglob("*.patch")
    }
    return sorted(on_disk - listed)


def _git(src: Path, *args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(src), *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def apply_series(patches: list[Patch], chromium_src: Path, check_only: bool = False) -> None:
    """Apply (or with check_only, dry-run) every patch. Stops at the first failure."""
    for patch in patches:
        data = patch.path.read_bytes()
        res = _git(chromium_src, "apply", "--check", "--whitespace=nowarn", "-", input_bytes=data)
        if res.returncode != 0:
            raise PatchError(
                f"patch {patch.name} does not apply to {chromium_src}:\n"
                + res.stderr.decode(errors="replace")
            )
        if check_only:
            continue
        res = _git(chromium_src, "apply", "--whitespace=nowarn", "-", input_bytes=data)
        if res.returncode != 0:
            raise PatchError(f"applying {patch.name} failed:\n" + res.stderr.decode(errors="replace"))


def export_patch(chromium_src: Path, patches_dir: Path, name: str, paths: list[str]) -> Path:
    """Write `git diff -- paths` from chromium/src to patches/<name> and list it in series."""
    if not _PATCH_NAME.match(name):
        raise PatchError(f"invalid patch name {name!r} (expected e.g. branding/product-name.patch)")
    if not paths:
        raise PatchError("export needs at least one path inside chromium/src")
    res = _git(chromium_src, "diff", "--no-color", "--no-ext-diff", "--", *paths)
    if res.returncode != 0:
        raise PatchError(res.stderr.decode(errors="replace"))
    if not res.stdout.strip():
        raise PatchError("no changes found for the given paths")
    out = patches_dir / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(res.stdout)

    series = patches_dir / "series"
    lines = series.read_text(encoding="utf-8").splitlines() if series.exists() else []
    if not any(l.split("#", 1)[0].strip() == name for l in lines):
        lines.append(name)
        series.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
