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

    # --- Inflection matching: Tier 1/2 words match their regular inflections
    #     (-s/-ing/-ed/-ly, silent-e drop), so 'leveraged', 'navigating',
    #     'seamlessly' count. (Supersedes the old exact-match-only behavior.) ---
    def test_inflection_matches_verb_forms(self):
        r = scan.scan(
            "They leveraged the data, navigated the complexities, fostered "
            "collaboration, and delved deeper.",
            self.cat,
        )
        hits = t1_texts(r)
        self.assertIn("leverage", hits)
        self.assertIn("navigate", hits)
        self.assertIn("foster", hits)
        self.assertIn("delve", hits)

    def test_inflection_matches_adverb_form(self):
        # 'seamlessly' and 'robustly' -> seamless / robust (Tier 1 adjectives).
        r = scan.scan("A seamlessly integrated, robustly defended system.", self.cat)
        self.assertIn("seamless", t1_texts(r))
        self.assertIn("robust", t1_texts(r))

    def test_inflection_no_double_count_verb_vs_derived_noun(self):
        # 'optimization' is its own Tier-2 noun; it must NOT also match the verb
        # 'optimize'. Derivational -ation is excluded on purpose.
        opt = next(e for e in self.cat.entries if e.text.lower() == "optimize")
        hits = scan.hits_in_block("a big optimization effort", self.cat.entries)
        self.assertNotIn(opt, hits)

    def test_tier3_words_do_not_inflect(self):
        # Tier-3 'essential' must NOT match 'essentially' (its own T2 entry).
        # Intensifier adverbs ('critically', 'essentially') are usually legit.
        ess = next(e for e in self.cat.entries if e.text.lower() == "essential")
        hits = scan.hits_in_block("done essentially right", self.cat.entries)
        self.assertNotIn(ess, hits)

    # --- Regression (Codex review on #7): a token that is BOTH a catalog entry
    #     and another entry's inflection must count once. 'optimized' is a
    #     Tier-2 adjective AND the -d form of 'optimize', so 'optimized
    #     optimized' is two hits, not four, and must not fake a cluster. ---
    def test_no_double_count_when_inflection_is_separate_entry(self):
        r = scan.scan("optimized optimized", self.cat)
        self.assertEqual(r["tier2"]["total"], 2)  # not 4
        self.assertEqual(len(r["tier2"]["clusters"]), 0)  # 2 < 3, no cluster
        opt = next(e for e in self.cat.entries if e.text.lower() == "optimize")
        self.assertNotIn(opt, scan.hits_in_block("optimized optimized", self.cat.entries))

    # --- Regression (Codex review on #7): -ic and -able adjectives form their
    #     adverbs as -ically / -ably, not plain -ly. ---
    def test_inflection_generates_ically_and_ably_adverbs(self):
        text = "holistically and strategically sound, sustainably built."
        hits = scan.hits_in_block(text, self.cat.entries)
        holistic = next(e for e in self.cat.entries if e.text.lower() == "holistic")
        strategic = next(e for e in self.cat.entries if e.text.lower() == "strategic")
        sustainable = next(e for e in self.cat.entries if e.text.lower() == "sustainable")
        self.assertIn(holistic, hits)
        self.assertIn(strategic, hits)
        self.assertIn(sustainable, hits)

    # --- Irregular inflections a regex can't derive (strong-verb pasts). ---
    def test_irregular_inflection_overrides(self):
        # 'drive' is a Tier-2 verb; its past 'drove' isn't reachable by the
        # regular -ed machinery. The _IRREGULAR_FORMS override catches it.
        hits = scan.hits_in_block("what drove the change.", self.cat.entries)
        drive = next(e for e in self.cat.entries if e.text.lower() == "drive")
        self.assertIn(drive, hits)

    def test_driven_compound_does_not_double_count(self):
        # Regression (Codex review on #9): 'driven' is excluded from the drive
        # override because it sits inside the cataloged compound 'data-driven'
        # (\b sees '-' as a boundary), which would double-count. 'data-driven'
        # matches its own entry once; 'drive' must NOT also match it.
        hits = scan.hits_in_block("a data-driven approach.", self.cat.entries)
        drive = next(e for e in self.cat.entries if e.text.lower() == "drive")
        data_driven = next(e for e in self.cat.entries if e.text.lower() == "data-driven")
        self.assertIn(data_driven, hits)
        self.assertNotIn(drive, hits)

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

    # --- Whole-piece Tier-2 density ceiling (diffuse density, no cluster) ---
    def test_dense_flag_when_whole_piece_rate_high(self):
        # 6 Tier-2 hits spread 2-per-paragraph across 250+ words: no paragraph
        # reaches the cluster threshold (3), but the whole-piece rate trips the
        # diffuse-density ceiling - exactly the case clusters miss.
        pad = lambda n: " ".join("word" for _ in range(n))
        p1 = f"Furthermore and moreover, {pad(80)}"
        p2 = f"Additionally and ultimately, {pad(80)}"
        p3 = f"Notably, that said, {pad(90)}"
        r = scan.scan(f"{p1}\n\n{p2}\n\n{p3}", self.cat)
        self.assertEqual(len(r["tier2"]["clusters"]), 0)  # spread out, no cluster
        self.assertTrue(r["tier2"]["dense"])

    def test_dense_flag_off_below_min_words(self):
        # Same density but under the minimum word count: clusters only, no dense.
        r = scan.scan("Furthermore. Moreover. Additionally. Ultimately. Notably. That said.", self.cat)
        self.assertFalse(r["tier2"]["dense"])

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


