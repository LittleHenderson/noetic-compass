# 02 — Labeling guide, version 0.2 (after the first look)

For label teams only. Never show this guide to case writers or to anyone tuning a reader.

Status: draft. Part A is canon and is unchanged from version 0.1. Part B is this study's working convention; version 0.2 changes it where the first look (40 practice passages, three label teams) showed the teams reading it differently. Every change is listed at the end.

## Part A — The definitions (canon, word for word)

Source: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`, Clarification 1, commit `1c8531ea`.

- `^0` **Idea** — All things in and outside the Mind.
- `^1` **Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- `^2` **Positive** — An Idea the Mind has an affinity for and is attracted toward.
- `^3` **Negative** — An Idea the Mind is adverse to and repelled by.
- `^4` **Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- `^5` **Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- `^6` **Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- `^7` **Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- `^8` **Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- `^9` **Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

These are not everyday meanings. Female and Male say nothing about gender. Positive and Negative do not mean good and bad. A Mind can be a person, an animal, a group or a machine.

If you are unsure, use the Colloquialism Test from Clarification 6: ask what everyday saying fits the moment, then see which definition that saying matches. If a saying and a definition disagree, the definition wins.

| Noetic | Sayings that fit (from Clarification 6) |
|---|---|
| `^1` Mind | "Paying attention." "Making up your mind." "Using your head." |
| `^2` Positive | "Drawn to it like a moth to a flame." "Speaks to me." "Can't resist." |
| `^3` Negative | "Can't stomach it." "Rubs me the wrong way." "Wouldn't touch it with a ten-foot pole." |
| `^4` Vibration | "Hit me hard." "Struck a chord." "Resonated." "Made an impression." |
| `^5` Female | "We are the sum of our experiences." "It's who I am." "Part of what makes me me." |
| `^6` Male | "Unpacking an idea." "Breaking it down." "Looking at what's underneath." |
| `^7` Rhythm | "Practice makes perfect." "You are what you repeatedly do." "Muscle memory." |
| `^8` Above/Cause | "That reminds me..." "One thing leads to another." "Triggered a memory." |
| `^9` Below/Effect | "It just popped into my head." "The thought came to me." "It just clicked." |

Two warnings from Clarification 6:

- `^3` is felt aversion. Finding flaws, auditing or criticizing by analysis is not `^3`; taking something apart is `^6`.
- `^8` is one Idea bringing a different Idea to Mind. Working out a cause by reasoning is not `^8`.

## Part B — How to label in this study (working convention, v0.2)

### What you produce

For each passage, a list of entries. Each entry says: this Noetic is occupied by these exact words, for this Mind, relative to this other thing.

```json
{"passage_id": "P00",
 "none_of_these": false,
 "entries": [
   {"noetic": "^8", "words": "the squeak of the gate", "mind": "Ines", "relative_to": "her first bicycle", "certainty": "clear"},
   {"noetic": "^9", "words": "her first bicycle", "mind": "Ines", "relative_to": "the squeak of the gate", "certainty": "clear"}
 ],
 "not_enough_information": []}
