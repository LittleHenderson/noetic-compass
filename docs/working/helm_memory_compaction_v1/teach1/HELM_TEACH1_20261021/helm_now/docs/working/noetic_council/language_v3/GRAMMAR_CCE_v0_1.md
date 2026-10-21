# CCE v0.1 — Controlled Core English: the grammar, in words

Written 2026-10-14 (Pacific) for LM-T1. This is the DESCRIPTION of the grammar (no code). It is frozen (sha256 in
`FROZEN.json`) before any parser code runs on the hand set. Source design:
`cas_language_first_principles_map_v1/` (MAP.md section A, TRANSLATOR_SPEC.md section 3, OPEN_QUESTIONS.md defaults
Q1-Q19, all taken).

CCE is a small, strict part of English. A sentence is either inside CCE (it has exactly one reading as CAS content)
or it is refused with a named code. Nothing is guessed.

## 1. Names

- **Minds:** `I`, `you`, or a declared name. A name is one capitalized word (letters, digits, `_`), for example `Ana`.
  It must be declared earlier in the same text with `Ana is a Mind.` Third-person pronouns (he, she, him, her, his,
  they, them, it) are **not** CCE.
- **Surface agreement (no content):** `I am` / `you are` / `Ana is`; `I have` / `Ana has`; `I intake` / `Ana intakes`;
  `I do not intake` / `Ana does not intake`. When `I` is an object it is written `me` ("resonates with me"). In
  `is part of who ... is`, write `who I am` / `who you are` / `who Ana is`.
- **Ideas:** a double-quoted text with no quote inside (`"the offer"`) or an Omega name `Ω_name` (letters, digits,
  `_`). Names are copied byte for byte.
- **Numbers:** digits (`2`, `0.5`, `10`) or the closed words `one` … `ten` and `half` (= 0.5). Numbers in content
  are compared exactly (`2.0` = `2`). Vague amounts (`a lot of`, `some`, `a bit of`, `many`, `few`, `several`,
  `much`) are refused.

## 2. The ten frames (one per Noetic; verbs from the verbatim definitions)

`<M>` = Mind slot, `<I>` and `<J>` = Idea slots, `<D>` degree, `<R>` rate, `<U>` unit word, `<P>` pattern word
(unit and pattern are one lowercase word each, e.g. `day`, `daily`, `weekly`).

| Noetic | CANON wording (fixed twin) | ALIAS wording (same content) | Slots in content |
|---|---|---|---|
| ^0 Idea | `<I> is an Idea.` | — | I |
| ^1 Mind | `<M> intakes <I>.` / `<M> processes <I>.` / `<M> stores <I>.` / `<M> outputs <I>.` (the verb is the ACT and is content) | `<M> is paying attention to <I>.` (no ACT) | M, I, ACT (intakes / processes / stores / outputs, or absent) |
| ^2 Positive | `<M> has an affinity for <I>.` / `<M> is attracted toward <I>.` | `<M> is drawn to <I>.` / `<I> speaks to <M>.` | M, I |
| ^3 Negative | `<M> is adverse to <I>.` / `<M> is repelled by <I>.` | `<I> rubs <M> the wrong way.` | M, I |
| ^4 Vibration | `<I> resonates with <M> to degree <D>.` or, degree not stated, `<I> resonates with <M>.` | `<I> struck a chord with <M>, degree <D>.` / `<I> made an impression on <M>, degree <D>.` (each also without `, degree <D>`) | I, M, D (or D absent) |
| ^5 Female | `<M> is impregnated with <I>.` / `<M> is composed of <I>.` | `<I> is part of who <M> is.` | M, I |
| ^6 Male | `<I> is impregnated with <J>.` / `<I> is composed of <J>.` | `<I> breaks down into <J>.` and, with a Mind doing it, `<M> breaks <I> down into <J>.` / `<M> breaks down <I> into <J>.` / `<M> unpacks <I> into <J>.` | I, J (and M when a Mind is named) |
| ^7 Rhythm | `<M> is exposed to <I> at rate <R> per <U>, pattern <P>.` or, rate and pattern not stated, `<M> is exposed to <I>.` | `<M> practices <I> at rate <R> per <U>, pattern <P>.` | M, I, R, U, P (or R, U, P absent) |
| ^8 Above/Cause | `<I> triggers <J> to come to <M>.` | `<I> reminds <M> of <J>.` / `<I> made <M> think of <J>.` | I (trigger), J (the other Idea), M |
| ^9 Below/Effect | `<J> is brought to <M> by <I>.` or, trigger unknown, `<J> is brought to <M> by an unknown trigger.` | `<J> came to <M> from <I>.` or, trigger unknown, `<J> came to <M> out of nowhere.` | J (the Idea brought), M, I (trigger, or absent when unknown) |

