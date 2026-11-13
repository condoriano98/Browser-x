# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""`bx`: the Browser-x fork tool (the equivalent of midori-desktop's Amelia).

    python bx.py validate            check browserx.json, patches/series, configs
    python bx.py doctor              report build-machine readiness (installs nothing)
    python bx.py download            fetch Chromium at the pinned tag into chromium/src
    python bx.py import [--brand B]  copy src/ overlay, apply patches, apply branding
    python bx.py reset               restore chromium/src to the pristine tag
    python bx.py build win-x64       gn gen + autoninja (add --dev for a fast dev build)
    python bx.py run                 start the built browser with a throwaway profile
    python bx.py package win-x64 ... assemble the portable program + zip + SHA256SUMS
    python bx.py export NAME PATHS   turn edits in chromium/src into patches/NAME
    python bx.py update [--check|--to VERSION]
    python bx.py checksums FILES...  write SHA256SUMS for release files
    python bx.py verify SHA256SUMS
    python bx.py license-check
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import chromium, gnargs, licensecheck, overlay, patches
from .checksums import ChecksumError, verify_sums, write_sums
from .config import ConfigError, find_repo_root, load_manifest, parse_manifest
from .package import PackageError, package

_CPU = {"win-x64": "x64", "win-arm64": "arm64"}

_ERRORS = (
    ConfigError,
    patches.PatchError,
    overlay.OverlayError,
    gnargs.GnArgsError,
    chromium.ChromiumError,
    PackageError,
    ChecksumError,
)


def _out_name(target: str, dev: bool) -> str:
    return f"{'Dev' if dev else 'Release'}-{_CPU[target]}"


