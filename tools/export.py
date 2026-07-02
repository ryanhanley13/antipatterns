#!/usr/bin/env python3
"""export.py - generate the sharing surface from the skill source.

The skill source (SKILL.md + ANTIPATTERNS.md) is the single source of truth.
Claude and Manus consume it DIRECTLY - they share the open Agent Skills format
(SKILL.md + resources), and Manus imports a skill from a GitHub repo URL. Those
two platforms need no generated artifact: point them at the repo / the .skill.

This script generates the artifacts for everyone else, all from source so the
sharing docs can never drift from the catalog:

  USING.md (repo root, committed)  : the community front door - a one-page
    "use this in Claude / Manus / ChatGPT / Gemini" guide. Its headline pattern
    count is pulled live from the catalog, so it updates as the catalog grows.
    `--check` verifies the committed file matches a fresh generation (CI runs it
    so a catalog/template edit that isn't regenerated fails loudly).

  dist/<variant>/chatgpt-instructions.md : a condensed (<8000 char) instruction
    set for a ChatGPT Project's custom-instructions field. The full catalog
    won't fit there, so this carries the zero-tolerance core; the full list is
    the uploaded file (full-instructions.md).
  dist/<variant>/full-instructions.md    : the procedure + full catalog, for a
    Gemini Gem, an API system prompt, a Claude Project, or a ChatGPT Project's
    uploaded file.

Two voice variants:
  - ryan       : the author's personal, voice-calibrated cut.
  - community  : generic ("you") + a customize-for-your-voice banner.

The dist/ wrappers are build artifacts (gitignored): the release workflow
(.github/workflows/release.yml) publishes the community cut to GitHub Releases
on v* tags.

Stdlib only. Run from the repo root:
    python tools/export.py                    # USING.md + both variants -> dist/
    python tools/export.py --variant community
    python tools/export.py --check            # CI: USING.md in sync? exit 1 if not
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# catalog.py lives at the repo root, next to ANTIPATTERNS.md.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from catalog import parse_catalog  # noqa: E402

SKILL_MD = REPO / "SKILL.md"
ANTIPATTERNS_MD = REPO / "ANTIPATTERNS.md"
USING_MD = REPO / "USING.md"

# Fallback when the repo URL can't be read from git (e.g. generation run outside
# a clone). Detected at runtime so a fork's regenerated USING.md points at the
# fork, not the upstream - the README invites forks, so the generated guide has
# to follow them.
UPSTREAM_URL = "https://github.com/ryanhanley13/antipatterns"


def detect_repo_url(repo_path: Path = REPO) -> str:
    """Best-effort GitHub URL of this repo from the `origin` remote.

    Normalizes both git@github.com:owner/repo.git and https://github.com/owner/repo(.git).
    Falls back to UPSTREAM_URL if git is missing, there's no origin, or the URL
    isn't a recognizable GitHub URL, so generation never breaks outside a clone.
    """
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(repo_path), capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return UPSTREAM_URL
    if out.returncode != 0:
        return UPSTREAM_URL
    m = re.match(
        r"(?:git@github\.com:|https?://github\.com/)([^/]+/[^/]+?)(?:\.git)?$",
        out.stdout.strip(),
    )
    return f"https://github.com/{m.group(1)}" if m else UPSTREAM_URL


# ChatGPT Project custom-instructions ceiling (leave headroom under 8000).
CHATGPT_CHAR_LIMIT = 8000

# How many chars of Tier-1 phrases to inline in the condensed ChatGPT set
# before deferring the rest to the full catalog (the uploaded file).
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
    "The full catalog (every Tier 1/2/3 list, all 15 categories) is in the uploaded "
    "file - this condensed set is just the zero-tolerance core."
)
_VOICE_NOTE_RYAN = (
    "> The full catalog (every Tier 1/2/3 list, all 15 categories) is in the uploaded "
    "file; this condensed set is the zero-tolerance core."
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
# Full instructions (Gemini Gem / API / Claude Project / ChatGPT Project file)
# -------------------------------------------------------------------------- #

def build_full(variant: str) -> str:
    skill = _strip_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    catalog = ANTIPATTERNS_MD.read_text(encoding="utf-8")

    banner = (
        "> **Antipatterns - AI-writing-tell scrubber.** Paste this block into your "
        "tool's system prompt / Gem / Project. (Claude and Manus users: use the "
        "packaged skill from the repo instead - it loads fully and fires "
        "automatically.)\n\n"
    )
    if variant == "community":
        # Keep the author's voice as a concrete example rather than
        # naive-genericizing the name - a find/replace breaks the surrounding
        # grammar ("you writes", "his voice") and would strip the only concrete
        # calibration the reader has. The catalog's own "Voice Drift Sanity
        # Check" and "What Good Sounds Like" sections tell them exactly what to
        # swap.
        banner += (
            "> **Community edition:** this skill is calibrated to its author's voice "
            "(Ryan) - the voice-check traits below are a concrete example to swap for "
            "your own, not a generic default. Open the **Voice Drift Sanity Check** "
            "and **What Good Sounds Like** sections below and replace those traits "
            "with your own before you rely on them.\n\n"
        )
    return banner + "# PROCEDURE\n\n" + skill + "\n\n---\n\n# CATALOG\n\n" + catalog


# -------------------------------------------------------------------------- #
# USING.md - the community front door (committed; --check keeps it in sync)
# -------------------------------------------------------------------------- #

_USING_TEMPLATE = """\
# Using the Antipatterns skill

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) that scrubs AI writing tells out of a draft while preserving voice. This page gets it running in whatever tool you use. The catalog currently covers **{count} patterns** across 15 categories - that number is pulled live from the source, so it stays honest as the catalog grows.