Rules on the frames:
- The **verb frame picks the Noetic**, never the topic words. `Ana is attracted toward "the risk".` is ^2.
- ^5 vs ^6 is decided by the **subject's kind**: a Mind subject is ^5, an Idea subject is ^6.
- ^8 needs two **different** Ideas (`"x" triggers "x" ...` is refused SAME_IDEA_TRIGGER). ^9 likewise.
  ^6 needs "another Idea" (`"x" is composed of "x"` is refused SLOT_TYPE).
- A Mind in an Idea slot, or an Idea in a Mind slot, is refused SLOT_TYPE.
- A capitalized name in a Mind slot that was not declared is refused UNDECLARED_NAME.
- Which wording (CANON or ALIAS, or which of two CANON verbs) was used is **not** content. `Ana has an affinity for
  "x".` and `Ana is drawn to "x".` have the same content. (Exception: the ^1 verb IS content, the ACT.)

## 3. Negation (polarity)

Put `not` at the frame's verb: `Ana is not attracted toward "x".`, `Ana does not have an affinity for "x".`,
`I do not intake "x".`, `"x" does not resonate with me.`, `"x" did not strike a chord with me, degree 2.`,
`"x" does not trigger "y" to come to me.`, `"y" did not come to me from "x".` Content: the same Noetic, with
polarity DENIED. **The word `not` never makes ^3.** `Ana is not attracted toward "x".` is ^2 DENIED.

Absence is different: `There is no Ω_flour.` (a stated absence; no Noetic).

## 4. The tail: Domain, Register, Drive

After a frame, comma-separated, **in any order**, each at most once:
- Domain word: `principled` (P), `cognitive` (C), `evaluative` (E), `operational` (O).
- Register: `transcendent register` (T), `analytical register` (A), `affective register` (f), `embodied register`
  (E); or a register SET: `in analytical and affective registers`, `in analytical, affective and transcendent
  registers` (the set ⟨…⟩: order does not matter; it is a set).
- Drive: `for Unity` (F1), `for Wisdom` (F2), `for Vitality` (F3), `for Connection` (F4), `for Agency` (F5),
  `for Structure` (F6), `for Purpose` (F7).

Example: `Ana is repelled by "the shortcut", principled, affective register.` = `Ana is repelled by "the shortcut",
affective register, principled.` (same content). Unstated = unspecified (register-neutral), never a default.
Social style is never a Register: `formal register`, `casual register`, `polite register` are NOT CCE.

## 5. Recipes (Clarification 9)

`To make <Ω>, use <TERM>; plus <TERM>; plus <TERM>.`

- TERM is `<number> of <NOETIC REF>, <domain>[, <register>][, for <Drive>]` (domain required in a recipe; tail
  items in any order), or `<number> of <Ω_other>` (an outcome as a prerequisite), or an emergent term
  `<number> of (<STATE> combined with <STATE> into <RESULT>)` (more factors: `... combined with <STATE> combined
  with <STATE> into <RESULT>`).
- NOETIC REF is the Noetic's name (`Idea`, `Mind`, `Positive`, `Negative`, `Vibration`, `Female`, `Male`,
  `Rhythm`, `Above/Cause`, `Below/Effect`) **or** its verbatim definition without the final period, in square
  brackets: `[The Idea brought to Mind by an Above/Cause trigger]`.
- RESULT is `Ω_name`, or `<Noetic name>, <domain> named Ω_name`, or `<Noetic name> named Ω_name`.
- `+` is co-presence ("plus"); `×` is "combined with ... into <named result>". "Combined" with **no named result**
  is refused OPERATOR_DISCIPLINE (Clarification 10). English "and" never means `×`.
- After the recipe sentence, optional sentences: `Side product: <number> of <Ω_side>.` (leakage b·Λ·Ω_side; with no
  number, `Side product: <Ω_side>.` means an implicit coefficient), `Helped by <Ω>.` (catalyst),
  `Slowed by <Ω>.` (inhibitor).
