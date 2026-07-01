---
name: antipatterns
description: Scan written drafts for AI writing tells and rewrite them out without flattening voice. Detects cliched vocabulary, antithesis tics, dramatic colons, em-dash rhythms, hedging, sycophancy, stat-flavored vagueness, stock phrasing, and chirpy closers. Triggers when a draft is reviewed, edited, refined, polished, or finalized; when the user pastes content for feedback or a "thoughts?"-style review; when Claude is about to deliver written content (LinkedIn posts, X threads, Substack pieces, blog posts, podcast scripts, newsletters, keynote notes); or when the user says "voice check," "AI tells," "antipatterns," "sound less like AI," "tighten this," "clean this up," "make this not suck," or similar. Outputs a cleaned draft, a tier-grouped flag list, and a voice drift check. Do NOT trigger on code, technical documentation, code review comments, PR descriptions, resumes, CVs, cover letters, system prompts, quoted material, casual chat replies, summaries, translations, outlines, or pre-draft brainstorming.
---

# Antipatterns Skill

This skill detects AI writing tells in any text and rewrites them out without losing voice.

The catalog of tells lives in `ANTIPATTERNS.md` in this same folder. That file is the data. This file is the procedure. Read the catalog before every run. It evolves, and cached knowledge goes stale.

## The contrarian framing

Most "AI detection" guides focus on banned words. This skill focuses on banned rhythms, banned densities, and banned structures. Words are downstream of patterns. "Delve" is a Tier 1 banned word, but the deeper problem is the cadence and tone that produced "delve" in the first place. Treat the scan as structural, not lexical.

## When to run

Run this skill whenever any of the following apply:

- The user pastes a draft and asks for review, edits, cleanup, or feedback
- The user asks Claude to write content (essays, blog posts, LinkedIn posts, X threads, Substack pieces, podcast scripts, email sequences, newsletter copy, keynote notes, anything that ships)
- The user says any of: "check this," "tighten this," "voice check," "AI tells," "sound less like AI," "run antipatterns," "is this AI-sounding," "scan this"
- Claude is about to deliver content Claude itself just wrote. Run the skill on Claude's own draft before showing the user.

Do NOT run this skill on:

- Code, technical documentation, system prompts, tool outputs (different rules apply)
- Code review comments, PR descriptions, or other engineering team communication
- Resumes, CVs, cover letters, or other career documents (different genre, different rules)
- Direct quotes from third parties. Do not edit other people's words.
- Casual back-and-forth chat replies. This is a content skill, not a conversation linter.
- Outlines, brainstorms, or pre-writing where no draft exists yet.
- Summaries and translations of other people's work.

## Workflow

### Step 1: Read the catalog
Open `ANTIPATTERNS.md`. Load the tier system, every category, the removal test, the false-positive guardrails, and the voice drift check questions. Do not skip this step. If the file has been updated since the last run, the new patterns matter.

### Step 2: Scan the draft
First, run the deterministic sweeper for a lexical baseline:

```bash
python scan.py path/to/draft.md
```