Claude and Manus speak the open Agent Skills format natively, so they take the skill directly - no wrapper needed. ChatGPT and Gemini don't, so there are ready-to-paste instruction files for those (see [The ready-to-paste files](#the-ready-to-paste-files-chatgpt--gemini) below).

## Claude (best experience)
Download the latest `antipatterns.skill` from the [Releases]({releases_url}) page, then **Settings -> Skills -> Import**. The skill loads fully and fires automatically when you paste a draft or ask for content.

## Manus
**Skills -> + Add -> Import from GitHub**, then paste this repo's URL: `{repo_url}`. Manus uses the same skill format as Claude, so it imports as-is.

## ChatGPT (a Project, not a Custom GPT)
1. Create a new **Project** (sidebar -> New project).
2. Paste `chatgpt-instructions.md` into the Project's **custom instructions**.
3. Upload `full-instructions.md` as a **file** in the Project. The custom-instructions field can't hold the full catalog, so the condensed file carries the zero-tolerance core and the full list lives in the uploaded file.

## Gemini
Create a **Gem**, then paste the contents of `full-instructions.md` as the Gem's instructions. Gems accept long instructions, so the full catalog fits in one paste.

## The ready-to-paste files (ChatGPT / Gemini)
Grab these from the [Releases]({releases_url}) page - the **community** cut is what most people want:

- **`chatgpt-instructions.md`** - the condensed (under 8,000-character) zero-tolerance core. Goes in a ChatGPT Project's custom instructions.
- **`full-instructions.md`** - the full procedure + catalog. Upload it to a ChatGPT Project, or paste it into a Gemini Gem / any tool with a system-prompt field.

To regenerate them locally (for example the `ryan` personal cut): `python tools/export.py`.

## Customize for your voice
This skill is calibrated to its author's voice. Before you rely on the voice drift check, open the catalog (`ANTIPATTERNS.md`), find the **Voice Drift Sanity Check** and **What Good Sounds Like** sections, and replace those traits with your own. The skill works best when it's tuned to you - a generic anti-AI filter strips voice along with the tells.

---

The source of truth is always `ANTIPATTERNS.md` + `SKILL.md` in the repo. `USING.md` and the `dist/` wrappers are generated from them by `tools/export.py`.
"""


def build_using(catalog, repo_url: str | None = None) -> str:
    """The one-page, multi-tool usage guide. The pattern count is live from the
    catalog; the repo/release links follow the repo this is generated in (so a
    fork's guide points at the fork, not the upstream)."""
    repo_url = repo_url or detect_repo_url()
    return _USING_TEMPLATE.format(
        count=len(catalog.entries),
        releases_url=repo_url + "/releases",
        repo_url=repo_url,
    )


# -------------------------------------------------------------------------- #
# CLI
# -------------------------------------------------------------------------- #

VARIANTS = ("ryan", "community")


def check_using(catalog, using_path: Path = USING_MD) -> int:
    """Return 0 if USING.md (at using_path) matches a fresh generation, else 1.

    Writes nothing. CI runs this so a catalog/template edit that isn't
    regenerated fails loudly instead of shipping a stale guide. `using_path`
    defaults to the committed guide and is parameterized for testing.
    """
    if not using_path.exists():
        print("::error::USING.md is missing; run `python tools/export.py` to generate it.")
        return 1
    actual = using_path.read_text(encoding="utf-8")
    expected = build_using(catalog)
    if actual != expected:
        print(
            "::error::USING.md is out of sync with the catalog; run "
            "`python tools/export.py` and commit the result."
        )
        return 1
    print("USING.md is in sync.")
    return 0


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
        help="output directory for the wrappers (default: ./dist)",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="verify the committed USING.md matches a fresh generation; "
        "write nothing; exit 1 if stale (used by CI)",
    )
    args = p.parse_args(argv)

    catalog = parse_catalog(ANTIPATTERNS_MD)

    if args.check:
        return check_using(catalog)

    # The committed community guide.
    USING_MD.write_text(build_using(catalog), encoding="utf-8")
    print(f"wrote {USING_MD.relative_to(REPO)}")

    # The gitignored dist/ wrappers.
    out_dir = Path(args.out)
    variants = VARIANTS if args.variant == "both" else [args.variant]

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

        try:
            where = str(vdir.relative_to(REPO))
        except ValueError:
            where = str(vdir)  # --out pointed outside the repo
        print(
            f"[{variant}] wrote chatgpt-instructions.md ({len(chatgpt)} chars), "
            f"full-instructions.md -> {where}/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
