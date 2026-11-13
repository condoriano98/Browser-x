#!/usr/bin/env python3
# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Entry point: `python bx.py <command>` (see tools/bx/cli.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

from bx.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
