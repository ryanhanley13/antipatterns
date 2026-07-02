"""Tests for tools/export.py - platform-wrapper generation from the source.

Run from the repo root:  python -m unittest discover -s tests
Stdlib only.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import export  # noqa: E402
from catalog import parse_catalog  # noqa: E402

CATALOG_PATH = REPO / "ANTIPATTERNS.md"


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = parse_catalog(CATALOG_PATH)

    def test_chatgpt_under_char_limit(self):
        for variant in ("ryan", "community"):
            text = export.build_chatgpt(variant, self.cat)
            self.assertLess(
                len(text), export.CHATGPT_CHAR_LIMIT, f"{variant} over the limit"
            )

    def test_chatgpt_has_tier1_core(self):
        text = export.build_chatgpt("ryan", self.cat)
        low = text.lower()
        self.assertIn("delve", low)           # Tier 1 word
        self.assertIn("let's dive in", low)   # Tier 1 phrase
        self.assertIn("removal test", low)    # the procedure
        self.assertIn("voice drift check", low)

    def test_community_genericizes_author(self):
        full = export.build_full("community")
        self.assertNotIn("Ryan", full)
        self.assertIn("you", full)

    def test_ryan_keeps_author_voice(self):
        self.assertIn("Ryan", export.build_full("ryan"))

    def test_full_strips_frontmatter_and_starts_with_banner(self):
        full = export.build_full("ryan")
        self.assertTrue(full.startswith(">"))            # banner first
        self.assertNotIn("name: antipatterns", full.lower())  # no YAML frontmatter

    def test_full_contains_catalog(self):
        full = export.build_full("ryan")
        self.assertIn("## 11.", full)              # a numbered catalog section
        self.assertIn("tapestry", full.lower())

    def test_setup_mentions_all_platforms(self):
        setup = export.build_setup("community")
        for platform in ("Claude", "Manus", "ChatGPT", "Gemini"):
            self.assertIn(platform, setup)


class TestCLI(unittest.TestCase):
    def test_writes_all_files_for_both_variants(self):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                [sys.executable, str(REPO / "tools/export.py"), "--out", d],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            for variant in ("ryan", "community"):
                for fn in ("chatgpt-instructions.md", "full-instructions.md", "SETUP.md"):
                    self.assertTrue(
                        (Path(d) / variant / fn).exists(), f"{variant}/{fn} missing"
                    )

    def test_variant_flag_restricts_output(self):
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                [sys.executable, str(REPO / "tools/export.py"),
                 "--variant", "community", "--out", d],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(d) / "community").exists())
            self.assertFalse((Path(d) / "ryan").exists())


if __name__ == "__main__":
    unittest.main()
