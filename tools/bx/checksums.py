# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""SHA256SUMS generation and verification (GNU coreutils format)."""

from __future__ import annotations

import hashlib
from pathlib import Path


class ChecksumError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sums(files: list[Path], base: Path, out: Path) -> None:
    lines = []
    for f in sorted(files, key=lambda p: p.relative_to(base).as_posix()):
        lines.append(f"{sha256_file(f)}  {f.relative_to(base).as_posix()}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_sums(sums_file: Path) -> list[str]:
    """Returns the list of verified relative paths; raises on any mismatch."""
    base = sums_file.parent
    verified = []
    for lineno, raw in enumerate(sums_file.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            digest, rel = raw.split("  ", 1)
        except ValueError:
            raise ChecksumError(f"{sums_file}:{lineno}: malformed line") from None
        target = (base / rel).resolve()
        if base.resolve() not in target.parents:
            raise ChecksumError(f"{sums_file}:{lineno}: path escapes directory: {rel}")
        if not target.is_file():
            raise ChecksumError(f"{rel}: missing")
        actual = sha256_file(target)
        if actual != digest.lower():
            raise ChecksumError(f"{rel}: checksum mismatch (expected {digest}, got {actual})")
        verified.append(rel)
    return verified
