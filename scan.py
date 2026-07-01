#!/usr/bin/env python3
"""scan.py - deterministic lexical-density sweeper for the antipatterns skill.

The skill's thesis (ANTIPATTERNS.md) is that AI tells are about banned
*densities and contexts*, not banned words. This script closes the gap between
that thesis and practice: it reads ANTIPATTERNS.md as the single source of
truth, then deterministically counts Tier 1/2/3 lexical hits and reports
per-paragraph density - so density is measured, not eyeballed.

Scope is lexical: single words, exact phrases, and em-dashes (the one
structural tell that is countable). Structural judgment (antithesis tics,
triplet rhythm, colon density, anaphora) stays with the model - a regex can't
catch those, and shouldn't pretend to. Tier 1/2 words match their regular
inflections (-s/-ing/-ed/-ly), so "leveraged", "navigating", and "seamlessly"
count; Tier 3 (removal-test) words stay exact.

Stdlib-only, matching the rest of the skill.

Usage:
    python scan.py draft.md
    python scan.py draft.md --json
    python scan.py - < draft.md            # stdin
    cat draft.md | python scan.py
    python scan.py draft.md --strict        # exit 1 if any Tier 1 hit / em-dash
    python scan.py draft.md --allow leverage,ecosystem   # suppress per-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from catalog import Entry, parse_catalog

# Sibling ANTIPATTERNS.md is the default catalog.
DEFAULT_CATALOG = Path(__file__).resolve().parent / "ANTIPATTERNS.md"

# Distinct Tier-2 entries in a single paragraph at or above this count is a
# cluster. Per ANTIPATTERNS.md §13: "Three is a confession."
CLUSTER_THRESHOLD = 3

# Whole-piece Tier-2 density ceiling. Paragraph clusters catch tells that pile
# up in one place; this catches diffuse density - too many Tier-2 hits spread
# across the piece to cluster, but still AI-dense overall. Guarded by a minimum
# word count so a single hit in a 50-word note (20/1000) can't trip it.
DENSE_PER_1000 = 5.0
DENSE_MIN_WORDS = 200


# -------------------------------------------------------------------------- #
# Text helpers
# -------------------------------------------------------------------------- #

def strip_code(text: str) -> str:
    """Remove fenced and inline code spans so their contents are not scanned.

    Implements the 'technical domain gets a pass' guardrail for code, which the
    skill explicitly does not lint. (Quoted third-party material is a known
    limitation - it can't be detected reliably and remains the model's call.)
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # fenced blocks
    text = re.sub(r"`[^`\n]*`", "", text)  # inline spans
    return text


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; drop empties."""
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


# Irregular inflections a regex can't derive (mostly strong-verb pasts). Only
# add a base here if its irregular form actually shows up in drafts - the
# regular suffix machinery already covers the common cases. _word_pattern's
# `reserved` guard prevents double-counting when a form is itself an exact
# catalog entry, but NOT when it's a substring of one - so 'driven' is excluded:
# it sits inside the cataloged compound 'data-driven' and \b sees '-' as a
# boundary, which would double-count every 'data-driven'.
_IRREGULAR_FORMS: dict[str, tuple[str, ...]] = {
    "drive": ("drove",),  # "what drove the change"; 'driven' excluded (see above)
}


def _inflected_forms(base: str) -> list[str]:
    """The base word plus its inflections, longest-first.

    Covers the regular -s/-es/-ing/-ed/-d/-ly set with the silent-e drop
    ('leverage' -> 'leveraging', 'navigate' -> 'navigating', 'delve' ->
    'delving'), the two adverb families that don't take plain -ly (-ic ->
    -ically: holistic -> holistically; -able -> -ably: sustainable ->
    sustainably), and the irregulars in _IRREGULAR_FORMS (drive -> drove).

    Deliberately NOT generated: derivational suffixes (-ation/-tion/-ment/-er,
    etc.) that build different words cataloged separately (optimize vs
    optimization, transform vs transformation) - and _word_pattern's `reserved`
    guard drops any generated form that is itself another entry.
    """
    base = base.lower()
    ends_e = base.endswith("e")
    stem = base[:-1] if ends_e else base
    forms = {base}
    forms.add(base + "s")
    forms.add(base + "es")  # -s/-ss/-ch/-sh stems (harness -> harnesses)
    forms.add((stem + "ing") if ends_e else (base + "ing"))
    forms.add((base + "d") if ends_e else (base + "ed"))
    forms.add(base + "ly")
    if base.endswith("ic"):
        forms.add(base + "ally")      # holistic -> holistically
    if base.endswith("able"):
        forms.add(base[:-2] + "ly")   # sustainable -> sustainably
    forms.update(_IRREGULAR_FORMS.get(base, ()))
    return sorted(forms, key=len, reverse=True)


def _word_pattern(base: str, inflect: bool, reserved: frozenset[str] = frozenset()) -> str:
    """Regex source matching a word, optionally with its regular inflections.

    `reserved` is the set of all catalog entry texts. When inflecting, any
    generated form that is itself another entry's exact text is dropped, so a
    token can't be double-counted across two entries - 'optimized' is both a
    Tier-2 adjective and the -d form of 'optimize', so only the adjective
    entry should match it (not both).
    """
    forms = _inflected_forms(base) if inflect else [base.lower()]
    if inflect and reserved:
        forms = [f for f in forms if f == base.lower() or f not in reserved]
    return r"\b(?:" + "|".join(re.escape(f) for f in forms) + r")\b"


def hits_in_block(block: str, entries: list[Entry]) -> dict[Entry, int]:
    """Return {Entry: count} for entries found in block, case-insensitively.

    Words match on word boundaries; Tier 1/2 words also match their regular
    inflections (-s/-ing/-ed/-ly) so 'leveraged', 'navigating', and
    'seamlessly' count. Tier 3 (removal-test) words stay exact: their adverb
    forms are usually legit and would collide with separate catalog entries
    (the T3 'essential' vs the T2 'Essentially'). Phrases match as
    whitespace-normalized substrings.
    """
    block_l = normalize_ws(block).lower()
    reserved = frozenset(e.text.lower() for e in entries)
    out: dict[Entry, int] = {}
    for e in entries:
        t = e.text.lower()
        if not t:
            continue
        if e.is_word:
            n = len(re.findall(_word_pattern(t, inflect=e.tier in (1, 2), reserved=reserved), block_l))
        else:
            n = block_l.count(t)
        if n:
            out[e] = n
    return out


# -------------------------------------------------------------------------- #
# Core scan
# -------------------------------------------------------------------------- #

def scan(text: str, catalog, allow: list[str] | None = None) -> dict:
    """Scan text against the catalog. Returns a structured result dict."""
    allow_set = {a.lower() for a in (allow or [])}
    entries = [e for e in catalog.entries if e.text.lower() not in allow_set]

    clean = strip_code(text)
    paragraphs = split_paragraphs(clean)

    whole = hits_in_block(clean, entries)
    para_hits = [hits_in_block(p, entries) for p in paragraphs]

    word_count = len(clean.split())
    em_dash_count = clean.count("—")  # U+2014 EM DASH

    # Tier 1: every hit is a flag.
    tier1 = []
    for e, n in whole.items():
        if e.tier == 1:
            para = next((i + 1 for i, h in enumerate(para_hits) if e in h), None)
            tier1.append({"entry": e, "count": n, "paragraph": para})

    # Tier 2: density. Cluster when a paragraph accumulates >= CLUSTER_THRESHOLD
    # Tier-2 hits by COUNT (repeats count - three "Furthermore"s is as much a
    # confession as three different transitions, per ANTIPATTERNS.md section 13).
    # This matches the whole-piece total below, which also sums counts.
    tier2_total = sum(n for e, n in whole.items() if e.tier == 2)
    clusters = []
    for i, h in enumerate(para_hits):
        entries = [e for e in h if e.tier == 2]
        count_in_para = sum(h[e] for e in entries)
        if count_in_para >= CLUSTER_THRESHOLD:
            clusters.append(
                {"paragraph": i + 1, "entries": entries, "count": count_in_para}
            )
    per_1000 = round(tier2_total / word_count * 1000, 1) if word_count else 0.0
    # Diffuse density: too many Tier-2 hits spread across the whole piece to
    # form a paragraph cluster, but still AI-dense overall.
    dense = word_count >= DENSE_MIN_WORDS and per_1000 >= DENSE_PER_1000

    # Tier 3: candidates only. Never auto-flagged - they need the removal test.
    tier3 = [{"entry": e, "count": n} for e, n in whole.items() if e.tier == 3]

    return {
        "metrics": {
            "words": word_count,
            "paragraphs": len(paragraphs),
            "em_dashes": em_dash_count,
        },
        "tier1": tier1,
        "tier2": {
            "clusters": clusters,
            "total": tier2_total,
            "per_1000": per_1000,
            "dense": dense,
        },
        "tier3": tier3,
    }


# -------------------------------------------------------------------------- #
# Rendering
# -------------------------------------------------------------------------- #

def _entry_dict(e: Entry) -> dict:
    return {"text": e.text, "tier": e.tier, "label": e.label}


def to_jsonable(result: dict, source: str) -> dict:
    """Make a result JSON-serializable (Entries -> dicts)."""
    return {
        "source": source,
        "metrics": result["metrics"],
        "tier1": [
            {"entry": _entry_dict(h["entry"]), "count": h["count"], "paragraph": h["paragraph"]}
            for h in result["tier1"]
        ],
        "tier2": {
            "clusters": [
                {
                    "paragraph": c["paragraph"],
                    "count": c["count"],
                    "entries": [_entry_dict(e) for e in c["entries"]],
                }
                for c in result["tier2"]["clusters"]
            ],
            "total": result["tier2"]["total"],
            "per_1000": result["tier2"]["per_1000"],
            "dense": result["tier2"]["dense"],
        },
        "tier3": [
            {"entry": _entry_dict(h["entry"]), "count": h["count"]}
            for h in result["tier3"]
        ],
    }


def render_human(result: dict, source: str) -> str:
    m = result["metrics"]
    out = [f"SCAN: {source}  ({m['words']} words, {m['paragraphs']} paragraphs)", ""]

    # TIER 1
    out.append("TIER 1 (zero tolerance)")
    t1 = result["tier1"]
    if not t1 and m["em_dashes"] == 0:
        out.append("  (clean)")
    else:
        for h in sorted(t1, key=lambda x: x["entry"].text.lower()):
            para = f" (para {h['paragraph']})" if h["paragraph"] else ""
            out.append(f'  "{h["entry"].text}" x{h["count"]} - {h["entry"].label}{para}')
        if m["em_dashes"]:
            out.append(f"  em-dashes: {m['em_dashes']} (hard ban)")
    out.append("")

    # TIER 2
    out.append("TIER 2 (density)")
    t2 = result["tier2"]
    if not t2["clusters"] and t2["total"] == 0:
        out.append("  (clean)")
    else:
        for c in t2["clusters"]:
            names = ", ".join(e.text for e in c["entries"])
            out.append(
                f'  para {c["paragraph"]} cluster ({c["count"]} hits): '
                f"{names}  <- 'three is a confession'"
            )
        if t2["total"]:
            out.append(
                f"  whole piece: {t2['total']} hits / {m['words']} words "
                f"({t2['per_1000']} per 1000)"
            )
        if t2["dense"]:
            out.append(
                f"  DENSE: {t2['per_1000']} per 1000 across the whole piece "
                f"(ceiling {DENSE_PER_1000}/1000 over {DENSE_MIN_WORDS}+ words) "
                f"- diffuse AI density even without a paragraph cluster"
            )
    out.append("")

    # TIER 3
    out.append("TIER 3 (removal test - candidates only, never auto-flagged)")
    t3 = result["tier3"]
    if not t3:
        out.append("  (none)")
    else:
        parts = [
            f'"{h["entry"].text}" x{h["count"]}'
            for h in sorted(t3, key=lambda x: x["entry"].text.lower())
        ]
        out.append("  " + ", ".join(parts))
    out.append("")

    n1 = len(t1) + (1 if m["em_dashes"] else 0)
    out.append(
        f"SUMMARY: {n1} tier-1, {len(t2['clusters'])} cluster(s), "
        f"{len(t3)} tier-3 candidate(s)"
    )
    return "\n".join(out)


# -------------------------------------------------------------------------- #
# CLI
# -------------------------------------------------------------------------- #

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scan a draft for AI-writing antipatterns and report lexical density.",
    )
    p.add_argument(
        "draft",
        nargs="?",
        default="-",
        help="draft file to scan, or '-' / omitted to read stdin",
    )
    p.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help=f"path to ANTIPATTERNS.md (default: {DEFAULT_CATALOG})",
    )
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit nonzero if any Tier 1 hit or em-dash is found (for CI / pre-commit)",
    )
    p.add_argument(
        "--allow",
        default="",
        help="comma-separated words/phrases to suppress this run (your-vocabulary guardrail)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    catalog = parse_catalog(args.catalog)

    if args.draft == "-":
        text = sys.stdin.read()
        source = "stdin"
    else:
        path = Path(args.draft)
        if not path.exists():
            print(f"Error: {path} not found.", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8")
        source = args.draft

    allow = [a.strip() for a in args.allow.split(",") if a.strip()] or None
    result = scan(text, catalog, allow=allow)

    if args.json:
        print(json.dumps(to_jsonable(result, source), indent=2, ensure_ascii=False))
    else:
        print(render_human(result, source))

    if args.strict:
        has_t1 = bool(result["tier1"]) or result["metrics"]["em_dashes"] > 0
        return 1 if has_t1 else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