```

Rules for the fields:

- `words`: copied exactly from the passage, one unbroken stretch, as short as possible while still naming the thing.
- `mind`: the exact words the passage uses for whose Mind it is. Use `""` only where the Noetic has no Mind in its definition (`^6`).
- `relative_to`: exact words from the passage for the other thing, or `""` if there is none. See the table below.
- `certainty`: `"clear"` or `"ambiguous"`. If ambiguous, add `"other_candidate": "^n"`.
- `none_of_these`: `true` when no Noetic `^1` to `^9` is occupied by anything in the passage. Then `entries` is empty.
- `not_enough_information`: short notes for things the passage hints at but does not settle. Do not turn a hint into an entry.

Never force a label. An honest "ambiguous", "not enough information" or "none of these" is a correct answer.

### What to mark for each Noetic

| Noetic | `words` = | `mind` = | `relative_to` = |
|---|---|---|---|
| `^1` Mind | the name or mention of each Mind in the passage, listed once per Mind (see rule 4) | the same mention | `""` |
| `^2` Positive | the Idea the Mind has an affinity for and is attracted toward | that Mind | `""` |
| `^3` Negative | the Idea the Mind is adverse to and repelled by | that Mind | `""` |
| `^4` Vibration | the words that state how strongly or how weakly the Idea impresses the Mind (see rule 10) | that Mind | the Idea that resonates |
| `^5` Female | the Idea or Ideas the Mind is composed of (what it has lived, learned, come to believe, become skilled in) | that Mind | `""` |
| `^6` Male | the Idea or Ideas that another Idea is composed of | `""` | the Idea they compose |
| `^7` Rhythm | the words that state the rate and pattern of exposure | the Mind exposed | the Idea it is exposed to |
| `^8` Above/Cause | the Idea that triggers a different Idea to come to Mind | that Mind | the Idea it brings to Mind (the `^9`) |
| `^9` Below/Effect | the Idea brought to Mind | that Mind | its trigger (the `^8`) |

`^0` Idea is not an entry. Every thing you point to is an Idea. You are not asked whether an Idea is present.

### Working rules

1. **One passage, many entries.** Mark every Noetic the passage settles. The same words may occupy two Noetics; write two entries.
2. **`^8` and `^9` come as a pair.** Mark the pair only when the passage says or plainly shows that noticing one thing brought a different thing to Mind. For `relative_to`, quote the other member of the pair from wherever it appears in the passage. If two things merely sit side by side, or the passage gives only one of them, mark neither and write a note under `not_enough_information`.
3. **No Mind, no `^8`/`^9`.** Rain making a road wet is not `^8`. The definition needs an Idea coming to Mind. Recalling something on purpose, with no named thing that brought it up, is not a pair either.
4. **List every Mind once.** A Mind is any person, animal, group or machine that the passage shows taking in, holding, working on or putting out at least one Idea. If you gave something any other entry as its `mind`, it is a Mind: add one `^1` entry for it. A person who is only mentioned, with nothing of their awareness shown, is not listed. Quote the first full mention of the name.
5. **`^2`/`^3` need the passage to show it.** A neutral mention of a thing is neither. What a Mind does counts when the passage presents it as being drawn toward or repelled by the thing (seeking it out, lingering over it; steering clear of it, being unable to touch it). Plain absence or plain routine does not count. Strength does not matter here: a mild pull or a mild unease counts when the passage states it. How strong it is belongs to `^4`.
6. **`^5` is what the Mind is made of; `^7` is the schedule of exposure.** A length of time alone ("thirty years on the wards") is `^5`, not `^7`. `^7` needs words for a rate or a pattern ("every morning", "twice a week", "again and again"). If the passage gives both the schedule and what the Mind has become, mark both, with different words.
7. **`^6` needs named parts.** Mark `^6` only when the passage names at least one thing that another thing is made of. Step-by-step thinking with no named parts is not `^6`. If the parts are separated by other words, write one entry per part.
8. **Do not label Worlds, Domains, Drives or Registers.**
9. **Do not use outside knowledge.** Label only what this passage says.
10. **`^4` needs words for how much.** Mark `^4` only when the passage says how strongly or how weakly a thing impressed the Mind ("could not stop thinking about it", "it barely registered", "left him cold", "it stayed with her all week"). The size of a bodily reaction counts when the passage presents it as the size of the impression. A reaction with no sense of how much is not `^4`.
11. **Several Noetics on one moment are normal.** A trained response can be `^5` (what the Mind is made of), `^7` (the schedule that built it) and an `^8`/`^9` pair (a signal bringing something to Mind) at once. Mark each one the passage settles.
12. **For `^7`, `relative_to` may be an activity.** Quote the words for what the Mind was repeatedly exposed to, whether a thing or an activity.
13. **A cue that sets off an action.** If the passage shows the cue bringing the action, or a thought of it, to Mind, mark the `^8`/`^9` pair. If it shows only that the Mind now acts without thinking, mark `^7` (and `^5` if the passage states what the Mind has become) and no pair.
14. **Ambiguous between a Noetic and nothing.** Write `"certainty": "ambiguous"` with `"other_candidate": "none"`.

### Three made-up examples (never used as cases)

Passage X1: "Renate lifted the lid and the steam smelled of cloves. At once she was back in her aunt's hallway, coat still on, nine years old."
Entries: `^1` words "Renate"; `^8` words "the steam smelled of cloves", mind "Renate", relative_to "her aunt's hallway"; `^9` words "her aunt's hallway", mind "Renate", relative_to "the steam smelled of cloves".

Passage X2: "The conveyor ran all night. Crates dropped from the chute, slid to the scale and were pushed left or right by a metal arm."
`none_of_these`: true.

Passage X3: "Odile read the proposal twice and set it down."
`^1` words "Odile" (her awareness is intaking the proposal). Nothing settles whether she is attracted toward it or repelled by it: add a note under `not_enough_information`. No `^2`, no `^3`.

Passage X4: "The first review of his book hit Anselm harder than he expected; he read it four times before lunch. The second one he skimmed and forgot by evening."
Entries: `^1` words "Anselm"; `^4` words "hit Anselm harder than he expected", mind "Anselm", relative_to "The first review of his book"; `^4` words "skimmed and forgot by evening", mind "Anselm", relative_to "The second one".

## Changes from version 0.1

Found in the first look (see `first_look/FIRST_LOOK_REPORT.md`). Part A is unchanged.

| Rule | Change | Why |
|---|---|---|
| 2, 3 | A pair needs the passage to say or plainly show the bringing-to-Mind; `relative_to` may quote the partner from anywhere in the passage; recall on purpose is not a pair | Teams differed on implied links and on recall by experts |
| 4 | Every Mind is listed once, by a mechanical test | `^1` agreement was the lowest of all: one team marked 19 passages, another 34 |
| 5 | Actions count when presented as attraction or repulsion | Teams differed on avoidance with no stated feeling |
| 6 | A length of time alone is `^5`; `^7` needs rate or pattern words | Teams confused `^5` and `^7` |
| 7 | `^6` needs at least one named part | Teams differed on stepwise reasoning |
| 10 | New: what counts as stating a degree; one new example (X4) | `^4`: one team marked 10 passages, another 2 |
| 11, 12 | New: several Noetics on one moment; activity as `relative_to` for `^7` | Raised by two teams |
| 5 (added sentence) | Strength does not matter for `^2`/`^3`; strength belongs to `^4` | Teams differed on mild unease |
| 7 (added sentence) | One entry per part when parts are split up | The one-unbroken-quote rule forced long quotes |
| 13, 14 | New: a cue that sets off an action; ambiguous between a Noetic and nothing | Raised by one team each |

These are conventions for applying the definitions in this study. They do not change a definition. The owner may correct any of them.