(Or `python scan.py -` to read stdin. Add `--allow word,word` to suppress the user's own vocabulary, `--strict` to exit nonzero on any Tier 1 hit or em-dash, `--json` for machine-readable output.)

`scan.py` reads `ANTIPATTERNS.md` as its source of truth and counts every Tier 1/2/3 word and phrase, plus em-dashes, and reports per-paragraph density. It grounds the scan in numbers instead of vibes: exactly how many "furthermore"s land in one paragraph, where the em-dashes are, what the per-1000-word rate is. Use its output as the floor.

It is **lexical only**. It cannot see antithesis tics, triplet rhythm, colon density, anaphora, or the contrarian-reveal formula. Those are structural and stay your job below. Treat the scan as the measurable layer; the rest is judgment.

Then walk the draft from top to bottom. For each suspect word, phrase, structure, or rhythm:

- Identify which antipattern category it belongs to
- Tag the tier (1, 2, or 3)
- For Tier 3 items, apply the removal test from `ANTIPATTERNS.md` before flagging. (`scan.py` lists Tier 3 hits as candidates only, never as flags, for exactly this reason.)
- Apply false-positive guardrails: skip the flag if the word is in the user's own vocabulary, in a technical domain context, or inside a direct quote

### Step 3: Rewrite
Fix Tier 1 items every time. Fix Tier 2 items when density is high or when they cluster within a paragraph. Fix Tier 3 items only when the removal test confirms the word was filler.

Rewrites must preserve:

- Voice (Ryan's voice, not a sanitized version)
- Specifics (do not replace concrete claims with vaguer ones)
- Point of view (do not flatten opinions into neutrality)
- Rhythm (intentional fragments, short punches, conversational asides, Gen X bluntness)

If a rewrite makes the text shorter but vaguer, the rewrite is wrong. Redo it.

### Step 4: Run the voice drift check
Before delivering, answer the five voice drift questions from `ANTIPATTERNS.md`. If any answer is no, go back to Step 3. Do not deliver a draft that fails this check.

### Step 5: Spot new candidates
While scanning, watch for patterns that aren't in `ANTIPATTERNS.md` yet but feel like AI tells. Signals:

- Same construction repeats three or more times across the draft
- A phrase or rhythm fits the spirit of an existing category but isn't on any list
- A new vocabulary cluster that signals "model is reaching for stock phrasing"

Do NOT add patterns to the file unilaterally. Surface them as proposals at the end of the output. The user owns the canonical catalog.

### Step 6: Deliver in the standard output format below.

## Output Format

Use this exact structure every time. Section headers in bold. Keep it skimmable.

---

**CLEANED DRAFT**

The rewritten text. Clean copy, no inline annotations, no commentary mid-draft.

---

**FLAGS**

Grouped by tier. Show what got flagged, the original text, and what it became. Keep each entry to one line where possible.

Tier 1:
- [Category]: "[original]" → "[rewrite]"

Tier 2:
- [Category]: "[original]" → "[rewrite]" (flagged: [density or cluster reason])

Tier 3:
- [Word]: "[original sentence]" → "[rewrite]" (removal test: filler)

If a tier had no flags, write "Tier N: clean."

---

**VOICE DRIFT CHECK**

Five-question pass. Short answers, with reason if no.

1. Sounds like Ryan: [yes / no, with reason]
2. Specifics intact: [yes / no, with reason]
3. Personality preserved: [yes / no, with reason]
4. Point of view present: [yes / no, with reason]
5. Rhythm preserved: [yes / no, with reason]

If any answer is no, redo Step 3 before delivering.

---

**PROPOSED ADDITIONS** (only if applicable)

If new candidate patterns surfaced during the scan:

- Proposed: [the pattern]
- Category: [existing category name, or "new category: X"]
- Suggested tier: [1, 2, or 3]
- Why: [short rationale, ideally with the actual example from this draft]

Wait for the user to approve, reject, or modify. To apply approved additions, run the bundled `add_pattern.py` script from the skill folder:

```bash
python add_pattern.py path/to/ANTIPATTERNS.md
```

The script walks through category selection, tier assignment (for tier-split sections), the new pattern text, and a log entry. It handles flat sections, tier-split sections (2, 6, 14), and the vocabulary subsections in Section 11 (verbs, adjectives, nouns, stock phrases). It updates the file in place and appends a dated entry to the change log.

---

## Worked Example (abbreviated)

To anchor the format, here's a short input and the structure of the output. Real outputs run longer.

**Input draft (3 sentences, AI-flavored):**
> In today's fast-paced world, AI is transforming the insurance landscape. It's not just a technology shift, it's a complete paradigm shift. Furthermore, agents who fail to leverage these tools will be left behind.

**CLEANED DRAFT**

> AI is changing how insurance gets sold. Agents who don't pick up the tools now are going to lose accounts to the ones who did.

**FLAGS**

Tier 1:
- Throat-clearing opener: "In today's fast-paced world" → cut
- Antithesis tic: "It's not just a technology shift, it's a complete paradigm shift" → cut and replace with concrete claim
- Verb: "leverage" → "pick up"
- Noun cluster: "landscape," "paradigm shift" → cut both

Tier 2:
- Transition robot: "Furthermore" → cut

Tier 3:
- "transforming": removal test failed (filler intensifier) → "changing"

**VOICE DRIFT CHECK**

1. Sounds like Ryan: yes (short, direct, punchy)
2. Specifics intact: partial. Original was already vague on tools. Rewrite stays at that level. Flag: a fuller draft should name the tools.
3. Personality preserved: yes (the "lose accounts to the ones who did" line has bite)
4. Point of view present: yes
5. Rhythm preserved: yes

**PROPOSED ADDITIONS:** none this run.

## Coordination with other skills

This skill runs independently from the Diamond Content Filter. Both can fire on the same draft. The Diamond Filter does three-stage editorial refinement on substance, structure, and voice. This skill does AI-tell detection and surgical rewriting. They do different jobs.

If both skills run on the same draft, run Diamond first, then run this skill on the Diamond output. The Diamond Filter shapes the piece. Antipatterns scrubs it.

Do not skip this skill just because Diamond ran. Diamond does not catch all AI tells. This is a separate quality gate.

## Failure modes to watch for

- **Overcorrection.** Stripping voice along with tells. Catch this with the voice drift check.
- **False positives on Tier 3.** Skipping the removal test and flagging legitimate uses of "critical" or "essential." Always run the test.
- **Catalog drift.** Adding patterns too aggressively and ballooning the file. New additions need rationale and tier assignment before they go in.
- **Ignoring user vocabulary.** Ryan uses certain "banned" words on purpose. Those are exempt in his voice. Match register.
- **Lexical-only scanning.** Catching words but missing rhythms. The structural tics (antithesis, contrarian-reveal formula, triplet rhythm, anaphora) are often more damaging than any single word.

## One last rule

When in doubt, write it the way Ryan would say it out loud.

*This is the way.*
