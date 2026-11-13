# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Shared helpers: make tools/ importable and build throwaway repos."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))


def make_temp_repo(test) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="bx-test-"))
    test.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    for name in ("browserx.json", "LICENSE"):
        shutil.copy2(REPO / name, tmp / name)
    for d in ("configs", "patches", "packaging"):
        shutil.copytree(REPO / d, tmp / d)
    return tmp


def manifest_data() -> dict:
    return json.loads((REPO / "browserx.json").read_text(encoding="utf-8"))
