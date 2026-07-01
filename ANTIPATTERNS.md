# ANTIPATTERNS.md

**Purpose:** This file catalogs the writing patterns, words, and structures that make text read like an LLM wrote it. Before delivering any draft, scan it against this list. Flag matches, rewrite, and never reach for the listed verbs, adjectives, or nouns unless the user used them first.

**Core rule:** It's not about banned *words*. It's about banned *densities and contexts*. One "furthermore" in a 1,500-word essay is invisible. Three "furthermores" plus a "delve" plus a "tapestry" inside 200 words gives the game away. Severity matters. Use the tier system below to triage.

---

## The Tier System

Not all antipatterns carry the same weight. Treat them in three tiers.

### Tier 1: Catastrophic (zero tolerance)
One instance ruins the piece. These are the words and phrases that scream "AI wrote this" the moment they appear. No exceptions, no edge cases, no "but in context..."

Examples: delve, tapestry, leverage, robust, navigate, foster, "In today's fast-paced world," "As an AI," the antithesis tic ("It's not X, it's Y"), the chirpy closer ("Hope this helps!"), em-dashes.

If a Tier 1 item shows up, kill it. No debate.

### Tier 2: Pattern-dependent (density matters)
Fine in isolation. Disastrous when clustered. These are the words that crop up naturally in real writing but signal AI when they repeat, stack, or appear in predictable rhythms.

Examples: furthermore, additionally, nuanced, landscape.

Rule of thumb: one is fine, two might be okay, three in a paragraph is a tell.

### Tier 3: Context-dependent (judgment call)
Legitimate vocabulary that gets reached for as filler. The question isn't "is this word banned." It's "is this word doing real work here, or is the AI grabbing for a generic intensifier?"

Examples: critical, essential, vital, important, key.

Apply the **removal test** (see False Positives section below). If the sentence survives the word's removal, the word was filler.

---

## 1. Antithesis & Contrast Tics [Tier 1]

The loudest tell. These constructions create false rhythm and signal "AI trying to sound profound."

- "It's not X, it's Y."
- "It's not just X, it's Y."
- "Not X, but Y."
- "More than just X."
- "X isn't a Y. It's a Z."
- Stacking two or three of these back-to-back for "punch"

---

## 2. Throat-Clearing Openers [Tier 1 to Tier 2]

Filler that delays the actual point. Cut and start with the substance.

**Tier 1 (never use):**
- "In today's fast-paced world..."
- "In an era of..."
- "In a world where..."
- "Great question!"
- "What a fascinating question."

**Tier 2 (depends on density):**
- "At its core,"
- "In essence,"
- "Essentially,"
- "Fundamentally,"
- "The truth is..."
- "Here's the thing..."
- "Here's the kicker..."

---

## 3. Sycophancy & Hollow Validation [Tier 1]

The model buttering up the reader before saying anything real. Especially deadly as a response opener.

- "Absolutely!"
- "Certainly!"
- "I'd be happy to help with that."
- "What a thoughtful question."
- "You raise an excellent point."
- "Brilliant observation."
- "That's a really interesting framing."
- Any opener that praises the question instead of answering it

Real engagement skips the validation and goes to substance.

---

## 4. Meta-Narration & Guided-Tour Phrases [Tier 1]

The reader doesn't need a tour guide. Just write the thing.

- "Let's dive in."
- "Let's unpack this."
- "Let's explore..."
- "Let's break this down."
- "Imagine this:"
- "Picture this:"
- "Whether you're X or Y..."
- "It's worth noting that..."
- "It's important to remember..."
- "Stick with me here..."

---

## 5. AI Disclaimers & False Humility [Tier 1]

Pre-emptive over-qualifying when the user didn't ask. Either give the answer or don't.

- "As an AI..."
- "As a language model..."
- "I'm just an AI, but..."
- "I don't have personal experience, but..."
- "While I'm not a [doctor/lawyer/financial advisor]..."
- "I can't give you definitive advice, but..."
- "Of course, this is just my perspective..."

Caveats that the user didn't ask for are noise.

---

## 6. Hedging & Fence-Sitting [Tier 1 to Tier 2]

The biggest blind spot in default LLM writing. The model refuses a point of view, presents both sides of every argument, and walks backwards out of every room with its hands up.

**Tier 1 (kill on sight):**
- "It depends on your specific situation."
- "Ultimately, the choice is yours."
- "Both approaches have merit."
- "There's no one right answer."
- Performative "on one hand / on the other hand" when no real tension exists

