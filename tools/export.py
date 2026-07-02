#!/usr/bin/env python3
"""export.py - generate platform wrappers from the skill source.

The skill source (SKILL.md + ANTIPATTERNS.md) is the single source of truth.
Claude and Manus consume it DIRECTLY - they share the same open Agent Skills
format (SKILL.md + resources, three-level progressive disclosure), and Manus
even imports a skill from a GitHub repo URL. So those two platforms need NO
generated wrapper.

This script generates wrappers for the tools that DON'T use the skill format:

  - chatgpt-instructions.md : a condensed (<8000 char) instruction set for a
    ChatGPT Custom GPT's Instructions field. The full catalog won't fit there,
    so this carries the zero-tolerance core; the full catalog is uploaded as
    Knowledge (see full-instructions.md).
  - full-instructions.md    : the procedure + full catalog, for Gemini Gems,
    API system prompts, Claude Projects, or Custom GPT Knowledge upload.
  - SETUP.md                : per-platform setup guide.

Two voice variants:
  - ryan       : the author's personal, voice-calibrated cut.
  - community  : generic ("you") + a customize-for-your-voice banner.

Stdlib only. Run from the repo root:
    python tools/export.py                    # both variants -> dist/
    python tools/export.py --variant community
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# catalog.py lives at the repo root, next to ANTIPATTERNS.md.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from catalog import parse_catalog  # noqa: E402

SKILL_MD = REPO / "SKILL.md"
ANTIPATTERNS_MD = REPO / "ANTIPATTERNS.md"

# ChatGPT Custom GPT Instructions field ceiling (leave headroom under 8000).
CHATGPT_CHAR_LIMIT = 8000

# How many chars of Tier-1 phrases to inline in the condensed ChatGPT set
# before deferring the rest to the full catalog (Knowledge file).
PHRASE_BUDGET = 2400


# -------------------------------------------------------------------------- #
# Source transforms
# -------------------------------------------------------------------------- #

def _strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block (--- ... ---)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            # skip past the closing delimiter line
            nl = text.find("\n", end + 4)
            return text[nl + 1 if nl != -1 else end + 4:].lstrip("\n")
    return text


# -------------------------------------------------------------------------- #
# ChatGPT condensed instructions
# -------------------------------------------------------------------------- #

_CHATGPT_TEMPLATE = """\
# Antipatterns - scrub AI writing tells from a draft

You detect the words, phrases, and rhythms that make text read like an LLM wrote it, and rewrite them out WITHOUT flattening the writer's voice. Thesis: AI tells are about **density and context, not banned words** - one "furthermore" is invisible; three plus a "delve" inside 200 words gives it away.

## When to apply
The user pastes a draft for review/edit/cleanup; asks you to write content (posts, blog, scripts, newsletters, emails); or says "voice check," "AI tells," "sound less like AI," "clean this up," or "make this not suck." Also run it on your own draft before delivering it.

## Do NOT apply to
Code, technical docs, code review, resumes/CVs, direct quotes, casual chat, summaries, translations, outlines, pre-draft brainstorms.

## Workflow
1. Scan the draft; tag each tell by category and tier.
2. **Tier 3** words: run the removal test BEFORE flagging.
3. Rewrite - fix every Tier 1; fix Tier 2 when clustered or dense; fix Tier 3 only if the removal test confirms filler. Preserve voice, specifics, point of view, rhythm. If a rewrite is shorter but vaguer, it's wrong; redo it.
4. Run the voice drift check before delivering.

## Tier system
- **Tier 1 - zero tolerance.** One instance ruins the piece.
- **Tier 2 - density.** Fine alone; 3+ in one paragraph (or a high whole-piece rate) is a tell.
- **Tier 3 - judgment.** Legit words grabbed as filler - use the removal test.

