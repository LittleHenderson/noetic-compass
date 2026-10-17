# The language layer v2 — CCE v0.1-pq, with RB-C4's restart fallback wired into the tap

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\language_v2\`, as the merged copy of
`..\language\`. The original is untouched and still passes (`30 of 30 cases passed.`). One mechanism that
already existed in this project and was not wired in is now in: **RB-C4's RESTART_FALLBACK**, in
`restart.py`, called by `tap_all` to choose which lossless wording each station is said in. The Unity Eye
lives in `..\faculties_v2\eye\` and watches this package; nothing here imports it.

A working two-way translator between a small, strict part of English and CAS content, plus the
two things that let it travel: **TAP**, which reads a station of the cognitive circuit and says
what is there, and **INJECT**, which brings English into a station.

`parse(CCE sentence) -> CASContent`. `render(CASContent) -> CCE sentence`. Both are deterministic
programs. There are **0 learned parameters** in this folder, and no rule was fitted to any data.

The only acceptance test is the round trip: `parse(render(C, w)) == C` after normalisation, for
every content and every wording. Everything below is claimed at that standard and no higher.

## The claim ceiling

**CONTROLLED ENGLISH ONLY. NOT OPEN CONVERSATION. FORM ONLY, NO MEANING CLAIM.**

In plain words:

- This speaks a small, strict English. It is not a chat system and it is not a language model.
- **Free English is a different and much larger build.** This translator parses roughly **none**
  of free LLM-written English: that is the spec's own stated limit (`TRANSLATOR_SPEC.md` section 9,
  and `lm_t1/RESULTS.md` mark M4, where the strict grammar read 0 of 439 LLM-written recipe rows
  while a wide phrase-matching mode read 233 of 439).
- The round trip proves that **form** survives: the same record goes out as English and comes back
  identical. It proves nothing about whether the record is true, well-chosen, or well described.
  A lookup table also round-trips; what stops a lookup table here is the frozen-word check, the
  independent CAS validator, and the fact that 12–24 different sentences per content all come
  back to the same record.

## What works, concretely

- **Exact numbers, both directions (the owner's Q13 ruling).** CCE compares exact Decimals and RB
  stores exact Fractions, so a non-terminating coefficient such as `1/3` had no form and the skin
  read `SKIN_FORM_BROKEN`. The ruling admits `p/q`. Now:

  ```
  To make Ω_bread, use 1/3 of Female, cognitive; plus 2 of Rhythm, operational, analytical register;
  plus 3/7 of Ω_starter. Side product: 1/9 of Ω_steam. Helped by Ω_warmth. Slowed by Ω_draught.
  ```

  parses back to the identical record, and `1/3` is never written `0.333…`. Asking `numbers.py`
  for a decimal form of `1/3` returns the typed refusal word `LOSSY_CONVERSION_REFUSED` instead of
  a rounded number. Nothing in this folder rounds a number.
- **All ten Noetics, all four Domains, all four Registers, all seven Drives, and an unspecified
  Register.** The coverage ledger probes 10 × 4 × 5 = **200 cells** and all 200 come back
  `COVERED`; `covered_without_charge` is 0.
- **Many wordings, one content.** A content with a full tail says 12 to 24 distinct sentences
  (CANON frame, ALIAS colloquialism, either tail order, either term order, digits or `p/q`, the
  Noetic name or its verbatim definition) and every one of them parses back to the same record.
- **Breadth, not a lucky example.** 200 pseudo-random content records (random Noetic, tail,
  polarity and exact coefficient, one to three terms) produce **1,119 sentences** in the test run,
  and every one comes back to its own record. The seed is fixed, so the figure is reproducible.
- **Refusals are typed and never guessed.** `NOT_CCE`, `AMBIGUOUS`, `SLOT_TYPE`,
  `SAME_IDEA_TRIGGER`, `UNDECLARED_NAME`, `HEDGE`, `VAGUE_QUANTITY`, `NEST_TOO_DEEP`,
  `OPERATOR_DISCIPLINE`, plus the number layer's own codes. An equal-length tie is refused
  (`Ana is composed of "ten years of nursing".` is `AMBIGUOUS`: a Mind is composed of an Idea, and
  an Idea is composed of another Idea, and no declaration settles which). `"x" is bad.` is
  `NOT_CCE`; `"x" triggers "x" …` is `SAME_IDEA_TRIGGER`; `because` and `therefore` are `NOT_CCE`,
  because they never name an Above/Cause.
- **No number is invented.** A degree that was not stated stays absent (never 0, never 1); a
  recipe term cannot exist without its coefficient; a side product with no number is marked
  `implicit`, never given a silent 1.
- **TAP reads, INJECT brings back.** A station's content leaves as English and arrives at another
  station as the same content. TAP writes nothing: the world digest before a tap equals the digest
  after it, and the tap log is a separate log.
- **FORM gaps say nothing and are counted.** The CJT arrival station holds a yield number, a
  limiting reagent, a region and an outcome, and CCE v0.1 has no form for any of them. That station
  therefore produces **no sentence** and is counted as a FORM gap (named fields, not a silence).
  A station with no content at all is `NO_EVIDENCE`, which is a different thing again.
- **`UNDETERMINED` is said as exactly `I cannot tell.`** — one fixed string, never drawn, never
  varied, and it is the only thing that content can say.

## What does not work, plainly

- **Free English.** Out of scope, as above. The strict grammar parses almost nothing that a
  language model writes.
- **Meta-logic sets are a declared LACUNA** in the spec's own 7-category table (`TRANSLATOR_SPEC`
  section 8): `CoverOf`, `PartitionOf`, `∪`, `∩`, `∖`, and `let` have no sentence form here, and
  `Positive is in the Noetic set {Positive}.` is refused `NOT_CCE`.
- **Two of the eleven turn types have no form** (`REFUSE`, `CLOSE`); CCE v0.1 covers six of them
  plus ANSWER, ACK, CLARIFY and REFUSE_CLAIM.
- **General `∘` composition** is not in: only the fractal-sequence form is.
- **Reasoned cause** ("I worked out why …") has no sequence form in this build; the spec's
  `SENTENCE` production does not include one.
- **A yield, a limiting reagent, an ASOM word, a region, a drive state, an order shape** — no form.
  Each is a FORM gap, listed by name where it occurs.
- **The CAS side is checked by `cas_validator.py`, not by the CAS compiler.** The compiler is not in
  this folder. The stand-in validator is independent (it imports no English, holds its own copy of
  the canon tables) but it is a smaller judge than the compiler.
- **The round trip does not check meaning.** It checks that a record survives the trip. Whether a
  term belongs to the state it names is the compiler's and the owner's business, not this layer's.

## How to run

```
python -B test_all.py      # the round-trip suite: every case named after its claim
python -B demo.py          # the human-readable demonstration
```

Standard library only. No model, no network, no AWS, no spend. Exact arithmetic is
`fractions.Fraction`.

## Files

| File | What it is |
|---|---|
| `numbers.py` | the `p/q` number form and the exactness refusals (the Q13 ruling) |
| `content.py` | `CASContent` — the one record type the round trip must preserve, with the spec's normalisation |
| `lexicon.py` | the three frozen tiers (CANON / ALIAS / FUNCTION), the 61 frozen frames (20 CANON, 41 ALIAS), the closed word list |
| `cce_parse.py` | CCE text → `CASContent`; verb frame first, longest match, exactly one parse or a typed refusal |
| `cce_render.py` | `CASContent` → CCE text; the fixed twin by default, any of the enumerated wordings on request |
| `roundtrip.py` | the only acceptance test, the write-once receipt log, the three anti-cheat checks, the coverage ledger |
| `cas_validator.py` | the independent CAS-side validator that never sees the English |
| `tap.py` | TAP: read a station, say it, or say nothing and count a FORM gap |
| `inject.py` | INJECT: bring English into a station as a state change, never as a written value |
| `test_all.py` | 30 runnable cases, no pytest |
| `demo.py` | the demonstration the owner reads |

## One engineering note

This folder has a file named `numbers.py` because the brief names it that way. A file with that
name on `sys.path` shadows the standard library's `numbers` module, which `fractions` imports, so
every `from fractions import Fraction` would fail with
`AttributeError: module 'numbers' has no attribute 'Rational'`. `numbers.py` therefore loads the
standard library file by its real path and registers it under the name `numbers` before importing
`fractions`, and the rest of the package loads `numbers.py` under the private alias `cce_numbers`
(exported as `N` from `content.py`). Nothing in the package does `import numbers` expecting this
file.


## What this merge added: the restart fallback

`rb_c4/RESULTS.md` line 43 measured one thing and kept it: when a fit leaves real rows unexplained,
retry it from **seeded alternative starting points** and keep whichever start explains the most
(`rb_c4/fitg.py` 150-179; fired **8,828** times, an alternative start kept **7,823** times).
`RESULTS.md` line 52: "The randomness win is a FIT-START win, not a proposal win."

In this build a **content** is a row and a **wording** is a route: `cce_render.wordings(content)`
is the frozen list of lossless ways to say one content, CANON first. Start 0 says every content in
the fixed twin and makes no draw; if any content fails to read back, the fallback fires and tries
the seeded starts 1 to 8, each of which draws an alternative wording per content; it keeps the
start that explains the most contents, ties to the lower start. Every start is recorded with its
seed, the start it tried, the contents it explained and whether it was kept.

The rule the tap already keeps does not move: **a sentence is said only when its round-trip
receipt passes and the independent CAS validator agrees.** `RestartResult.accepted_forms()` is the
only reader that hands a sentence back as sayable, it demands a passing `roundtrip.Receipt` for
every candidate, and it refuses with `RESTART_RESULT_NOT_VERIFIED` otherwise.

**What it reads on this build, honestly:** on the demonstration world the fixed twin already reads
back every speakable station, so the fallback does **not** fire (`fallback_fired` is `False`, one
start used). Its value here is the retry before silence: a content whose CANON sentence fails
read-back is tried in its other wordings instead of the tap going quiet on the first failure. The
"an alternative start was kept" case is proved in `restart.py`'s own tests on a supplied host, and
in the faculties copy where a route choice genuinely changes how many rows are explained.

## Every `# UNDECIDED IN SOURCES:` marker in this build