**Tier 2 (watch for clustering):**
- "Generally speaking..."
- "In many cases..."
- "Some would argue..."
- "It can be..."
- "Often,"
- "Typically,"

A point of view is a feature, not a risk. Take one.

---

## 7. Rhetorical Question + Answer Structure [Tier 1]

The model asks itself a question and then answers it. Reads like a committee-written TED talk.

- "What does this mean? It means..."
- "Why does this matter? Because..."
- "The question is: can you afford not to?"
- "So what should you do? Start by..."
- "Where does that leave us? Right here..."

If the answer is worth giving, give it. The fake question is theater.

---

## 8. Engagement-Bait Reveals [Tier 1]

LinkedIn-poisoning. The model promises a payoff that the next sentence rarely delivers.

- "But here's where it gets interesting..."
- "Here's the kicker..."
- "Wait until you hear this..."
- "But there's a twist..."
- "Plot twist:"
- "And then everything changed."
- "What happened next surprised everyone."

If the next line is genuinely surprising, let it be surprising on its own. Trumpets before the punchline always undercut the punchline.

---

## 9. Performative Honesty Announcements [Tier 1]

The model announcing it's about to be real, instead of just being real.

- "Let me be direct..."
- "I'll be honest..."
- "Real talk..."
- "Hot take:"
- "Brutal truth:"
- "Look, I'm just going to say it..."

Anyone who has to announce honesty isn't being honest yet. Skip the warm-up and say the thing.

---

## 10. The Contrarian Reveal Formula [Tier 2]

Important callout: the user *likes* contrarian takes. The problem is that the LLM version of "contrarian" is itself formulaic. Real contrarianism doesn't announce itself with a setup-punchline rhythm.

Banned form:
- "Most people think X. But actually Y."
- "Everyone says X. The opposite is true."
- "The common wisdom is X. Wrong."
- "Conventional thinking: X. Reality: Y."

The thinking can be contrarian. The structure can't be canned. Write the contrarian point the way it would land in conversation, not in a slide deck.

---

## 11. AI Vocabulary Tells

### Verbs (avoid unless user used them first)

**Tier 1:** delve, leverage, foster, embark, harness, usher, illuminate, navigate (as a verb for abstract topics)

**Tier 2:** cultivate, empower, unlock, elevate, resonate, drive, fuel, power, shape, transform, revolutionize, disrupt, supercharge, amplify, accelerate, redefine, reimagine, optimize, align

### Adjectives

**Tier 1:** seamless, robust, multifaceted, holistic, cutting-edge, game-changing, revolutionary, paradigm-shifting, world-class, best-in-class

**Tier 2:** nuanced, pivotal, transformative, sustainable, scalable, mission-critical, data-driven, future-proof, agile, lean, optimized, strategic, tactical

**Tier 3 (judgment):** critical, crucial, vital, essential, key, important, significant, meaningful

### Nouns & Metaphors

**Tier 1:** tapestry, treasure trove, plethora, myriad, synergy, testament, cornerstone

**Tier 2:** landscape, ecosystem, journey, realm, alignment, optimization, engagement, transformation, evolution, paradigm, framework, methodology, mindset, philosophy

### Stock Phrases [Tier 1]

- "plays a crucial role"
- "pave the way for"
- "speaks volumes"
- "stand the test of time"
- "two sides of the same coin"
- "the power of [X]"
- "captures the essence"
- "a wealth of [X]"
- "best practices"
- "going forward"
- "move the needle"
- "push the envelope"
- "no one-size-fits-all"
- "delicate balance between"
- "speaks to a broader trend"
- "lean into"
- "double down on"
- "unlock the potential"
- "shift the paradigm"
- "rise to the occasion"
- "weather the storm"
- "the dust settles"
- "stay ahead of the curve"
- "at the end of the day"
- "when all is said and done"

---

## 12. Stat-Flavored Vagueness [Tier 1]

Authority cosplay. The model invokes data without ever naming the data.

- "Studies show..."
- "Research suggests..."
- "Experts agree..."
- "Data tells us..."
- "Statistics indicate..."
- "Reports have found..."

Either name the source, or cut the appeal to authority. Vague stats are worse than no stats.

---

## 13. Transition Robots [Tier 2]

These transitions are the connective tissue of LLM-generated text. Use real transitions or none at all.

- Furthermore
- Moreover
- Additionally
- That said,
- In conclusion,
- To summarize,
- In summary,
- Ultimately,

One per long piece, maybe. Two is a flag. Three is a confession.

---

## 14. Structural & Formatting Tics

