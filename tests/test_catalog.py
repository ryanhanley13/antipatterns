"""Tests for catalog.py — parser correctness against the real ANTIPATTERNS.md.

Run from the repo root:  python -m unittest discover -s tests
Stdlib only; no third-party deps.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Make the sibling catalog.py importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog import parse_catalog  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "ANTIPATTERNS.md"


def find(cat, text):
    """Exact (case-insensitive) entry lookup."""
    for e in cat.entries:
        if e.text.lower() == text.lower():
            return e
    return None


class TestRealCatalog(unittest.TestCase):
    """Parse the actual, hand-curated ANTIPATTERNS.md and assert known mappings."""

    @classmethod
    def setUpClass(cls):
        cls.cat = parse_catalog(CATALOG_PATH)

    def assertEntry(self, text, tier, is_word=None):
        e = find(self.cat, text)
        self.assertIsNotNone(e, f"{text!r} was not parsed from the catalog")
        self.assertEqual(e.tier, tier, f"{text!r}: expected Tier {tier}, got Tier {e.tier}")
        if is_word is not None:
            self.assertEqual(
                e.is_word, is_word, f"{text!r}: expected is_word={is_word}, got {e.is_word}"
            )

    # --- Tier 1 vocabulary ---
    def test_tier1_verbs(self):
        self.assertEntry("delve", 1, True)
        self.assertEntry("leverage", 1, True)
        self.assertEntry("navigate", 1, True)  # parenthetical "(as a verb...)" stripped

    def test_tier1_nouns(self):
        self.assertEntry("tapestry", 1, True)
        self.assertEntry("plethora", 1, True)

    def test_tier1_adjectives(self):
        self.assertEntry("seamless", 1, True)
        self.assertEntry("robust", 1, True)

    # --- Tier 3 vocabulary (removal-test words) ---
    def test_tier3_adjectives(self):
        self.assertEntry("critical", 3, True)  # added 2026-07-01
        self.assertEntry("crucial", 3, True)
        self.assertEntry("essential", 3, True)
        self.assertEntry("vital", 3, True)

    # --- §13 transitions are unquoted bullets; parser must still capture them ---
    def test_tier2_transitions_unquoted_bullets(self):
        self.assertEntry("furthermore", 2, True)
        self.assertEntry("Moreover", 2, True)
        self.assertEntry("Additionally", 2, True)
        self.assertEntry("That said", 2, False)  # 2-word phrase, comma stripped

    # --- Tier 1 phrases (openers, meta-narration) ---
    def test_tier1_phrases(self):
        self.assertEntry("In today's fast-paced world", 1, False)
        self.assertEntry("Let's dive in", 1, False)
        self.assertEntry("As an AI", 1, False)

    # --- Regression: phrases starting with the English word "I" must NOT be
    #     mistaken for a template placeholder (X/Y/Z) and dropped. ---
    def test_closer_starting_with_I_is_kept(self):
        self.assertEntry(
            "I hope this helps! Let me know if you have any other questions", 1, False
        )

    # --- Regression: an alternatives slot "[doctor/lawyer/...]" is stripped,
    #     keeping the real tell around it. A "[X]" template slot is excluded. ---
    def test_bracketed_alternatives_slot_stripped(self):
        self.assertEntry("While I'm not a", 1, False)  # was "[doctor/lawyer/...]"
        # Template slot "[X]" must NOT become the generic prefix "the power of".
        self.assertIsNone(find(self.cat, "the power of"))
        self.assertIsNone(find(self.cat, "a wealth of"))

    # --- Tier 1 stock phrases ---
    def test_tier1_stock_phrases(self):
        self.assertEntry("plays a crucial role", 1, False)
        self.assertEntry("pave the way for", 1, False)
        self.assertEntry("best practices", 1, False)

    # --- Research-driven enrichment (2026-07): 2024-2026 excess-word studies ---
    def test_research_driven_additions(self):
        # Verbs / adjectives / noun added from excess-word research (arXiv, FSU).
        self.assertEntry("underscore", 2, True)
        self.assertEntry("intricate", 2, True)
        self.assertEntry("meticulous", 2, True)
        self.assertEntry("beacon", 2, True)
        # Stock phrases (always Tier 1) added from the same research.
        self.assertEntry("underscores the importance of", 1, False)
        self.assertEntry("a testament to", 1, False)
        self.assertEntry("sheds light on", 1, False)
        # §13 transition added.
        self.assertEntry("Notably", 2, True)

    # --- Parenthetical / annotation stripping ---
    def test_no_stray_parens_or_brackets_anywhere(self):
        for e in self.cat.entries:
            self.assertNotIn("(", e.text, f"stray '(' in {e!r}")
            self.assertNotIn(")", e.text, f"stray ')' in {e!r}")
            self.assertNotIn("[", e.text, f"stray '[' in {e!r}")

    # --- Template patterns with placeholder tokens (X, Y, Z) are not literal ---
    def test_template_placeholders_excluded(self):
        self.assertIsNone(find(self.cat, "It's not X, it's Y"))
        self.assertIsNone(find(self.cat, "Not X, but Y"))
        self.assertIsNone(find(self.cat, "X isn't a Y"))

    # --- The "## The Tier System" overview is prose, not a parsed list ---
    def test_all_entries_sourced_from_sections_1_to_15(self):
        for e in self.cat.entries:
            self.assertRegex(e.label, r"^§\d+ ")
            num = int(e.label[len("§"):].split()[0])
            self.assertTrue(1 <= num <= 15, f"entry {e!r} sourced from §{num}")

    # --- Dedupe: each lowercased text appears exactly once, at its worst tier ---
    def test_no_duplicate_texts(self):
        lowers = [e.text.lower() for e in self.cat.entries]
        self.assertEqual(len(lowers), len(set(lowers)), "duplicate entry texts after dedupe")

    def test_catalog_has_reasonable_size(self):
        # Sanity: the real catalog has well over a hundred lexical entries.
        self.assertGreater(len(self.cat.entries), 100)
        self.assertGreater(len(self.cat.words), 50)
        self.assertGreater(len(self.cat.phrases), 50)


class TestTolerantParsing(unittest.TestCase):
    """The catalog is hand-edited; the parser must not crash on odd input."""

    def test_malformed_snippet_does_not_raise(self):
        snippet = """# junk front matter

## The Tier System
### Tier 1: Catastrophic (zero tolerance)
Examples: delve, tapestry, and prose that must not become a search string.

## 1. Antithesis Tics [Tier 1]

- "It's not just X, it's Y."
- a descriptive bullet that is far too long to be a search string so skip it
- "A real quoted tell."

## 99. Not A Real Section
- "ignore me entirely"
"""
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(snippet)
            path = f.name
        cat = parse_catalog(path)  # must not raise

        # Template placeholder excluded.
        self.assertIsNone(find(cat, "It's not just X, it's Y"))
        # Long descriptive bullet excluded.
        self.assertIsNone(find(cat, "a descriptive bullet that is far too long"))
        # Real quoted tell captured at the header-annotated tier (1).
        e = find(cat, "A real quoted tell")
        self.assertIsNotNone(e)
        self.assertEqual(e.tier, 1)
        # Section 99 ignored entirely.
        for entry in cat.entries:
            self.assertNotIn("ignore me", entry.text)
        # Overview prose not captured.
        self.assertIsNone(find(cat, "and prose that must not"))


if __name__ == "__main__":
    unittest.main()