Each is a point `rb_c4` or the RB-I design does not settle for this host, marked in the code where
it was decided, listed here, and guarded by a drift test
(`every_new_language_module_carries_its_own_undecided_sources_list`).
- # UNDECIDED IN SOURCES: which exact numbers the fallback uses, when fitg.py freezes 8 seeded starts and a 20-iteration cap -- fitg.py:52 and :171 give both numbers for rb_c4's own grammar fit and no source says whether another host must use the same two, so this build uses 8 and 20 exactly as rb_c4 froze them.
- # UNDECIDED IN SOURCES: how a start is scored when the host has no yields, when fitg.py keeps the fewest unexplained rows and breaks ties by the exact residual sum -- fitg.py:167 compares `res` only, and `res` comes from yields this build does not have, so this build counts unexplained contents and breaks ties by the lower start index alone.
- # UNDECIDED IN SOURCES: whether a wording that fails read-back may be retried within one start, when fitg.py reassigns a row only to a route that is a clear winner -- fitg.py:135-138 requires a `CLEAR` win before a row moves, so this build retries a failing content only with a wording whose support is a clear winner, which with one sentence per content never happens, and the start's own choice therefore stands.
- # UNDECIDED IN SOURCES: whether the restart fallback belongs in the language layer at all, when FACULTIES.md section 2.3 puts it in pondering and no source says the language skin needs one -- the owning instruction names this build as one of the two the mechanisms must be wired into, so this build wires it into the tap as a retry before silence, and the reading states that on today's build it never fires.

