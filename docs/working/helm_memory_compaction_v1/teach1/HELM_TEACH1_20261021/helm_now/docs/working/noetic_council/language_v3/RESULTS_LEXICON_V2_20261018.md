# Results: alias-wide lexicon v2 (fix E, dictionary half) — 2026-10-18 PDT, laptop, 0 USD

Owner order: `C:/Users/wakil/Documents/Codex/2026-10-18/OWNER_APPROVALS_20261018.md`, fix E — "expand the
deterministic dictionary on the 99 dev rows". Stdlib Python, one process, no torch, no cloud.

## In one paragraph

The word list that reads free SDG English was widened with 10 new Noetic phrases and 1 new domain word, each
taken from the canon colloquialisms, the definition verbs, or words seen in the 99 DEV rows. On the 99 DEV rows,
v1 read 0; v2 reads 41 (39 correct, 2 wrong). On the sealed 98, scored once at the end, v1 read 0; v2 reads 34
(32 correct, 2 wrong). On the 439 headline rows MATCH goes 233 → 304 and MISMATCH 9 → 13. Most of what is
still unreadable is NOT a missing word: the English never names a domain, or names two Noetics in one ingredient.

## Order of work (so the sealed result can be trusted)

| Step | Commit | What |
|---|---|---|
| 1 | `0b7cde89` (+ `cf3c7512` JSON-escape fix, content unchanged) | `FROZEN_LEXICON_V2.json` pushed: admission rule, DEV baseline 0/99, predicted lift. Written before any v2 word. |
| 2 | (working tree) | v2 words chosen from the 99 DEV rows only; `behavior` refused by the frozen domain test (below). |
| 3 | (working tree) | first 481 / 439 run. No word changed after it. |
| 4 | `dd60f490` | `lexicon_v2.py` (sha256 `b1eee572e67445552a80a90630120855218480292574c71bbbffa0f471131113`), tests, `tabulate_v2.py` committed and pushed. |
| 5 | (receipt in this PR) | the ONE sealed-98 pass, counts only. |

Honest note: the 439 headline view contains the sealed 98, so step 3 already fixed the sealed counts by
subtraction (439 view minus DEV). That is why no word was allowed to change after step 3. The sealed file was
never opened to pick or test a word.

## Numbers (all computed by `tabulate_v2.py`; JSON `docs/working/SDG_TABULATION_V1_V2_20261018.json`)

### 481 accepted rows

| Reader | MATCH | UNPARSEABLE | MISMATCH |
|---|---:|---:|---:|
| bridge v2 | 118 | 321 | 42 |
| lexicon v1 | 265 | 199 | 17 |
| lexicon v2 | 337 | 124 | 20 |

v1 → v2 row moves: MATCH→MATCH 265, UNPARSEABLE→MATCH 72, UNPARSEABLE→UNPARSEABLE 123,
UNPARSEABLE→MISMATCH 4, MISMATCH→UNPARSEABLE 1, MISMATCH→MISMATCH 16. **No v1 MATCH was lost.**
Second number (register and drive agree, MATCH rows): v1 196, v2 246.

### 439 headline rows

| Reader | MATCH | UNPARSEABLE | MISMATCH |
|---|---:|---:|---:|
| bridge v2 | 118 | 321 | 0 |
| lexicon v1 | 233 | 197 | 9 |
| lexicon v2 | 304 | 122 | 13 |

v1 → v2: MATCH→MATCH 233, UNPARSEABLE→MATCH 71, UNPARSEABLE→UNPARSEABLE 122, UNPARSEABLE→MISMATCH 4,
MISMATCH→MISMATCH 9. Second number: v1 174, v2 223. (The frozen M4 mark in `FROZEN.json` is MATCH ≥ 176 of
439, PROPOSED; v1 already passed it.)

Failure reasons in the 439 (one row can carry several): v1 NO_STATE 148, NO_DOMAIN 56, AMBIGUOUS_STATE 27,
AMBIGUOUS_DOMAIN 16 → v2 NO_STATE 21, NO_DOMAIN 69, AMBIGUOUS_STATE 30, AMBIGUOUS_DOMAIN 19.
**Reading:** the audit note said the 148 NO_STATE and 56 NO_DOMAIN were vocabulary gaps. For NO_STATE that was
true (148 → 21). For NO_DOMAIN it was not: rows that now get past the state step stop at the domain step
because the English never names a domain ("a thought about wisdom and insight"). No admissible word fixes that.

### DEV 99 (before / after)

| Reader | MATCH | UNPARSEABLE | MISMATCH |
|---|---:|---:|---:|
| lexicon v1 | 0 | 99 | 0 |
| lexicon v2 | 39 | 58 | 2 |

Predicted before the code (FROZEN_LEXICON_V2.json): parsed 30–50, MATCH 22–40, new MISMATCH 3–12.
Actual: parsed 41 (inside), MATCH 39 (inside), new MISMATCH 2 (below the range).

### Sealed 98 — scored once, counts only

Receipt: `SEALED_98_SCORE_RECEIPT_LEXICON_V2.json` (sha256
`2ac6fe71eabbfc23be498a3a2138d543c51145dd8f130f0a06157fa6a81a2295`).

| Reader | MATCH | UNPARSEABLE | MISMATCH |
|---|---:|---:|---:|
| lexicon v1 | 0 | 98 | 0 |
| lexicon v2 | 32 | 64 | 2 |

sha256 before = after = `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe` (unchanged: true).
DEV 39/99 vs sealed 32/98: the words carry over to unseen rows at a slightly lower rate, as expected.

