# GRAMMAR_CCE_v0_1 — language_v3 addendum

Two additions to `GRAMMAR_CCE_v0_1.md`. Nothing in the frozen grammar file was edited; it is byte-identical to
the base build and its sha256 in `FROZEN.json` still matches. This addendum is the whole of the grammar change,
and it adds two things only: a number form and two turn forms. The frames, the tail, the recipes, the relations,
the nesting rule, the fractals, the refusals and the normalization are untouched.

---

## 1. The number form `p/q` (the owner's Q13 ruling)

`GRAMMAR_CCE_v0_1.md` section 5, and `OPEN_QUESTIONS` Q8, gave `<number>` as digits-with-decimals or one of the
words `one` … `ten`, `half`. A fraction therefore had **no form at all**. That is why LM-T4 recorded **5,903
yields with no sentence**: a coefficient such as `1/3` could not be written.

`<number>` is now:

    <number>  ::=  p/q                      e.g. 1/3, 3/7, 22/7, 1/4
                |  digits with decimals     e.g. 0, 2, 0.5, 2.25, 0.0625
                |  one number word          one … ten, half

with `p` an integer `0` or a number without a leading zero, and `q` an integer starting at 1 with no leading zero.
No sign, no spaces, no exponent. `1/0`, `1/`, `/3`, `1//3` and `-1/3` are not numbers and are refused `NOT_CCE`.

Wherever `<number>` appeared, `p/q` now appears: a recipe coefficient (`1/3 of Male, operational`), a stock amount
(`There is 1/3 of Ω_flour.`), a leakage coefficient (`Side product: 1/9 of Ω_steam.`), a degree
(`to degree 1/2`), and a rate. No new number word was invented: Q8's closed word list is unchanged, and a fraction
is written as `p/q`, never as a word.

### The exactness rule

One value has one canonical text, and **nothing rounds**:

- A value with an exact finite decimal form is written as that decimal. `1/4` is read as one quarter and written
  `0.25`. `2.0` is written `2`. `2/8` is written `0.25`.
- A value with no exact finite decimal form is written as reduced `p/q`. `1/3` is written `1/3`. `2/6` is written
  `1/3`. `22/7` is written `22/7`, never `3.142857`.
- A finite decimal form exists exactly when the reduced denominator is `2^a · 5^b` and nothing else. The test is on
  the whole denominator, so `1/5` has one (`0.2`) and `1/3` does not.
- Asking for the decimal form of a value that has none raises `Refusal` with the code
  **`LOSSY_CONVERSION_REFUSED`**. That is the rule the reference implementation at
  `docs/working/noetic_council/language_v2/numbers.py` states, ported into this package's own number handling.

Two written forms of one value are one quantity, so `0.25`, `1/4` and `2/8` are one content, and `half`, `0.5` and
`1/2` are one content. This is the choice `FROZEN.json` already made for `2.0` and `2`, carried to fractions:
comparing written forms instead would split one number into several contents and break the round trip.

### Refusal code added

| Code | When |
|---|---|
| LOSSY_CONVERSION_REFUSED | a decimal form was asked for and the value has no exact one; the fraction is written `p/q` instead and is never rounded |

---

## 2. Two turn forms: REFUSE and CLOSE

`GRAMMAR_CCE_v0_1.md` section 6 gave sentence forms for CLARIFY, ANSWER, ACK and REFUSE_CLAIM, and the coverage
ledger recorded **U-TURN COVERED 4, LACUNA 2** — with REFUSE and CLOSE having no form. Both now have one.

The wording was chosen from `api/notation/turn_admissibility.py` (the compiler-adjacent turn gate in
`noetic-compass-scaffold`), which names the fact each turn requires:

- `REFUSE` requires `boundary_violation`, and its effects are `boundary_preserved` and
  `alternative_path_available`. So the form names the act that was not done and carries the boundary words as
  `reason`.
- `CLOSE` requires `response_delivered`, and its effect is `dialogue_turn_closed`. So the form is a bare closing
  statement, optionally naming the subject that is being closed.

### REFUSE

    I will not do that: <reason words>.

- `reason` holds the words after the colon, byte for byte, e.g. `boundary violation`. Same shape and same field as
  REFUSE_CLAIM's reason, so there is one place reasons live.
- It is a **different sentence from `I cannot support that: …`** (REFUSE_CLAIM) and the two never read as each
  other. REFUSE_CLAIM refuses a *claim* because the evidence will not carry it; REFUSE declines an *act* because
  it crosses a boundary. Collapsing them would lose exactly the distinction the turn gate draws.
