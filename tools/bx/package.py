# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Assembles the single portable program.

Layout produced (see docs/portable-mode.md):

    BrowserX/
      BrowserX.exe            launcher: the one program users run
      App/current.txt         active version, written only by bx/updater
      App/<version>/          Chromium application files (browserx.exe, DLLs, ...)
      README-PORTABLE.txt
      LICENSE, THIRD_PARTY_NOTICES.html
      (Data/ is created visibly by the launcher on first run)

and a deterministic zip of that folder plus SHA256SUMS. Signing and the
self-extracting .exe wrapper are separate steps (packaging/windows/).
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from .checksums import write_sums
from .config import Manifest

_FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class PackageError(RuntimeError):
    pass


def portable_dir_name(manifest: Manifest) -> str:
    return "BrowserX"


def artifact_basename(manifest: Manifest, target: str) -> str:
    return f"BrowserX-{manifest.display_version}-{target}-portable"


def assemble(
    manifest: Manifest,
    target: str,
    staging: Path,
    launcher: Path,
    out_dir: Path,
    notices: Path | None = None,
) -> Path:
    """Builds out_dir/BrowserX/. `staging` is the Chromium application dir."""
    if target not in manifest.targets:
        raise PackageError(f"target {target!r} is not listed in browserx.json targets")
    main_exe = staging / f"{manifest.binary_name}.exe"
    if not main_exe.is_file():
        raise PackageError(f"{main_exe}: not found; is {staging} a Chromium application dir?")
    if not launcher.is_file():
        raise PackageError(f"{launcher}: launcher not found (build launcher/ first)")

    # A Chromium profile root always contains "Local State".
    profile_dirs = [p for p in (staging / "Data", staging / "User Data") if p.exists()]
    profile_dirs += [p.parent for p in staging.rglob("Local State")]
    if profile_dirs:
        raise PackageError(
            "staging contains user-data folders, which are never shipped: "
            + ", ".join(str(p) for p in profile_dirs)
        )

    root = out_dir / portable_dir_name(manifest)
    if root.exists():
        shutil.rmtree(root)
    app = root / "App" / manifest.display_version
    shutil.copytree(staging, app)
    (root / "App" / "current.txt").write_text(manifest.display_version + "\n", encoding="ascii")
    shutil.copy2(launcher, root / "BrowserX.exe")

    repo = manifest.root
    shutil.copy2(repo / "packaging" / "windows" / "README-PORTABLE.txt", root / "README-PORTABLE.txt")
    shutil.copy2(repo / "LICENSE", root / "LICENSE")
    if notices is not None:
        shutil.copy2(notices, root / "THIRD_PARTY_NOTICES.html")
    return root


def make_zip(root: Path, zip_path: Path) -> Path:
    """Deterministic zip: sorted entries, fixed timestamps, folder name as prefix."""
    files = sorted(p for p in root.rglob("*") if p.is_file())
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in files:
            arc = (Path(root.name) / f.relative_to(root)).as_posix()
            info = zipfile.ZipInfo(arc, date_time=_FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())
    return zip_path


def package(
    manifest: Manifest,
    target: str,
    staging: Path,
    launcher: Path,
    out_dir: Path,
    notices: Path | None = None,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    root = assemble(manifest, target, staging, launcher, out_dir, notices)
    zip_path = make_zip(root, out_dir / f"{artifact_basename(manifest, target)}.zip")
    sums = out_dir / "SHA256SUMS"
    write_sums([zip_path], out_dir, sums)
    return zip_path, sums
