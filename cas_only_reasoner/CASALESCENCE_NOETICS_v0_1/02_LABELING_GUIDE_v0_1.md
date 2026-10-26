# 02 — Labeling guide, version 0.1 (first-look draft)

For label teams only. Never show this guide to case writers or to anyone tuning a reader.

Status: draft. Its purpose in the first look is to find out where it is unclear. Part A is canon and may not be changed. Part B is this study's working convention and will change when the first look shows a problem.

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

## Part B — How to label in this study (working convention, v0.1)

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
| `^1` Mind | the mention of a Mind whose awareness the passage shows at work on Ideas (processing, storing, outputting or intaking them) | the same mention | `""` |
| `^2` Positive | the Idea the Mind has an affinity for and is attracted toward | that Mind | `""` |
| `^3` Negative | the Idea the Mind is adverse to and repelled by | that Mind | `""` |
| `^4` Vibration | the words that state the degree to which the Idea resonates with the Mind (strong or weak) | that Mind | the Idea that resonates |
| `^5` Female | the Idea or Ideas the Mind is composed of (what it has lived, learned, come to believe, become skilled in) | that Mind | `""` |
| `^6` Male | the Idea or Ideas that another Idea is composed of | `""` | the Idea they compose |
| `^7` Rhythm | the words that state the rate and pattern of exposure | the Mind exposed | the Idea it is exposed to |
| `^8` Above/Cause | the Idea that triggers a different Idea to come to Mind | that Mind | the Idea it brings to Mind (the `^9`) |
| `^9` Below/Effect | the Idea brought to Mind | that Mind | its trigger (the `^8`) |

`^0` Idea is not an entry. Every thing you point to is an Idea. You are not asked whether an Idea is present.

### Working rules

1. **One passage, many entries.** Mark every Noetic the passage settles. The same words may occupy two Noetics; write two entries.
2. **`^8` and `^9` come as a pair.** If you mark one, mark the other, unless the passage truly gives only one of them; then note it under `not_enough_information`.
3. **No Mind, no `^8`/`^9`.** Rain making a road wet is not `^8`. The definition needs an Idea coming to Mind.
4. **A named person is not automatically `^1`.** Mark `^1` only where the passage shows that Mind's awareness at work on Ideas.
5. **`^2`/`^3` need the passage to show it.** A neutral mention of a thing is neither.
6. **`^5` is what the Mind is made of; `^7` is the schedule of exposure.** A passage can show both. Mark both, with different words.
7. **`^6` is about what an Idea is made of.** Mark it when the passage takes a thing apart or says what it consists of.
8. **Do not label Worlds, Domains, Drives or Registers.**
9. **Do not use outside knowledge.** Label only what this passage says.

### Three made-up examples (never used as cases)

Passage X1: "Renate lifted the lid and the steam smelled of cloves. At once she was back in her aunt's hallway, coat still on, nine years old."
Entries: `^1` words "Renate"; `^8` words "the steam smelled of cloves", mind "Renate", relative_to "her aunt's hallway"; `^9` words "her aunt's hallway", mind "Renate", relative_to "the steam smelled of cloves".

Passage X2: "The conveyor ran all night. Crates dropped from the chute, slid to the scale and were pushed left or right by a metal arm."
`none_of_these`: true.

Passage X3: "Odile read the proposal twice and set it down."
`^1` words "Odile" (her awareness is intaking the proposal). Nothing settles whether she is attracted toward it or repelled by it: add a note under `not_enough_information`. No `^2`, no `^3`.
