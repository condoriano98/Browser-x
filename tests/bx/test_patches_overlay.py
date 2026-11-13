# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import shutil
import subprocess
import unittest
from pathlib import Path

from tests.bx.helpers import make_temp_repo

from bx import overlay, patches


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@unittest.skipIf(shutil.which("git") is None, "git not available")
class PatchesOverlayTest(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_repo(self)
        self.src = self.repo / "chromium" / "src"
        self.src.mkdir(parents=True)
        git(self.src, "init", "-q")
        git(self.src, "config", "user.email", "bx@test.invalid")
        git(self.src, "config", "user.name", "bx test")
        (self.src / "chrome").mkdir()
        (self.src / "chrome" / "name.txt").write_text("Chromium\n")
        git(self.src, "add", ".")
        git(self.src, "commit", "-q", "-m", "base")

    def test_series_comments_and_validation(self):
        pdir = self.repo / "patches"
        self.assertEqual(patches.read_series(pdir), [])
        (pdir / "series").write_text("# c\nmissing.patch\n")
        with self.assertRaises(patches.PatchError):
            patches.read_series(pdir)
        (pdir / "series").write_text("../escape.patch\n")
        with self.assertRaises(patches.PatchError):
            patches.read_series(pdir)

    def test_export_then_apply_roundtrip(self):
        (self.src / "chrome" / "name.txt").write_text("Browser-x\n")
        out = patches.export_patch(self.src, self.repo / "patches", "branding/name.patch", ["chrome"])
        self.assertTrue(out.is_file())
        series = patches.read_series(self.repo / "patches")
        self.assertEqual([p.name for p in series], ["branding/name.patch"])
        self.assertEqual(patches.unlisted_patches(self.repo / "patches"), [])

        git(self.src, "checkout", "-q", "--", ".")
        patches.apply_series(series, self.src, check_only=True)
        self.assertEqual((self.src / "chrome" / "name.txt").read_text(), "Chromium\n")
        patches.apply_series(series, self.src)
        self.assertEqual((self.src / "chrome" / "name.txt").read_text(), "Browser-x\n")
        with self.assertRaises(patches.PatchError):
            patches.apply_series(series, self.src)  # already applied: must not apply twice

    def test_overlay_adds_files_and_refuses_upstream_overwrite(self):
        ov = self.repo / "src"
        (ov / "browserx" / "portable").mkdir(parents=True)
        (ov / "browserx" / "portable" / "a.cc").write_text("// a\n")
        copied = overlay.apply_overlay(ov, self.src)
        self.assertEqual(copied, ["browserx/portable/a.cc"])
        self.assertTrue((self.src / "browserx" / "portable" / "a.cc").is_file())

        # Re-import replaces our own files and drops removed ones.
        (ov / "browserx" / "portable" / "a.cc").unlink()
        (ov / "browserx" / "portable" / "b.cc").write_text("// b\n")
        overlay.apply_overlay(ov, self.src)
        self.assertFalse((self.src / "browserx" / "portable" / "a.cc").exists())
        self.assertTrue((self.src / "browserx" / "portable" / "b.cc").exists())

        (ov / "chrome").mkdir()
        (ov / "chrome" / "name.txt").write_text("overwrite\n")
        with self.assertRaises(overlay.OverlayError):
            overlay.apply_overlay(ov, self.src)
        self.assertEqual((self.src / "chrome" / "name.txt").read_text(), "Chromium\n")


if __name__ == "__main__":
    unittest.main()
