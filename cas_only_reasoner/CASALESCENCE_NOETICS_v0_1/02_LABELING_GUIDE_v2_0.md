# 02 — Labeling guide, version 2.0 (candidate; not frozen)

For label teams only. Never show this guide to case writers or to anyone tuning a reader.

Status: CANDIDATE. It is not frozen. It may be used for the build and for the practice pass. It may still change during the practice pass. It is frozen and hashed before any new passage is sealed. No change is made to this guide after labels are seen.

- **What this version is.** Part A is canon. It is the same, byte for byte, as Part A of versions 0.1, 0.2, 1.0, 1.1 and 1.2. Part B is this study's working convention. Part B is rewritten for version 2.0 from the owner's direction of 2026-10-05 (`OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json`): keep identifying which thing occupies each role; "Use a short, consistent identifying label PLUS the full supporting quote. Don't reduce everything to one word"; "Also count extra and missing roles separately". The design is in `design_v2/labeling_final.json`.
- **What is unchanged.** Part A. Rule 15, the owner's working ruling on reading a sign (`OWNER_RULING_SIGN_READING_20261004.json`), word for word. Rules 3, 8 and 9.
- **What is a proposal.** The nine conventions at the end of rule 16 and the eight hold codes of rule 17 are proposals. The bars, the outcome words, the `^5` bar row and the seal conditions S1 to S5 are proposals too; they are in the plan, not in this guide. A proposal takes effect only when the owner signs it, before any new passage is sealed. None of them is canon. The owner may reverse any of them.
- **What is not decided here.** Two questions are open with the owner. (1) Does recognizing a familiar sign count as Cause -> Effect when it brings another idea to mind? (2) Does an idea reached through reasoning also count as Effect? Rule 15 stays in force as written until the owner answers. Every other question about what a definition covers also stays with the owner. This guide decides none of them.
- **What a labeler does with an open question.** For the owner's two questions and for the eight held kinds you still write the entry. For a sign or a worked-out conclusion you follow rule 15 as written. For the eight kinds listed in rule 17 you write the entry in full and mark it `held` with its code. You never leave such an entry out. You never write it as clear. Held entries are counted in their own rows.
- **Where there is no held kind.** Only the eight kinds of rule 17 have a held row. Other open questions have none: the fixed design gives them no hold code. For those, both teams follow one working line of Part B inside the ordinary rows, so that they write the same thing. For a few kinds that line says to write no entry. A working line is this study's convention. It is not a ruling on a definition. A result for such a row is read as 'under this convention'. Section B5 lists every such line, so that the owner can strike it before the seal. As a labeler you follow the numbered rules of Part B as they are written, also where a rule says to write no entry.

How to use this guide: read it once, from top to bottom. Part A gives the definitions. Part B gives the record you return (B1), the checker (B2), rules 1 to 17 (B3), worked examples (B4), a record of changes (B5) and a one-page checklist (B6).

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

## Part B — How to label in this study (working convention, v2.0)

### B1. What you produce

For each passage you return one JSON record. The record holds a list of entries.

ONE ENTRY = one thing, in one role, for one Mind. Every quoted field is an exact copy from the passage, one unbroken stretch.

**The passage record** is unchanged. It has five fields.

- `passage_id`: the id you were given.
- `none_of_these`: `true` when no Noetic `^1` to `^9` is occupied by anything in the passage. Then `entries` is empty.
- `entries`: the list of entries.
- `not_enough_information`: short notes for things the passage hints at but does not settle. Do not turn a hint into an entry.
- `guide_problem`: one short sentence when a rule of this guide was unclear for this passage, or when two rules seemed to order opposite things, or when a saying of Part A pointed to a Noetic and a numbered rule said to write no entry of it (rule 14). Otherwise `""`.

**One entry** has these fields.

- `noetic`: '^1' to '^9'.
- `mind`: the `label` of this team's own `^1` entry for that Mind, character for character. Empty only for `^6`. In a `^1` entry, `mind` equals its own `label`.
- `label`: the short identifying name of the thing. 1 to 12 words (stretches between spaces). It lies inside `support`. Never a naming phrase cut down to its bare noun.
- `support`: the full supporting quote. Whole sentences, at most 4. It holds the label and, for `^4` and `^7`, the measure. It is where the meaning is kept. It is never compared between teams.
- `measure`: only for `^4` (the how-much words) and `^7` (the rate and pattern words; in a held H7-RESULT entry the without-thinking words; in a held H7-UNBROKEN entry the unbroken word). It lies inside `support`. Empty for every other Noetic.
- `relative_to`: `^8`: the label of its `^9`. `^9`: the label of its `^8` (empty only with `reached_by`). `^6`: the whole (empty only with `clue`). Empty for `^1`, `^2`, `^3`, `^4`, `^5`, `^7`.
- `certainty`: 'clear', 'ambiguous' or 'held'.
- `other_candidate`: only with ambiguous: '^n', 'none' or 'reasoning' (rule 15(d), unchanged).
- `held_under`: only with held. One of 8 codes: H2-COMFORT, H3-NOPULL, H3-BORED, H5-ROLE, H7-RESULT, H7-NOEFFECT, H7-UNBROKEN, H89-FOLLOWS (rule 17).
- `reached_by`: 'reasoning', only on a `^9` under rule 15(b). Unchanged.
- `clue`: true, only on a `^6`, and only in a passage where this team wrote a `^9` with `reached_by` reasoning (rule 7).
- `no_fuller_name`: true, optional. Only when no noun anywhere in the passage names the thing.

Write the first seven fields in every entry: `noetic`, `mind`, `label`, `support`, `measure`, `relative_to`, `certainty`. An empty field is `""`. Write the other five fields only when they apply. Otherwise leave them out.

**How the fields go together.** These lines add no rule about what to label. The first line says how a program reads an empty field. The others put in one place what the field list above and rules 7, 15, 16 and 17 already fix. The checker and the scorer follow all of them.

- An optional field that does not apply is left out. A program reads an optional field with an empty value as left out. The empty values are: `""` for `other_candidate`, `held_under` and `reached_by`; `false` for `clue` and `no_fuller_name`; `null` for any of the five. Left out and empty mean the same.
- `mind` is `""` in every `^6` entry, and only there.
- A `^9` with `reached_by` (rule 15b) always has `relative_to` `""`. So it is never the partner of a `^8`: rule 15(b) says 'Do not mark `^8`'. It is never `held`. It never has `other_candidate` 'reasoning': that value belongs to the uncertain pair of rule 15(d), and each entry of a pair names the other.
- A `^6` with `clue` true (rule 7) always has `relative_to` `""` and certainty `clear`.
- One thing, one entry (rule 16, step 10), whatever the certainty. For one Noetic and one Mind, do not write the same thing twice in two certainties: not once clear and once held, not once clear and once ambiguous. Do not write one piece both as a clue and as a plain part. The three exceptions of step 10 stay.

`^0` Idea is not an entry. Every thing you point to is an Idea. You are not asked whether an Idea is present.

**Which fields are filled.** `label` and `support` are always filled.

| Noetic | `mind` | `measure` | `relative_to` |
|---|---|---|---|
| `^1` | its own `label` | `""` | `""` |
| `^2`, `^3`, `^5` | the `label` of that Mind's `^1` entry | `""` | `""` |
| `^4` | the `label` of that Mind's `^1` entry | the how-much words | `""` |
| `^6` | `""` | `""` | the whole (`""` only with `clue` true) |
| `^7` | the `label` of that Mind's `^1` entry | the rate and pattern words (held entries: rule 17) | `""` |
| `^8` | the `label` of that Mind's `^1` entry | `""` | the `label` of its `^9` |
| `^9` | the `label` of that Mind's `^1` entry | `""` | the `label` of its `^8` (`""` only with `reached_by`) |

#### X7. A filled example

Passage X7 (made up, never used as a case):

> Maren opened the old ledger. The dry smell of ink and dust rose from its pages. That smell put her back in her father's shop, counting coins into paper rolls.