**Tier 1:**
- **Em-dashes** (hard ban already in place)
- **Em-dash rhythm replacements** when the dash is removed but the cadence isn't: drama parentheticals (`(and this changes everything)`), the staccato sentence break preserving dash-shaped pacing
- **Colon density / setup-payoff colons:** AI uses colons far more than humans do, especially as dramatic setup before a "reveal" sentence or fake-list intro. Examples: "Here's what's actually happening:" / "The result:" / "Three things to know:" / "The truth:" / "Bottom line:". Removal test: drop the colon and the setup phrase. Did the prose lose anything? If no, the colon was theatrical pacing. Legitimate uses (real itemized lists, time, ratios, subtitles like "The Status Trap: How...") are exempt. Density flag: more than one or two prose colons per piece is a tell.
- **Bolded bullet lead-ins:** every bullet starts with `**Two-word concept:**` followed by the same colon-led structure
- **Triplet-rhythm prose:** "Clear, compelling, and concise." "Fast, focused, and effective." Tricolon abuse outside of lists.
- **Imperative-pair listicle structure:** "Stop doing X. Start doing Y." "Less talking. More doing." "Forget X. Embrace Y." LinkedIn fortune cookies.
- **Single-word punch sentences:** "Period." "Done." "Boom." "Full stop." Faux conviction.

**Tier 2:**
- **Bullet-pointing prose:** breaking up conversational answers into lists that didn't need to be lists
- **Header pollution:** H2/H3 headers slapped onto responses that should flow as prose
- **Random mid-paragraph bolding** for "emphasis"
- **One-sentence paragraphs stacked** for fake gravitas. LinkedIn-poetry mode.
- **Anaphora abuse:** "It's about X. It's about Y. It's about Z."
- **Unsolicited TL;DR labels** at the top or bottom of short pieces
- **Summary recap tables** appearing after explanatory prose

---

## 15. Closing Tics [Tier 1]

- "I hope this helps! Let me know if you have any other questions!"
- "Hope that's useful!"
- "Happy to clarify anything!"
- "Let me know if you'd like me to expand on any of these!"
- "Feel free to ask if anything is unclear."
- The full recap close: restating the entire response right after delivering it
- The italicized one-liner closer: *That's the real shift.* *This is everything.*
- The "and that's [adjective]" closer: "And that's powerful." "And that's the truth."
- The maxim closer: "The future belongs to the bold." "Fortune favors the brave." "X belongs to the Y."
  - **Context note:** Maxim closers are a tell in standard prose (LinkedIn posts, essays, blog posts, professional writing). They're acceptable in *deliberately* motivational or inspirational content (keynote closers, manifesto-style writing, anthem pieces) where the tone is explicitly anthemic. Use the voice drift check to decide: does the piece earn the maxim, or did the maxim show up because the model ran out of ideas?

End on substance. The piece either lands or it doesn't. A chirpy outro doesn't save a weak ending and it kneecaps a strong one.

---

## False Positives: The Removal Test

Most Tier 3 words (critical, essential, vital, important) have legitimate uses. The skill isn't avoiding the word. The skill is detecting whether it's doing work.

**The removal test:**
1. Take out the suspect word.
2. Read the sentence.
3. Does the sentence still say what it needs to say?

If yes, the word was filler. Cut it.
If no, the word is carrying real weight. Keep it.

**Worked examples:**

> "Critical infrastructure faces new threats." → Remove "critical": "Infrastructure faces new threats." The meaning shifts. The word is doing real work. Keep it.

> "It's critical to plan ahead." → Remove "critical": "It's [important/key/vital] to plan ahead." Any intensifier swaps in cleanly. The word is filler. Rewrite the whole sentence with a concrete reason: "Plan ahead or you'll miss the window."

> "Vital signs were normal." → Remove "vital": "Signs were normal." Different meaning. Keep it.

> "It's vital that we move quickly." → Remove "vital": "We need to move quickly." Cleaner. The word was throat-clearing.

**Other false-positive guardrails:**

- **User's vocabulary trumps the list.** If the user reaches for "leverage" or "ecosystem" in their own writing, those words are not banned in their voice. Match register, don't impose ours.
- **Technical domain terms get a pass.** "Robust" in software architecture, "harness" in motorsports, "delve" in academic archaeology. Domain meaning beats the AI tell.
- **Quoted material is exempt.** If you're quoting someone else, do not edit the quote. Flag the AI tell in your commentary, not the source.

---

## Pre-Delivery Checklist

Before any draft ships, run this scan:

