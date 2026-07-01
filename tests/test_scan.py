"""Tests for scan.py - the lexical-density sweeper.

Run from the repo root:  python -m unittest discover -s tests
Stdlib only. Logic tests call scan() directly; CLI/exit-code tests run the
real script as a subprocess.
"""

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog import parse_catalog  # noqa: E402
import scan  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO / "ANTIPATTERNS.md"


def t1_texts(result):
    return {h["entry"].text.lower() for h in result["tier1"]}


def t3_texts(result):
    return {h["entry"].text.lower() for h in result["tier3"]}


class TestScanLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = parse_catalog(CATALOG_PATH)

    # --- Tier 1 words counted, case-insensitive ---
    def test_tier1_word_counted_case_insensitive(self):
        r = scan.scan("Delve into this. We DELVE again and delve more.", self.cat)
        hits = {h["entry"].text.lower(): h["count"] for h in r["tier1"]}
        self.assertIn("delve", hits)
        self.assertEqual(hits["delve"], 3)

    # --- Word boundaries: 'leveraged' is not 'leverage' ---
    def test_word_boundary_no_substring_match(self):
        r = scan.scan("We saw leveraged growth and seamlessly integrated tools.", self.cat)
        # 'leveraged' must not match 'leverage'; 'seamlessly' must not match 'seamless'.
        self.assertNotIn("leverage", t1_texts(r))
        self.assertNotIn("seamless", t1_texts(r))

    # --- Phrase matching (opener) ---
    def test_tier1_phrase_matched(self):
        r = scan.scan("In today's fast-paced world, things change.", self.cat)
        self.assertIn("in today's fast-paced world", t1_texts(r))

    # --- Density threshold: 2 distinct Tier-2 words = no cluster ---
    def test_density_two_distinct_no_cluster(self):
        text = "Furthermore, we agree. Moreover, it works."
        r = scan.scan(text, self.cat)
        self.assertEqual(len(r["tier2"]["clusters"]), 0)

    # --- Density threshold: 3 distinct Tier-2 words = cluster ---
    def test_density_three_distinct_cluster(self):
        text = "Furthermore, we agree. Moreover, it works. Additionally, it scales."
        r = scan.scan(text, self.cat)
        self.assertEqual(len(r["tier2"]["clusters"]), 1)
        c = r["tier2"]["clusters"][0]
        self.assertEqual(c["count"], 3)
        cluster_entries = {e.text.lower() for e in c["entries"]}
        self.assertEqual(cluster_entries, {"furthermore", "moreover", "additionally"})

    # --- Regression (Codex review): 3 repeats of ONE Tier-2 word = cluster.
    #     Per ANTIPATTERNS.md section 13: "Three is a confession." Repeats must
    #     count toward the threshold, not just distinct entries. ---
    def test_density_three_repeats_of_one_word_cluster(self):
        r = scan.scan("Furthermore. Furthermore. Furthermore.", self.cat)
        self.assertEqual(len(r["tier2"]["clusters"]), 1)
        c = r["tier2"]["clusters"][0]
        self.assertEqual(c["count"], 3)
        self.assertEqual({e.text.lower() for e in c["entries"]}, {"furthermore"})

    def test_density_two_repeats_no_cluster(self):
        r = scan.scan("Furthermore. Furthermore.", self.cat)
        self.assertEqual(len(r["tier2"]["clusters"]), 0)

    def test_cluster_paragraph_index_is_correct(self):
        para1 = "A clean opening paragraph about ordinary insurance topics."
        para2 = "Furthermore, we agree. Moreover, it works. Additionally, it scales."
        r = scan.scan(f"{para1}\n\n{para2}", self.cat)
        self.assertEqual(r["tier2"]["clusters"][0]["paragraph"], 2)

    # --- Tier 3: candidate only, never a flag ---
    def test_tier3_candidate_never_flagged_as_tier1(self):
        # 'critical', 'crucial', 'essential' are all cataloged Tier-3 adjectives.
        r = scan.scan(
            "It is critical to plan ahead, crucial to stay focused, and essential to act.",
            self.cat,
        )
        self.assertEqual(r["tier1"], [])  # Tier 3 is never auto-flagged
        candidates = t3_texts(r)
        self.assertIn("critical", candidates)
        self.assertIn("crucial", candidates)
        self.assertIn("essential", candidates)

    # --- Inline code span is exempt ---
    def test_inline_code_span_exempt(self):
        r = scan.scan("Call the `leverage` helper to begin.", self.cat)
        self.assertNotIn("leverage", t1_texts(r))

    # --- Fenced code block is exempt ---
    def test_fenced_code_block_exempt(self):
        text = "```\nleverage tapestry synergy\n```\nPlain prose follows."
        r = scan.scan(text, self.cat)
        self.assertEqual(r["tier1"], [])

    # --- Em-dash count ---
    def test_em_dash_count(self):
        r = scan.scan("One — two — three. No dash here.", self.cat)
        self.assertEqual(r["metrics"]["em_dashes"], 2)

    # --- --allow suppresses the listed word ---
    def test_allow_suppresses_word(self):
        r = scan.scan("We leverage the approach.", self.cat, allow=["leverage"])
        self.assertNotIn("leverage", t1_texts(r))

    # --- A genuinely clean draft scores zero across the board ---
    def test_clean_draft_is_clean(self):
        clean = (
            "AI is changing how insurance gets sold. Agents who don't pick up "
            "the tools now are going to lose accounts to the ones who did."
        )
        r = scan.scan(clean, self.cat)
        self.assertEqual(r["tier1"], [])
        self.assertEqual(r["tier2"]["clusters"], [])
        self.assertEqual(r["tier2"]["total"], 0)
        self.assertEqual(r["tier3"], [])
        self.assertEqual(r["metrics"]["em_dashes"], 0)


class TestCLI(unittest.TestCase):
    """Exercise the real CLI as a subprocess (stdin + exit codes)."""

    def _run(self, args, stdin_text):
        proc = subprocess.run(
            [sys.executable, "scan.py", *args],
            input=stdin_text,
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        return proc

    def test_strict_exit_nonzero_on_tier1(self):
        proc = self._run(["-", "--strict"], "In today's fast-paced world, we leverage synergy.")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_strict_exit_zero_on_clean(self):
        proc = self._run(["-", "--strict"], "Plain prose with no tells at all, just facts.")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_strict_exit_nonzero_on_em_dash_only(self):
        # No banned words, but an em-dash is itself a Tier-1 hard ban.
        proc = self._run(["-", "--strict"], "A clean sentence with one dash — right here.")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)

    def test_json_output_is_valid(self):
        proc = self._run(["-", "--json"], "We leverage synergy and delve in.")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        import json
        data = json.loads(proc.stdout)
        self.assertIn("tier1", data)
        self.assertIn("metrics", data)
        t1 = {h["entry"]["text"].lower() for h in data["tier1"]}
        self.assertIn("leverage", t1)
        self.assertIn("delve", t1)

    def test_missing_file_exits_nonzero(self):
        proc = self._run(["does_not_exist.md"], "")
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
