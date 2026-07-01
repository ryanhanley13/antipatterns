"""Tests for add_pattern.py - the catalog writer.

Run from the repo root:  python -m unittest discover -s tests
Stdlib only. Function tests operate on the real catalog text in memory (no file
writes); CLI tests run the script as a subprocess against a temp copy.

Key invariant under test: every mutation round-trip validates (re-parse with
catalog.parse_catalog_text) and SECTIONS is the single shared source of truth.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import add_pattern as ap  # noqa: E402
from catalog import SECTIONS as CAT_SECTIONS  # noqa: E402
from catalog import parse_catalog_text  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REAL = (REPO / "ANTIPATTERNS.md").read_text(encoding="utf-8")


def find(catalog, text):
    for e in catalog.entries:
        if e.text.lower() == text.lower():
            return e
    return None


class TestApplyAddition(unittest.TestCase):
    """apply_addition routes by section kind; each result must validate."""

    def test_flat_section_adds_phrase(self):
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(REAL, ap.Addition(section="13", text="Moving forward"))
        ap.validate(new, before)  # must not raise
        self.assertIsNotNone(find(parse_catalog_text(new), "Moving forward"))

    def test_tiered_section_adds_quoted_bullet(self):
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(REAL, ap.Addition(section="2", tier=2, text="By and large"))
        ap.validate(new, before)
        self.assertIsNotNone(find(parse_catalog_text(new), "By and large"))

    def test_vocab_word_adds_to_correct_tier_line(self):
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(
            REAL, ap.Addition(section="11", subsection="Verbs", tier=1, text="synergize")
        )
        ap.validate(new, before)
        e = find(parse_catalog_text(new), "synergize")
        self.assertIsNotNone(e)
        self.assertEqual(e.tier, 1)
        self.assertEqual(e.label, "§11 Verbs")  # landed in the right subsection

    def test_stock_phrase_added(self):
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(
            REAL, ap.Addition(section="11", subsection="Stock Phrases", text="circle back to")
        )
        ap.validate(new, before)
        self.assertIsNotNone(find(parse_catalog_text(new), "circle back to"))

    def test_rejects_unknown_section(self):
        with self.assertRaises(ValueError):
            ap.apply_addition(REAL, ap.Addition(section="99", text="x"))

    def test_rejects_vocab_missing_subsection(self):
        with self.assertRaises(ValueError):
            ap.apply_addition(REAL, ap.Addition(section="11", tier=1, text="x"))

    def test_rejects_tiered_missing_tier(self):
        with self.assertRaises(ValueError):
            ap.apply_addition(REAL, ap.Addition(section="2", text="x"))

    def test_rejects_bad_tier_value(self):
        with self.assertRaises(ValueError):
            ap.apply_addition(REAL, ap.Addition(section="2", tier=9, text="x"))

    def test_round_trip_preserves_all_sections(self):
        # After a valid add, all 15 numbered sections are still present.
        import re
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(REAL, ap.Addition(section="13", text="Moving forward"))
        present = set(re.findall(r"^## (\d+)\. ", new, re.MULTILINE))
        self.assertEqual(present, {s[0] for s in CAT_SECTIONS})

    def test_flat_section_does_not_orphan_indented_children(self):
        # Regression (Codex review on #2): section 15's last bullet has an
        # indented "Context note" child. Adding a new closer must land AFTER
        # that note, not between the bullet and its child (which would orphan
        # the note under the new bullet). validate() does NOT catch this, so
        # the writer must.
        before = len(parse_catalog_text(REAL).entries)
        new = ap.apply_addition(REAL, ap.Addition(section="15", text="New closer test"))
        ap.validate(new, before)  # still parses
        maxim = new.find("The maxim closer:")
        note = new.find("**Context note:**")
        newb = new.find('"New closer test"')
        self.assertLess(maxim, note, "context note should follow its maxim-closer bullet")
        self.assertLess(note, newb, "new bullet must come AFTER the context note, not orphan it")


class TestParseSpec(unittest.TestCase):
    def test_single_object_becomes_list(self):
        adds = ap.parse_spec({"section": "13", "tier": 2, "text": "Moving forward"})
        self.assertEqual(len(adds), 1)
        self.assertEqual(adds[0].section, "13")

    def test_list_of_objects(self):
        adds = ap.parse_spec(
            [{"section": "11", "subsection": "Verbs", "tier": 1, "text": "a"},
             {"section": "12", "text": "b"}]
        )
        self.assertEqual(len(adds), 2)

    def test_missing_section_rejected(self):
        with self.assertRaises(ValueError):
            ap.parse_spec({"text": "x"})

    def test_missing_text_rejected(self):
        with self.assertRaises(ValueError):
            ap.parse_spec({"section": "13"})

    def test_tier_coerced_from_string(self):
        adds = ap.parse_spec({"section": "2", "tier": "2", "text": "x"})
        self.assertEqual(adds[0].tier, 2)

    def test_non_object_rejected(self):
        with self.assertRaises(ValueError):
            ap.parse_spec("just a string")


class TestValidate(unittest.TestCase):
    def test_untouched_catalog_passes(self):
        before = len(parse_catalog_text(REAL).entries)
        ap.validate(REAL, before)  # no raise

    def test_dropped_entries_fails(self):
        before = len(parse_catalog_text(REAL).entries)
        truncated = REAL[: len(REAL) // 2]  # loses entries
        with self.assertRaises(ValueError):
            ap.validate(truncated, before)

    def test_missing_section_fails(self):
        before = len(parse_catalog_text(REAL).entries)
        bad = REAL.replace("## 1. Antithesis", "## X. Antithesis", 1)
        with self.assertRaises(ValueError):
            ap.validate(bad, before)


class TestChangelog(unittest.TestCase):
    def test_dated_entry_appended_at_top(self):
        new = ap.apply_addition(REAL, ap.Addition(section="13", text="Moving forward"))
        new = ap.append_changelog(new, "a test summary")
        marker = f"**{date.today().isoformat()}:** a test summary"
        self.assertIn(marker, new)
        # And it lands above older log entries (v1 / 2026-05 entries remain).
        self.assertIn("- **v1:** Initial file.", new)


class TestSingleSource(unittest.TestCase):
    def test_SECTIONS_is_the_same_object_as_catalog(self):
        # add_pattern imports SECTIONS from catalog - proof of single source.
        self.assertIs(ap.SECTIONS, CAT_SECTIONS)


class TestCLI(unittest.TestCase):
    """End-to-end via subprocess against a temp copy of the real catalog."""

    def _run(self, args):
        return subprocess.run(
            [sys.executable, str(REPO / "add_pattern.py"), *args],
            capture_output=True, text=True,
        )

    def test_apply_batch_adds_all_and_logs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cat = d / "ANTIPATTERNS.md"
            cat.write_text(REAL)
            spec = d / "spec.json"
            spec.write_text(json.dumps([
                {"section": "11", "subsection": "Verbs", "tier": 1,
                 "text": "synergize", "log": "appeared 3x in a draft"},
                {"section": "13", "tier": 2, "text": "Moving forward", "log": "L2"},
            ]))
            proc = self._run(["--apply", str(spec), str(cat)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            parsed = parse_catalog_text(cat.read_text())
            self.assertIsNotNone(find(parsed, "synergize"))
            self.assertIsNotNone(find(parsed, "Moving forward"))
            self.assertEqual(len(parsed.entries), 183 + 2)
            text = cat.read_text()
            self.assertIn("appeared 3x in a draft", text)
            self.assertIn("L2", text)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cat = d / "ANTIPATTERNS.md"
            original = REAL
            cat.write_text(original)
            spec = d / "spec.json"
            spec.write_text(json.dumps({"section": "12", "text": "Research confirms"}))
            proc = self._run(["--apply", str(spec), "--dry-run", str(cat)])
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(cat.read_text(), original)  # byte-identical

    def test_reject_unknown_section_exit_code_and_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cat = d / "ANTIPATTERNS.md"
            cat.write_text(REAL)
            spec = d / "spec.json"
            spec.write_text(json.dumps({"section": "99", "text": "nope"}))
            proc = self._run(["--apply", str(spec), str(cat)])
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(cat.read_text(), REAL)  # unchanged

    def test_missing_path_exits_nonzero(self):
        proc = self._run(["does_not_exist.md"])
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