## Every `UNDECIDED IN SPEC` marker in this build

Each is a real gap in the written spec, marked in the code where it is decided, listed here, and
guarded by a drift test (`test_all.py`: *every_undecided_marker_is_listed_in_the_readme*).

- `# UNDECIDED IN SPEC: do two written forms of one exact value (0.5 and 1/2) compare equal, when TRANSLATOR_SPEC section 2 says Decimals and the Q13 ruling admits p/q?` — decided by value: `0.5 == 1/2`, because the alternative would make one number into two contents.
- `# UNDECIDED IN SPEC: does a one-element register set <A> equal the single register A?` — decided yes; both are stored as the one-letter tuple `("A",)`.
- `# UNDECIDED IN SPEC: is "nesting" a stored field of the record or a derived view of the nested slots?` — derived, so a stored copy cannot drift from the slots.
- `# UNDECIDED IN SPEC: may the unit and pattern slots of the Rhythm frame take any lowercase word, or must they come from a closed list?` — closed lists, because an open word cannot be proved to come from a frozen tier.
- `# UNDECIDED IN SPEC: does a comma segment beside an in-frame slot ("pattern cognitive") belong to the frame or to the tail?` — the longest frame is tried first; a segment is peeled only when the longer core matches no frame.
- `# UNDECIDED IN SPEC: are the REFUSE_CLAIM reason words content, when the section 2 field table does not list them?` — yes, stored in `content.reason`.
- `# UNDECIDED IN SPEC: may a nested frame inside "that [...]" carry its own evidence and turn words?` — no: one plain frame per slot.
- `# UNDECIDED IN SPEC: section 5 cross-checks the CAS side against the CAS compiler; may an independently written validator stand in for it?` — yes, `cas_validator.py`; it is a smaller judge than the compiler.
- `# UNDECIDED IN SPEC: does TAP draw a wording, when the design says no draw and the spec requires every said wording to round-trip?` — no draw; the tap says the fixed twin.
- `# UNDECIDED IN SPEC: when one station field has no CCE form, does the whole station stay silent or is the rest said?` — the whole station stays silent and the FORM gap is counted.
- `# UNDECIDED IN SPEC: which station a plain frame claim starts, since the design file only PROPOSES it?` — S5 as a witness; the full routing table is in `inject.route()`.
- `# UNDECIDED IN SPEC: is the turn index that tags USER_SAID evidence part of the content record or provenance outside it?` — outside: the record holds the word, the `InjectRecord` holds the index.

## Where the design came from

`TRANSLATOR_SPEC.md` (the spec: grammar, tiers, the round-trip rule, the typed codes, the gate
table, the 7-category check, the coverage ledger), `MAP.md` sections A, C and D (the ten frames,
the NO-MAP list, the trap table), `OPEN_QUESTIONS.md` Q9 and Q16 defaults (nesting depth 2, draw
cap 8), the frozen grammar lineage `GRAMMAR_CCE_v0_1.md` plus its `v0.1b` and `v0.1c-R` addenda,
`STATIONS.md` S0–S6, `TAP_AND_INJECT.md`, and `CAS_MAPPING.md`. The owner's Q13 ruling on the
`p/q` form governs the number layer, and it is implemented first because it unblocks the rest.