- Terms are a multiset: order does not matter. Numbers are exact.
- Stock (how much is on hand): `There is <number> of <NOETIC REF>, <domain>[, <register>][, for <Drive>].` or
  `There is <number> of <Ω>.`

## 6. Turns, evidence, gate (speech acts)

- `I checked: <sentence(s)>` — evidence CHECKED for everything after it.
- `You said: <sentence(s)>` — evidence USER_SAID.
- `I need <slot words> for <Ω>. What is it?` — CLARIFY naming the unfilled slot (the slot words are copied byte for
  byte, e.g. `the stock of Ω_leaves`).
- `I cannot tell.` — the gate's UNDETERMINED. Fixed wording; never varied.
- `I cannot support that: <reason words>.` — REFUSE_CLAIM (reason copied byte for byte, e.g. `no evidence`).
- `New subject: <Ω>.` — ACK of a subject change. `Are we still on <Ω>?` — CLARIFY at a possible seam.
  `Topic: <Ω>.` — the turn's topic header.
- Promise is not in CCE v0.1 (no turn type).

## 7. Facts, declarations, sets, order, nesting, fractals

- `Ana is a Mind.` — declaration (relation is_a Mind).
- `"tea" is one of {"tea", "coffee"}.` — membership (the braces hold a set; order inside does not matter).
- `Fact: "rain" leads to "flood".` — a fact about the world (relation leads_to; not a Noetic, not a Mind state).
- `Ω_b needs Ω_a first.` — RPM prerequisite (order, one direction).
- Sequence (time order; not ^8): `First <frame>; then <frame>.` (more steps: `; then <frame>`). Each step is a
  frame with its own tail, without its final period. Reasoned cause (OPEN_QUESTIONS Q1) is written as a sequence:
  `First I break down "the failure" into "the late part"; then "the cause list" is brought to me by "the failure".`
  ("Because", "therefore", "so" are NOT CCE.)
- Nesting (an Idea slot filled by a whole frame): `that [<frame>]`, e.g. `I intake that [Ana is attracted toward
  "x"].` Depth at most 2 (OPEN_QUESTIONS Q9): `I store that [Ana intakes that [Bo is repelled by "x"]].` is depth 2
  and allowed; depth 3 is refused NEST_TOO_DEEP.
- Fractal sequence (PROPOSED form, 2 to 4 Noetics): `The fractal sequence is Above/Cause : Below/Effect : Vibration.`

## 8. Refusals (a sentence outside CCE is never guessed)

| Code | When |
|---|---|
| NOT_CCE | words or shapes outside the grammar: e.g. `"x" is bad.`, any `because` / `therefore` / `so`, bare `cause` / `effect` / `side effect`, pronouns he/she/they/it, `formal register`, an unknown verb |
| HEDGE | `might`, `maybe`, `perhaps`, `possibly`, `could`, `if`, `unless` (outside quotes) |
| VAGUE_QUANTITY | `a lot of`, `some`, `a bit of`, `many`, `few`, `several`, `much` |
| AMBIGUOUS | two different readings fit equally |
| SLOT_TYPE | wrong kind of name in a slot; ^6 with the same Idea twice |
| SAME_IDEA_TRIGGER | ^8 or ^9 with the same Idea as trigger and result |
| UNDECLARED_NAME | a capitalized Mind name that was not declared earlier in the text |
| NEST_TOO_DEEP | nesting deeper than 2 |
| OPERATOR_DISCIPLINE | "combined" with no named result (`×` needs a named emergent result) |

Words inside double quotes are names, not grammar: `Ana is drawn to "the cause"` is fine.

## 9. Content (what a sentence means, as a JSON record) — the gold format

A text (one or more sentences) maps to ONE content record. Fields (omit nothing; use the empty value when unused):

