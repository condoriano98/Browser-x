# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Keeps the documented forbidden switches and the launcher in sync."""
import re
import unittest

from tests.bx.helpers import REPO


class LauncherDocSyncTest(unittest.TestCase):
    def test_forbidden_switches_documented(self):
        code = (REPO / "launcher" / "core" / "launch_plan.cc").read_text(encoding="utf-8")
        block = code.split("kForbiddenSwitches[] = {", 1)[1].split("};", 1)[0]
        switches = re.findall(r'L"([a-z0-9-]+)"', block)
        doc = (REPO / "docs" / "portable-mode.md").read_text(encoding="utf-8")
        for s in switches:
            self.assertIn(f"--{s}", doc, f"--{s} missing from docs/portable-mode.md")


if __name__ == "__main__":
    unittest.main()
