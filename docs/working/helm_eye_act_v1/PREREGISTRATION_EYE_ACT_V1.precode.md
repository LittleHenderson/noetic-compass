# EYE-ACT-1 — the Unity Eye ACTING inside live HELM: pre-registration (written BEFORE any code)

Status: PRE-CODE FREEZE. Nothing below is built, run or scored when this file is hashed.
Owner's word (2026-10-21, typed in the U1b session, verbatim): "want the Eye to act inside real HELM, GO!"
Earlier owner word on the Eye (2026-10-15, spec 7.38): the Eye should "act at times as well like our unconscious or
subconscious brain is in charge of our involuntary actions", and Eye and brain should "operate in concert".
Claude is not the research governor: the status words below are computed by a program from counts; this file is frozen
before code; a failed hard gate is a FAILURE (verdict INCONCLUSIVE), never "pass with caveats".

## 0. Said plainly first

Today the Eye inside the live HELM loop (`helm_*.py`) only reports. On a packaged copy of the brain, wave 4 (spec 7.77)
showed the Eye can find planted damage and make HELM hold back the damaged answer and ask instead. U1b (spec 7.40)
showed, on made-up worlds outside HELM, that an Eye allowed to *restore* verified state fixed every planted fault without
harming clean answers. EYE-ACT-1 puts that acting into the live loop, behind a new switch `HELM_EYE_ACT` that is OFF by
default, and tests whether acting (restore, then answer) beats holding (ask), without harm, and how it compares with two
plain rules that need no Eye at all.

The Eye acts only like an involuntary reflex: it may only **put back** what the user's own words already established,
re-derived by HELM's own writer. It never adds a fact, a number, a recipe or a capacity. When nothing can be re-derived,
it holds the answer and HELM asks.

## 1. What is built (behind `HELM_EYE_ACT`, default OFF)

New file `helm_eye_act.py` (standard library only, exact Fractions, 0 learned parameters) and a hook of a few lines in
`helm_end_to_end_loop.py`:
- constructor: `eye_act=None` argument; env `HELM_EYE_ACT` in {`HOLD`, `ACT`, `CONCERT`} turns it on; anything else,
  or unset, is OFF; OFF constructs no Eye object and imports nothing new.
- `process_turn`: when the Eye is on, `eye.before_turn(loop, text, tick)` runs first and may (a) sweep, (b) restore
  through the loop's own routines, (c) return a HOLD result that the loop finishes with status `CLARIFY_EYE_HOLD`;
  otherwise the turn runs exactly as today. When OFF, `process_turn` is byte-for-byte today's code path.
- Only the wide path (switch `WIDE_BRAIN`, ON by default) is watched in v1: the wide book (`loop.wide_book`) and the
  wide stock (`loop.wide_stock`). The licensed brain is untouched and not watched in v1 (disclosed limit).

### 1.1 The Eye's sources of truth (the user's own words only)
- **Book:** `wide_book.witness_log` rows (what the user said each batch was), replayed in order on a FRESH book with the
  book's own writer (`WideRecipeBook.replay`). The re-derived digest is the verified book.
- **Stock:** the loop's own trace record of recorded stock (`S2 Bias ^5`, `what = "stock_on_hand (wide)"`) taken ONLY
  from a tick whose `S6 next` record has `loop_status = STOCK_RECORDED` (the stock statement passed the CCE round trip
  and its cube read-back). The loop also emits `S2 Bias ^5` at question turns with whatever stock is held then; those
  records are never a source (checked on the laptop before this freeze: a question at tick 7 emitted one). The latest
  qualifying record is the verified stock. (The Eye re-reads it; it does not re-parse English.)
- The Eye's own log is append-only and holds digests and findings, never a copy of state. (A copy-keeping rival is R1.)

### 1.2 The Eye's one sweep (a read; changes nothing)
Compute the re-derived book digest and the verified stock; compare with the live `learned_digest()` and live
`wide_stock`. Findings: `BOOK_DIFFERS` (named recipe and cells that differ), `STOCK_DIFFERS` (named ingredients),
`SOURCE_MISSING` (a learned cell with no witness row behind it, or a held stock entry with no stock record behind it).
The live digests are taken before and after every sweep and must be equal (hard gate H7).

