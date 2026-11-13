# Copyright 2026 The Browser-x Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest

from tests.bx.helpers import REPO, make_temp_repo

from bx import gnargs


class GnArgsTest(unittest.TestCase):
    def test_layers_merge_with_dev_override(self):
        release = gnargs.merge_layers(gnargs.layers_for(REPO, "windows", dev=False))
        dev = gnargs.merge_layers(gnargs.layers_for(REPO, "windows", dev=True))
        self.assertEqual(release["is_official_build"], "true")
        self.assertEqual(dev["is_official_build"], "false")
        self.assertEqual(release["target_os"], '"win"')
        self.assertEqual(release["use_official_google_api_keys"], "false")

    def test_forbidden_args_rejected(self):
        repo = make_temp_repo(self)
        with (repo / "configs" / "windows" / "args.gn").open("a") as f:
            f.write("proprietary_codecs = true\n")
        with self.assertRaises(gnargs.GnArgsError):
            gnargs.merge_layers(gnargs.layers_for(repo, "windows", dev=False))

    def test_unsupported_syntax_rejected(self):
        repo = make_temp_repo(self)
        (repo / "configs" / "dev" / "args.gn").write_text("if (x) { y = 1 }\n")
        with self.assertRaises(gnargs.GnArgsError):
            gnargs.merge_layers(gnargs.layers_for(repo, "windows", dev=True))

    def test_render_is_sorted(self):
        text = gnargs.render({"b": "1", "a": "2"}, "hdr")
        self.assertLess(text.index("a = 2"), text.index("b = 1"))


if __name__ == "__main__":
    unittest.main()
