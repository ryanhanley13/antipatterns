#!/usr/bin/env python3
"""
add_pattern.py
Add a new antipattern to ANTIPATTERNS.md and log the change.

Usage:
    python add_pattern.py [path/to/ANTIPATTERNS.md]

If no path is given, looks for ANTIPATTERNS.md in the current directory.

Interactive prompts walk you through:
  1. Which category to add to
  2. (If section is tier-split) which tier
  3. The pattern text
  4. A short rationale for the change log

The file is updated in place. The change log gets a dated entry.
"""

import sys
import re
from datetime import date
from pathlib import Path


# Section metadata: number -> (display name, insertion strategy)
SECTIONS = [
    ("1",  "Antithesis & Contrast Tics", "flat"),
    ("2",  "Throat-Clearing Openers", "tiered"),
    ("3",  "Sycophancy & Hollow Validation", "flat"),
    ("4",  "Meta-Narration & Guided-Tour Phrases", "flat"),
    ("5",  "AI Disclaimers & False Humility", "flat"),
    ("6",  "Hedging & Fence-Sitting", "tiered"),
    ("7",  "Rhetorical Question + Answer Structure", "flat"),
    ("8",  "Engagement-Bait Reveals", "flat"),
    ("9",  "Performative Honesty Announcements", "flat"),
    ("10", "The Contrarian Reveal Formula", "flat"),
    ("11", "AI Vocabulary Tells (verbs/adjectives/nouns/stock phrases)", "vocab"),
    ("12", "Stat-Flavored Vagueness", "flat"),
    ("13", "Transition Robots", "flat"),
    ("14", "Structural & Formatting Tics", "tiered"),
    ("15", "Closing Tics", "flat"),
]


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
    bullet_re = re.compile(r"^- .+$", re.MULTILINE)
    bullets = list(bullet_re.finditer(section_text))
    if not bullets:
        raise ValueError(f"Section {section_num} has no bullets to anchor.")

    last = bullets[-1]
    insert_pos = m.end() + last.end()
    new_line = f'\n- "{pattern}"'
    return content[:insert_pos] + new_line + content[insert_pos:]


def add_to_tiered_section(content, section_num, tier, bullet_content):
    """Append a bullet under a specific tier inside a tier-split section."""
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

    tier_text = content[tm.end():tier_end]
    # Top-level bullets only (no leading whitespace, so sub-bullets are skipped)
    bullet_re = re.compile(r"^- .+$", re.MULTILINE)
    bullets = list(bullet_re.finditer(tier_text))

    if not bullets:
        # Tier marker exists but no bullets yet. Insert right after the marker.
        insert_pos = tm.end()
        new_line = f"\n- {bullet_content}"
    else:
        last = bullets[-1]
        insert_pos = tm.end() + last.end()
        new_line = f"\n- {bullet_content}"

    return content[:insert_pos] + new_line + content[insert_pos:]


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


def main():
    filepath = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("ANTIPATTERNS.md")
    if not filepath.exists():
        print(f"Error: {filepath} not found.")
        print("Pass the path to ANTIPATTERNS.md as the first argument.")
        sys.exit(1)

    content = filepath.read_text()
    print(f"\nEditing: {filepath}")
    print("\nPick a category to add to:")
    show_sections()

    sec_input = input("Section number: ").strip()
    section = next((s for s in SECTIONS if s[0] == sec_input), None)
    if not section:
        print(f"Unknown section: {sec_input}")
        sys.exit(1)

    section_num, section_name, kind = section

    if kind == "tiered":
        print(f"\nSection {section_num} ({section_name}) has tier subsections.")
        tier = input("Tier (1, 2, or 3): ").strip()
        if tier not in ("1", "2", "3"):
            print(f"Bad tier: {tier}")
            sys.exit(1)

        print("\nEnter the bullet content exactly as it should appear after '- '.")
        print("Examples:")
        print('  "Just to chime in..."             (for quote-style entries like Section 2)')
        print('  **Pattern name:** description.    (for bold-lead entries like Section 14)')
        bullet = input("\nBullet content: ").strip()
        if not bullet:
            print("Empty bullet, aborting.")
            sys.exit(1)

        summary = input("Log entry summary: ").strip()
        try:
            new_content = add_to_tiered_section(content, section_num, tier, bullet)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        new_content = append_changelog(
            new_content,
            summary or f"Added Tier {tier} entry to '{section_name}'",
        )
        filepath.write_text(new_content)
        print(f"\nDone. Tier {tier} entry added to section {section_num}.")
        return

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
            filepath.write_text(new_content)
            print("\nDone.")
            return

        sub_map = {
            "v": ("### Verbs", "verb"),
            "a": ("### Adjectives", "adjective"),
            "n": ("### Nouns & Metaphors", "noun"),
        }
        if sub not in sub_map:
            print(f"Unknown subsection: {sub}")
            sys.exit(1)

        sub_header, label = sub_map[sub]
        tier = input("Tier (1, 2, or 3): ").strip()
        if tier not in ("1", "2", "3"):
            print(f"Bad tier: {tier}")
            sys.exit(1)

        word = input(f"{label.title()} to add: ").strip()
        summary = input("Log entry summary: ").strip()
        new_content = add_to_vocab_inline(content, sub_header, tier, word)
        new_content = append_changelog(
            new_content, summary or f"Added Tier {tier} {label}: {word}"
        )
        filepath.write_text(new_content)
        print("\nDone.")
        return

    # Flat section
    pattern = input("\nPattern to add (the actual text): ").strip().strip('"')
    summary = input("Log entry summary: ").strip()
    new_content = add_to_flat_section(content, section_num, pattern)
    new_content = append_changelog(
        new_content, summary or f'Added to "{section_name}": "{pattern}"'
    )
    filepath.write_text(new_content)
    print(f"\nPattern added to section {section_num}. Change log updated.")


if __name__ == "__main__":
    main()