class TestDiscover(unittest.TestCase):
    """Candidate discovery: uncataloged words that repeat (propose->apply fuel)."""

    @classmethod
    def setUpClass(cls):
        cls.cat = parse_catalog(CATALOG_PATH)

    def test_finds_uncataloged_repeat(self):
        # 'synergize' is not cataloged (it's the canonical example of an addition).
        cands = scan.discover_candidates(
            "synergize this. synergize that. synergize now.", self.cat
        )
        self.assertEqual([c["word"] for c in cands], ["synergize"])
        self.assertEqual(cands[0]["count"], 3)

    def test_excludes_cataloged_entries_and_their_inflections(self):
        # 'leverage' is cataloged Tier 1; 'leveraged'/'leveraging' are its
        # inflections, 'delve'/'navigating' likewise. None should be suggested.
        text = "leverage leveraged leveraging delve delving navigate navigating"
        self.assertEqual(scan.discover_candidates(text, self.cat), [])

    def test_filters_stopwords_and_short_tokens(self):
        text = "the the the and and and of of of is is is be be be a a a"
        self.assertEqual(scan.discover_candidates(text, self.cat), [])

    def test_respects_min_count(self):
        text = "synergize synergize. operationalize operationalize operationalize."
        # default (3): only operationalize (x3); synergize x2 is below threshold.
        self.assertEqual([c["word"] for c in scan.discover_candidates(text, self.cat)],
                         ["operationalize"])
        # min 2: both.
        self.assertEqual({c["word"] for c in scan.discover_candidates(text, self.cat, min_count=2)},
                         {"synergize", "operationalize"})

    def test_sorted_by_count_desc(self):
        text = ("synergize " * 5 + "operationalize " * 3).strip()
        cands = scan.discover_candidates(text, self.cat, min_count=2)
        self.assertEqual([c["word"] for c in cands], ["synergize", "operationalize"])


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

    def test_discover_flag_lists_candidates(self):
        proc = self._run(["-", "--discover"], "synergize synergize synergize.")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CANDIDATES", proc.stdout)
        self.assertIn("synergize", proc.stdout)


if __name__ == "__main__":
    unittest.main()
