# antipatterns

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) that scans written drafts for AI writing tells and rewrites them out without flattening your voice.

Built originally for [Ryan Hanley's](https://ryanhanley.com) content workflow at Finding Peak. The catalog is opinionated, the voice is specific, and that's the point. **Fork it, customize it, and make it yours.**

## What it does

Detects the structural patterns, vocabulary, and rhythms that make text read like a language model wrote it:

- Cliched vocabulary (`delve`, `tapestry`, `leverage`, `robust`, `holistic`)
- Antithesis tics ("It's not X, it's Y")
- Dramatic colons and em-dash rhythms
- Hedging and sycophancy
- Stat-flavored vagueness ("Studies show...")
- Bolded bullet lead-ins, anaphora abuse, triplet-rhythm prose
- Stock phrasing and chirpy closers
- About 200 more, organized into 15 categories

Then it rewrites the offending sections and runs a **voice drift check** to make sure the cleanup didn't sanitize the writing into corporate sludge.

## Quick before/after

**Before (deliberately AI-flavored):**

> In today's fast-paced world, AI is transforming the insurance landscape. It's not just a technology shift, it's a complete paradigm shift. Furthermore, agents who fail to leverage these tools will be left behind.

**After:**

> AI is changing how insurance gets sold. Agents who don't pick up the tools now are going to lose accounts to the ones who did.

## What's in the box

| File | Purpose |
|------|---------|
| `SKILL.md` | The skill procedure: when to trigger, workflow, output format, failure modes |
| `ANTIPATTERNS.md` | The catalog: 15 sections, ~200 patterns, tier system, removal test, voice drift check |
| `add_pattern.py` | Interactive CLI for adding new patterns as you spot them |
| `antipatterns.skill` | Packaged installable bundle for Claude.ai |

## Installation

### For Claude.ai (web/desktop/mobile)

1. Download `antipatterns.skill` from this repo (or the [Releases](../../releases) page).
2. Import via Settings → Skills.

### For Claude Code

Drop the three files into your user skills directory:

```bash
mkdir -p ~/.claude/skills/antipatterns
cp SKILL.md ANTIPATTERNS.md add_pattern.py ~/.claude/skills/antipatterns/
```

### Manual (any setup)

Clone this repo and place `SKILL.md`, `ANTIPATTERNS.md`, and `add_pattern.py` together in whatever skill folder your Claude environment uses. They have to live in the same directory because `SKILL.md` references `ANTIPATTERNS.md` as a sibling file.

## How it triggers

The skill fires automatically when you:

- Paste a draft and ask for review, edits, or cleanup
- Ask Claude to write content (LinkedIn posts, blog posts, podcast scripts, newsletters, etc.) — it scans its own output before delivering
- Use phrases like "voice check," "AI tells," "antipatterns," "tighten this," "clean this up," or "make this not suck"

It does **not** fire on code, technical docs, code reviews, resumes/CVs, casual chat, summaries, translations, outlines, or pre-draft brainstorming.

## The tier system

Not all antipatterns carry the same weight.

- **Tier 1 (catastrophic):** Zero tolerance. One instance ruins the piece. Examples: `delve`, `tapestry`, "In today's fast-paced world," chirpy closers.
- **Tier 2 (density-dependent):** Fine in isolation. Disastrous when clustered. Examples: `furthermore`, `leverage`, `robust`.
- **Tier 3 (context-dependent):** Legitimate vocabulary that gets reached for as filler. Use the removal test. Examples: `critical`, `essential`, `vital`.

## The removal test (for Tier 3)

1. Take out the suspect word.
2. Read the sentence.
3. Does it still say what it needs to say?

If **yes**, the word was filler. Cut it.
If **no**, keep it.

Example: "It's critical to plan ahead." → Remove "critical" → "It's important to plan ahead" reads the same → word was filler. Rewrite with a real reason: "Plan ahead or you'll miss the window."

## Adding new patterns

When the skill spots a pattern that's not in the catalog, it proposes the addition at the end of its output. To apply approved additions:

```bash
python add_pattern.py path/to/ANTIPATTERNS.md
```

Interactive prompts walk you through:
- Section selection (15 categories)
- Tier assignment (for tier-split sections)
- The pattern text
- A change log entry (dated automatically)

The file is updated in place. The change log at the bottom of `ANTIPATTERNS.md` tracks every addition.

## Customizing for your voice

This skill is calibrated to a specific person's voice (mostly direct, Gen X register, intentional fragments, conversational, signature sign-off). To use it for your own voice:

1. **Fork this repo.**
2. **Edit the Voice Drift Check section** in `ANTIPATTERNS.md`. Replace the calibration questions with traits that match YOUR voice.
3. **Edit the "What Good Sounds Like" section** at the bottom of `ANTIPATTERNS.md`.
4. **Edit references to "Ryan"** in `SKILL.md` to your name.
5. **Curate the catalog.** Some entries flag vocabulary or rhythms that are legitimate parts of your voice. Move them to Tier 2 or remove them.
6. **Add your own patterns.** Every writer has personal tells. Run `add_pattern.py` to catalog them.

The skill works best when it's calibrated. A generic anti-AI filter strips voice along with the AI tells. A personal anti-AI filter preserves YOUR voice while killing the LLM defaults.

## Coordination with other skills

The skill is designed to run independently of other content-editing skills (like the Diamond Content Filter, if you have one). Both can fire on the same draft and do different jobs:

- Editorial filters shape substance, structure, and argument.
- Antipatterns scrubs the surface: vocabulary, rhythm, structural tics.

Run editorial first, antipatterns second.

## Contributing

Pull requests welcome. Especially:

- New antipatterns you've caught in the wild (with examples)
- Tier reassignments based on real-world false positives
- Improvements to `add_pattern.py` (the v1 has limitations around sub-bullet entries)
- Translation to other voices (forks with different calibrations)

For new patterns, include:
- The pattern itself
- Why it's a tell (1-2 sentences)
- Suggested tier
- An example from real text

## License

MIT. Use it, fork it, change it, ship it.

## Credit

Built by [Ryan Hanley](https://ryanhanley.com) through iterative pair-programming with Claude. The original `ANTIPATTERNS.md` was a personal style guide that grew into a full Claude skill over the course of an afternoon.

If this saves you from publishing "Let's dive into this fascinating topic" one more time, my work here is done.

This is the way.