## Tier 1 - kill on sight
Words: {tier1_words}
Phrases: {tier1_phrases}
Also: em-dashes (hard ban); the antithesis tic ("It's not X, it's Y" / "Not X, but Y"); chirpy closers ("Hope this helps!"); engagement-bait ("But here's where it gets interesting..."); stat-flavored vagueness ("Studies show...").

## Removal test (Tier 3)
Take the suspect word out. Read the sentence. Does it still say what it needs to? **Yes** -> filler, cut. **No** -> it's doing real work, keep.

## False-positive guardrails
- The writer's own vocabulary trumps the list (if they use "leverage," it's not banned in their voice).
- Technical domain terms get a pass ("robust" in software architecture).
- Direct quotes are exempt - don't edit them.

## Voice drift check (run before delivering)
1. Does it still sound like {voice_subject}? (Rhythm and punch intact?)
2. Did we lose specifics? (Shorter but vaguer = worse.)
3. Did we strip personality (edge, humor, bluntness, fragments)?
4. Is there still a point of view?
5. Did we lose the rhythm (intentional fragments, short punches, asides)?
Any "no" -> redo the rewrite.

## Output format
**CLEANED DRAFT** - clean copy, no inline notes.
**FLAGS** - grouped by tier: `Tier 1: [Category]: "[original]" -> "[rewrite]"`.
**VOICE DRIFT CHECK** - the five answers.
**PROPOSED ADDITIONS** - only if new tells surfaced that aren't cataloged; propose, don't add unilaterally.

{voice_note}
"""

_VOICE_NOTE_COMMUNITY = (
    "> **Community edition:** the voice traits above are calibrated to the skill's "
    "author. Before relying on the voice drift check, swap them for YOUR traits. "
    "The full catalog (every Tier 1/2/3 list, all 15 categories) is in the attached "
    "knowledge file - this condensed set is just the zero-tolerance core."
)
_VOICE_NOTE_RYAN = (
    "> The full catalog (every Tier 1/2/3 list, all 15 categories) is in the attached "
    "knowledge file; this condensed set is the zero-tolerance core."
)


def _tier1_lines(catalog) -> tuple[str, str]:
    """Render Tier-1 words (full) and phrases (budgeted) for the condensed set."""
    words = sorted(e.text for e in catalog.by_tier(1) if e.is_word)
    phrases = sorted(e.text for e in catalog.by_tier(1) if not e.is_word)

    words_str = ", ".join(words)

    included, total = [], 0
    for p in phrases:
        if total + len(p) + 4 > PHRASE_BUDGET:
            break
        included.append(p)
        total += len(p) + 4
    phrases_str = "; ".join(f'"{p}"' for p in included)
    leftover = len(phrases) - len(included)
    if leftover > 0:
        phrases_str += f"; +{leftover} more in the full catalog"
    return words_str, phrases_str


def build_chatgpt(variant: str, catalog) -> str:
    voice_subject = "you" if variant == "community" else "Ryan"
    voice_note = _VOICE_NOTE_COMMUNITY if variant == "community" else _VOICE_NOTE_RYAN
    words_str, phrases_str = _tier1_lines(catalog)
    out = _CHATGPT_TEMPLATE
    out = out.replace("{tier1_words}", words_str)
    out = out.replace("{tier1_phrases}", phrases_str)
    out = out.replace("{voice_subject}", voice_subject)
    out = out.replace("{voice_note}", voice_note)
    return out


# -------------------------------------------------------------------------- #
# Full instructions (Gemini / API / Claude Projects / GPT Knowledge)
# -------------------------------------------------------------------------- #

def build_full(variant: str) -> str:
    skill = _strip_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    catalog = ANTIPATTERNS_MD.read_text(encoding="utf-8")

    banner = (
        "> **Antipatterns - AI-writing-tell scrubber.** Paste this block into your "
        "tool's system prompt / custom instructions / Gem. (Claude and Manus users: "
        "use the packaged skill from the repo instead - it loads fully and fires "
        "automatically.)\n\n"
    )
    if variant == "community":
        # Keep the author's voice as a concrete example rather than
        # naive-genericizing the name - a find/replace breaks the surrounding
        # grammar ("you writes", "his voice") and would strip the only concrete
        # calibration the reader has. The catalog's own "Customizing for your
        # voice" section tells them exactly what to swap.
        banner += (
            "> **Community edition:** this skill is calibrated to its author's voice "
            "(Ryan) - the voice-check traits below are a concrete example to swap for "
            "your own, not a generic default. Follow the 'Customizing for your voice' "
            "section in the catalog to retune them.\n\n"
        )
    return banner + "# PROCEDURE\n\n" + skill + "\n\n---\n\n# CATALOG\n\n" + catalog


# -------------------------------------------------------------------------- #
# SETUP guide
# -------------------------------------------------------------------------- #

def build_setup(variant: str) -> str:
    edition = "community edition" if variant == "community" else "personal edition"
    customize = ""
    if variant == "community":
        customize = (
            "\n## Customize for your voice\n"
            "The voice traits are the author's. Open `full-instructions.md`, find the "
            "**Voice Drift Sanity Check** and **What Good Sounds Like** sections, and "
            "replace those traits with your own before you rely on them.\n"
        )
    return f"""\