### 1.3 The three Eye modes (the arms A1–A3)
- `HOLD` (A1): sweep; on any finding, a whisper; the next question that uses a flagged object is held: HELM says what
  failed and asks (status `CLARIFY_EYE_HOLD`); nothing is restored. (Wave 4's behaviour, on the live loop.)
- `ACT` (A2): sweep; on `BOOK_DIFFERS` / `STOCK_DIFFERS`, an AUTONOMIC restore through the loop's routine
  `eye_restore_book(rederived)` / `eye_restore_stock(verified)`, logged in the concert ledger with trigger, measured
  value and the digest after; after a restore the state must equal the re-derived state (else the restore is undone and
  the object is held). `SOURCE_MISSING` cells are restored to what the sources support (an unlearned cell stays
  unlearned, so HELM asks for a batch: the Eye never fills a number). No veto (involuntary), bounded cost.
- `CONCERT` (A3): ACT, plus the loop asks the Eye before every question turn ("REQUEST: look at the objects this answer
  will use"); the Eye replies in the same turn after a sweep limited to those objects; the ledger keeps REQUEST / REPLY.
- Cadence (A1, A2, A3): a sweep at the first turn of a session and then after every 4 turns (`SWEEP_EVERY = 4`).
  A3 also sweeps on every request.

## 2. The exam (made-up worlds, the live loop, real English turns)

A world is one session of the live loop (`HELMEndToEndLoop(wide_brain=True)`, fresh cube store), driven only through
`process_turn` with plain English. Made-up words only (product and ingredient names built from a fixed syllable table),
so nothing comes from any real recipe.

Script per world (seeded): teaching turns, one per support ingredient (2 or 3), in the form "We made {m} batches of {p}
from {x} cups {a} and {y} cups {b}[ and {z} cups {c}], and the {r} ran out first." (exact integers, the named
ingredient at exactly m × its requirement, every other ingredient at least one cup more than it needs); a stock turn
"We have {..} cups {a} and {..} cups {b}[..]." ; probe P1 "How many {p} can we make?"; [the plant, between turns];
probe P2 (the very next turn); three neutral turns "Thanks." (checked before this freeze: status `CLARIFY_NOT_CCE`,
book digest, wide stock and store write count unchanged); probe P3. Requirements 1–4 cups per batch, batches made
1–4, stock 5–40 cups, chosen by the seed so that the plant changes the P2 / P3 answer in A0 (else the planting is
VOID, reported, excluded from denominators).

**Answer key:** the same script with no plant, run under A0 (the unbroken live HELM). An item is RIGHT if the answer's
value (exact Fraction) and limiting ingredient equal the key; ASK if HELM gives no amount (any CLARIFY / UNDETERMINED
status); WRONG if it gives an amount or a limiting ingredient that differs from the key. Order: RIGHT > ASK > WRONG.

**Faults (planted out of band between P1 and P2; no write through the loop except F3):**
- `F1 TAMPER_COEFF` — one learned requirement of the product is doubled in place in `wide_book.recipes` (the cell is
  the key's limiting ingredient); `witness_log` untouched.
- `F2 TAMPER_STOCK` — the held amount of the key's limiting ingredient in `loop.wide_stock` is halved in place.
- `F3 SLIPPED_LESSON` — a batch is admitted through the book's writer with its conflict refusal and memory check
  bypassed for that one write, doubling the limiting cell; its witness row is appended `admitted = True`, its lesson
  appended, the digest moves. (A real write that the protections should have refused; a write-time copy accepts it.)
- `F4 LOST_SOURCE` — F1, AND every witness row (and lesson) whose ran-out ingredient is that cell is deleted. Nothing
  the user said still supports the cell; the right behaviour is to ask, never to invent.
- `CLEAN` — no plant.

Sizes: 40 worlds per kind × 5 kinds = 200 worlds; items: P1, P2, P3 per world (P1 is before the plant: a harness
check, must equal the key in every arm).

## 3. Arms

| Arm | What runs | Role |
|---|---|---|
| A0 `OFF` | live HELM, switch OFF | the unbroken baseline; also produces the key on the unplanted twin |
| A1 `HOLD` | switch HOLD | wave 4's behaviour on the live loop |
| A2 `ACT` | switch ACT | the candidate: acting by cadence |
| A3 `CONCERT` | switch CONCERT | the candidate: acting plus the loop's requests |
| R1 `CHECKSUM_COPY` | switch OFF + harness rule: after every turn that changed the book or stock, keep a sha256 and a deep copy; before every question, if the live digest differs from the kept one, put the copy back; never an Eye | mechanism-free rival 1 (keeps copies) |
| R2 `REBUILD_ALWAYS` | switch OFF + harness rule: before every question, replace the book with `replay(witness_log)` and the stock with the last stock record, whether or not anything differs | mechanism-free rival 2 (no detection, no ledger) |
| C1 `RANDOM_REPAIR` | switch OFF + harness rule: at each of A2's sweep times, pick ONE object at random (book or stock; seeded), re-derive and put it back | control: repairs that are not driven by detection |
| replay | A0 and A3 run twice on 8 worlds (one per kind + 4 clean) | determinism |

## 4. Marks (all from counts)
- `RIGHT / ASK / WRONG` per arm, per fault kind, on P2 and P3 (faulted) and on P1–P3 (clean).
- `INTERVENTIONS` per arm: state changes made by the Eye or the rule (restores, rebuilds, copy-restores) on clean worlds
  and on faulted worlds; `HOLDS` per arm.
- `BYTES_HELD` per arm: bytes of state the arm keeps beside HELM's own (R1's copies; the Eye's log), reported.
- `FIX` per arm and kind: faulted worlds where P3 is RIGHT.
- `EYE_LEDGER`: sweeps, findings by code, restores, holds, requests, replies.

## 5. Hard gates (any failure → verdict INCONCLUSIVE, no other word)
- H1 `G_TESTS` — the new unit tests pass in every part; every HELM suite passes on the laptop with the switch OFF.
- H2 `G_OFF_PIN` — `test_helm_cas_address.py` passes unmodified (`PINNED_OFF_SHA256` unchanged) with the hook in place.
- H3 `G_INSTRUMENT` — every planned world counted exactly once; the generator gives byte-identical scripts for the same
  seed; VOID plantings ≤ 10% per kind; every P1 equals the key in every arm.
- H4 `G_REPLAY` — the replay runs equal the first runs (every answer, every final digest) on 8 of 8 worlds.
- H5 `G_CLEAN` — on CLEAN worlds A1, A2, A3 give answers identical to A0 on every item (C1, R1, R2 are reported, not gated).
- H6 `G_NO_NEW_KNOWLEDGE` — after every Eye restore, the book digest equals `replay(witness_log)` and the stock equals
  the last verified stock record: 0 exceptions.
- H7 `G_READS_PURE` — every Eye sweep that does not restore leaves the live book digest, stock and store write count
  unchanged: 0 exceptions.
- H8 `G_LEDGERED` — every state change made by the Eye is an AUTONOMIC ledger entry made through `eye_restore_*`: 0
  unlogged changes (checked by digests before and after every turn).
- H9 `G_CONTROLS` — C1's FIX count ≤ E + 3σ of its chance expectation (each repair picks the faulted object with
  probability 1/2 per pick; E and σ computed exactly from its pick count before P3).
- H10 `G_NO_INVENT` — on F4, A1–A3 give 0 WRONG items.

## 6. Status words (computed by the reader from counts, in this order)
1. `INCONCLUSIVE` — any hard gate fails; no other word.
2. `EYE_ACT_HARMFUL` — an eye arm (A1–A3) is worse than A0 on any faulted item (A0 RIGHT or ASK, eye arm WRONG), or A2 /
   A3 is worse than A1 on any faulted item (acting turned an honest ask into a wrong answer). Blocks the keep words.
3. `EYE_ACT_EARNED_KEEP` — RIGHT(A2) > RIGHT(A1) and WRONG(A2) ≤ WRONG(A1) over faulted items (acting beats holding).
4. `CONCERT_ACT_EARNED_KEEP` — WRONG(A3) ≤ WRONG(A2) and RIGHT(A3) > RIGHT(A2); or RIGHT and WRONG equal and
   INTERVENTIONS(A3) < INTERVENTIONS(A2).
5. Rival words, one each for R1 and R2 against the better of A2 / A3 by (WRONG ascending, then RIGHT descending):
   `EYE_ACT_BEATS_<R>` (strictly better), `<R>_BEATS_EYE_ACT` (strictly better the other way), `TIES_<R>`
   (equal WRONG and RIGHT; INTERVENTIONS and BYTES_HELD reported beside it).
6. `NO_EYE_ACT_WORD` — none of 2–4 awarded and no instrument problem.

Claim status if words are earned: `ENGINEERED-NOT-VALIDATED`, ceiling `SYNTHETIC_ONLY` (made-up words; the faults
were planted knowing what the sweep checks). The Eye's ACTING in HELM stays `NOT LICENSED` until the owner rules after
reading the result; nothing here switches it on by default.

## 7. Runs, seeds, cost
- Practice: dev seeds `dev:1` … `dev:8` (one world per kind + 3 clean), laptop, before the seal. Practice numbers are
  never scored and are reported as practice.
- Seal: the package (the new files, the hook, the generator, the reader, the tests) is zipped and hashed after practice.
- Scored: world seeds `sha256(owner_line + ":" + zip_sha256 + ":" + kind + ":" + i)`, so neither the operator nor the
  builder picks them. The owner's line is typed after the seal.
- Compute: laptop, standard library, no model, no network, 0 USD expected (practice measured ~0.6 s for a 4-turn world
  including imports). Alternative on the owner's word: one small AWS CPU host, cap 1 USD.
- Parts: at most 40 parts of at most 300 s each; one driver at a time.

## 8. Predictions (written before any code)
Builder (this session, Claude Opus 5.5):
- F1, F2: A2 and A3 RIGHT on P3 in about 40 of 40 each; A3 RIGHT on P2 about 40 of 40; A2 RIGHT on P2 only when the
  cadence sweep falls before P2 (about 1 in 4); A1 ASK on P3; R1 and R2 RIGHT on P2 and P3.
- F3: A2 and A3 RIGHT on P3 (replay refuses the slipped row); R1 WRONG on P2 and P3 (its copy holds the slipped state);
  R2 RIGHT (it rebuilds).
- F4: A1–A3 and R2 ASK; R1 RIGHT (its copy survives).
- Words: `EYE_ACT_EARNED_KEEP` about 0.85; `CONCERT_ACT_EARNED_KEEP` about 0.8; versus R1 `NEITHER` strictly — R1 wins
  F4, the Eye wins F3 — so by (WRONG first) `EYE_ACT_BEATS_CHECKSUM_COPY` about 0.7; versus R2 `TIES_REBUILD_ALWAYS`
  about 0.8 on answers, with the Eye making far fewer state changes on clean worlds (R2 rebuilds before every question).
- `EYE_ACT_HARMFUL` about 0.1; `INCONCLUSIVE` about 0.15 (an instrument slip in a first build).
- The honest reading this test exists to settle: if R2 ties the Eye on answers, a plain "rebuild before you answer" rule
  does the Eye's acting job on these faults; the Eye's remaining value is fewer state changes, the ledger, and holding.

## 9. Limits stated now
- Only the wide book and wide stock are watched; the licensed brain, the triad faces, the cube store's own records,
  `helm_memory` and memory capsules are not (each is a later step).
- One session per world; no restart across sessions.
- Faults are planted knowing what the sweep checks (as wave 4 and U3-T1): close to by-construction for detection.
- Made-up words only; nothing here is evidence about real recipes or real users.