### The old typed-in literals, now computed

`tabulate_439_sdg_baseline.py` lines 170-173 and 209-210 typed 42 / 17 / 25 / 59.52 % and 118 / 321 / 42 and
265 / 199 / 17. All seven now come out of the code with the same values: bridge v2 481 MISMATCH 42; v1 481
MISMATCH 17; reduction 25; 59.52 %; bridge v2 481 = 118 / 321 / 42; v1 481 = 265 / 199 / 17. One more:
bridge v2's 42 MISMATCH rows are exactly the 42 excluded rows (439 view: 0). The old script was not edited and
not re-run (it rewrites the split files). `tabulate_v2.py` writes nothing into `cas-synthetic/`; it re-derives
the 98/99 split in memory and both re-derived hashes match the files (the old script wrote CRLF line ends).

## What v2 adds (every entry carries its source tag; full text in `lexicon_v2.py`)

| Tier | Target | Words | Source | Colloquialism test |
|---|---|---|---|---|
| frame | ^2 | draws / drawn / drawing (you) to / toward | a+b+d | "Drawn to it" / "attracted toward" |
| frame | ^3 | pushed away, pushed-away | b+d | "repelled by"; visceral, not analytical |
| frame | ^4 | resonant | b+d | "Resonated" / "resonates with" |
| frame | ^7 | practice-makes-perfect, practice making perfect | a+d | "Practice makes perfect" |
| noun | ^0 | thought(s) | d | "It's all in your head"; v1 already had "a thought" |
| noun | ^1 | attention | a+d | "Paying attention" |
| noun | ^7 | practice / practiced / practicing / practices | a+d | "Practice makes perfect" |
| noun | ^7 | repetition(s) | a+d | "You are what you repeatedly do" |
| noun | ^7 | groove | a+d | "Getting into a groove" |
| noun | ^9 | realization(s) | d | "It just clicked"; a landing, not a trigger |
| domain | C | mental | d | plain gloss of "cognitive"; 0 DEV gold conflicts in 5 segments |

Refused, with the reason kept in `lexicon_v2.REFUSED`: `behavior/behavioral` → O (2 DEV segments whose gold is P:
the writer wrote "operational behavior" for a P cell; the frozen rule refuses on one conflict), `judgment` → E
(9 conflicts, e.g. "a cognitive judgment" gold ^6^C), `thinking` → C (33 conflicts; "foundational thinking" is P),
`realm` / `frame` (not a domain gloss), `thinking` → ^1, bare `memory` → ^8 ("muscle memory" is ^7), and a mask
for "shaped by a need for" (it would drop real ^5 rows).

Clarifications names the domains only as Principled / Cognitive / Evaluative / Operational, so source (c) added
nothing beyond v1.

## Tests (stdlib, laptop)

| Suite | Result |
|---|---|
| `test_lm_t1` (base) | Ran 26, OK |
| `test_lm_t1b` (base) | Ran 11, OK |
| `test_lm_t1c` (base) | Ran 5, OK |
| `test_lm_t1v3` (language_v3) | Ran 26, OK |
| `test_lexicon_v2` (new) | Ran 19, OK |
| `docs/working/scribe_l4_eval/test_score_scribe_l4_adapter` (new) | Ran 6, OK |

`test_lexicon_v2` holds: v1 JSON hash unchanged and v1 tables not mutated; every addition has a legal source tag
and names its canon match; **^3 vs ^6** — audit / scrutinize / find flaws / critique / analyze never read as ^3,
decomposition reads ^6, visceral aversion reads ^3; **^8 vs ^6/^9** — deduce / infer / causal analysis /
reasoning never read as ^8, "a realization" reads ^9, triggers read ^8; verb frame beats a bare noun; two bare
nouns stay AMBIGUOUS; "pulled by a need for" is not ^2; DEV lock (v1 0/99, v2 39/58/2).

Commands (from `docs/working/noetic_council/language_v3`, PYTHONPATH as in `PROVENANCE.md`):
`C:\Python314\python.exe -X utf8 -B run_suites.py` and `C:\Python314\python.exe -X utf8 -B -m unittest -v test_lexicon_v2`.
Tabulation (repo root): `C:\Python314\python.exe -X utf8 -B tabulate_v2.py` (3.1 s).

## Claim status

- v2 reader: `ENGINEERED-NOT-VALIDATED` (FORM check, not a meaning judge). Measured on rows never used to pick a
  word: sealed 98 → 32 MATCH, 2 MISMATCH, 64 UNPARSEABLE (`REAL` laptop measurement, SYNTHETIC-SOURCE English:
  the SDG sentences were written by an LLM).
- `NOT LICENSED`: reading open English in general; any meaning claim; "the NO_DOMAIN rows are vocabulary gaps".
- New MISMATCH rows are kept and counted (481: 17 → 20; 439: 9 → 13). Several come from SDG English that contradicts
  its own gold (e.g. DEV "drawn to you in cognitive thinking" with gold ^2^O).

## Small English model (Scribe L4) scoring — prepared, `NOT_RUN`

`docs/working/scribe_l4_eval/SCORE_SCRIBE_L4_PLAN.md` + `score_scribe_l4.py`. Needs torch on an AWS CPU box
(t3.medium, about 0.01 USD, seconds of scoring); waits for the owner's word. Read from the commit: the model can
only say one unweighted clause, so exact match against the recipe gold is 0 of 98 by construction — written down
before any run.
