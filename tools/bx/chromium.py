# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Chromium checkout, branding, GN/ninja build and upstream version checks.

These commands drive depot_tools (gclient, gn, autoninja). They need a
Windows build machine for real builds; see docs/building-windows.md.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .config import Brand, Manifest

CHROMIUM_URL = "https://chromium.googlesource.com/chromium/src.git"
CHROMIUMDASH = (
    "https://chromiumdash.appspot.com/fetch_releases?channel={channel}&platform=Windows&num=1"
)


class ChromiumError(RuntimeError):
    pass


def chromium_dir(repo: Path) -> Path:
    override = os.environ.get("BX_CHROMIUM_DIR")
    return Path(override).resolve() if override else repo / "chromium"


def src_dir(repo: Path) -> Path:
    return chromium_dir(repo) / "src"


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    exe = shutil.which(cmd[0])
    if exe is None:
        raise ChromiumError(
            f"{cmd[0]!r} not found on PATH. Install depot_tools and add it to PATH "
            "(see docs/building-windows.md)."
        )
    res = subprocess.run([exe, *cmd[1:]], cwd=cwd, check=False)
    if res.returncode != 0:
        raise ChromiumError(f"command failed ({res.returncode}): {' '.join(cmd)}")


def _git_out(src: Path, *args: str) -> str:
    res = subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise ChromiumError(res.stderr.strip())
    return res.stdout.strip()


def gclient_file(target_os: str = "win") -> str:
    return (
        "solutions = [{\n"
        '  "name": "src",\n'
        f'  "url": "{CHROMIUM_URL}",\n'
        '  "managed": False,\n'
        '  "custom_deps": {},\n'
        '  "custom_vars": {"checkout_pgo_profiles": False},\n'
        "}]\n"
        f'target_os = ["{target_os}"]\n'
    )


def is_dirty(src: Path) -> bool:
    return bool(_git_out(src, "status", "--porcelain", "--untracked-files=no"))


def download(manifest: Manifest, repo: Path) -> None:
    """Fetch Chromium at the pinned tag (shallow) and sync dependencies."""
    top = chromium_dir(repo)
    src = top / "src"
    tag = manifest.chromium_version
    top.mkdir(parents=True, exist_ok=True)
    gclient = top / ".gclient"
    if not gclient.exists():
        gclient.write_text(gclient_file(), encoding="utf-8")

    if not (src / ".git").exists():
        src.mkdir(parents=True, exist_ok=True)
        _run(["git", "init", "-q", str(src)])
        _run(["git", "-C", str(src), "remote", "add", "origin", CHROMIUM_URL])
    elif is_dirty(src):
        raise ChromiumError(
            "chromium/src has local changes (imported patches?). Run `bx reset` first."
        )

    _run(["git", "-C", str(src), "fetch", "--depth=1", "origin", f"refs/tags/{tag}:refs/tags/{tag}"])
    _run(["git", "-C", str(src), "checkout", "-q", "--force", f"tags/{tag}"])
    _run(["gclient", "sync", "-D", "--force", "--reset", "--no-history", "--nohooks"], cwd=top)
    _run(["gclient", "runhooks"], cwd=top)


def reset(manifest: Manifest, repo: Path) -> None:
    """Return chromium/src to the pristine pinned tag (keeps out/, which is ignored)."""
    src = src_dir(repo)
    if not (src / ".git").exists():
        raise ChromiumError(f"{src}: no checkout (run `bx download`)")
    _run(["git", "-C", str(src), "reset", "-q", "--hard", f"tags/{manifest.chromium_version}"])
    _run(["git", "-C", str(src), "clean", "-q", "-fd"])


def current_tag(repo: Path) -> str | None:
    src = src_dir(repo)
    if not (src / ".git").exists():
        return None
    try:
        return _git_out(src, "describe", "--tags", "--exact-match", "HEAD")
    except ChromiumError:
        return None


# Branding: each line of configs/branding/<brand>/map.txt is
#   <file in branding dir> => <path inside chromium/src>
def read_brand_map(brand: Brand) -> list[tuple[Path, str]]:
    map_file = brand.branding_dir / "map.txt"
    if not map_file.is_file():
        raise ChromiumError(f"{map_file}: not found")
    entries = []
    for lineno, raw in enumerate(map_file.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "=>" not in line:
            raise ChromiumError(f"{map_file}:{lineno}: expected '<file> => <chromium path>'")
        left, right = (s.strip() for s in line.split("=>", 1))
        source = (brand.branding_dir / left).resolve()
        if brand.branding_dir.resolve() not in source.parents:
            raise ChromiumError(f"{map_file}:{lineno}: source escapes branding dir")
        if right.startswith(("/", "\\")) or ".." in Path(right).parts:
            raise ChromiumError(f"{map_file}:{lineno}: destination must be relative inside src/")
        entries.append((source, right))
    return entries


def apply_brand(brand: Brand, src: Path) -> list[str]:
    copied = []
    for source, dest in read_brand_map(brand):
        if not source.is_file():
            raise ChromiumError(f"branding file missing: {source}")
        target = src / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(dest)
    return copied


def gn_gen_and_build(src: Path, out_name: str, args_text: str, targets: list[str]) -> Path:
    out = src / "out" / out_name
    out.mkdir(parents=True, exist_ok=True)
    args_file = out / "args.gn"
    if not args_file.exists() or args_file.read_text(encoding="utf-8") != args_text:
        args_file.write_text(args_text, encoding="utf-8")
    _run(["gn", "gen", str(out)], cwd=src)
    _run(["autoninja", "-C", str(out), *targets], cwd=src)
    return out


def latest_upstream(channel: str = "stable") -> str:
    url = CHROMIUMDASH.format(channel="Extended" if channel == "extended" else "Stable")
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 (fixed https URL)
        data = json.load(resp)
    if not data or "version" not in data[0]:
        raise ChromiumError("unexpected response from chromiumdash")
    return data[0]["version"]


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def platform_supported_for_build() -> bool:
    return sys.platform == "win32"
