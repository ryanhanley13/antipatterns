"""catalog.py — parse ANTIPATTERNS.md into structured lexical lists.

ANTIPATTERNS.md is the single source of truth for the antipatterns catalog.
This module reads it and returns a Catalog of (text, tier, label) entries so
that scan.py (and later add_pattern.py) never duplicate or drift from the
hand-curated lists. "That file is the data"; this file turns it into a query.

Stdlib-only, matching the rest of the skill.

Scope is lexical: single words and exact phrases that can be searched for.
Structural tells (antithesis tics, triplet rhythm, colon density) live in the
catalog as prose, not as greppable strings, and are intentionally not parsed —
those are the model's job. scan.py measures density; the model judges structure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    """One lexical antipattern.

    text:   the search string (original case; matched case-insensitively).
    tier:   1 (catastrophic), 2 (density-dependent), or 3 (removal test).
    label:  human-readable provenance, e.g. "§11 Verbs" or "§2 Openers".
    is_word: True for single-token entries (word-boundary match),
             False for multi-token phrases (substring match).
    """

    text: str
    tier: int
    label: str
    is_word: bool


@dataclass
class Catalog:
    """All lexical antipatterns parsed from ANTIPATTERNS.md."""

    entries: list[Entry] = field(default_factory=list)

    @property
    def words(self) -> list[Entry]:
        return [e for e in self.entries if e.is_word]

    @property
    def phrases(self) -> list[Entry]:
        return [e for e in self.entries if not e.is_word]

    def by_tier(self, tier: int) -> list[Entry]:
        return [e for e in self.entries if e.tier == tier]


# --------------------------------------------------------------------------
# Section structure — the single source of truth shared with add_pattern.py.
# add_pattern.py imports SECTIONS and VOCAB_SUBSECTIONS from here so the reader
# and the writer can never disagree about which sections exist or how they're
# laid out. Tuple form: (number, name, kind); kind drives insertion strategy.
# --------------------------------------------------------------------------

SECTIONS = [
    ("1", "Antithesis & Contrast Tics", "flat"),
    ("2", "Throat-Clearing Openers", "tiered"),
    ("3", "Sycophancy & Hollow Validation", "flat"),
    ("4", "Meta-Narration & Guided-Tour Phrases", "flat"),
    ("5", "AI Disclaimers & False Humility", "flat"),
    ("6", "Hedging & Fence-Sitting", "tiered"),
    ("7", "Rhetorical Question + Answer Structure", "flat"),
    ("8", "Engagement-Bait Reveals", "flat"),
    ("9", "Performative Honesty Announcements", "flat"),
    ("10", "The Contrarian Reveal Formula", "flat"),
    ("11", "AI Vocabulary Tells (verbs/adjectives/nouns/stock phrases)", "vocab"),
    ("12", "Stat-Flavored Vagueness", "flat"),
    ("13", "Transition Robots", "flat"),
    ("14", "Structural & Formatting Tics", "tiered"),
    ("15", "Closing Tics", "flat"),
]

SECTION_NUMS = {s[0] for s in SECTIONS}

# Section 11 (vocab) subsections: friendly name -> markdown header.
VOCAB_SUBSECTIONS = {
    "Verbs": "### Verbs",
    "Adjectives": "### Adjectives",
    "Nouns & Metaphors": "### Nouns & Metaphors",
    "Stock Phrases": "### Stock Phrases",
}


# --------------------------------------------------------------------------
# Regexes. Kept module-level so they compile once and are easy to audit.
# --------------------------------------------------------------------------

# A numbered content section: "## 2. Throat-Clearing Openers [Tier 1 to Tier 2]"
SECTION_HEADER_RE = re.compile(
    r"^##\s+(\d+)\.\s+(.+?)(?:\s+\[(?:Tier\s+)?(\d+)(?:\s+to\s+(?:Tier\s+)?\d+)?\])?\s*$"
)

# A vocab/structural subsection inside §11: "### Verbs (avoid unless user used them first)"
SUBSECTION_RE = re.compile(r"^###\s+(.+?)\s*$")

# A tier marker line. Captures the tier number and any inline word list.
#   "**Tier 1:** delve, leverage, ..."           -> (1, "delve, leverage, ...")
#   "**Tier 1 (never use):**"                    -> (1, "")
#   "**Tier 3 (judgment):** crucial, vital, ..." -> (3, "crucial, vital, ...")
TIER_LINE_RE = re.compile(r"^\*\*\s*Tier\s+(\d+)(?:\s*\([^)]*\))?\s*:\s*\*\*\s*(.*)$")

# A quoted bullet: - "In today's fast-paced world..."
QUOTED_BULLET_RE = re.compile(r'^-\s+"(.+?)"\s*$')

# A generic bullet: - Furthermore   (used for unquoted content like §13 transitions).
GENERIC_BULLET_RE = re.compile(r"^-\s+(.+?)\s*$")

# Trailing "[Tier 1]" annotation on a subsection title:
# "### Stock Phrases [Tier 1]" -> "Stock Phrases".
TRAILING_BRACKET_RE = re.compile(r"\s*\[Tier[^\]]*\]\s*$")

# Trailing parenthetical on a word, e.g. "navigate (as a verb ...)" -> "navigate".
TRAILING_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")

# Trailing punctuation to strip from phrases so they match as prefixes/substrings:
# "In today's fast-paced world..." -> "In today's fast-paced world".
TRAILING_PUNCT_RE = re.compile(r"[.,;:!?]+\s*$|…|\.{2,}\s*$")

# Standalone placeholder tokens (X, Y, Z) mark template patterns like
# "It's not X, it's Y." These aren't literal search strings; skip them.
# Restricted to X/Y/Z so the real English words "A" and "I" are NOT mistaken
# for placeholders (e.g. the Tier-1 closer "I hope this helps!").
PLACEHOLDER_RE = re.compile(r"\b[XYZ]\b")

# A bracketed slot of alternatives, e.g. "[doctor/lawyer/financial advisor]".
BRACKET_SLOT_RE = re.compile(r"\[[^\]]*\]")

# A placeholder slot like "[X]" — a non-literal template slot.
PLACEHOLDER_SLOT_RE = re.compile(r"\[[XYZ]\]")


def _clean_word(raw: str) -> str | None:
    """Normalize a single vocab word. Returns None if it should be skipped."""
    w = raw.strip()
    w = TRAILING_PAREN_RE.sub("", w).strip()
    w = w.strip("\"'").strip()
    return w or None


def _clean_phrase(raw: str) -> str | None:
    """Normalize a quoted phrase. Returns None if it should be skipped."""
    p = raw.strip()
    p = TRAILING_PUNCT_RE.sub("", p).strip()
    p = p.strip("\"'").strip()
    if not p:
        return None
    # A [X]/[Y]/[Z] slot marks a non-literal template ("the power of [X]");
    # it can never be grepped literally, so drop the whole phrase.
    if PLACEHOLDER_SLOT_RE.search(p):
        return None
    # An alternatives slot ("While I'm not a [doctor/lawyer/...]") is a real
    # tell, but the bracketed content isn't literal. Drop the slot, keep the
    # surrounding text -> "While I'm not a".
    p = BRACKET_SLOT_RE.sub("", p)
    p = re.sub(r"\s+", " ", p).strip()
    if not p:
        return None
    # Template patterns with standalone placeholder tokens aren't literal either.
    if PLACEHOLDER_RE.search(p):
        return None
    return p


def _split_inline_words(rest: str) -> list[str]:
    """Split a comma-separated inline word list, dropping empties."""
    out = []
    for chunk in rest.split(","):
        w = _clean_word(chunk)
        if w:
            out.append(w)
    return out


def _label(section_num: str, section_name: str, subsection: str | None) -> str:
    """Build a provenance label like '§11 Verbs' or '§2 Openers'."""
    # Shorten the section name to its last meaningful word for skimmability
    # only when we have a subsection to carry detail; otherwise keep the full name.
    if subsection:
        return f"§{section_num} {subsection}"
    return f"§{section_num} {section_name}"


def _make_entry(text: str, tier: int, label: str) -> Entry | None:
    """Classify cleaned text as a word or phrase and build an Entry."""
    is_word = " " not in text.strip()
    return Entry(text=text, tier=tier, label=label, is_word=is_word)


def parse_catalog_text(text: str) -> Catalog:
    """Parse catalog markdown from a string into a Catalog.

    Tolerant: hand-edited oddities (unrecognized bullets, stray prose) are
    skipped silently. The catalog evolves; the parser degrades gracefully
    rather than crashing on a format change.
    """
    lines = text.splitlines()

    catalog = Catalog()

    # Split into numbered sections (## N. ...). Only sections 1-15 carry
    # lexical entries; the "## The Tier System" overview, "## False Positives",
    # "## Versioning", etc. are skipped.
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = SECTION_HEADER_RE.match(line)
        if not m:
            i += 1
            continue

        section_num, section_name, ann_tier = m.group(1), m.group(2).strip(), m.group(3)
        # Only known content sections (1-15) are lexical catalogs.
        if section_num not in SECTION_NUMS:
            i += 1
            continue

        # §14 is structural formatting tics (prose descriptions, not greppable).
        if section_num == "14":
            # Advance past this section to the next ## header.
            i += 1
            while i < n and not lines[i].startswith("## "):
                i += 1
            continue

        # Default tier from the header annotation, e.g. [Tier 1] -> 1.
        header_tier = int(ann_tier) if ann_tier else 2

        # Walk the section body until the next top-level (## ) header.
        i += 1
        current_tier: int | None = None
        current_subsection: str | None = None
        section_entries: list[Entry] = []

        while i < n and not lines[i].startswith("## "):
            body = lines[i]

            sub = SUBSECTION_RE.match(body)
            if sub:
                # Inside §11: "### Verbs", "### Stock Phrases", etc.
                name = sub.group(1).strip()
                # Drop trailing parenthetical / [Tier N] from the title:
                # "Verbs (avoid unless user used them first)" -> "Verbs"
                # "Stock Phrases [Tier 1]" -> "Stock Phrases"
                name = TRAILING_PAREN_RE.sub("", name).strip()
                name = TRAILING_BRACKET_RE.sub("", name).strip()
                current_subsection = name
                current_tier = None  # reset; tier comes from the next marker
                i += 1
                continue

            tm = TIER_LINE_RE.match(body)
            if tm:
                current_tier = int(tm.group(1))
                inline = tm.group(2)
                # Stock Phrases subsection uses bullet lists, not inline words,
                # even though a tier marker may sit above it. Only treat inline
                # content as words when we're in a Verbs/Adjectives/Nouns subsection.
                if inline.strip() and current_subsection in (
                    "Verbs",
                    "Adjectives",
                    "Nouns & Metaphors",
                ):
                    lbl = _label(section_num, section_name, current_subsection)
                    for w in _split_inline_words(inline):
                        e = _make_entry(w, current_tier, lbl)
                        if e:
                            section_entries.append(e)
                i += 1
                continue

            qb = QUOTED_BULLET_RE.match(body)
            if qb:
                raw = qb.group(1)
                # Stock Phrases are always Tier 1 regardless of marker.
                if current_subsection == "Stock Phrases":
                    tier = 1
                    lbl = _label(section_num, section_name, "Stock Phrases")
                    p = _clean_phrase(raw)
                    if p:
                        e = _make_entry(p, tier, lbl)
                        if e:
                            section_entries.append(e)
                else:
                    tier = current_tier if current_tier is not None else header_tier
                    lbl = _label(section_num, section_name, current_subsection)
                    # A quoted bullet may be a phrase or a lone word ("Essentially,").
                    p = _clean_phrase(raw)
                    if p:
                        e = _make_entry(p, tier, lbl)
                        if e:
                            section_entries.append(e)
                i += 1
                continue

            gb = GENERIC_BULLET_RE.match(body)
            if gb:
                raw = gb.group(1)
                # Skip bold-lead structural entries (§14-style) — not lexical.
                if "**" in raw:
                    i += 1
                    continue
                tier = current_tier if current_tier is not None else header_tier
                lbl = _label(section_num, section_name, current_subsection)
                p = _clean_phrase(raw)
                # Only treat short unquoted bullets as content entries (e.g.
                # §13 "Furthermore", "That said,"). Long unquoted bullets are
                # descriptive prose and must not become search strings.
                if p and len(p.split()) <= 4:
                    e = _make_entry(p, tier, lbl)
                    if e:
                        section_entries.append(e)
                i += 1
                continue

            # Anything else (descriptive bullets, prose, blanks) is skipped.
            i += 1

        catalog.entries.extend(section_entries)

    return _dedupe(catalog)


def parse_catalog(path: Path | str) -> Catalog:
    """Parse ANTIPATTERNS.md from a file path into a Catalog."""
    return parse_catalog_text(Path(path).read_text(encoding="utf-8"))


def _dedupe(catalog: Catalog) -> Catalog:
    """Collapse entries that share the same lowercased text, keeping the most
    severe (lowest tier). A word listed in two places should only ever flag
    once, at its worst tier."""
    best: dict[str, Entry] = {}
    for e in catalog.entries:
        key = e.text.lower()
        prev = best.get(key)
        if prev is None or e.tier < prev.tier:
            best[key] = e
    catalog.entries = list(best.values())
    return catalog


if __name__ == "__main__":
    # Smoke test: parse the sibling catalog and print a summary.
    here = Path(__file__).resolve().parent
    cat_path = here / "ANTIPATTERNS.md"
    cat = parse_catalog(cat_path)
    print(f"Parsed {len(cat.entries)} entries from {cat_path.name}")
    for tier in (1, 2, 3):
        words = [e for e in cat.by_tier(tier) if e.is_word]
        phrases = [e for e in cat.by_tier(tier) if not e.is_word]
        print(f"  Tier {tier}: {len(words)} words, {len(phrases)} phrases")
