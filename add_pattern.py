#!/usr/bin/env python3
"""add_pattern.py - add antipatterns to ANTIPATTERNS.md and log the change.

Two modes:

  Interactive (default):
      python add_pattern.py [path/to/ANTIPATTERNS.md]

  Non-interactive batch apply (closes the skill's propose -> apply loop):
      python add_pattern.py --apply additions.json [path/to/ANTIPATTERNS.md] [--dry-run]

The JSON spec is a single object or a list:

    [
      {"section": "11", "subsection": "Verbs", "tier": 1,
       "text": "synergize", "log": "appeared 3x in a draft"},
      {"section": "13", "tier": 2, "text": "Moving forward",
       "log": "transition variant"}
    ]

Section structure (SECTIONS) and vocab subsections are imported from catalog.py,
which is the single source of truth - this writer and the reader (catalog.py /
scan.py) can never disagree about the catalog's layout.

Every edit is round-trip validated: after mutating, the result is re-parsed
with catalog.parse_catalog_text and must still contain all known sections with
no loss of entries. If validation fails, nothing is written. Stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from catalog import (
    SECTION_NUMS,
    SECTIONS,
    VOCAB_SUBSECTIONS,
    parse_catalog_text,
)


# -------------------------------------------------------------------------- #
# Writer functions - mutate the catalog markdown. Each is scoped to one shape
# of section. They raise ValueError when an anchor can't be found.
# -------------------------------------------------------------------------- #

def show_sections():
    print()
    for num, name, _kind in SECTIONS:
        print(f"  [{num:>3}] {name}")
    print()


def add_to_flat_section(content, section_num, pattern):
    """Append a bullet to a flat-bullet section."""
    section_header_re = re.compile(
        rf"^## {re.escape(section_num)}\. .*$", re.MULTILINE
    )
    m = section_header_re.search(content)
    if not m:
        raise ValueError(f"Section {section_num} header not found.")

    # Find boundary of this section (next ## header or end of file)
    after = content[m.end():]
    next_section_re = re.compile(r"^## \S", re.MULTILINE)
    nm = next_section_re.search(after)
    section_end_pos = m.end() + (nm.start() if nm else len(after))

    section_text = content[m.end():section_end_pos]
    lines = section_text.splitlines(keepends=True)

    # Last top-level bullet (starts with "- "; indented children start with
    # whitespace and are deliberately excluded here).
    last_top = None
    for idx, ln in enumerate(lines):
        if ln.startswith("- "):
            last_top = idx
    if last_top is None:
        raise ValueError(f"Section {section_num} has no bullets to anchor.")

    # Insert AFTER the last top-level bullet and any indented children that
    # belong to it, so a nested note (e.g. section 15's Context note) isn't
    # orphaned under the new bullet.
    ins = last_top + 1
    while ins < len(lines) and lines[ins][:1].isspace():
        ins += 1
    lines.insert(ins, f'- "{pattern}"\n')
    return content[:m.end()] + "".join(lines) + content[section_end_pos:]


def add_to_tiered_section(content, section_num, tier, bullet_content):
    """Append a bullet under a specific tier inside a tier-split section.

    Lands the new bullet AFTER the last top-level bullet and any indented
    children belonging to it, so a nested note isn't orphaned under the new
    bullet. Mirrors add_to_flat_section. (No tiered section currently has
    nested children, so the child-skipping is defensive.)
    """
    section_header_re = re.compile(
        rf"^## {re.escape(section_num)}\. .*$", re.MULTILINE
    )
    m = section_header_re.search(content)
    if not m:
        raise ValueError(f"Section {section_num} header not found.")

    # Bound this section
    after = content[m.end():]
    next_section_re = re.compile(r"^## \S", re.MULTILINE)
    nm = next_section_re.search(after)
    section_end_pos = m.end() + (nm.start() if nm else len(after))

    # Find the tier marker. Format examples:
    #   **Tier 1:**
    #   **Tier 1 (never use):**
    #   **Tier 2 (depends on density):**
    tier_marker_re = re.compile(
        rf"^\*\*Tier {tier}(?: \([^)]+\))?:\*\*\s*$", re.MULTILINE
    )
    tm = tier_marker_re.search(content, m.end(), section_end_pos)
    if not tm:
        raise ValueError(
            f"Tier {tier} marker not found in section {section_num}."
        )

    # Bound the tier subsection: next **Tier marker or section end
    next_tier_re = re.compile(r"^\*\*Tier \d", re.MULTILINE)
    ntm = next_tier_re.search(content, tm.end(), section_end_pos)
    tier_end = ntm.start() if ntm else section_end_pos

    tier_lines = content[tm.end():tier_end].splitlines(keepends=True)

    # Last top-level bullet (starts with "- "; indented children start with
    # whitespace and are excluded here).
    last_top = None
    for idx, ln in enumerate(tier_lines):
        if ln.startswith("- "):
            last_top = idx

    new_bullet_line = f"- {bullet_content}\n"
    if last_top is None:
        # No bullets in this tier yet. tier_text normally starts with the
        # newline that follows the marker; insert the bullet AFTER it so the
        # bullet lands on its own line instead of glued to the marker
        # ("**Tier 1:**- ...", which the parser would swallow as inline text).
        # If there's no leading newline, supply one.
        if tier_lines and tier_lines[0] == "\n":
            tier_lines.insert(1, new_bullet_line)
        else:
            tier_lines.insert(0, "\n" + new_bullet_line)
    else:
        # Insert AFTER the last top-level bullet, skipping any indented children
        # (whitespace-leading, non-blank) so a nested note isn't orphaned under
        # the new bullet. Stop at a blank line so insertion stays tight.
        ins = last_top + 1
        while (
            ins < len(tier_lines)
            and tier_lines[ins][:1].isspace()
            and tier_lines[ins].strip()
        ):
            ins += 1
        tier_lines.insert(ins, new_bullet_line)

    return content[:tm.end()] + "".join(tier_lines) + content[tier_end:]


def add_to_vocab_inline(content, sub_header_text, tier, word):
    """Append a word to a comma-separated tier line under a vocab subsection."""
    sh_re = re.compile(rf"^{re.escape(sub_header_text)}.*$", re.MULTILINE)
    sm = sh_re.search(content)
    if not sm:
        raise ValueError(f"Subsection '{sub_header_text}' not found.")

    after = content[sm.end():]
    next_re = re.compile(r"^(###|##) ", re.MULTILINE)
    nm = next_re.search(after)
    sub_end = sm.end() + (nm.start() if nm else len(after))

    sub_text = content[sm.end():sub_end]
    tier_re = re.compile(rf"^\*\*Tier {tier}.*?\*\*[^\n]*$", re.MULTILINE)
    tm = tier_re.search(sub_text)
    if not tm:
        raise ValueError(f"Tier {tier} line not found in '{sub_header_text}'.")

    line_start = sm.end() + tm.start()
    line_end = sm.end() + tm.end()
    old_line = content[line_start:line_end]
    new_line = old_line.rstrip() + f", {word}"
    return content[:line_start] + new_line + content[line_end:]


def add_stock_phrase(content, phrase):
    """Append a phrase to the Stock Phrases bullet list under section 11."""
    sh_re = re.compile(r"^### Stock Phrases.*$", re.MULTILINE)
    sm = sh_re.search(content)
    if not sm:
        raise ValueError("Stock Phrases subsection not found.")

    after = content[sm.end():]
    next_re = re.compile(r"^(###|##) ", re.MULTILINE)
    nm = next_re.search(after)
    sub_end = sm.end() + (nm.start() if nm else len(after))

    sub_text = content[sm.end():sub_end]
    bullet_re = re.compile(r'^- ".+"$', re.MULTILINE)
    bullets = list(bullet_re.finditer(sub_text))
    if not bullets:
        raise ValueError("No existing stock phrase bullets to anchor.")

    last = bullets[-1]
    insert_pos = sm.end() + last.end()
    new_line = f'\n- "{phrase}"'
    return content[:insert_pos] + new_line + content[insert_pos:]


def append_changelog(content, summary):
    """Insert a dated entry at the top of the change log."""
    marker = "### Change log"
    idx = content.find(marker)
    if idx == -1:
        print("Warning: change log section not found. Skipping log entry.")
        return content

    line_end = content.find("\n", idx)
    today = date.today().isoformat()
    new_entry = f"\n- **{today}:** {summary}"
    return content[:line_end] + new_entry + content[line_end:]


# -------------------------------------------------------------------------- #
# Addition model + dispatch (shared by --apply and tests). The interactive
# flow still collects input itself, but every write goes through validation.
# -------------------------------------------------------------------------- #

@dataclass
class Addition:
    """One approved catalog addition."""

    section: str            # "11"
    text: str               # the pattern
    log: str = ""           # changelog entry (auto-generated if empty)
    tier: int | None = None  # 1/2/3, required for tiered + vocab-word sections
    subsection: str | None = None  # "Verbs" etc., required for vocab section 11


def _section_meta(section_num):
    return next((s for s in SECTIONS if s[0] == str(section_num)), None)


def _default_log(add: Addition) -> str:
    meta = _section_meta(add.section)
    name = meta[1] if meta else f"section {add.section}"
    where = name + (f" > {add.subsection}" if add.subsection else "")
    return f'Added to {where}: "{add.text}"'


def apply_addition(content: str, add: Addition) -> str:
    """Apply one Addition to catalog text. Returns the new content.

    Raises ValueError on an invalid addition (unknown section, missing tier,
    unknown subsection). Routing by section kind:
      flat   -> add_to_flat_section (auto-quoted)
      tiered -> add_to_tiered_section (quoted, unless text is a bold-lead bullet)
      vocab  -> add_to_vocab_inline / add_stock_phrase
    """
    meta = _section_meta(add.section)
    if meta is None:
        raise ValueError(
            f"Unknown section {add.section!r}. Known: {sorted(SECTION_NUMS, key=int)}. "
            f"New sections are added manually (by design - section layout is the "
            f"single source of truth): add ('{add.section}', 'Name', 'flat|tiered|vocab') "
            f"to SECTIONS in catalog.py, then add the '## {add.section}. Name' "
            f"section to ANTIPATTERNS.md."
        )
    _num, _name, kind = meta
    text = add.text.strip().strip('"').strip()
    if not text:
        raise ValueError("text is empty")

    if kind == "flat":
        return add_to_flat_section(content, add.section, text)

    if kind == "tiered":
        if add.tier not in (1, 2, 3):
            raise ValueError(
                f"section {add.section} is tiered; 'tier' (1/2/3) is required"
            )
        # Quote the bullet unless the caller supplied a bold-lead entry
        # (section 14 style: "**Pattern name:** description").
        bullet = text if text.startswith("**") else f'"{text}"'
        return add_to_tiered_section(content, add.section, add.tier, bullet)

    # kind == "vocab"
    if add.subsection not in VOCAB_SUBSECTIONS:
        raise ValueError(
            f"section {add.section} is vocab; 'subsection' must be one of "
            f"{list(VOCAB_SUBSECTIONS)} (got {add.subsection!r})"
        )
    if add.subsection == "Stock Phrases":
        return add_stock_phrase(content, text)
    if add.tier not in (1, 2, 3):
        raise ValueError(
            f"vocab subsection {add.subsection!r} requires 'tier' (1/2/3)"
        )
    return add_to_vocab_inline(
        content, VOCAB_SUBSECTIONS[add.subsection], add.tier, text
    )


# -------------------------------------------------------------------------- #
# Spec parsing + round-trip validation
# -------------------------------------------------------------------------- #

def parse_spec(data) -> list[Addition]:
    """Validate parsed JSON (a single object or a list) into Additions."""
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("spec must be a JSON object or a list of objects")

    additions = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"spec entry {i} is not an object")
        section = str(item.get("section", "")).strip()
        text = str(item.get("text", "")).strip()
        if not section:
            raise ValueError(f"spec entry {i} is missing 'section'")
        if not text:
            raise ValueError(f"spec entry {i} is missing 'text'")
        raw_tier = item.get("tier")
        tier = int(raw_tier) if raw_tier is not None else None
        subsection = item.get("subsection")
        if subsection is not None:
            subsection = str(subsection).strip() or None
        log = str(item.get("log", "")).strip()
        additions.append(
            Addition(section=section, text=text, tier=tier,
                     subsection=subsection, log=log)
        )
    return additions


def validate(content: str, before_entry_count: int) -> None:
    """Round-trip validate mutated catalog text. Raises ValueError if broken.

    Catches any edit that corrupts structure: the result must re-parse, must
    not lose entries, and must still contain all known numbered sections.
    """
    catalog = parse_catalog_text(content)  # raises if unparseable
    if len(catalog.entries) < before_entry_count:
        raise ValueError(
            f"entry count dropped after edit ({before_entry_count} -> "
            f"{len(catalog.entries)}); the file may be malformed"
        )
    present = set(re.findall(r"^## (\d+)\. ", content, re.MULTILINE))
    missing = SECTION_NUMS - present
    if missing:
        raise ValueError(
            f"sections missing after edit: {sorted(missing, key=int)}"
        )


def write_validated(filepath: Path, new_content: str, before_entry_count: int) -> None:
    """Validate, then write. Aborts (sys.exit 1) without writing on failure."""
    try:
        validate(new_content, before_entry_count)
    except ValueError as e:
        print(f"Validation failed - file left unchanged: {e}", file=sys.stderr)
        sys.exit(1)
    filepath.write_text(new_content, encoding="utf-8")


# -------------------------------------------------------------------------- #
# CLI
# -------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Add antipatterns to ANTIPATTERNS.md and log the change.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Non-interactive apply (closes the skill's propose -> apply loop):
  python add_pattern.py --apply additions.json

JSON spec (single object or a list):
  [
    {"section": "11", "subsection": "Verbs", "tier": 1,
     "text": "synergize", "log": "appeared 3x in a draft"},
    {"section": "13", "tier": 2, "text": "Moving forward", "log": "transition variant"}
  ]

Section structure is imported from catalog.py (single source of truth).
Every edit is round-trip validated before it is written.
""",
    )
    p.add_argument(
        "path", nargs="?", default="ANTIPATTERNS.md",
        help="path to ANTIPATTERNS.md (default: ./ANTIPATTERNS.md)",
    )
    p.add_argument(
        "--apply", metavar="SPEC.json", default=None,
        help="apply additions from a JSON spec, non-interactively",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="with --apply: print the plan and validate, but write nothing",
    )
    return p


