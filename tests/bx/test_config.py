# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import copy
import unittest

from tests.bx.helpers import REPO, manifest_data

from bx.config import ConfigError, load_manifest, parse_manifest


class ConfigTest(unittest.TestCase):
    def test_repository_manifest_is_valid(self):
        m = load_manifest(REPO)
        self.assertEqual(m.app_id, "browserx")
        self.assertEqual(m.policy_registry_key, "SOFTWARE\\Policies\\BrowserX")
        self.assertIn("stable", m.brands)

    def _expect_error(self, mutate, fragment):
        data = copy.deepcopy(manifest_data())
        mutate(data)
        with self.assertRaises(ConfigError) as cm:
            parse_manifest(data, REPO)
        self.assertIn(fragment, str(cm.exception))

    def test_only_portable_distribution(self):
        self._expect_error(lambda d: d.update(distribution="msi"), "portable")

    def test_chromium_version_format(self):
        self._expect_error(lambda d: d["upstream"].update(version="158.0"), "upstream.version")

    def test_policy_key_must_be_policies_hive(self):
        self._expect_error(lambda d: d["policy"].update(registryKey="SOFTWARE\\BrowserX"), "Policies")

    def test_branding_dir_cannot_escape_repo(self):
        self._expect_error(
            lambda d: d["brands"]["stable"].update(brandingDir="../elsewhere"), "inside the repository"
        )

    def test_update_url_must_be_https(self):
        self._expect_error(lambda d: d["update"].update(manifestUrl="http://x"), "https")

    def test_unknown_target(self):
        self._expect_error(lambda d: d.update(targets=["linux-x64"]), "unsupported target")


if __name__ == "__main__":
    unittest.main()
