# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Checks that our own source files carry the project license header."""

from __future__ import annotations

from pathlib import Path

HEADER_MARKER = "The Browser-x Authors"
CHECKED_DIRS = ("tools", "tests", "launcher", "src", "scripts", "packaging")
CHECKED_SUFFIXES = {".py", ".cc", ".h", ".ps1", ".gn", ".gni", ".ts", ".js", ".css", ".rc"}


def missing_headers(repo: Path) -> list[str]:
    missing = []
    for d in CHECKED_DIRS:
        base = repo / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in CHECKED_SUFFIXES:
                continue
            if "__pycache__" in p.parts:
                continue
            head = p.read_text(encoding="utf-8", errors="replace").splitlines()[:5]
            if not any(HEADER_MARKER in line for line in head):
                missing.append(p.relative_to(repo).as_posix())
    return missing
