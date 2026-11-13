# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Loads and validates browserx.json (the product manifest)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_NAME = "browserx.json"

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_CHROMIUM_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")
_TARGETS = {"win-x64", "win-arm64"}


class ConfigError(ValueError):
    """Raised when browserx.json is missing or invalid."""


@dataclass(frozen=True)
class Brand:
    key: str
    full_name: str
    short_name: str
    branding_dir: Path


@dataclass(frozen=True)
class Manifest:
    root: Path
    name: str
    vendor: str
    app_id: str
    binary_name: str
    display_version: str
    chromium_version: str
    channel: str
    targets: tuple[str, ...]
    brands: dict[str, Brand]
    policy_registry_key: str
    portable_mode_default: str
    update_manifest_url: str | None
    license: str
    raw: dict[str, Any]

    def brand(self, key: str) -> Brand:
        try:
            return self.brands[key]
        except KeyError:
            raise ConfigError(
                f"unknown brand {key!r}; known: {', '.join(sorted(self.brands))}"
            ) from None


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ConfigError(f"{where}: missing required key {key!r}")
    return data[key]


def _str(data: dict[str, Any], key: str, where: str, pattern: re.Pattern[str] | None = None) -> str:
    value = _require(data, key, where)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where}.{key}: must be a non-empty string")
    if pattern is not None and not pattern.match(value):
        raise ConfigError(f"{where}.{key}: {value!r} does not match {pattern.pattern}")
    return value


def parse_manifest(data: Any, root: Path) -> Manifest:
    if not isinstance(data, dict):
        raise ConfigError("browserx.json: top level must be an object")

    w = "browserx.json"
    distribution = _str(data, "distribution", w)
    if distribution != "portable":
        raise ConfigError(f"{w}.distribution: only 'portable' is supported (got {distribution!r})")

    upstream = _require(data, "upstream", w)
    if not isinstance(upstream, dict):
        raise ConfigError(f"{w}.upstream: must be an object")
    if _str(upstream, "product", f"{w}.upstream") != "chromium":
        raise ConfigError(f"{w}.upstream.product: must be 'chromium'")
    chromium_version = _str(upstream, "version", f"{w}.upstream", _CHROMIUM_VERSION)
    channel = _str(upstream, "channel", f"{w}.upstream")
    if channel not in ("stable", "extended"):
        raise ConfigError(f"{w}.upstream.channel: must be 'stable' or 'extended'")

    targets = _require(data, "targets", w)
    if not isinstance(targets, list) or not targets:
        raise ConfigError(f"{w}.targets: must be a non-empty list")
    for t in targets:
        if t not in _TARGETS:
            raise ConfigError(f"{w}.targets: unsupported target {t!r}")

    brands_raw = _require(data, "brands", w)
    if not isinstance(brands_raw, dict) or not brands_raw:
        raise ConfigError(f"{w}.brands: must be a non-empty object")
    brands: dict[str, Brand] = {}
    for key, b in brands_raw.items():
        where = f"{w}.brands.{key}"
        if not isinstance(b, dict):
            raise ConfigError(f"{where}: must be an object")
        rel = _str(b, "brandingDir", where)
        branding_dir = (root / rel).resolve()
        if root.resolve() not in branding_dir.parents:
            raise ConfigError(f"{where}.brandingDir: must stay inside the repository")
        brands[key] = Brand(
            key=key,
            full_name=_str(b, "brandFullName", where),
            short_name=_str(b, "brandShortName", where),
            branding_dir=branding_dir,
        )

    policy = _require(data, "policy", w)
    if not isinstance(policy, dict):
        raise ConfigError(f"{w}.policy: must be an object")
    registry_key = _str(policy, "registryKey", f"{w}.policy")
    if not registry_key.startswith("SOFTWARE\\Policies\\"):
        raise ConfigError(f"{w}.policy.registryKey: must be under SOFTWARE\\Policies\\")
    portable_default = _str(policy, "portableModeDefault", f"{w}.policy")
    if portable_default not in ("allow", "deny"):
        raise ConfigError(f"{w}.policy.portableModeDefault: must be 'allow' or 'deny'")

    update = _require(data, "update", w)
    if not isinstance(update, dict):
        raise ConfigError(f"{w}.update: must be an object")
    manifest_url = update.get("manifestUrl")
    if manifest_url is not None and (
        not isinstance(manifest_url, str) or not manifest_url.startswith("https://")
    ):
        raise ConfigError(f"{w}.update.manifestUrl: must be null or an https:// URL")

    return Manifest(
        root=root,
        name=_str(data, "name", w),
        vendor=_str(data, "vendor", w),
        app_id=_str(data, "appId", w, _IDENT),
        binary_name=_str(data, "binaryName", w, _IDENT),
        display_version=_str(data, "displayVersion", w, _SEMVER),
        chromium_version=chromium_version,
        channel=channel,
        targets=tuple(targets),
        brands=brands,
        policy_registry_key=registry_key,
        portable_mode_default=portable_default,
        update_manifest_url=manifest_url,
        license=_str(data, "license", w),
        raw=data,
    )


def load_manifest(root: Path) -> Manifest:
    path = root / MANIFEST_NAME
    if not path.is_file():
        raise ConfigError(f"{path}: not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: invalid JSON: {e}") from e
    return parse_manifest(data, root)


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / MANIFEST_NAME).is_file():
            return candidate
    raise ConfigError(f"could not find {MANIFEST_NAME} in {here} or any parent directory")
