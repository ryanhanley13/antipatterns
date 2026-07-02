"""Tests for tools/export.py - generate USING.md + platform wrappers from source.

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
        # Fixed URL keeps the build_using tests hermetic (no git dependency).
        cls.url = "https://github.com/example/skill"

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

    def test_community_keeps_author_as_example_with_banner(self):
        # Regression (Codex review on #13): the community variant does NOT
        # naive-genericize the author's name - that breaks grammar ("you writes",
        # "his voice"). It keeps the author's voice as a concrete example and
        # points at the in-bundle voice sections to retune.
        full = export.build_full("community")
        self.assertIn("Community edition", full)
        self.assertIn("Voice Drift Sanity Check", full)
        self.assertIn("What Good Sounds Like", full)
        self.assertIn("Ryan", full)  # kept as the example, not mangled

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

    # ---- USING.md (the committed community guide) ----

    def test_using_mentions_all_platforms(self):
        using = export.build_using(self.cat, repo_url=self.url)
        for platform in ("Claude", "Manus", "ChatGPT", "Gemini"):
            self.assertIn(platform, using)

    def test_using_chatgpt_path_is_a_project(self):
        # The rejected direction was a Custom GPT. The guide must route ChatGPT
        # users to a Project instead.
        using = export.build_using(self.cat, repo_url=self.url)
        self.assertIn("## ChatGPT (a Project", using)

    def test_using_carries_live_pattern_count(self):
        # The whole point of generating USING.md is that the headline count
        # tracks the catalog. It must equal the parsed entry count.
        using = export.build_using(self.cat, repo_url=self.url)
        self.assertIn(f"**{len(self.cat.entries)} patterns**", using)

    def test_using_links_follow_the_repo(self):
        # Fork-correctness (Codex P2): the generated links must point at the
        # repo the guide is generated for, not a hardcoded upstream.
        using = export.build_using(self.cat, repo_url=self.url)
        self.assertIn(self.url, using)                # Manus import URL
        self.assertIn(self.url + "/releases", using)  # Releases links

    def test_using_is_idempotent(self):
        # Generation is deterministic: same catalog -> identical bytes. This is
        # what makes the --check sync guard meaningful.
        self.assertEqual(
            export.build_using(self.cat, repo_url=self.url),
            export.build_using(self.cat, repo_url=self.url),
        )

    def test_detect_repo_url_falls_back_outside_a_clone(self):
        # Outside a git repo (no origin), detection falls back to upstream so
        # generation never breaks.
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(export.detect_repo_url(Path(d)), export.UPSTREAM_URL)


class TestCheck(unittest.TestCase):
    """check_using() is the CI sync guard for the committed USING.md."""

    @classmethod
    def setUpClass(cls):
        cls.cat = parse_catalog(CATALOG_PATH)

    def test_check_passes_when_in_sync(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "USING.md"
            p.write_text(export.build_using(self.cat), encoding="utf-8")
            self.assertEqual(export.check_using(self.cat, using_path=p), 0)

    def test_check_fails_when_stale(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "USING.md"
            p.write_text("stale hand-edited content", encoding="utf-8")
            self.assertEqual(export.check_using(self.cat, using_path=p), 1)

    def test_check_fails_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "USING.md"  # never created
            self.assertEqual(export.check_using(self.cat, using_path=p), 1)


class TestCLI(unittest.TestCase):
    def test_writes_wrappers_for_both_variants(self):
        # --out isolates the wrapper output. (The CLI also regenerates the
        # committed USING.md at the repo root; that write is idempotent.)
        with tempfile.TemporaryDirectory() as d:
            proc = subprocess.run(
                [sys.executable, str(REPO / "tools/export.py"), "--out", d],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            for variant in ("ryan", "community"):
                for fn in ("chatgpt-instructions.md", "full-instructions.md"):
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

    def test_check_flag_passes_when_in_sync(self):
        # --check reads the committed USING.md at the repo root. It is in sync
        # (the same code generated it), so the CLI must exit 0.
        proc = subprocess.run(
            [sys.executable, str(REPO / "tools/export.py"), "--check"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