# Antipatterns - setup ({edition})

Four ways to use the skill, depending on your tool.

## Claude (best experience)
Download `antipatterns.skill` from the repo's Releases page, then Settings ->
Skills -> Import. The skill loads fully and fires automatically when you paste a
draft or ask for content.

## Manus
Manus -> Skills -> + Add -> Import from GitHub -> paste the repo URL. Manus uses
the same skill format as Claude, so it imports as-is.

## ChatGPT (Custom GPT)
1. Create a new GPT (Explore -> Create).
2. Paste `chatgpt-instructions.md` into the **Instructions** field.
3. Upload `full-instructions.md` as a **Knowledge** file (the instructions field
   can't hold the full catalog, so the condensed set carries the zero-tolerance
   core and the full list lives in Knowledge).

## Gemini (or any tool with a system prompt)
Paste the contents of `full-instructions.md` as your Gem instructions / system
prompt / custom instructions.
{customize}
The source of truth is always `ANTIPATTERNS.md` + `SKILL.md` in the repo; these
files are generated from them by `tools/export.py`.
"""


# -------------------------------------------------------------------------- #
# CLI
# -------------------------------------------------------------------------- #

VARIANTS = ("ryan", "community")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--variant",
        choices=[*VARIANTS, "both"],
        default="both",
        help="which voice variant to export (default: both)",
    )
    p.add_argument(
        "--out",
        default=str(REPO / "dist"),
        help="output directory (default: ./dist)",
    )
    args = p.parse_args(argv)

    out_dir = Path(args.out)
    variants = VARIANTS if args.variant == "both" else [args.variant]
    catalog = parse_catalog(ANTIPATTERNS_MD)

    for variant in variants:
        vdir = out_dir / variant
        vdir.mkdir(parents=True, exist_ok=True)

        chatgpt = build_chatgpt(variant, catalog)
        if len(chatgpt) > CHATGPT_CHAR_LIMIT:
            print(
                f"::error::[{variant}] chatgpt-instructions.md is {len(chatgpt)} "
                f"chars (limit {CHATGPT_CHAR_LIMIT}); trim the template or budget."
            )
            return 1
        (vdir / "chatgpt-instructions.md").write_text(chatgpt, encoding="utf-8")
        (vdir / "full-instructions.md").write_text(build_full(variant), encoding="utf-8")
        (vdir / "SETUP.md").write_text(build_setup(variant), encoding="utf-8")

        try:
            where = str(vdir.relative_to(REPO))
        except ValueError:
            where = str(vdir)  # --out pointed outside the repo
        print(
            f"[{variant}] wrote chatgpt-instructions.md ({len(chatgpt)} chars), "
            f"full-instructions.md, SETUP.md -> {where}/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