def cmd_validate(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    series = patches.read_series(repo / "patches")
    stray = patches.unlisted_patches(repo / "patches")
    for dev in (False, True):
        gnargs.merge_layers(gnargs.layers_for(repo, "windows", dev))
    for brand in m.brands.values():
        chromium.read_brand_map(brand)
    missing = licensecheck.missing_headers(repo)
    print(f"{m.name} {m.display_version} on Chromium {m.chromium_version} ({m.channel})")
    print(f"targets: {', '.join(m.targets)}; brands: {', '.join(sorted(m.brands))}")
    print(f"patches in series: {len(series)}")
    if stray:
        print("error: patch files not listed in patches/series:\n  " + "\n  ".join(stray))
    if missing:
        print("error: files missing the license header:\n  " + "\n  ".join(missing))
    return 1 if (stray or missing) else 0


def cmd_doctor(repo: Path, args: argparse.Namespace) -> int:
    ok = True

    def report(good: bool, msg: str) -> None:
        nonlocal ok
        ok = ok and good
        print(("ok    " if good else "MISSING ") + msg)

    report(sys.version_info >= (3, 11), f"Python >= 3.11 (have {sys.version.split()[0]})")
    report(shutil.which("git") is not None, "git on PATH")
    for tool in ("gclient", "gn", "autoninja"):
        report(shutil.which(tool) is not None, f"{tool} on PATH (depot_tools)")
    report(chromium.platform_supported_for_build(), "running on Windows (required for builds)")
    top = chromium.chromium_dir(repo)
    probe = top if top.exists() else repo
    free_gb = shutil.disk_usage(probe).free / 1e9
    report(free_gb >= 250, f"free disk at {probe}: {free_gb:.0f} GB (>= 250 GB recommended)")
    if sys.platform == "win32":
        vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
        report(vswhere.exists(), "Visual Studio installer (vswhere.exe) present")
    print("\nbx installs nothing. Follow docs/building-windows.md for anything missing.")
    return 0 if ok else 1


def cmd_download(repo: Path, args: argparse.Namespace) -> int:
    chromium.download(load_manifest(repo), repo)
    return 0


def cmd_reset(repo: Path, args: argparse.Namespace) -> int:
    chromium.reset(load_manifest(repo), repo)
    return 0


def cmd_import(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    src = chromium.src_dir(repo)
    if chromium.current_tag(repo) != m.chromium_version:
        raise chromium.ChromiumError(
            f"chromium/src is not at tag {m.chromium_version}; run `bx download`"
        )
    if chromium.is_dirty(src):
        if not args.reset:
            raise chromium.ChromiumError(
                "chromium/src has local changes; re-run with --reset to discard them"
            )
        chromium.reset(m, repo)
    copied = overlay.apply_overlay(repo / "src", src)
    series = patches.read_series(repo / "patches")
    patches.apply_series(series, src)
    branded = chromium.apply_brand(m.brand(args.brand), src)
    print(f"overlay files: {len(copied)}, patches: {len(series)}, branding files: {len(branded)}")
    return 0


def cmd_brand(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    for dest in chromium.apply_brand(m.brand(args.brand), chromium.src_dir(repo)):
        print(dest)
    return 0


def cmd_build(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    if args.target not in m.targets:
        raise ConfigError(f"target {args.target!r} is not listed in browserx.json")
    if not chromium.platform_supported_for_build():
        raise chromium.ChromiumError("Chromium for Windows is built on Windows build machines")
    merged = gnargs.merge_layers(gnargs.layers_for(repo, "windows", args.dev))
    merged["target_cpu"] = f'"{_CPU[args.target]}"'
    text = gnargs.render(merged, f"{m.name} {m.display_version} / Chromium {m.chromium_version}")
    out = chromium.gn_gen_and_build(
        chromium.src_dir(repo), _out_name(args.target, args.dev), text, args.ninja_targets
    )
    print(f"built: {out}")
    return 0


def cmd_run(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    out = chromium.src_dir(repo) / "out" / _out_name(args.target, args.dev)
    for name in (f"{m.binary_name}.exe", "chrome.exe"):
        exe = out / name
        if exe.is_file():
            break
    else:
        raise chromium.ChromiumError(f"no browser executable in {out}; run `bx build` first")
    with tempfile.TemporaryDirectory(prefix="bx-profile-") as profile:
        return subprocess.run([str(exe), f"--user-data-dir={profile}"], check=False).returncode


def cmd_package(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    zip_path, sums = package(
        m,
        args.target,
        staging=Path(args.staging).resolve(),
        launcher=Path(args.launcher).resolve(),
        out_dir=(repo / args.out).resolve(),
        notices=Path(args.notices).resolve() if args.notices else None,
    )
    print(f"portable zip: {zip_path}\nchecksums:    {sums}")
    print("next: sign binaries and build the self-extracting .exe (packaging/windows/README.md)")
    return 0


def cmd_export(repo: Path, args: argparse.Namespace) -> int:
    out = patches.export_patch(chromium.src_dir(repo), repo / "patches", args.name, args.paths)
    print(f"wrote {out.relative_to(repo)} and listed it in patches/series")
    return 0


def cmd_patches(repo: Path, args: argparse.Namespace) -> int:
    series = patches.read_series(repo / "patches")
    patches.apply_series(series, chromium.src_dir(repo), check_only=True)
    print(f"all {len(series)} patches apply cleanly")
    return 0


def cmd_update(repo: Path, args: argparse.Namespace) -> int:
    m = load_manifest(repo)
    target = args.to or chromium.latest_upstream(m.channel)
    print(f"pinned: {m.chromium_version}  upstream {m.channel}: {target}")
    if args.check or target == m.chromium_version:
        return 0
    if chromium.version_tuple(target) < chromium.version_tuple(m.chromium_version) and not args.allow_downgrade:
        raise ConfigError(f"refusing to downgrade to {target} (use --allow-downgrade)")
    data = json.loads((repo / "browserx.json").read_text(encoding="utf-8"))
    data["upstream"]["version"] = target
    parse_manifest(data, repo)  # validate before writing
    (repo / "browserx.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"browserx.json now pins Chromium {target}. Next: bx download && bx import && bx build")
    return 0


def cmd_verify(repo: Path, args: argparse.Namespace) -> int:
    for rel in verify_sums(Path(args.sums).resolve()):
        print(f"OK  {rel}")
    return 0


def cmd_checksums(repo: Path, args: argparse.Namespace) -> int:
    files = [Path(f).resolve() for f in args.files]
    if not files:
        raise ChecksumError("no files given")
    base = files[0].parent
    if any(f.parent != base or not f.is_file() for f in files):
        raise ChecksumError("all files must exist and be in the same directory")
    write_sums(files, base, base / "SHA256SUMS")
    print(f"wrote {base / 'SHA256SUMS'} ({len(files)} files)")
    return 0


def cmd_license_check(repo: Path, args: argparse.Namespace) -> int:
    missing = licensecheck.missing_headers(repo)
    for p in missing:
        print(f"missing license header: {p}")
    return 1 if missing else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bx", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("validate").set_defaults(func=cmd_validate)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("download").set_defaults(func=cmd_download)
    sub.add_parser("reset").set_defaults(func=cmd_reset)

    s = sub.add_parser("import")
    s.add_argument("--brand", default="stable")
    s.add_argument("--reset", action="store_true", help="discard local changes in chromium/src first")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("brand")
    s.add_argument("brand", nargs="?", default="stable")
    s.set_defaults(func=cmd_brand)

    s = sub.add_parser("build")
    s.add_argument("target", choices=sorted(_CPU))
    s.add_argument("--dev", action="store_true", help="component, non-official build for development")
    s.add_argument("--ninja-targets", nargs="+", default=["chrome", "mini_installer"])
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("run")
    s.add_argument("--target", default="win-x64", choices=sorted(_CPU))
    s.add_argument("--dev", action="store_true")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("package")
    s.add_argument("target", choices=sorted(_CPU))
    s.add_argument("--staging", required=True, help="Chromium application dir (e.g. extracted Chrome-bin)")
    s.add_argument("--launcher", required=True, help="built BrowserX.exe launcher")
    s.add_argument("--notices", help="THIRD_PARTY_NOTICES / about:credits HTML")
    s.add_argument("--out", default="dist")
    s.set_defaults(func=cmd_package)

    s = sub.add_parser("export")
    s.add_argument("name", help="e.g. branding/product-name.patch")
    s.add_argument("paths", nargs="+", help="paths inside chromium/src")
    s.set_defaults(func=cmd_export)

    sub.add_parser("patches", help="dry-run the patch series against chromium/src").set_defaults(func=cmd_patches)

    s = sub.add_parser("update")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--to", metavar="VERSION")
    s.add_argument("--allow-downgrade", action="store_true")
    s.set_defaults(func=cmd_update)

    s = sub.add_parser("verify")
    s.add_argument("sums")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("checksums", help="write SHA256SUMS for release files")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=cmd_checksums)

    sub.add_parser("license-check").set_defaults(func=cmd_license_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = find_repo_root()
        return args.func(repo, args)
    except _ERRORS as e:
        print(f"bx: error: {e}", file=sys.stderr)
        return 2