def run_apply(filepath: Path, content: str, args) -> int:
    spec_path = Path(args.apply)
    if not spec_path.exists():
        print(f"Error: spec file {spec_path} not found.", file=sys.stderr)
        return 2
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        additions = parse_spec(data)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error parsing spec: {e}", file=sys.stderr)
        return 2
    if not additions:
        print("Spec contained no additions.")
        return 0

    before_n = len(parse_catalog_text(content).entries)
    new = content
    try:
        for add in additions:
            new = apply_addition(new, add)
    except ValueError as e:
        print(f"Aborted before any change: {e}", file=sys.stderr)
        return 1
    for add in additions:
        new = append_changelog(new, add.log or _default_log(add))

    print(f"Applying {len(additions)} addition(s):")
    for add in additions:
        where = f"section {add.section}" + (
            f" > {add.subsection}" if add.subsection else ""
        )
        tier = f" T{add.tier}" if add.tier else ""
        print(f"  + {where}{tier}: {add.text}")

    if args.dry_run:
        try:
            validate(new, before_n)
        except ValueError as e:
            print(f"Would FAIL validation: {e}", file=sys.stderr)
            return 1
        print("\n(dry-run: validated, no changes written)")
        return 0

    write_validated(filepath, new, before_n)
    print(f"\nDone. {filepath} updated.")
    return 0


