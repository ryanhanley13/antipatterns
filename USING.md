# Using the Antipatterns skill

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) that scrubs AI writing tells out of a draft while preserving voice. This page gets it running in whatever tool you use. The catalog currently covers **200 patterns** across 15 categories - that number is pulled live from the source, so it stays honest as the catalog grows.

Claude and Manus speak the open Agent Skills format natively, so they take the skill directly - no wrapper needed. ChatGPT and Gemini don't, so there are ready-to-paste instruction files for those (see [The ready-to-paste files](#the-ready-to-paste-files-chatgpt--gemini) below).

## Claude (best experience)
Download the latest `antipatterns.skill` from the [Releases](https://github.com/ryanhanley13/antipatterns/releases) page, then **Settings -> Skills -> Import**. The skill loads fully and fires automatically when you paste a draft or ask for content.

## Manus
**Skills -> + Add -> Import from GitHub**, then paste this repo's URL: `https://github.com/ryanhanley13/antipatterns`. Manus uses the same skill format as Claude, so it imports as-is.

## ChatGPT (a Project, not a Custom GPT)
1. Create a new **Project** (sidebar -> New project).
2. Paste `chatgpt-instructions.md` into the Project's **custom instructions**.
3. Upload `full-instructions.md` as a **file** in the Project. The custom-instructions field can't hold the full catalog, so the condensed file carries the zero-tolerance core and the full list lives in the uploaded file.

## Gemini
Create a **Gem**, then paste the contents of `full-instructions.md` as the Gem's instructions. Gems accept long instructions, so the full catalog fits in one paste.

## The ready-to-paste files (ChatGPT / Gemini)
Grab these from the [Releases](https://github.com/ryanhanley13/antipatterns/releases) page - the **community** cut is what most people want:

- **`chatgpt-instructions.md`** - the condensed (under 8,000-character) zero-tolerance core. Goes in a ChatGPT Project's custom instructions.
- **`full-instructions.md`** - the full procedure + catalog. Upload it to a ChatGPT Project, or paste it into a Gemini Gem / any tool with a system-prompt field.

To regenerate them locally (for example the `ryan` personal cut): `python tools/export.py`.

## Customize for your voice
This skill is calibrated to its author's voice. Before you rely on the voice drift check, open the catalog (`ANTIPATTERNS.md`), find the **Voice Drift Sanity Check** and **What Good Sounds Like** sections, and replace those traits with your own. The skill works best when it's tuned to you - a generic anti-AI filter strips voice along with the tells.

---

The source of truth is always `ANTIPATTERNS.md` + `SKILL.md` in the repo. `USING.md` and the `dist/` wrappers are generated from them by `tools/export.py`.