1. **Tier 1 sweep:** Any catastrophic items present? Fix immediately. No exceptions.
2. **Antithesis check:** Any "not X, it's Y" patterns? Rewrite.
3. **Opener check:** Does the first sentence carry weight, or is it throat-clearing or sycophancy?
4. **Hedging check:** Did we duck a position the piece needed to take?
5. **Verb scan:** Search Tier 1 and Tier 2 verb lists. Replace with concrete action verbs.
6. **Adjective scan:** Search the adjective list. Cut filler or replace with specific descriptors.
7. **Metaphor scan:** Any tapestry, landscape, journey, ecosystem? Kill them.
8. **Transition scan:** Any "furthermore," "moreover," "additionally"? Reduce or delete.
9. **Tier 3 removal test:** For every "critical," "essential," "vital," "key," "important," run the removal test.
10. **Closer check:** Does the piece end on substance, or with a chirpy "hope this helps"?
11. **Density check:** Even if individual items pass, did we hit three or more Tier 2 or Tier 3 flags inside one paragraph?
12. **Voice drift check (see below).**

If any check fails, rewrite before delivery.

---

## Voice Drift Sanity Check

This list grows over time. Every rewrite makes the filter stricter. Without a counter-pressure, we will eventually strip the voice along with the AI tells.

After a rewrite passes the antipattern scan, run one more pass with these questions:

1. **Does it still sound like Ryan?** Read it out loud. Does the rhythm match how he'd actually say it? Does the punch survive?
2. **Did we lose specifics?** AI tells often hide vagueness. The fix is concreteness, not just deletion. If the rewrite is shorter but vaguer, we made it worse.
3. **Did we strip the personality?** Dirty humor, contrarian edge, Gen X bluntness, locker-room directness. These are features. If the rewrite reads like a corporate memo, we overcorrected.
4. **Is there still a point of view?** Antipattern removal can flatten opinions into neutrality. If the piece no longer takes a side, put the side back in.
5. **Did we lose the rhythm?** Ryan writes with intentional fragments, short punches, and conversational asides. A rewrite that smooths all of that out is also wrong.

The goal isn't sanitized text. The goal is text that sounds like Ryan and doesn't sound like an LLM. Those are two different criteria. Both have to pass.

---

## What Good Sounds Like

Short sentences. Concrete nouns. Verbs that do work. A point of view. Voice. Specifics over abstractions. Contractions. The occasional fragment for punch. Confidence without bluster. The willingness to be wrong instead of the refusal to commit.

When in doubt: write it the way Ryan would say it out loud.

---

## Versioning

When new antipatterns get added to this file, log them at the bottom with a date and a short note on what prompted the add. Helps catch overcorrection and lets us audit what's actually showing up in drafts versus what's hypothetical.

### Change log
- **2026-07-01:** Added `critical` to the §11 Tier-3 adjective list. It was missing despite being the word used to demonstrate the removal test ("It's critical to plan ahead") and listed in the Tier System overview — only `crucial` was in the detailed list. Surfaced by scan.py, which faithfully reports only what's cataloged.
- **2026-07-01:** Reconciled the "## The Tier System" overview examples with the §11 detailed lists. The overview listed `leverage`, `robust`, `navigate`, `foster` as Tier-2 examples, but §11 catalogs them as Tier 1 (verbs/adjectives). Moved them to the Tier-1 overview line; replaced the Tier-2 overview examples with genuine Tier-2 words (`furthermore`, `additionally`, `nuanced`, `landscape`). §11 is the authoritative source the skill scans against; the overview now matches it.
- **2026-05-15:** Added Section 14 entry for colon density / setup-payoff colons (Tier 1). Caught during first skill test when the cleaned draft itself contained "Here's what's actually happening:" as a dramatic setup colon. Pattern was previously buried as a sub-example under em-dash replacements; promoted to its own bullet with examples, removal test, and density rule.
- **2026-05-15:** Added "maxim closer" entry to Section 15 ("The future belongs to the bold," "Fortune favors the brave," etc.) with a context note: tell in standard prose, acceptable in deliberately motivational content. Surfaced during first skill test.
- **v2 (2026-05-14):** Added tier system, sycophancy, hedging, AI disclaimers, rhetorical question structure, engagement-bait reveals, performative honesty, contrarian-reveal formula, stat-flavored vagueness, expanded verb/adjective/noun lists, em-dash rhythm ban, additional structural tics, false-positive removal test, voice drift sanity check, versioning section.
- **v1:** Initial file.

---

*This is the way.*