def run_interactive(filepath: Path, content: str) -> int:
    print(f"\nEditing: {filepath}")
    print("\nPick a category to add to:")
    show_sections()

    sec_input = input("Section number: ").strip()
    section = next((s for s in SECTIONS if s[0] == sec_input), None)
    if not section:
        print(f"Unknown section: {sec_input}")
        return 1

    section_num, section_name, kind = section
    before_n = len(parse_catalog_text(content).entries)

    if kind == "tiered":
        print(f"\nSection {section_num} ({section_name}) has tier subsections.")
        tier = input("Tier (1, 2, or 3): ").strip()
        if tier not in ("1", "2", "3"):
            print(f"Bad tier: {tier}")
            return 1

        print("\nEnter the bullet content exactly as it should appear after '- '.")
        print("Examples:")
        print('  "Just to chime in..."             (for quote-style entries like Section 2)')
        print('  **Pattern name:** description.    (for bold-lead entries like Section 14)')
        bullet = input("\nBullet content: ").strip()
        if not bullet:
            print("Empty bullet, aborting.")
            return 1

        summary = input("Log entry summary: ").strip()
        try:
            new_content = add_to_tiered_section(content, section_num, tier, bullet)
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        new_content = append_changelog(
            new_content, summary or f"Added Tier {tier} entry to '{section_name}'"
        )
        write_validated(filepath, new_content, before_n)
        print(f"\nDone. Tier {tier} entry added to section {section_num}.")
        return 0

    if kind == "vocab":
        print("\nVocab subsection:")
        print("  [v] Verbs")
        print("  [a] Adjectives")
        print("  [n] Nouns & Metaphors")
        print("  [s] Stock Phrases")
        sub = input("Choice (v/a/n/s): ").strip().lower()

        if sub == "s":
            phrase = input("\nStock phrase to add: ").strip().strip('"')
            summary = input("Log entry summary: ").strip()
            new_content = add_stock_phrase(content, phrase)
            new_content = append_changelog(
                new_content, summary or f'Added stock phrase: "{phrase}"'
            )
            write_validated(filepath, new_content, before_n)
            print("\nDone.")
            return 0

        sub_map = {
            "v": (VOCAB_SUBSECTIONS["Verbs"], "verb"),
            "a": (VOCAB_SUBSECTIONS["Adjectives"], "adjective"),
            "n": (VOCAB_SUBSECTIONS["Nouns & Metaphors"], "noun"),
        }
        if sub not in sub_map:
            print(f"Unknown subsection: {sub}")
            return 1

        sub_header, label = sub_map[sub]
        tier = input("Tier (1, 2, or 3): ").strip()
        if tier not in ("1", "2", "3"):
            print(f"Bad tier: {tier}")
            return 1

        word = input(f"{label.title()} to add: ").strip()
        summary = input("Log entry summary: ").strip()
        new_content = add_to_vocab_inline(content, sub_header, tier, word)
        new_content = append_changelog(
            new_content, summary or f"Added Tier {tier} {label}: {word}"
        )
        write_validated(filepath, new_content, before_n)
        print("\nDone.")
        return 0

    # Flat section
    pattern = input("\nPattern to add (the actual text): ").strip().strip('"')
    summary = input("Log entry summary: ").strip()
    new_content = add_to_flat_section(content, section_num, pattern)
    new_content = append_changelog(
        new_content, summary or f'Added to "{section_name}": "{pattern}"'
    )
    write_validated(filepath, new_content, before_n)
    print(f"\nPattern added to section {section_num}. Change log updated.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    filepath = Path(args.path)
    if not filepath.exists():
        print(f"Error: {filepath} not found.", file=sys.stderr)
        print("Pass the path to ANTIPATTERNS.md as the first argument.", file=sys.stderr)
        return 2
    content = filepath.read_text(encoding="utf-8")
    if args.apply is not None:
        return run_apply(filepath, content, args)
    return run_interactive(filepath, content)


if __name__ == "__main__":
    sys.exit(main())