```json
{
  "turn": "ANSWER",              // ANSWER | CLARIFY | REFUSE_CLAIM | ACK
  "evidence": "NONE",            // NONE | CHECKED | USER_SAID
  "gate": "RIGHT_PATH",          // RIGHT_PATH | UNDETERMINED ("I cannot tell." only)
  "topic": null,                 // "Ω_x" from "Topic: Ω_x." / "New subject: Ω_x." / "Are we still on Ω_x?" / CLARIFY's Ω
  "terms": [],                   // frames (a multiset; order free)
  "sequence": [],                // frames in time order (First ...; then ...)
  "recipe": null,                // {"omega": "Ω_x", "terms": [...], "leakage": [...], "catalysts": [], "inhibitors": []}
  "stocks": [],                  // [{"amount": "4", "ref": STATE or {"outcome": "Ω_y"}}]
  "relations": [],               // ["is_a", "Ana", "Mind"] | ["one_of", "\"tea\"", ["\"coffee\"", "\"tea\""]] |
                                 // ["leads_to", "\"rain\"", "\"flood\""] | ["needs_first", "Ω_b", "Ω_a"] | ["absent", "Ω_flour"]
  "fractal": [],                 // e.g. [8, 9, 4]
  "lacunae": [],                 // CLARIFY slot words, e.g. ["the stock of Ω_leaves"]
  "reason": null                 // REFUSE_CLAIM reason words, e.g. "no evidence"
}
```

A **frame term**:

```json
{"noetic": 2, "domain": "P", "register": ["f"], "drive": "F2", "polarity": "ASSERTED",
 "slots": {"M": "Ana", "I": "\"the offer\""}}
```

- `domain`: "P" | "C" | "E" | "O" | null. `register`: null, or a list of register letters ("T", "A", "f", "E"),
  one letter for a single register, two or more for a register set (sorted in the order T, A, f, E).
  `drive`: "F1".."F7" | null. `polarity`: "ASSERTED" | "DENIED".
- `slots` keys: `M` (Mind: "I", "you" or the declared name — `me` is written back as "I"), `I`, `J` (Ideas, with
  their double quotes kept, e.g. "\"the offer\"", or "Ω_x"), `ACT` (^1 only), `D` (degree), `R` (rate), `U`
  (unit), `P` (pattern). Numbers are strings in plain digits ("3", "0.5"). An absent slot is left out.
- A nested Idea slot holds `{"that": <frame term>}` instead of a string.

A **recipe term**: `{"coefficient": "2", "kind": "state", "noetic": 9, "domain": "O", "register": ["A"],
"drive": "F1"}`, or `{"coefficient": "1", "kind": "outcome", "name": "Ω_water"}`, or
`{"coefficient": "1", "kind": "emergent", "components": [<state>, <state>], "result": "Ω_x"}` (a component state is
`{"noetic": .., "domain": .., "register": .., "drive": ..}`; a result written `Positive, principled named Ω_x` is
`"^2^P|Ω_x"`, and `Positive named Ω_x` is `"^2|Ω_x"`). Leakage: `{"coefficient": "0.1", "side": "Ω_y_side",
"implicit": false}` (implicit true and coefficient "1" when no number was written).

The `is_a` relation for a declaration and the `^0` frame for `"x" is an Idea.` are different records: the first is
a relation, the second is a frame term with slot I.

## 10. Composition of the hand set (from TEST_PLAN.md section 5)

64 sentences (a "sentence" may be a short text of 2-3 CCE sentences when a declaration is needed):
- 48 positives: each of the 21 mapped fundamentals (F1-F12, F14-F17, F19-F23) at least twice (42), plus 6 turn
  items (ANSWER with `I checked:`, CLARIFY naming a slot, REFUSE_CLAIM, `I cannot tell.`, `You said:`, one
  declaration). At least 16 of the 48 use ALIAS wording; at least 8 use a non-default slot or tail order.
- 16 traps from MAP.md section D. Trap-parse (must parse to the right reading): "not attracted toward" -> ^2 DENIED;
  "breaking down an idea" (in CCE form) -> ^6; "struck a chord ... degree 3" -> ^4; "is one of {...}" -> membership;
  "First ...; then ..." -> sequence. Trap-refuse (must be refused with the named code): "X is bad" (NOT_CCE);
  a "because" sentence (NOT_CCE); "might" (HEDGE); "a lot of" (VAGUE_QUANTITY); `"x" triggers "x"`
  (SAME_IDEA_TRIGGER); an undeclared name in a ^5 or ^6 slot (UNDECLARED_NAME); same-Noetic multi-register
  "combined" with no named result (OPERATOR_DISCIPLINE); a feminine pronoun offered as ^5 (NOT_CCE); "formal
  register" offered as |A (NOT_CCE); depth-3 nesting (NEST_TOO_DEEP); "side effect" offered as ^9 (NOT_CCE).
