# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import zipfile

from tests.bx.helpers import make_temp_repo

from bx.checksums import ChecksumError, verify_sums
from bx.chromium import read_brand_map
from bx.config import load_manifest
from bx.package import PackageError, package


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.repo = make_temp_repo(self)
        self.m = load_manifest(self.repo)
        self.staging = self.repo / "staging"
        (self.staging / "158.0.8127.37").mkdir(parents=True)
        (self.staging / "browserx.exe").write_bytes(b"MZ fake browser")
        (self.staging / "158.0.8127.37" / "chrome.dll").write_bytes(b"MZ fake dll")
        self.launcher = self.repo / "BrowserX.exe"
        self.launcher.write_bytes(b"MZ fake launcher")

    def test_portable_layout_zip_and_checksums(self):
        zip_path, sums = package(self.m, "win-x64", self.staging, self.launcher, self.repo / "dist")
        root = self.repo / "dist" / "BrowserX"
        self.assertTrue((root / "BrowserX.exe").is_file())
        self.assertEqual((root / "App" / "current.txt").read_text().strip(), "0.1.0")
        self.assertTrue((root / "App" / "0.1.0" / "browserx.exe").is_file())
        self.assertTrue((root / "README-PORTABLE.txt").is_file())
        self.assertFalse((root / "Data").exists())
        self.assertEqual(zip_path.name, "BrowserX-0.1.0-win-x64-portable.zip")
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        self.assertIn("BrowserX/BrowserX.exe", names)
        self.assertEqual(names, sorted(names))
        self.assertEqual(verify_sums(sums), [zip_path.name])

    def test_zip_is_deterministic(self):
        a, _ = package(self.m, "win-x64", self.staging, self.launcher, self.repo / "d1")
        b, _ = package(self.m, "win-x64", self.staging, self.launcher, self.repo / "d2")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_tampered_zip_detected(self):
        zip_path, sums = package(self.m, "win-x64", self.staging, self.launcher, self.repo / "dist")
        zip_path.write_bytes(zip_path.read_bytes() + b"x")
        with self.assertRaises(ChecksumError):
            verify_sums(sums)

    def test_user_data_never_shipped(self):
        (self.staging / "Data").mkdir()
        with self.assertRaises(PackageError):
            package(self.m, "win-x64", self.staging, self.launcher, self.repo / "dist")

    def test_profile_anywhere_in_staging_rejected(self):
        nested = self.staging / "158.0.8127.37" / "leftover"
        nested.mkdir()
        (nested / "Local State").write_text("{}")
        with self.assertRaises(PackageError):
            package(self.m, "win-x64", self.staging, self.launcher, self.repo / "dist")

    def test_requires_browser_exe(self):
        (self.staging / "browserx.exe").unlink()
        with self.assertRaises(PackageError):
            package(self.m, "win-x64", self.staging, self.launcher, self.repo / "dist")

    def test_brand_maps_are_valid(self):
        for brand in self.m.brands.values():
            entries = read_brand_map(brand)
            self.assertTrue(entries)
            for source, _ in entries:
                self.assertTrue(source.is_file(), source)


if __name__ == "__main__":
    unittest.main()