```json
{"passage_id": "X7", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Maren", "label": "Maren", "support": "Maren opened the old ledger.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Maren", "label": "The dry smell of ink and dust", "support": "The dry smell of ink and dust rose from its pages. That smell put her back in her father's shop, counting coins into paper rolls.", "measure": "", "relative_to": "her father's shop", "certainty": "clear"},
  {"noetic": "^9", "mind": "Maren", "label": "her father's shop", "support": "The dry smell of ink and dust rose from its pages. That smell put her back in her father's shop, counting coins into paper rolls.", "measure": "", "relative_to": "The dry smell of ink and dust", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

What to see in X7:

- The `label` is short and names the thing. The `support` is the full quote in whole sentences.
- The bringing words are in the third sentence ('put her back in'). The trigger is named there only as 'That smell', a pointer. So the label is taken from the sentence before (rule 16, steps 2 and 3).
- `mind` copies the `^1` label. Each `relative_to` copies the other entry's `label`. Both entries of the pair carry the same `support`.

Never force a label (rule 14).

### B2. The checker

A fixed program checks every record before it is accepted. It is plain Python, with no model. It checks one record at a time. It reads form only. It does not say whether any role is right or wrong. A record that passes is not thereby correct.

If a check fails, you get the checker's messages. Each message names an entry, a check and what is wrong. Fix what the messages name. Then hand in the whole record again. You have up to three tries per passage.

After the third try the record is final. An entry that still fails checks C1 to C8 is dropped. A dropped entry does not vanish. It stays in the count as an unmatched entry. An entry that failed a check and that you then left out of your next try is kept in the same way: the program puts it back and counts it as a dropped entry of yours. The one exception is a repeated entry that check C8 told you to remove. If the third try gives no record that can be read, the passage counts as not labeled.

The checks:

- R0. The record as a whole. It is one JSON object. `passage_id` is the id of the passage. `entries` is a list of entries. `none_of_these` is `true` or `false`. When `none_of_these` is `true`, `entries` is empty.
- C1. Allowed values. `noetic` is '^1' to '^9'. `certainty` is clear, ambiguous or held. `other_candidate` is there only with ambiguous. `held_under` is there only with held and belongs to that Noetic. `reached_by` only on a `^9`. `clue` only on a `^6`, and only when this team's record for the passage has a `^9` with `reached_by` reasoning. `reached_by` never with `held`, and never with `other_candidate` 'reasoning'. `clue` true only with certainty clear. An optional field with an empty value is read as left out.
- C2. `support` is an exact copy from the passage, after one fixed clean-up (curly quotes to straight quotes, runs of spaces to one space). The program then widens it to whole sentences. The widened support has at most 4 sentences.
- C3. `label` is an exact copy, lies inside the widened support, and has 1 to 12 words. For `^1` the support must hold the name; the label is then located at the first place the name occurs in the passage, whatever the support.
- C4. `measure` is filled and lies inside the support for `^4` and `^7`. It is empty for every other Noetic.
- C5. `mind` equals the label of one of this team's own `^1` entries in the passage (empty only for `^6`). In a `^6` entry `mind` is always empty.
- C6. `relative_to`. `^8`: equals the label of a `^9` entry with the same mind, the same certainty and the same hold code, and that `^9` points back. `^9`: the reverse, or empty with `reached_by`. An entry may be written again with the same label when each copy points at a different partner (rule 16, step 10). `^6`: an exact copy from the passage of 1 to 12 words, or empty with `clue` true. All other Noetics: empty. A `^9` with `reached_by` always has an empty `relative_to`, so no `^8` can have it as its partner. A `^6` with `clue` true always has an empty `relative_to`.
- C7. Pointer check on every `label` except a `^1` label, and on a `^6` `relative_to`, unless `no_fuller_name` is true. Not a pronoun alone (it, this, that, they, them, he, she, here, there, one). Not starting with this, that, these, those or such. Not 'the', 'a' or 'an' plus one bare word from this fixed list: sound, noise, smell, scent, odour, odor, aroma, fragrance, sight, feeling, sensation, memory, image, picture, thought, moment. Not starting with a holder lead-in: 'a memory of', 'the memory of', 'memories of', 'a picture of', 'pictures of', 'an image of', 'a vision of', 'a thought of', 'the thought of'.
- C8. No duplicate. No two entries of one team in one passage that the scorer's own test would call the same reading. The same holds across certainties: the same thing, for the same Noetic and the same Mind, written a second time with another certainty is a duplicate too (rule 16, step 10). So is one piece written both as a clue and as a plain part. The later entry fails. Two sizes for one thing (`^4`) and copies that point at different partners (`^8`, `^9`) stay allowed.
- C9. One re-ask, never a rejection. For `^2` and `^3`: the last content word of the label is a feeling word (satisfaction, pleasure, comfort, peace, calm, relief, aversion, annoyance, disgust, unease, irritation, distaste, dislike, yearning, longing, feeling, sense). Fixed message: 'Your label names a feeling. If it is the Mind's own pull or push and the passage names what it is aimed at, use that thing as the label. If the feeling is itself what the Mind is drawn to or repelled by, send the same label again.' The second answer is accepted.

### B3. Working rules (1 to 17)

1. **One passage, many entries.** Mark every Noetic the passage settles. The same words may occupy two Noetics; write two entries. One exception: rule 6(c). The `^5` that would share a label with your own `^7` entry is added by the program, not by you.
2. **`^8` and `^9` come as a pair.** Mark a clear pair only when the passage says or plainly shows that noticing one thing brought a different thing to Mind. There are exactly three other cases. Two are in rule 15: a conclusion reached by reasoning (15b), which is marked on its own and flagged; and a sign whose way of working the passage does not reveal (15d), which is marked as an uncertain pair. The third is a memory or a picture that only follows something noticed: it is written as a held pair under H89-FOLLOWS (rule 17). For `relative_to`, copy the label of the other member of the pair (rule 16, step 9). If two things merely sit side by side and H89-FOLLOWS does not fit, or the passage gives only one of them, mark neither and write a note under `not_enough_information`.
    - **What 'plainly shows' needs.** A clear pair needs one of these in the passage.
        - (i) Bringing words: words that say one thing brought the other, or that the other came to the Mind on the noticing. The five phrases of rule 15(a) count for anything noticed, sign or not: 'reminded', 'brought back', 'made her think of', 'came to him', 'was suddenly in'. So do words like them: 'took her back', 'transported', 'pulled her thoughts to', 'put her back in', 'brought to his thoughts', 'shifted her thoughts to', 'flooded his thoughts'. These lists are examples.
        - (ii) A memory or a picture of something else arriving at once on the noticing, said with 'instantly', 'suddenly', 'at once', 'immediately' or 'for a moment she was'. Test (ii) is only about a memory or a picture. When what comes is what a sign means, rule 15 decides, and there speed proves nothing.
        - The words 'remembered', 'recalled' and 'pictured' alone are not bringing words.
    - **A memory or a picture that only follows** something noticed, with neither (i) nor (ii), is held under H89-FOLLOWS (rule 17), or left out with a note when H89-FOLLOWS does not fit.
    - **One thing brought to Mind, one `^9`.** Sentences that only add detail to the same memory ('She remembered the warmth of his hand', 'He pictured the tools on the wall') give no new entry. A second pair needs its own bringing words that say what brought the second thing up. A further memory that has only a sudden word ('She suddenly remembered the worn leather armchair') gets no pair: add a note under `not_enough_information`. Do not make the first memory the `^8` of the next one unless the passage says it brought the next one up. Every `^9` has its `^8`, except a `^9` marked `reached_by` reasoning. A bodily reaction alone is not a `^9`.
    - **Several noticed things, one thing brought to Mind.** Write one pair per noticed thing. The `^9` is written once per trigger with the same label (rule 16, step 10). Whether such a pair is clear, uncertain or reasoning is decided by rule 15, as written.
    - Reminder: a held pair is not left out. Both entries are written in full and marked `held` with the code H89-FOLLOWS.
3. **No Mind, no `^8`/`^9`.** Rain making a road wet is not `^8`. The definition needs an Idea coming to Mind. Recalling something on purpose, with no named thing that brought it up, is not a pair either.
4. **List every Mind once.** A Mind is any person, animal, group or machine that the passage shows taking in, holding, working on or putting out at least one Idea. If you gave something any other entry as its `mind`, it is a Mind: add one `^1` entry for it. A person who is only mentioned, with nothing of their awareness shown, is not listed. Someone shown speaking is putting out Ideas and is listed. An animal is listed only when the passage shows it taking something in or responding to it as a Mind; bare movement is not enough. Quote the first full mention of the name.
    - For a Mind the `label` is the name only, at its first full mention, without the role phrase after it. The `support` is a sentence that holds the name.
5. **`^2`/`^3` need the passage to show it.** A neutral mention of a thing is neither. What a Mind does counts when the passage presents it as being drawn toward or repelled by the thing (seeking it out, lingering over it; steering clear of it, being unable to touch it). Plain absence or plain routine does not count. Strength does not matter here: a mild pull or a mild unease counts when the passage states it. How strong it is belongs to `^4`. Attention alone ("focused on", "absorbed in") is a Mind at work, not `^2`; mark `^2` only when the passage also shows the pull.
    - **Label what the pull or the push is aimed at, as the passage names it.** That may be a thing ('the lumpy fish pie') or something of a thing ('its mechanical might', 'their softness', 'restoring such items'). Do not swap one for the other. The Mind's own pull or push named as a feeling ('a surge of satisfaction', 'a distinct aversion') and what the Mind did in response ('she quickly turned away') are not the label when the passage names what they are aimed at (rule 16, step 6).
    - **Which sentence.** If the passage states the pull or the push for one thing more than once, use the first sentence that has a word of affinity, pull or aversion aimed at it, or that shows a move toward it or away from it (rule 16, steps 1 and 10).
    - **A stated affinity aimed at the thing is enough for a clear `^2`.** The thing does not have to be in the scene: a stated preference counts.
    - **A good feeling and nothing more** is held under H2-COMFORT (rule 17).
    - **A missing pull, or boredom,** is held under H3-NOPULL or H3-BORED (rule 17). Being set against something the Mind is drawn to ('however', 'but') shows nothing by itself: a thing the passage says nothing against is a neutral mention.
    - **`^4` never replaces `^2` or `^3`.** Which way the Mind leans and how strongly are two entries (rule 10f).
    - Rule 5 holds for every Mind you listed under rule 4, not only the main one.
    - Reminder: a kind held under H2-COMFORT, H3-NOPULL or H3-BORED is not left out. You write the entry in full and mark it `held` with its code.
6. **`^5` is what the Mind is made of. `^7` is the rate and pattern of exposure.**
    - (a) **The rate test for `^7`.** These pass: (i) a schedule or frequency: every morning, each Tuesday and Friday, every day, daily, nightly, weekly, twice a week, every time ..., whenever ..., always, often, regularly, day in and day out, again and again, over and over; (ii) a count of repeats: countless, hundreds of times, thousands of times, time after time; (iii) a length of time joined by 'of' to a plural noun for something that comes round again: years of early mornings, sixty years of shows.
        - These do not pass. A length of time alone, or joined to a job, a place or an activity (thirty years on the wards, years of cutting hair, decades spent managing busy lunchtimes, years of loading and unloading): an -ing word after 'of' or 'spent' does not pass. A number of years, winters, seasons or decades: that is a length of time, not a count of repeats (forty winters, many isolated winters). Practising with no rate. One thing said or done once. Usual, familiar, everyday or routine standing alone. Words that only say the Mind acts without thinking (automatically, without thinking, instinctively). Words for exposure with no break (constant, steady: see H7-UNBROKEN).
        - The rate words must say how often this Mind meets or does the thing. Three cases give no `^7` entry and no held entry. One: rate words on something another person did, when the passage does not show this Mind meeting it each time. Two: rate words inside a remembered scene ('the gentle way he always smiled at her', 'where she often fell asleep'). Three: 'always', 'never', 'usually' or 'often' on what a thing does to the Mind when it is met ('always made her wince slightly', 'always brought back vivid pictures of her grandmother's old armchair'): that says the result is the same each time, not how often the Mind meets the thing.
    - (b) **`^5` needs a named thing the Mind has lived, learned, come to believe or become skilled in.** Label what was lived or learned, never the length of time alone: 'parcels burst open on the rollers', not 'her thirty years here'; 'every type of handwriting imaginable', not 'his career'. A standing skill or habit that the passage names as the Mind's own counts: 'a habit', 'second nature', 'ingrained', 'muscle memory', 'had learned to', 'knew how / where / what to'. Words that only say how an action is done now ('automatically', 'without thinking', 'effortlessly', 'precise and unhurried', 'familiar', 'no longer needed to look') name no such thing: write no `^5` for those words alone.
        - Which naming. If the evidence sentence names an experience and a habit or skill it left, label the experience. If the experience is only a length of time ('many isolated winters', 'thirty-five years'), label the habit or skill ('a familiar pattern'). If the sentence names two experiences, label the first ('worked in this canteen', not 'generations pass through').
        - Roles. A role with a length of time ('a fishmonger for nearly sixty years') is a clear `^5`; label the role with its length of time. A role with an experience word and no length of time is held under H5-ROLE. A plain job title or life stage with neither gives no `^5` entry and no held entry.
    - (c) **One statement that gives a rate and an experience** ('Years of daily milking had shaped every gesture'). Write the `^7` entry: label 'daily milking', measure 'daily'. Do not write a `^5` entry with the same label as your own `^7` entry, clear or held, for that Mind. The program adds that `^5` itself for every clear `^7`, and the report shows `^5` with and without those added entries. Write a `^5` entry only for a thing that 6(b) gives under a label of its own. Do not move a `^5` to other words to get round this: words that only say the experience formed the Mind ('had shaped every gesture', 'had taught her') stay in the support and are never a `^5` label.
    - (d) **A clear `^7` needs two things:** words that pass the rate test, and the passage saying what the repeated exposure has done to this Mind (it now acts without thinking, expects it, no longer notices it, or has become skilled or used to it). The effect may be stated in another sentence. Everything else that looks like `^7` is held under rule 17 or left out.
    - (e) **The `^7` label is what the rate words count.** Ask: what is it that happens every day, each time, countless times? Label that, by rule 16, step 5. It may be a thing the Mind meets ('three short honks', 'Judge Davies would strike her gavel twice') or something the Mind does ('tapped the microphone stand twice', 'reached for the heavy toolbox'). In 'every time X, the Mind does or meets Y', label Y; the whole 'every time X' clause is the measure, so X is kept too. Never label only the thing the action is done to (not 'the heavy toolbox'). A place or a time that only sits inside the rate words is never the label (not 'a client's address'). This is a pointing convention that the owner signs before the seal. It does not say which of X and Y is the Idea the Mind is exposed to.
    - Reminder: a kind held under H5-ROLE, H7-RESULT, H7-NOEFFECT or H7-UNBROKEN is not left out. You write the entry in full and mark it `held` with its code.
7. **`^6` needs named parts.** Mark `^6` only when the passage names at least one thing that another thing is made of. Step-by-step thinking with no named parts is not `^6`. If the parts are separated by other words, write one entry per part. Details that merely accompany a memory or a scene are not its parts; mark `^6` when the passage presents the named things as what the other thing consists of.
    - A word that only counts or groups the parts ('three main flaws', 'four distinct segments', 'its parts', 'these signs') is never a part and never the whole.
    - One entry per part. The `label` is the part. `relative_to` is the whole, found by rule 16, step 9.
    - (Kept from version 1.2.) Details that merely accompany a memory or a scene are not its parts: the tools in a remembered shed, the tracks of a remembered station. Leave them out.
    - **Clues.** In a passage where you write a `^9` with `reached_by` reasoning (rule 15b), every piece the Mind checks on the way to that conclusion is written as a clue: `relative_to` empty, `clue` true, certainty clear. That holds even when the piece is also a feature of a named thing ('One large round had a slightly darker rind'). Do not put the thing examined, the conclusion, or a summing-up phrase ('these signs', 'this combination') in `relative_to`. A missing whole is not a reason to write `ambiguous` and not a reason to leave the clue out. Pieces the Mind does not check on the way stay plain parts with their whole. In a passage with no `^9` reached by reasoning, never write `clue` true. Entries with `clue` true are counted in their own row and never as plain `^6`.
8. **Do not label Worlds, Domains, Drives or Registers.**
9. **Do not use outside knowledge.** Label only what this passage says.
10. **`^4` needs words for how much this thing impressed this Mind.** Put those words in `measure`. The `label` is the thing. No measure, no `^4`.
    - (a) Little or none counts, with or without an adverb: 'it barely registered', 'left him cold', 'unheard', 'no longer noticed', 'did not distract him', 'unfazed', 'just background noise to her', 'faded from her awareness'. The no-appeal phrases of H3-NOPULL ('held little appeal', 'held no appeal', 'did not interest her') count too: write the clear `^4` and also the held `^3`. Words that say a thing has become background give no rate or pattern, so they are not `^7`.
    - (b) Much counts: 'could not stop thinking about it', 'hit him harder than he expected', 'it stayed with her all week'.
    - (c) The words must be about this Mind taking the thing in. Words for how faint, loud, small or large the thing itself is ('a faint scrape', 'a barely perceptible click', 'the noise was immense', 'the slight sway') are not `^4`. Words for how it strikes other people ('barely visible to an untrained eye', 'nearly imperceptible to others') are not `^4` for this Mind. Write no `^4` entry for others who are not a Mind you listed.
    - (d) What kind of impression it was is not how much. 'felt warm and familiar', 'comforting', 'soothing', 'jarring', 'felt like an unending chore', 'felt completely different' are not `^4` unless a how-much word is on them.
    - (e) A bodily reaction counts only with a size word on it: 'recoiled slightly', 'barely flinched', 'made her wince slightly'. 'made her jump', 'made him flinch', 'a frown' with no size word are not `^4`. Leave them out. Do not mark them ambiguous. Rule 15's last line points here.
    - (f) A how-much word on any feeling the passage says the thing gives this Mind: a pull, an aversion, comfort, calm, anxiety, awe, a sense of purpose ('a strong pull', 'deeply cherished', 'a distinct aversion', 'mild annoyance', 'intensely anxious', 'a small sense of comfort', 'a profound sense of purpose'). Write one `^4` entry with the thing as the label and the how-much words as `measure`. It stands beside the `^2` or `^3` entry, clear or held, when rule 5 or rule 17 gives one. Size words are words like: strong, powerful, deep, deeply, intense, intensely, keen, keenly, great, profound, overwhelming, sharp; mild, slight, slightly, faint, faintly, small, little, barely, hardly; and distinct, undeniable, unmistakable. The list gives examples.
    - (g) One entry per thing, Mind and size. The same size said twice is one entry; if one sentence states it in two places, copy the first place that lies outside your label (rule 16, step 8). Two different sizes for one thing are two entries, each with its own measure: 'The first siren shook her badly; by the tenth she hardly heard it.' When one half has a how-much word and the other half says only what kind ('once overwhelming, now felt like a comforting hum'), write one entry, on the half with the how-much word ('once overwhelming').
    - Parts (a), (c), (d), (e) and (f) say more plainly what rules 10 and 5 of version 1.2 already said. They are this study's convention. They are not canon and the owner has not confirmed them.
11. **Several Noetics on one moment are normal.** A trained response can be `^5` (what the Mind is made of), `^7` (the schedule that built it) and an `^8`/`^9` pair (a signal bringing something to Mind) at once. Mark each one the passage settles. Rules 6(c) and 13 say how: write the `^7`; write the pair only if the passage shows the cue bringing something to Mind; write a `^5` only under a label of its own.
12. **(Removed.)** Rule 12 is removed; what it said is now in 6(e) and rule 16.
13. **A cue that sets off an action.** If the passage shows the cue bringing the action, or a thought of it, to Mind, mark the `^8`/`^9` pair. If it shows only that the Mind now acts without thinking ('automatically', 'without thinking', 'without a moment's conscious thought', 'before he knew it'), mark no pair and do not write the action as a `^9`. Then mark `^7` by rule 6: clear when rate words pass and the effect is stated; held under H7-RESULT when no rate words pass. An action done without thinking that you used as the stated effect of a clear `^7` entry of the same Mind is not written again under H7-RESULT (rule 17). Mark `^5` only under rule 6(b).
14. **Three kinds of certainty.**
    - `clear`: the passage settles it under this guide.
    - `ambiguous`: the passage itself can be read two ways. Add `other_candidate`: another Noetic ('^n'), 'none', or 'reasoning' (rule 15d).
    - `held`: the passage is plain, but whether this is the Noetic depends on a question that is open with the owner. Use it only for the kinds listed in rule 17, and add `held_under` with the code. Write a held entry in full, like any other.
    - If your doubt is about what a guide rule means, write neither `ambiguous` nor `held`. Decide by the rule's own text and examples. Mark the entry clear or leave it out. Write the doubt in `guide_problem`. Never force a label: `ambiguous`, a note under `not_enough_information`, and `none_of_these` stay correct answers when the passage does not settle it.
    - If a saying in the Part A table points to one Noetic, and a numbered rule of Part B says to hold that entry or to write no entry of that Noetic, follow the numbered rule. When the rule says no entry, also write one sentence in `guide_problem` that names the saying and the rule. Start that sentence with the words 'Saying against rule:' so that these reports can be counted apart. This line only makes two labelers do the same thing. It does not say what the definition covers. That stays with the owner.
15. **A sign, reasoning, or both (owner's working ruling, 2026-10-04).** When a Mind meets a sign and something else comes to it, read what the passage shows:
    - **(a) The sign directly brings a different Idea to Mind.** Mark `^8` and `^9`. Words that show this: "reminded", "brought back", "made her think of", "came to him", "was suddenly in".
    - **(b) The Mind works through evidence to a conclusion.** Mark the reasoning roles the canon names: `^6` for the named pieces it takes apart, and `^9` for the conclusion it lands on, with `relative_to` `""` and `"reached_by": "reasoning"`. Do not mark `^8`. The flag keeps these conclusions apart from a `^9` brought to Mind by a trigger: the two are counted separately and never mixed. (Clarification 6: deductive causal inference is a compound of `^6` Male and `^9` Below/Effect, not `^8` Above/Cause alone.) Words that show this: "worked out", "checked", "ruled out", "compared", "so it had to be".
    - **(c) Both happen.** Mark both, each attached to its own words.
    - **(d) The passage does not reveal which happened.** Do not mark a clear pair. Mark an uncertain pair: both entries get `"certainty": "ambiguous"` with `"other_candidate": "reasoning"`. Uncertain entries are counted separately and never count as a clear pair. A passage that says only that the Mind "knew", "recognised", "could tell" or that the sign "meant" something is this case.
    - **Speed proves nothing either way.** "At once" or "instantly" does not show that no reasoning occurred.
    - **`^5` may be marked as well.** Experience that shapes the reading is `^5`; it does not exclude a pair.
    - **A bodily reaction alone is not a `^9`.** A flinch or a startle does not show that a different Idea came to Mind. It may be `^4` under rule 10.
16. **How to point: label, supporting quote, measure.** Every entry points at one thing: the Mind or the Idea that holds the Noetic. Do these steps in this order.
    - **Step 1. Find the evidence sentence.** It is the sentence whose words make the thing hold the role.
        - `^1`: the sentence with the first full mention of the name.
        - `^2`, `^3`: the first sentence that has a word of affinity, pull or aversion aimed at the thing, or that shows a move toward it or away from it.
        - `^4`: the sentence with the how-much words.
        - `^5`: the sentence that says what was lived or learned.
        - `^6`: the sentence that lists the part.
        - `^7`: the sentence with the rate or pattern words.
        - `^8`, `^9`: the sentence with the bringing words (rule 2).
        - A held kind (rule 17): the sentence with the words rule 17 names for that code: the good-feeling words (H2-COMFORT), the no-appeal words (H3-NOPULL), the boredom words (H3-BORED), the role words (H5-ROLE), the without-thinking words (H7-RESULT), the rate words (H7-NOEFFECT), the unbroken word (H7-UNBROKEN), the remembering words (H89-FOLLOWS).
        - If you find no such words and no held kind fits, write no entry.
    - **Step 2. Take the label from the evidence sentence.** The `label` is the naming of the thing in the evidence sentence, as the passage words it there. If that sentence names the thing more than once, take the first naming that is not a pointer (step 3). Do not swap it for an earlier, different naming: 'The dryer noise faded quickly in her awareness' gives 'The dryer noise', although an earlier sentence says 'A sudden metallic clanging from the industrial dryer'. Do not swap it for the thing it belongs to: 'feeling a pull towards its mechanical might' gives 'its mechanical might', not 'the heavy excavator'; the trigger is 'Its lanolin scent', not 'a roll of raw tweed'.
        - If the evidence sentence does not name the thing, or names it only with pointers, go to the nearest sentence that names it outright. For the thing brought to Mind (`^9`) look forward: first later in the same sentence, then in the next sentence. For everything else go back one sentence at a time. Take the naming of what the pointer points at. That need not be the first noun of that sentence: in 'The air filled with the familiar, sharp scent of salt spray and warm diesel fumes. It brought to his thoughts ...' the trigger is the scent, the thing noticed, not 'The air' that carries it. A describing phrase after 'was' or after a comma does not name a thing outright: in 'The sound was constant, a soft, vibrating drone' neither 'The sound' (a pointer) nor 'a soft, vibrating drone' (a description of it) is the label; go back to the sentence that names the sound ('the low, steady hum'). Do not go further than you must.
    - **Step 3. A pointer is never a label.** A pointer is one of these, and nothing else:
        - (a) a pronoun alone: it, this, that, they, them, he, she, here, there, one;
        - (b) any phrase that starts with this, that, these, those or such ('This smell', 'That familiar feeling', 'these signs', 'those simpler days');
        - (c) 'the', 'a' or 'an' plus one bare word from this list: sound, noise, smell, scent, odour, odor, aroma, fragrance, sight, feeling, sensation, memory, image, picture, thought, moment. 'The sound' is a pointer. 'The sharp sound' is not.
        - Use a pointer as the label, with `no_fuller_name` true, only when no noun anywhere in the passage names the thing. Never use it because the naming is far away or plain.
    - **Step 4. Holder words.** 'a vivid picture', 'a memory', 'an image', 'a thought' only announce a thing. Treat them as pointers. The naming is what the picture or the memory is of. It usually comes just after: go forward for it. Drop 'a memory of' and 'pictures of' from the front of a label.
    - **Step 5. Where a label starts and stops.**
        - A thing (an object, a person, a place, a smell, a sound). Start at the first word of its naming phrase: the, a, his, its, a number or count word, or the first describing word. Keep the describing words in front of the noun. A name of the form 'X of Y' starts at X ('The rough texture of the tweed'). Keep one short phrase right after the noun that says what it is of or which one it is ('of ancient paper', 'from the microphone', 'in the percussion'). Stop before a verb, before a comma that adds description ('heavy with juice'), before which, that, who or where, and before 'near ...' or 'nearby'. If you are unsure where to stop, stop earlier: where a label stops is not compared.
        - Never cut a naming phrase down to its bare noun: not 'scent' for 'Its lanolin scent', not 'girl', not 'pallets'. A plain re-naming that the passage itself writes ('the mess', 'the roses') is allowed when it is the naming in the evidence sentence.
        - A scene or a happening (no noun of its own names it).
            - (i) Something the Mind of this entry does or is: never put the Mind in the label. Leave off its name or pronoun, a role phrase set off by commas after the name, a part of its body that stands for it ('his hand', 'her feet'), helper words (had, has, was, were, would, is) and words ending in -ly in front of the doing word. Start at the doing word. If there is no doing word, start at the first word after the helper. 'Sam, an apprentice locksmith, automatically reached for the heavy toolbox' gives 'reached for the heavy toolbox'. 'She was a little girl again, watching her grandfather shave for Sunday church' gives 'a little girl again, watching her grandfather shave'.
            - (ii) A word of noticing or recalling right after the Mind is a lead-in too: saw, had seen, watched, observed, heard, noticed, felt, pictured, remembered, recalled. Leave it off. The label is what was seen or recalled. 'He had seen countless pallets move down the conveyor belt' gives 'countless pallets move down the conveyor belt'.
            - (iii) Something another person or thing does: start at that doer's naming. 'Judge Davies would strike her gavel twice'.
            - (iv) Never label only the thing the action is done to: not 'the heavy toolbox', not 'the pool', not 'countless pallets'.
            - Keep the doing word and what it is done to or where it goes. Stop before a tail that starts with for, when, while, as, before, after or because, and before a tail that only says when or how often ('decades ago', 'exactly at opening time', 'every day'). Stop at the end of the sentence.
        - A length of time in front ('Years of', 'Decades of', 'Decades spent'): leave it off when two or more words are left that name what was lived ('daily milking', 'managing busy lunchtimes'). Keep the whole phrase when fewer are left ('Forty winters of roofing').
        - Never more than 12 words. If the naming phrase is longer, stop after the 12th word.
        - If you and another labeler would stop a word or two apart, that is harmless. Labels are compared by where they start in the passage, not letter by letter.
    - **Step 6. These are never the label.**
        - For every Noetic: a length of time alone ('twenty years', 'his career', 'his fifty years'). A word that only counts or groups other things ('three main flaws', 'its parts', 'four distinct segments', 'these signs'). The how-much words or the rate words alone: those go in `measure`.
        - For `^2` and `^3` only: the Mind's own pull or push named as a feeling ('a surge of satisfaction', 'a distinct aversion', 'a quiet yearning'), and what the Mind did in response ('she quickly turned away'). When the passage names what they are aimed at, label that. A feeling is the label only when the feeling is itself what the Mind is drawn to or repelled by.
        - In the other Noetics a feeling or an action can be the thing. A remembered fear can be a `^9`. An action done every day can be the `^7` label (rule 6e).
        - All of these stay in the support.
    - **Step 7. Write the supporting quote (`support`).** Copy whole sentences, from the first word to the full stop. Copy the unbroken run from the sentence that holds your label to the evidence sentence. Most of the time that is one sentence. For an `^8`/`^9` pair, copy from the sentence of the `^8` label through the sentence of the `^9` label; both entries carry the same support. If your label is a plain re-naming ('the mess', 'The recording') or leans on an earlier naming with its, their, his or her ('Its simple presence'), and the sentence just before says what it is, start one sentence earlier. Add no other sentence. Never more than 4 sentences. Do not trim inside a sentence.
    - **Step 8. `measure` (only `^4` and `^7`).** Copy the shortest unbroken stretch that states how much (`^4`) or the rate and pattern (`^7`). It must lie inside the support. If the sentence states it in two places, copy the first place that lies outside your label. If the only place lies inside your label, copy that ('daily' in 'daily milking'). An 'every time ...' or 'whenever ...' clause is copied whole. It belongs to the measure, never to the label.
    - **Step 9. `mind` and `relative_to` are labels. Do not quote them afresh.**
        - `mind`: the `label` of that Mind's `^1` entry, character for character. For a Mind the label is the name only, at its first full mention ('George', not 'George, the puppeteer').
        - `relative_to` for `^8`: the `label` of its `^9`. For `^9`: the `label` of its `^8`. Character for character.
        - `relative_to` for `^6`, the whole. Find it in this order.
            - (a) Look in the sentence that holds the first part, before the part. Then go back one sentence at a time. Take the nearest naming, as that sentence words it ('The process', 'The recording', 'The problem'). Do not swap it for an earlier, different name.
            - (b) Skip Minds, pointers, and phrases that only count or group the parts ('three main areas', 'its parts', 'Each element', 'several distinct phases').
            - (c) A possessive counts as a naming: in 'the issue's constituent parts' the whole is 'the issue'. In 'the steps for X', 'the parts of X', 'the components of X' the whole is X, starting at X ('propagating her prize orchid', 'a hive inspection').
            - (d) If a doing word stands between that naming and the parts, the sentence says something is done to the parts. It does not say the naming is made of them. 'The task involved dismantling the main pivot bolt, the spring mechanism, and the cage assembly.' Skip that naming and go back to the thing the doing is done to ('a complex derailleur'). When no doing word stands between ('The process involved several distinct phases. First, ...'; 'The problem involved three components: ...'), the naming is the whole.
            - (e) Every part of one list carries the same whole.
        - All other Noetics: `relative_to` is empty.
    - **Step 10. One thing, one entry.** For one Noetic and one Mind, a thing gets one entry however often the passage comes back to it. If the passage states the role twice, use the first statement: the first sentence that passes step 1 for that Noetic. Three exceptions.
        - (1) For `^4`, two different sizes for one thing are two entries (rule 10g).
        - (2) If one trigger brings two different things to Mind and the bringing words cover both, write two pairs. The `^8` entry is written twice with the same label. Each copy points at its own `^9`.
        - (3) If several noticed things bring one thing to Mind, write one pair per noticed thing. The `^9` entry is written once per trigger with the same label. Each copy points back at its own `^8`.
        - Exception 3 says how to write the entries. It does not say that such a pair is Cause and Effect. Rule 15 decides clear, uncertain or reasoning, as written.
    - **What the label names.**
        - `^1`: the Mind. `support`: a sentence that holds the name.
        - `^2`: the Idea the Mind has an affinity for and is attracted toward.
        - `^3`: the Idea the Mind is adverse to and repelled by.
        - `^4`: the Idea that resonates with the Mind. `measure`: the words that state how strongly or how weakly it impresses the Mind.
        - `^5`: the Idea or Ideas the Mind is composed of (what it has lived, learned, come to believe, become skilled in).
        - `^6`: the Idea that another Idea is composed of (one part). `relative_to`: the Idea they compose (the whole).
        - `^7`: what the rate words count: the thing this Mind meets or does again and again. `measure`: the words that state the rate and pattern of exposure. (Where a cue and the Mind's response both come round each time, the entry keeps both: the cue in the measure, the response in the label. Which of the two Part A means by 'an Idea' the Mind 'is exposed to' is the owner's to say.)
        - `^8`: the Idea that triggers a different Idea to come to Mind.
        - `^9`: the Idea brought to Mind.
    - **Worked examples.** They are in section B4. Every one of them is a made-up passage with its full record.
    - CONVENTIONS IN THIS RULE THAT THE OWNER SIGNS BEFORE THE SEAL. None is canon. The owner may reverse any of them. They cannot be changed after labels are seen.
        1. The label is the naming in the evidence sentence. Go back only for a pointer. (The other choice: the first naming in the passage.)
        2. The label is what the passage says the pull, the push or the impression is aimed at, as the passage names it. That may be something of a thing ('its mechanical might', 'their softness'). (The other choice: always the thing. That was the draft's step 7. It is deleted.)
        3. For `^5`, the experience is the label, not the words that say it formed the Mind (rule 6b, 6c).
        4. The `^6` whole is the nearest naming as the passage words it. A naming followed by a doing word is skipped (step 9d).
        5. A clue is written with no whole (rule 7).
        6. In 'every time X, the Mind does or meets Y' the `^7` label is Y, and X stays in the measure (rule 6e). (The other choice: label the cue X.)
        7. The program, not the labeler, writes the `^5` that goes with a clear `^7`. The `^5` bar row is the one without those entries (rule 6c).
        8. Several noticed things that bring one thing are written as one pair per noticed thing (step 10).
        9. The written-out word tests: the rate test (rule 6a), the bringing words (rule 2), the size words (rule 10f), the experience words (H5-ROLE).
    - Note for labelers: follow the steps as they are written. The list of nine conventions is there for the owner's signature. It gives you no second way to label.
17. **Kinds that are held for the owner.** For each kind below, do not write a clear entry of that Noetic and do not leave it out. Write the entry in full with certainty held and `held_under` set to the code. Its evidence sentence is the sentence that holds the words named below (rule 16, step 1). Held entries are matched and counted in their own rows. They never count as clear. A clear entry from one team against a held entry from the other is a miss in both rows. If the passage also gives what the kind lacks, the entry is clear. The list is closed: hold nothing else. These kinds wait on the owner. This rule does not say what any definition means.
    - **H2-COMFORT (`^2`).** The passage says only that a thing gave the Mind a good feeling: comfort, warmth, calm, peace, relief, satisfaction, pleasure. No word of affinity is aimed at the thing (liked, loved, enjoyed, preferred, admired, appreciated, cherished, fond of). No pull is stated (drawn to, a pull toward, could not resist). No move toward it is shown (sought it out, lingered over it, went back to it, chose it). Example: 'Its simple presence offered a small sense of comfort.' The label is what the passage says gave the feeling, as the passage names it ('Its simple presence'). The support starts one sentence earlier, at the sentence that names the plant (rule 16, step 7).
    - **H3-NOPULL (`^3`).** The passage says only that a thing did not draw the Mind or did not interest it: 'held little appeal', 'held no appeal', 'did not interest her', 'left him cold', 'without a second glance'. No feeling against the thing is stated. No pushing away from it is shown. The same words are also a how-little measure: write the clear `^4` entry as well (rule 10a).
    - **H3-BORED (`^3`).** The passage says only that a thing bored the Mind, or that the Mind found it dull, tedious or uninspiring. If the passage says both this and what H3-NOPULL describes, use H3-BORED. If a word of dislike is also there ('disliked them, finding them tedious'), the entry is a clear `^3`.
    - **H5-ROLE (`^5`).** The passage gives a role or a life stage together with an experience word from this list: seasoned, veteran, experienced, long-time, lifelong, master, expert, old hand. It does not say what was lived or learned in it: 'the seasoned barber', 'a veteran locksmith'. The label is the role phrase with its experience word. Not held: a role with a length of time ('a fishmonger for nearly sixty years') is a clear `^5` under rule 6(b). Not written at all: a plain job title or life stage with no experience word and no length of time ('a taxi driver', 'the cobbler', 'a retired teacher', 'a young florist', 'as a student'). For those write no entry, no held entry and no note.
    - **H7-RESULT (`^7`).** The passage shows only that the Mind now does a thing without thinking, automatically or by habit, and no words pass the rate test (rule 6a) for that thing. The label is the action. The `measure` is the without-thinking words. Example: 'Without thinking, he adjusted the ear defenders over his ears.' Label 'adjusted the ear defenders over his ears'; measure 'Without thinking'. Not written under this code: an action done without thinking that you used as the stated effect of a clear `^7` entry of the same Mind (rule 6d). That action is what made the other entry clear. It is not written a second time (examples T2 and T11).
    - **H7-NOEFFECT (`^7`).** Words pass the rate test for a thing, but the passage says nothing of what the repeated exposure has done to the Mind. Examples: 'Finally, she misted it daily.' 'She often guessed the contents before even reading the address.' The entry is clear, not held, when the passage also says what it did: the Mind now acts without thinking, expects it, no longer notices it, or has become skilled or used to it.
    - **H7-UNBROKEN (`^7`).** No words pass the rate test for the thing. The passage gives only a word for exposure with no break: constant, steady, incessant, ceaseless, continuous, never-ending. The `measure` is that word. Example: 'The constant hum of the industrial dryers had become a quiet backdrop to her thoughts'. Measure 'constant'.
    - **H89-FOLLOWS (`^8` and `^9`, both entries of the pair).** A memory or a picture follows something noticed. The passage has no bringing words and no word of sudden arrival (rule 2). Exactly one named thing, in the sentence right before the remembering words or earlier in the same sentence, is the plain occasion for it. Example: 'Thomas observed the young skier struggling with the boarding gate. He remembered his own clumsy attempts decades ago.' If another sentence stands between, or you cannot point to exactly one named thing, write no pair and add a note under `not_enough_information`. If what comes is what the noticed thing means (a reading of a sign, a conclusion), use rule 15, never this code.
    - **Order for `^7`.** Apply it to each thing, not once per passage. First apply the rate test to the words about that thing. If words pass: clear when the effect on the Mind is stated, H7-NOEFFECT when it is not. If no words pass: H7-UNBROKEN when an unbroken word sits on that thing; H7-RESULT when the passage shows only that the Mind does that thing without thinking; otherwise no `^7` entry. An action that you used as the stated effect of a clear `^7` entry is not a thing of its own in this order (see H7-RESULT).
    - Said once more, plainly: where this rule holds a kind for the owner, you still write the entry. You write it in full. You mark it `held` and give its code. You do not write it as clear and you do not leave it out.

### B4. Worked examples

Every passage below is made up. None is one of the sealed passages. None is ever used as a case. Each example gives the passage, the full correct record and a short note.

| Example | What it shows |
|---|---|
| X1 to X6 | The six examples of version 1.2, rewritten in the new format |
| T1 | A remembered scene |
| T2 | A repeated activity |
| T3 | A pointing-back phrase |
| T4 | A chain of pointers |
| T5a, T5b, T5c | A naming in the evidence sentence |
| T6 | A whole named twice |
| T7a, T7b | Work done on a thing; 'the steps for X' |
| T8 | A pull aimed at something of a thing |
| T9 | A cue and a response |
| T10 | Several noticed things |
| T11 | One statement with a rate and an experience |
| E1 to E8 | One example for each hold code |
| E9 | Not held: a sentence stands between |

#### X1. Something noticed brings a memory at once

> Renate lifted the lid and the steam smelled of cloves. At once she was back in her aunt's hallway, coat still on, nine years old.

```json
{"passage_id": "X1", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Renate", "label": "Renate", "support": "Renate lifted the lid and the steam smelled of cloves.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Renate", "label": "the steam smelled of cloves", "support": "Renate lifted the lid and the steam smelled of cloves. At once she was back in her aunt's hallway, coat still on, nine years old.", "measure": "", "relative_to": "her aunt's hallway", "certainty": "clear"},
  {"noetic": "^9", "mind": "Renate", "label": "her aunt's hallway", "support": "Renate lifted the lid and the steam smelled of cloves. At once she was back in her aunt's hallway, coat still on, nine years old.", "measure": "", "relative_to": "the steam smelled of cloves", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. 'At once she was back in' is a memory arriving at once on the noticing (rule 2, test ii). The second sentence does not name the trigger, so go back one sentence. No noun names the smell, so the trigger is a happening: start at the doer's naming (rule 16, step 5 iii). The place is named by a noun: label 'her aunt's hallway' and stop at the comma.

#### X2. No Mind, nothing to mark

> The conveyor ran all night. Crates dropped from the chute, slid to the scale and were pushed left or right by a metal arm.

```json
{"passage_id": "X2", "none_of_these": true,
 "entries": [],
 "not_enough_information": [], "guide_problem": ""}
```

Note. No Mind is shown. Nothing holds any of `^1` to `^9`.

#### X3. A Mind and a hint that is not settled

> Odile read the proposal twice and set it down.

```json
{"passage_id": "X3", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Odile", "label": "Odile", "support": "Odile read the proposal twice and set it down.", "measure": "", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": ["Nothing settles whether Odile is attracted toward the proposal or repelled by it."], "guide_problem": ""}
```

Note. Her awareness is intaking the proposal, so she is a Mind. No `^2`, no `^3`: a neutral mention is neither (rule 5).

#### X4. Two things, two sizes of impression

> The first review of his book hit Anselm harder than he expected; he read it four times before lunch. The second one he skimmed and forgot by evening.

```json
{"passage_id": "X4", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Anselm", "label": "Anselm", "support": "The first review of his book hit Anselm harder than he expected; he read it four times before lunch.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^4", "mind": "Anselm", "label": "The first review of his book", "support": "The first review of his book hit Anselm harder than he expected; he read it four times before lunch.", "measure": "hit Anselm harder than he expected", "relative_to": "", "certainty": "clear"},
  {"noetic": "^4", "mind": "Anselm", "label": "The second one", "support": "The first review of his book hit Anselm harder than he expected; he read it four times before lunch. The second one he skimmed and forgot by evening.", "measure": "skimmed and forgot by evening", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The `label` is the thing. The how-much words go in `measure` (rule 10). A semicolon does not end a sentence. 'The second one' is not on the pointer list of step 3, so it is the label; it is a plain re-naming, so its support starts one sentence earlier (step 7). No `^7`: 'four times before lunch' is a count inside one morning, not a rate at which this Mind keeps meeting a thing (rule 6a). Version 1.2 wrote no `^7` here either.

#### X5. Experience, and a sign whose way of working is not shown

> Forty winters of roofing had taught Ludmila what a soft step meant. Her boot sank a finger's width near the chimney and she knew the board beneath was rotten.

```json
{"passage_id": "X5", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Ludmila", "label": "Ludmila", "support": "Forty winters of roofing had taught Ludmila what a soft step meant.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^5", "mind": "Ludmila", "label": "Forty winters of roofing", "support": "Forty winters of roofing had taught Ludmila what a soft step meant.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Ludmila", "label": "Her boot sank a finger's width", "support": "Her boot sank a finger's width near the chimney and she knew the board beneath was rotten.", "measure": "", "relative_to": "the board beneath was rotten", "certainty": "ambiguous", "other_candidate": "reasoning"},
  {"noetic": "^9", "mind": "Ludmila", "label": "the board beneath was rotten", "support": "Her boot sank a finger's width near the chimney and she knew the board beneath was rotten.", "measure": "", "relative_to": "Her boot sank a finger's width", "certainty": "ambiguous", "other_candidate": "reasoning"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. Rule 15(d): the passage says she knew, not how. So the pair is uncertain, not clear. `^5`: the sentence names an experience and a skill it left, so the experience is the label (rule 6b); 'Forty winters of roofing' is kept whole (step 5). No `^7`: a number of winters is a length of time (rule 6a).

#### X6. Reasoning to a conclusion: clues and a flagged `^9`

> Tobias laid the bill out line by line: the call-out fee, two hours of labour, a pump he had never asked for. He added the first two, compared the sum with the quote, and worked out that the pump was the whole difference.

```json
{"passage_id": "X6", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Tobias", "label": "Tobias", "support": "Tobias laid the bill out line by line: the call-out fee, two hours of labour, a pump he had never asked for.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the call-out fee", "support": "Tobias laid the bill out line by line: the call-out fee, two hours of labour, a pump he had never asked for.", "measure": "", "relative_to": "", "certainty": "clear", "clue": true},
  {"noetic": "^6", "mind": "", "label": "two hours of labour", "support": "Tobias laid the bill out line by line: the call-out fee, two hours of labour, a pump he had never asked for.", "measure": "", "relative_to": "", "certainty": "clear", "clue": true},
  {"noetic": "^6", "mind": "", "label": "a pump", "support": "Tobias laid the bill out line by line: the call-out fee, two hours of labour, a pump he had never asked for.", "measure": "", "relative_to": "", "certainty": "clear", "clue": true},
  {"noetic": "^9", "mind": "Tobias", "label": "the pump was the whole difference", "support": "He added the first two, compared the sum with the quote, and worked out that the pump was the whole difference.", "measure": "", "relative_to": "", "certainty": "clear", "reached_by": "reasoning"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. Rule 15(b): he works through evidence to a conclusion. No `^8`. The `^9` has an empty `relative_to` and `reached_by` reasoning. The three bill items are pieces he checks on the way, so each is a clue: no whole, `clue` true, certainty clear (rule 7). Wrong: `relative_to` 'the bill' on a clue.

#### T1. A remembered scene

> Ingrid finished varnishing the last chair and rinsed her brush in turpentine. The thin, oily smell instantly took her back. She was a small child again, watching her uncle paint the boat for the spring launch. She remembered the cold of the slipway, the row of open tins, and the slow way he always stirred the paint.

```json
{"passage_id": "T1", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Ingrid", "label": "Ingrid", "support": "Ingrid finished varnishing the last chair and rinsed her brush in turpentine.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Ingrid", "label": "The thin, oily smell", "support": "The thin, oily smell instantly took her back. She was a small child again, watching her uncle paint the boat for the spring launch.", "measure": "", "relative_to": "a small child again, watching her uncle paint the boat", "certainty": "clear"},
  {"noetic": "^9", "mind": "Ingrid", "label": "a small child again, watching her uncle paint the boat", "support": "The thin, oily smell instantly took her back. She was a small child again, watching her uncle paint the boat for the spring launch.", "measure": "", "relative_to": "The thin, oily smell", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The bringing words are 'took her back'. The trigger is named in that sentence. The thing brought to Mind is not, so look in the next sentence. It is a scene: leave off the Mind and the helper word ('She was'), keep the doing word and what it is done to, and stop before the tail 'for the spring launch' (step 5 i). The tail is not lost: it is in the support. Wrong: label 'child' (the remembered scene is lost). Wrong: label 'her uncle' (a person inside the scene, not the scene). No second `^9` for the last sentence: it adds detail to the same memory (rule 2). No `^7` for 'always stirred': rate words inside a remembered scene (rule 6a). No `^6`: details that accompany a memory are not its parts (rule 7).

#### T2. A repeated activity

> Halima stood at the sorting table in the post room. She had watched countless letters slide down the brass chute, time after time. Her hands now sorted them without thinking. She seldom needed to read the whole address anymore. Her fingers simply knew how to square a bundle before tying it.

```json
{"passage_id": "T2", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Halima", "label": "Halima", "support": "Halima stood at the sorting table in the post room.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Halima", "label": "countless letters slide down the brass chute", "support": "She had watched countless letters slide down the brass chute, time after time.", "measure": "time after time", "relative_to": "", "certainty": "clear"},
  {"noetic": "^5", "mind": "Halima", "label": "how to square a bundle", "support": "Her fingers simply knew how to square a bundle before tying it.", "measure": "", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. Leave off the lead-in 'She had watched' (step 5 ii). Keep the doing word and where it goes. Stop before the tail that says how often. 'countless' lies inside the label, so the measure is the next place, 'time after time' (step 8). The `^7` is clear: the rate words pass, and the passage says what the exposure did ('without thinking', 'seldom needed to read'). Those words are the stated effect; they are not written as a second `^7`. The `^5` is a named skill with a label of its own ('knew how to', rule 6b). You write no `^5` on the letters label: the program adds it (rule 6c). Wrong: label 'letters' or 'countless letters' (the repeated activity is lost).

#### T3. A pointing-back phrase

> Dagny pulled the tarpaulin off the old rowing boat. The sweet, sticky smell of pine tar hung under the shed roof. This smell brought back her grandmother's net loft.

```json
{"passage_id": "T3", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Dagny", "label": "Dagny", "support": "Dagny pulled the tarpaulin off the old rowing boat.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Dagny", "label": "The sweet, sticky smell of pine tar", "support": "The sweet, sticky smell of pine tar hung under the shed roof. This smell brought back her grandmother's net loft.", "measure": "", "relative_to": "her grandmother's net loft", "certainty": "clear"},
  {"noetic": "^9", "mind": "Dagny", "label": "her grandmother's net loft", "support": "The sweet, sticky smell of pine tar hung under the shed roof. This smell brought back her grandmother's net loft.", "measure": "", "relative_to": "The sweet, sticky smell of pine tar", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The bringing words 'brought back' are in the third sentence. The trigger there is 'This smell'. It starts with 'This', so it is a pointer (step 3). Go back one sentence. Keep the 'of' phrase and stop before the verb 'hung'. Wrong: label 'This smell' (check C7 refuses it). Wrong: label 'the old rowing boat' (the passage says the smell did the bringing).

#### T4. A chain of pointers

> Petra heard the slow, even tick coming from the hall clock. The sound was small, a dry, wooden knock. It suddenly brought to her thoughts her teacher's old metronome.

```json
{"passage_id": "T4", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Petra", "label": "Petra", "support": "Petra heard the slow, even tick coming from the hall clock.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Petra", "label": "the slow, even tick", "support": "Petra heard the slow, even tick coming from the hall clock. The sound was small, a dry, wooden knock. It suddenly brought to her thoughts her teacher's old metronome.", "measure": "", "relative_to": "her teacher's old metronome", "certainty": "clear"},
  {"noetic": "^9", "mind": "Petra", "label": "her teacher's old metronome", "support": "Petra heard the slow, even tick coming from the hall clock. The sound was small, a dry, wooden knock. It suddenly brought to her thoughts her teacher's old metronome.", "measure": "", "relative_to": "the slow, even tick", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The bringing words are in the third sentence. The trigger there is 'It', a pointer. Go back: in the second sentence 'The sound' is a pointer, and 'a dry, wooden knock' is a describing phrase after a comma. Go back again: the first sentence names it outright. Stop before 'coming'. The support is the unbroken run of all three sentences. Wrong: label 'The sound'. Wrong: label 'a dry, wooden knock'. Wrong: `no_fuller_name` (a noun in the passage does name the thing). No `^4`: 'small' says how the sound itself is, not how much it impressed her (rule 10c).

#### T5a. The naming in the evidence sentence wins

> Bettina carried a tray of seedlings across the yard. A sudden rattle of hail on the greenhouse glass made her jump. She set the tray on the bench and wiped her hands. The hail noise faded from her awareness.

```json
{"passage_id": "T5a", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Bettina", "label": "Bettina", "support": "Bettina carried a tray of seedlings across the yard.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^4", "mind": "Bettina", "label": "The hail noise", "support": "The hail noise faded from her awareness.", "measure": "faded from her awareness", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The how-much words are in the last sentence. That sentence names the thing: 'The hail noise'. It is a naming, not a pointer ('The noise' alone would be one). So do not go back to 'A sudden rattle of hail on the greenhouse glass'. 'made her jump' has no size word, so it gives no `^4` (rule 10e).

#### T5b. The naming in the evidence sentence wins, for a trigger

> Corin was drying pans when a ladle slid off its hook and rang against the stone sink. The bright ring made him stop, suddenly hearing his old school's dinner bell in his thoughts.

```json
{"passage_id": "T5b", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Corin", "label": "Corin", "support": "Corin was drying pans when a ladle slid off its hook and rang against the stone sink.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Corin", "label": "The bright ring", "support": "The bright ring made him stop, suddenly hearing his old school's dinner bell in his thoughts.", "measure": "", "relative_to": "his old school's dinner bell", "certainty": "clear"},
  {"noetic": "^9", "mind": "Corin", "label": "his old school's dinner bell", "support": "The bright ring made him stop, suddenly hearing his old school's dinner bell in his thoughts.", "measure": "", "relative_to": "The bright ring", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. A remembered sound arrives 'suddenly' on the noticing (rule 2, test ii). The evidence sentence has its own naming of the trigger, 'The bright ring'. Do not go back to the ladle. Stop the `^9` label before 'in his thoughts'.

#### T5c. A plain re-naming: the support starts one sentence earlier

> Jonas reached the gate just as the goat bolted past and knocked a bucket of feed across the path. He barely noticed the spill.

```json
{"passage_id": "T5c", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Jonas", "label": "Jonas", "support": "Jonas reached the gate just as the goat bolted past and knocked a bucket of feed across the path.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^4", "mind": "Jonas", "label": "the spill", "support": "Jonas reached the gate just as the goat bolted past and knocked a bucket of feed across the path. He barely noticed the spill.", "measure": "barely noticed", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. 'the spill' is the naming in the evidence sentence, so it is the label. It is a plain re-naming, and the sentence just before says what it is. So the support starts one sentence earlier (step 7). The goat is not listed as a Mind: bare movement is not enough (rule 4).

#### T6. A whole named twice

> Wilma read through the draft once more. The speech needed work. She marked the long opening joke, the thanks to the cooks, and the toast at the end. Then there was the story about the ferry, told twice over. Each piece needed its own small repair.

```json
{"passage_id": "T6", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Wilma", "label": "Wilma", "support": "Wilma read through the draft once more.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the long opening joke", "support": "She marked the long opening joke, the thanks to the cooks, and the toast at the end.", "measure": "", "relative_to": "The speech", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the thanks to the cooks", "support": "She marked the long opening joke, the thanks to the cooks, and the toast at the end.", "measure": "", "relative_to": "The speech", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the toast at the end", "support": "She marked the long opening joke, the thanks to the cooks, and the toast at the end.", "measure": "", "relative_to": "The speech", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the story about the ferry", "support": "Then there was the story about the ferry, told twice over.", "measure": "", "relative_to": "The speech", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. One entry per part. The whole: the sentence of the first part names nothing before the part but 'She', a Mind. Go back one sentence: 'The speech needed work.' So `relative_to` is 'The speech' in all four (step 9 a, b, e). `mind` is empty for `^6`. Wrong: `relative_to` 'the draft' (an earlier, different name). Wrong: `relative_to` 'Each piece' (it only groups the parts).

#### T7a. Work done on a thing

> Joss studied the old pedal loom. The job meant taking off the breast beam, the treadle cords and the heddle frame.

```json
{"passage_id": "T7a", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Joss", "label": "Joss", "support": "Joss studied the old pedal loom.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the breast beam", "support": "The job meant taking off the breast beam, the treadle cords and the heddle frame.", "measure": "", "relative_to": "the old pedal loom", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the treadle cords", "support": "The job meant taking off the breast beam, the treadle cords and the heddle frame.", "measure": "", "relative_to": "the old pedal loom", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "the heddle frame", "support": "The job meant taking off the breast beam, the treadle cords and the heddle frame.", "measure": "", "relative_to": "the old pedal loom", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The nearest naming before the parts is 'The job'. A doing word ('taking off') stands between it and the parts. So the sentence says something is done to the parts; it does not say the job is made of them. Skip 'The job' and go back to the thing the doing is done to (step 9 d). Wrong: `relative_to` 'The job'.

#### T7b. 'The steps for X': the whole is X

> Ana wrote out the steps for cleaning the press. First came wiping the rollers, then draining the ink tray, and last oiling the hinge.

```json
{"passage_id": "T7b", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Ana", "label": "Ana", "support": "Ana wrote out the steps for cleaning the press.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "wiping the rollers", "support": "First came wiping the rollers, then draining the ink tray, and last oiling the hinge.", "measure": "", "relative_to": "cleaning the press", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "draining the ink tray", "support": "First came wiping the rollers, then draining the ink tray, and last oiling the hinge.", "measure": "", "relative_to": "cleaning the press", "certainty": "clear"},
  {"noetic": "^6", "mind": "", "label": "oiling the hinge", "support": "First came wiping the rollers, then draining the ink tray, and last oiling the hinge.", "measure": "", "relative_to": "cleaning the press", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. In 'the steps for X' the whole is X, starting at X (step 9 c). Wrong: `relative_to` 'the steps for cleaning the press' ('the steps' only groups the parts).

#### T8. A pull aimed at something of a thing

> Nadia watched the old letterpress stamp each sheet and felt a pull toward its slow, exact motion. She turned her face away from the sharp fumes of the cleaning solvent. The loud hiss of the air compressor nearby, however, barely registered with her.

```json
{"passage_id": "T8", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Nadia", "label": "Nadia", "support": "Nadia watched the old letterpress stamp each sheet and felt a pull toward its slow, exact motion.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^2", "mind": "Nadia", "label": "its slow, exact motion", "support": "Nadia watched the old letterpress stamp each sheet and felt a pull toward its slow, exact motion.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^3", "mind": "Nadia", "label": "the sharp fumes of the cleaning solvent", "support": "She turned her face away from the sharp fumes of the cleaning solvent.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^4", "mind": "Nadia", "label": "The loud hiss of the air compressor", "support": "The loud hiss of the air compressor nearby, however, barely registered with her.", "measure": "barely registered", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage says the pull is toward the motion. Label what the passage names (rule 5). The letterpress stays in the support. Wrong: label 'the old letterpress'. Wrong: label 'a pull' (the Mind's own pull is never the label, step 6). `^3`: a move away is shown. `^4`: stop the label before 'nearby'; 'loud' says how the hiss itself is and is not the measure (rule 10c). No `^3` for the hiss: 'however' shows nothing by itself (rule 5).

#### T9. A cue and a response

> Every time the kettle clicked off, Oskar, a night porter, automatically reached for the chipped blue mug.

```json
{"passage_id": "T9", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Oskar", "label": "Oskar", "support": "Every time the kettle clicked off, Oskar, a night porter, automatically reached for the chipped blue mug.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Oskar", "label": "reached for the chipped blue mug", "support": "Every time the kettle clicked off, Oskar, a night porter, automatically reached for the chipped blue mug.", "measure": "Every time the kettle clicked off", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. In 'every time X, the Mind does Y', the label is Y and the whole 'every time X' clause is the measure (rule 6e). Leave off the name, the role phrase and 'automatically'; start at the doing word (step 5 i). The `^7` is clear: the rate words pass, and 'automatically' says what the exposure did. The kettle is kept: it is in the measure. No `^8`/`^9` pair: the passage shows only that he acts without thinking (rule 13). The `^1` label is the name only. 'a night porter' is a plain job title: no `^5` entry, no held entry, no note (rule 6b). Wrong: label 'the chipped blue mug' (only the thing the action is done to). Wrong: label 'the kettle' (it sits inside the rate words).

#### T10. Several noticed things, one thing comes

> Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.

```json
{"passage_id": "T10", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Rosa", "label": "Rosa", "support": "Rosa saw the grey film on the jar and caught a sharp, sour smell.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Rosa", "label": "the grey film on the jar", "support": "Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.", "measure": "", "relative_to": "the starter had turned", "certainty": "ambiguous", "other_candidate": "reasoning"},
  {"noetic": "^9", "mind": "Rosa", "label": "the starter had turned", "support": "Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.", "measure": "", "relative_to": "the grey film on the jar", "certainty": "ambiguous", "other_candidate": "reasoning"},
  {"noetic": "^8", "mind": "Rosa", "label": "a sharp, sour smell", "support": "Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.", "measure": "", "relative_to": "the starter had turned", "certainty": "ambiguous", "other_candidate": "reasoning"},
  {"noetic": "^9", "mind": "Rosa", "label": "the starter had turned", "support": "Rosa saw the grey film on the jar and caught a sharp, sour smell. She knew the starter had turned.", "measure": "", "relative_to": "a sharp, sour smell", "certainty": "ambiguous", "other_candidate": "reasoning"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage says only that she knew: rule 15(d), an uncertain pair. Two things were noticed, so two pairs (step 10, exception 3). The `^9` is written once per trigger with the same label, and each copy points back at its own `^8`. Wrong: one `^9` with two `^8` entries (check C6 refuses the `^8` that has no `^9` pointing back).

#### T11. One statement with a rate and an experience

> Benno slid the next loaf into the oven without thinking. His hands found the peel and the door latch on their own. Years of nightly baking had shaped every movement.

```json
{"passage_id": "T11", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Benno", "label": "Benno", "support": "Benno slid the next loaf into the oven without thinking.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Benno", "label": "nightly baking", "support": "Years of nightly baking had shaped every movement.", "measure": "nightly", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. 'nightly' passes the rate test, and the passage says what the exposure did ('without thinking', 'on their own'). So the `^7` is clear. 'slid the next loaf into the oven without thinking' is that stated effect, so it is not written again under H7-RESULT (rule 17). Leave 'Years of' off the label: two words are left that name what was lived (step 5). The only rate word lies inside the label, so copy that as the measure (step 8). You write no `^5` on 'nightly baking' and none on 'had shaped every movement': the program adds the `^5` that goes with a clear `^7` (rule 6c).

#### E1. Held under H2-COMFORT

> Lotte waited in the corridor outside the exam hall. On the windowsill stood a small clay owl with one chipped ear. Its plain shape gave her a small sense of calm.

```json
{"passage_id": "E1", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Lotte", "label": "Lotte", "support": "Lotte waited in the corridor outside the exam hall.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^2", "mind": "Lotte", "label": "Its plain shape", "support": "On the windowsill stood a small clay owl with one chipped ear. Its plain shape gave her a small sense of calm.", "measure": "", "relative_to": "", "certainty": "held", "held_under": "H2-COMFORT"},
  {"noetic": "^4", "mind": "Lotte", "label": "Its plain shape", "support": "On the windowsill stood a small clay owl with one chipped ear. Its plain shape gave her a small sense of calm.", "measure": "a small sense of calm", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage says only that the thing gave her a good feeling. No word of affinity, no pull, no move toward it. So the `^2` entry is written in full and marked held. The label is what the passage says gave the feeling, as the passage names it. It leans on an earlier naming with 'Its', so the support starts one sentence earlier (step 7). The how-much word 'small' on the feeling gives a clear `^4` beside it (rule 10f).

#### E2. Held under H3-NOPULL

> Ruben walked along the stalls at the book fair. For him the table of travel guides held little appeal.

```json
{"passage_id": "E2", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Ruben", "label": "Ruben", "support": "Ruben walked along the stalls at the book fair.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^3", "mind": "Ruben", "label": "the table of travel guides", "support": "For him the table of travel guides held little appeal.", "measure": "", "relative_to": "", "certainty": "held", "held_under": "H3-NOPULL"},
  {"noetic": "^4", "mind": "Ruben", "label": "the table of travel guides", "support": "For him the table of travel guides held little appeal.", "measure": "held little appeal", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage says only that the thing did not draw him. Nothing against it is stated. So the `^3` entry is written in full and marked held. The same words are a how-little measure, so the clear `^4` is written as well (rule 10a).

#### E3. Held under H3-BORED

> Mirela sat through the afternoon safety briefing. She found the long slide show tedious.

```json
{"passage_id": "E3", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Mirela", "label": "Mirela", "support": "Mirela sat through the afternoon safety briefing.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^3", "mind": "Mirela", "label": "the long slide show", "support": "She found the long slide show tedious.", "measure": "", "relative_to": "", "certainty": "held", "held_under": "H3-BORED"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage says only that she found the thing tedious. No word of dislike is there. So the `^3` entry is written in full and marked held. No `^4`: 'tedious' says what kind, not how much (rule 10d).

#### E4. Held under H5-ROLE

> Edda, a veteran ferry pilot, checked the tide table and then the sky.

```json
{"passage_id": "E4", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Edda", "label": "Edda", "support": "Edda, a veteran ferry pilot, checked the tide table and then the sky.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^5", "mind": "Edda", "label": "a veteran ferry pilot", "support": "Edda, a veteran ferry pilot, checked the tide table and then the sky.", "measure": "", "relative_to": "", "certainty": "held", "held_under": "H5-ROLE"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. A role with an experience word from the list ('veteran') and nothing about what was lived or learned in it. So the `^5` entry is written in full and marked held. The label is the role phrase with its experience word. The `^1` label is the name only. With a plain 'a ferry pilot' there would be no `^5` entry at all.

#### E5. Held under H7-RESULT

> Kasper stepped onto the factory floor. Without thinking, he tucked his tie inside his shirt.

```json
{"passage_id": "E5", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Kasper", "label": "Kasper", "support": "Kasper stepped onto the factory floor.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Kasper", "label": "tucked his tie inside his shirt", "support": "Without thinking, he tucked his tie inside his shirt.", "measure": "Without thinking", "relative_to": "", "certainty": "held", "held_under": "H7-RESULT"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. The passage shows only that he does the thing without thinking. No words pass the rate test. So the `^7` entry is written in full and marked held. The label is the action, starting at the doing word. The measure is the without-thinking words. No pair (rule 13). No `^5` (rule 6b, 6c).

#### E6. Held under H7-NOEFFECT

> Solveig kept a small lemon tree by the kitchen door. She watered it twice a week.

```json
{"passage_id": "E6", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Solveig", "label": "Solveig", "support": "Solveig kept a small lemon tree by the kitchen door.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Solveig", "label": "watered it", "support": "She watered it twice a week.", "measure": "twice a week", "relative_to": "", "certainty": "held", "held_under": "H7-NOEFFECT"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. 'twice a week' passes the rate test. The passage says nothing of what the repeated exposure has done to her. So the `^7` entry is written in full and marked held. Stop the label before the tail that says how often.

#### E7. Held under H7-UNBROKEN

> Yara typed up the night's reports in the back office. The ceaseless whine of the ventilation fans filled the room around her.

```json
{"passage_id": "E7", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Yara", "label": "Yara", "support": "Yara typed up the night's reports in the back office.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^7", "mind": "Yara", "label": "The ceaseless whine of the ventilation fans", "support": "The ceaseless whine of the ventilation fans filled the room around her.", "measure": "ceaseless", "relative_to": "", "certainty": "held", "held_under": "H7-UNBROKEN"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. No words pass the rate test. The passage gives only a word for exposure with no break. So the `^7` entry is written in full and marked held. The measure is that word.

#### E8. Held under H89-FOLLOWS

> Folke watched the new apprentice fumble with the bench vice. He remembered his own first week in the workshop.

```json
{"passage_id": "E8", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Folke", "label": "Folke", "support": "Folke watched the new apprentice fumble with the bench vice.", "measure": "", "relative_to": "", "certainty": "clear"},
  {"noetic": "^8", "mind": "Folke", "label": "the new apprentice fumble with the bench vice", "support": "Folke watched the new apprentice fumble with the bench vice. He remembered his own first week in the workshop.", "measure": "", "relative_to": "his own first week in the workshop", "certainty": "held", "held_under": "H89-FOLLOWS"},
  {"noetic": "^9", "mind": "Folke", "label": "his own first week in the workshop", "support": "Folke watched the new apprentice fumble with the bench vice. He remembered his own first week in the workshop.", "measure": "", "relative_to": "the new apprentice fumble with the bench vice", "certainty": "held", "held_under": "H89-FOLLOWS"}
 ],
 "not_enough_information": [], "guide_problem": ""}
```

Note. A memory follows something noticed. There are no bringing words and no word of sudden arrival. Exactly one named thing, in the sentence right before, is the plain occasion for it. So both entries of the pair are written in full and marked held. 'watched' and 'remembered' are lead-ins and are left off the labels (step 5 ii). The apprentice is not listed as a Mind in this example: nothing of his awareness is shown, and he has no entry of another Noetic. Rule 4 has no added line for a person who is shown only doing a physical thing. That question is the owner's (section B5).

#### E9. Not held: a sentence stands between

> Folke watched the new apprentice fumble with the bench vice. He put down his plane and wiped his hands. He remembered his own first week in the workshop.

```json
{"passage_id": "E9", "none_of_these": false,
 "entries": [
  {"noetic": "^1", "mind": "Folke", "label": "Folke", "support": "Folke watched the new apprentice fumble with the bench vice.", "measure": "", "relative_to": "", "certainty": "clear"}
 ],
 "not_enough_information": ["A sentence stands between the apprentice at the vice and the memory of his own first week, so no pair is written."], "guide_problem": ""}
```

Note. Another sentence stands between the noticed thing and the remembering words. H89-FOLLOWS does not fit. Write no pair and add a note (rule 17).

### B5. Record of changes from version 1.2 (for the owner and reviewers)

Labelers: this section changes nothing in the rules above. Follow the rules as they are written.

Part A is unchanged. Rule 15 is unchanged, word for word. Rules 3, 8 and 9 are unchanged.

What moved. The field `words` is gone. For `^2`, `^3`, `^5`, `^6`, `^8`, `^9` it splits into `label` (short) and `support` (full). For `^4` and `^7` the old `words` (how-much words, rate words) becomes `measure`, and the old `relative_to` (the thing) becomes `label`. So every label names a thing, and nothing is lost.

| Where | Change | Why |
|---|---|---|
| Entry format | `label` plus `support` in every entry; `measure` for `^4` and `^7`; `mind` and `relative_to` copy labels; `certainty` may be `held`; new fields `held_under`, `clue`, `no_fuller_name` | Owner's direction: a short, consistent identifying label plus the full supporting quote |
| B2 (new) | The checks R0 and C1 to C9 are written into the guide | A labeler should know what is sent back and why |
| Rule 1 | One sentence added | Rule 1 must not order the `^5` that rule 6(c) leaves to the program |
| Rule 2 | Three sentences replaced; four paragraphs added | Version 1.2 named only two other cases and told the labeler to quote the partner afresh |
| Rule 4 | One line added: the label of a Mind | New entry format |
| Rule 5 | Seven lines added | What to label; which sentence; what is held |
| Rule 6 | Replaced: the rate test, what `^5` needs, one statement with a rate and an experience, what a clear `^7` needs, what the `^7` label names | Version 1.2 said 'mark both, with different words' in rule 6 and 'the same words may occupy two Noetics' in rule 1 |
| Rule 7 | Four lines added: group words, one entry per part, accompanying details, clues | The whole is now found by rule 16, step 9; clues are counted in their own row |
| Rule 10 | Replaced by parts (a) to (g) | Says more plainly what version 1.2 implied |
| Rule 11 | One sentence added | Rule 11 must not order what rules 6(c) and 13 forbid |
| Rule 12 | Removed | What it said is now in rule 6(e) and rule 16 |
| Rule 13 | Replaced | Version 1.2 said 'mark `^7`' here while rule 6 said `^7` needs rate words |
| Rule 14 | Replaced: three kinds of certainty | Keeps three doubts apart: about the passage, about an open question on a definition, about a rule |
| Rule 16 | Replaced: how to point | Owner's direction |
| Rule 17 (new) | Eight kinds held for the owner | A question about what a definition covers is not decided here; the entry is written, marked held and counted in its own row |
| Examples | X1 to X6 rewritten in the new format; X7, T1 to T11 and E1 to E9 added; all made up | Rule 16 needs examples that are never used as cases |
| After the one review round of the build | Header: the bullet 'Where there is no held kind'. B1: 'How the fields go together'. B2: an entry left out after a re-ask is kept as dropped; sentences added to C1, C5, C6 and C8. Rules 13 and 17: an action used as the stated effect of a clear `^7` is not written again under H7-RESULT. Rule 14: a Part A saying against a numbered rule. Notes of E8 and T11. The list of working lines below | Findings of the review round. None of these changes decides what a definition covers |

Proposals that wait for the owner's signature, before any new passage is sealed:

- The nine conventions at the end of rule 16.
- The eight hold codes of rule 17. If the owner answers a held question before the seal, that code is removed from rule 17.
- In the plan, not in this guide: the bars, the outcome words, the `^5` bar row and the seal conditions S1 to S5.

Working lines with no held kind. Each one touches a question that is open with the owner (plan section 19). The fixed design gives it no held row. So both teams follow the line inside the ordinary rows. Some lines are kept from version 1.2. Some are taken from how the rules were already applied. None is canon. None decides what a definition covers. Each is listed so that the owner can strike it before the seal. On the owner's sign-off sheet (`label_v2/OWNER_SIGNOFF_SHEET.md`) these lines are item 9, 'Working lines used inside the pass/fail rows until you rule'.

- A stated affinity aimed at a thing, with no move toward it shown, is a clear `^2` (rule 5).
- A standing skill or habit that the passage names as the Mind's own is a clear `^5`: 'a habit', 'second nature', 'ingrained', 'muscle memory' (rule 6b). Words that only say how an action is done now ('automatically', 'without thinking') give no `^5`. Part A lists the saying "Muscle memory." under `^7`. Under rule 6 the words 'muscle memory' give a clear `^5`, and a `^7` for that moment is at most held (H7-RESULT).
- A plain job title or life stage is left out (rule 6b, H5-ROLE).
- 'always' on what a thing does to the Mind gives no `^7` (rule 6a).
- Repeats, or time spent doing a thing, stated with no how-often word give no `^7` entry and no held entry: practising with no rate, 'years of loading and unloading' (rule 6a). Part A lists the saying "Practice makes perfect." under `^7`. A labeler who meets this case reports it in `guide_problem` (rule 14).
- A number of winters or years is a length of time, not a count of repeats (rule 6a).
- The no-appeal phrases are how-little measures for `^4` (rule 10a).
- A how-much word on any feeling a thing gives the Mind gives a `^4` (rule 10f).
- What kind of impression a thing made is not `^4` (rule 10d).
- The steps of a procedure are written as `^6` parts (rule 16, step 9c; example T7b).
- A further memory with only a sudden word gets no pair (rule 2).
- An action that a cue sets off without thinking is not written as a `^9`, and no pair is written (rule 13).
- For H89-FOLLOWS, 'just before' means the sentence right before, or the same sentence (rule 17).
- A naming followed by a doing word is not the whole (rule 16, step 9d).
- Example X4 writes no `^7` for 'four times before lunch', as version 1.2 did.
- An action done without thinking that is the stated effect of a clear `^7` is not written again as a held `^7` (rule 13; rule 17, H7-RESULT; examples T2 and T11). The other choice: write it as a second `^7`, held under H7-RESULT.
- When a saying of Part A points to a Noetic and a numbered rule says to hold the entry or to write none, the labeler follows the numbered rule (rule 14). When the rule says none, the labeler reports the case in `guide_problem`.

These are conventions for applying the definitions in this study. They do not change a definition. The owner may correct any of them.

One question has no working line at all. Is a person who is shown only doing a physical thing a Mind to be listed? Rule 4 keeps its version 1.2 text on who is a Mind and has no line for it. Example E8 does not list such a person (the apprentice), who has no entry of another Noetic. Under rule 4 a person who has an entry of another Noetic is always listed. Labelers may still differ on this. The report counts unmatched Minds that carry no other entry on their own line. The question stays with the owner (plan section 19).

### B6. One-page checklist

Use this on every passage.

1. Read the whole passage first. Use only what it says (rule 9).
2. List every Mind once. One `^1` entry each. The label is the name only, at its first full mention (rule 4).
3. Go through `^2` to `^9`. For each role, find the evidence sentence (rule 16, step 1). No such words and no held kind: no entry.
4. Choose the certainty (rule 14).
    - `clear`: the passage settles it under this guide.
    - `ambiguous`: the passage can be read two ways. Add `other_candidate`.
    - `held`: one of the eight kinds of rule 17. Add `held_under`. Write the entry in full. Never leave it out. Never write it as clear.
5. Write the `label` (rule 16, steps 2 to 6).
    - It is the naming in the evidence sentence. Go back only for a pointer.
    - Never a pointer. Never a holder word. Never a naming phrase cut down to its bare noun.
    - For a happening: start at the doing word, without the Mind. Never only the thing the action is done to.
    - 1 to 12 words. If unsure where to stop, stop earlier.
6. Write the `support` (step 7): whole sentences, at most 4. It holds the label and the measure.
7. `^4` and `^7`: write the `measure` (step 8). Every other Noetic: `measure` is `""`.
8. `mind`: copy the `^1` label, character for character. It is `""` only for `^6`.
9. `relative_to`: `^8` and `^9` copy each other's label. `^6` gets the whole, or `""` with `clue` true. Every other Noetic: `""`.
10. Pairs: every `^8` has a `^9` that points back, with the same mind, the same certainty and the same hold code. Every `^9` has its `^8`, except a `^9` with `reached_by` reasoning. That `^9` has `relative_to` `""` and is never `held`.
11. A sign or a conclusion: rule 15 decides. A clear pair (15a); `^6` clues plus a `^9` with `reached_by` reasoning (15b); both (15c); or an uncertain pair (15d).
12. Do not write a `^5` on the label of your own `^7` (rule 6c).
13. One thing, one entry (step 10). No duplicates. Not the same thing twice in two certainties either.
14. Nothing holds any Noetic: `none_of_these` is `true` and `entries` is empty. A hint goes under `not_enough_information`. A doubt about a rule goes in `guide_problem`.
15. Every quoted field is an exact copy: the same letters, the same capitals, the same punctuation, one unbroken stretch.
16. Write `^1` to `^9` only. Never label Worlds, Domains, Drives or Registers (rule 8).
17. If the checker sends an entry back: fix what the message names and return the whole record again. Up to three tries. A failing entry that you leave out is still counted, as a dropped entry.

The eight hold codes at a glance (rule 17 has the exact words):

| Code | Noetic | Hold it when the passage gives only this |
|---|---|---|
| H2-COMFORT | `^2` | a good feeling from a thing; no affinity, no pull, no move toward it |
| H3-NOPULL | `^3` | no appeal or no interest; nothing against the thing (also write the clear `^4`) |
| H3-BORED | `^3` | boredom, dull, tedious; no word of dislike |
| H5-ROLE | `^5` | a role with an experience word; no length of time; nothing about what was lived or learned |
| H7-RESULT | `^7` | an action done without thinking; no rate words |
| H7-NOEFFECT | `^7` | rate words; nothing about what the exposure did to the Mind |
| H7-UNBROKEN | `^7` | a word for exposure with no break; no rate words |
| H89-FOLLOWS | `^8` and `^9` | a memory or a picture that follows one named thing; no bringing words |