- It carries `reason` and nothing else. A REFUSE content that also holds frames, a recipe, a topic, stocks or
  relations is refused by the renderer rather than written as a sentence that drops them.

### CLOSE

    That closes the turn.            (no subject named)
    That closes <Ω>.                 (the subject that is closed)

- The first sets `turn` = `CLOSE` and leaves `topic` empty. The second also sets `topic`.
- It carries `topic` at most, and nothing else. Content that a closing sentence cannot say is refused by the
  renderer, never dropped.
- `That closes the turn.` contains no pronoun, no hedge, no banned marker and no vague quantity, so it passes the
  grammar's own global checks without those checks being loosened. (`it` is refused everywhere in CCE, so the form
  says `the turn`, not `it`.)

### Both turns

- Both accept the evidence prefix: `I checked: I will not do that: boundary violation.`,
  `You said: That closes the turn.`
- Both round-trip: the sentence renders, parses back to the same record, and the record is identical after
  normalization.
- Every turn type with **no** form still raises and is never guessed: `OPEN`, `MIRROR`, `EMPATHIZE`, `PLAN`,
  `REPAIR` raise on render (`turn type … has no CCE v0.1 form`) and a sentence claiming one is refused `NOT_CCE`.

### Varied surface wordings for all five turn types (`rng` draws, `round_trip` verifies)

When `rng=None`, `render` emits the canonical (index 0) sentence for each turn type. When a seeded `rng` is passed
(including via `cce.say`), `render` draws from 5 closed surface templates per turn type, and `parse` reads every
template back to the identical canonical content record:

- **REFUSE** (`CLARIFY`/`REFUSE_CLAIM` distinct):
  1. `I will not do that: <reason>.` (canonical)
  2. `I must refuse that: <reason>.`
  3. `That is refused: <reason>.`
  4. `I cannot comply with that: <reason>.`
  5. `I refuse that action: <reason>.`
- **REFUSE_CLAIM**:
  1. `I cannot support that: <reason>.` (canonical)
  2. `That claim is not supported: <reason>.`
  3. `I have no support for that claim: <reason>.`
  4. `I cannot back that claim: <reason>.`
  5. `The receipts do not support that: <reason>.`
- **CLOSE (bare / with `<Ω>`)**:
  1. `That closes the turn.` / `That closes <Ω>.` (canonical)
  2. `The turn is now closed.` / `<Ω> is now closed.`
  3. `We are done with this turn.` / `We are done with <Ω>.`
  4. `That completes the turn.` / `That completes <Ω>.`
  5. `Closing the turn now.` / `Closing <Ω> now.`
- **CLARIFY (with `<slot>` / topic check)**:
  1. `I need <slot> for <Ω>. What is it?` / `Are we still on <Ω>?` (canonical)
  2. `Before I can continue with <Ω>, I need <slot>.` / `Are we still working on <Ω>?`
  3. `Please provide <slot> for <Ω>.` / `Should we stay on <Ω>?`
  4. `For <Ω>, I still need <slot>.` / `Is the subject still <Ω>?`
  5. `<Ω> is missing <slot>. What is the value?` / `Do we remain on <Ω>?`
- **ACK**:
  1. `New subject: <Ω>.` (canonical)
  2. `Switching subject to <Ω>.`
  3. `Moving to <Ω>.`
  4. `Now on <Ω>.`
  5. `Turning to <Ω>.`

### The ledger after this addendum

| side universe | before | after |
|---|---|---|
| U-TURN (6 turn types) | COVERED 4, LACUNA 2 (REFUSE, CLOSE) | **COVERED 6, LACUNA 0** |

The charge for each of the six is written in `coverage.py` (`TURN_CHARGES`). A cell still reads `COVERED` only
because its probe round-trips through `cce.round_trip`; the charge names the rule, it does not replace the proof.

---

## 3. What this addendum does not change

- `GRAMMAR_CCE_v0_1.md` is untouched, byte for byte, and its sha256 in `FROZEN.json` still matches.
- The number words (`one` … `ten`, `half`) are unchanged. No word was added.
- No frame, template, alias, tail word, relation, refusal code, nesting limit, fractal rule, recipe shape or
  normalization rule was altered.
- `U-CATEGORY` keeps its own seven declared lacunae (general `∘` composition, `CoverOf`, `PartitionOf`, union,
  intersection, difference, `let`). They are still LACUNA, because no form was added for them.

