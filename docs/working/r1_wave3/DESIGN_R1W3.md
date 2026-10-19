# HELM-R1 wave 3 (R1W3) — frozen design, written BEFORE any wave-3 code

Written 2026-10-19 (Pacific) by the wave-3 builder session (Claude) on the owner's order "wave 3 plan".
This file is the design freeze. Its sha256 is recorded in `PREREGISTRATION_R1W3.md` and in `FROZEN_R1W3.json`.
Any change after this point is written into the preregistration's amendment log with the reason, before the seal.
NOT LAUNCHED. No spend. No ledger hold.

## 0. Plain summary

Wave 2 switched off one part at a time and gave each part one word. Wave 3 does the same again on a new sealed
exam, with four NEW parts on switches (cube store, atlas, Unity Eye, cascade), and adds the first COOPERATION
test: two parts switched off together. If losing both costs more than losing each one alone, the pair works
together ("whole > sum"). Two new exams make the new parts actually do something: a FACES exam (plain sentences
like "we have 12 cups of flour but I barely know how to use it") and a CASCADE exam (recipe chains 3 to 5 levels
deep, where the new stopping rule can stop early).

## 1. Owner rulings this design obeys (OWNER_APPROVALS_20261018.md, every block read)

- "recipe brain is canonical"; "no more GPU for now"; "plain-rule valve"; "Desire is Purpose"; one scale
  Rising 1/4, Peak 1, Waning 1/2, Absent 0 for all three faces; "min"; "earliest"; Wisdom rule C; "use my GitHub
  email".
- Decoupling-stop rule ADOPTED as HELM's primary stopping rule; the fixed depth cap stays only as a FUSE; a fuse
  firing = Structural Deadlock, a diagnostic.
- "Built together" stays (ability 7). Growth trigger = CURIOSITY (F2). Growth itself stays PARKED: wave 3 has no
  growth switch and grows nothing.
- Gravity pull / drive loop = RB-I's design, retested as RB-I1c. FACULTIES / DRIVE_LOOP gets a wave-3 switch only
  if RB-I1c's frozen reader earns a word; otherwise it is listed NOT_IN_WAVE with the reason (decided at the
  freeze from RB-I1c's own reading file, never from prose).
- Claude is not the research governor: every word below is computed by the frozen reader; a failed hard gate is a
  FAILURE.

## 2. Method

1. FULL = every switch on.
2. One part off at a time (wave 2's method), for every switch.
3. One SWAP arm: CASCADE_FIXED_CAP (the old fixed-cap rule in place of the decoupling stop).
4. PAIRS OFF: two earned parts switched off together, on an exam where both are exercised.
   Joint loss is compared with the sum of the two single losses, in exact fractions.

## 3. Switches (13 named, 12 single-off arms + 1 swap)

Carried from wave 2 (switched off exactly as wave 2 did): RECIPE_MATH, RPM_GATE, LACUNA_CADENCE,
RESTART_FALLBACK, CCE_SKIN, TRIAD, ENGLISH_IN, VOICE.

New in wave 3:

| Switch | ON (FULL) | OFF |
|---|---|---|
| CUBE_STORE | the live loop writes to the cube store after the gate and the read-back; reads use its three operations (LIST_PARTS, FIND_SHARED_PART, REACHED_VIA); in the cascade, every COVERED cell is a cube with a receipt digest | a plain Python list of written lines (name, amount or "absent", tick) in its place: last line wins, no admission rules, no receipts, no three operations |
| ATLAS | each cascade thought gets an atlas entry at S0 (a real `AtlasSnapshot` digest from the CAS-RPU atlas model, commit eb998556) and every descent is a suspended caller with an exact `ReturnAddress`; a returning child must pass `ReturnStack.resume` | no atlas entry, no return stack: a child's value is delivered into a mailbox keyed by node name; the last message for that name wins |
| EYE | U1b's two acting tiers (one-way whispers + the autonomic / involuntary check sweep) run while HELM is IDLE; OFF while AWAKE (U2's default) | no eye |
| CASCADE | decoupling-stop PRIMARY + fuse (see 4.3) | no cascade: the thought answers from the root's stored inputs (flat, LM-T6's A7) |
| CASCADE_FIXED_CAP (swap, not an off) | — | full descent, stopped only by the fixed cap 5 (LM-T6's frozen `CAP = 5`, canon's number) |

AWAKE vs IDLE (stated now): AWAKE = HELM is handling a user turn (every English-16 and Faces-16 turn and setup
step). IDLE = a headless thought with no user turn (every Cascade-exam chain is an idle thought). The eye acts only
when IDLE, in every arm that has it. So the eye is NOT_EXERCISED on English-16 and Faces-16 by definition.

FACULTIES / DRIVE_LOOP: conditional on RB-I1c (section 1).

## 4. Exams

| Exam | What | Exposure | Exercises |
|---|---|---|---|
| E1 Gate B | c21's sealed worlds | exposed | RECIPE_MATH, RPM_GATE, LACUNA_CADENCE |
| E2 Task B | RB2c's worlds (c25's 20 draws) | exposed | RECIPE_MATH, RPM_GATE, LACUNA_CADENCE |
| X2-GB, X2-TB | fresh Gate B worlds / Task B draws | fresh | same as E1 / E2 |
| X2-D34 | two fresh depth families (laptop, wave 1's depth code) | fresh | RPM_GATE, RESTART_FALLBACK |
| X2-CCE | 1,280 rendered inputs + 64 planted items | fresh | CCE_SKIN |
| X2-E16 | English-16, NEW 16 turns (families G1-G7 below) | fresh | ENGLISH_IN, VOICE, TRIAD (at Peak: identity), CUBE_STORE |
| X2-F16 | Faces-16, NEW (families H1-H7 below) | fresh | TRIAD, ENGLISH_IN, VOICE |
| X2-CASC | Cascade exam, 64 chains, depth 3-6 (families C1-C8 below) | fresh | CASCADE (+ swap), EYE, ATLAS, CUBE_STORE, TRIAD |

Every X2 part is written and sealed by a separate custodian session from the sha256 of the owner's R1W3 sign line.
The builder sees hashes only.

### 4.1 English-16 v3 (X2-E16), 16 items, families and counts

G1 STOCK_THEN_ASK 3 (ANSWER); G2 ABSENT_THEN_ASK 2 (ASK); G3 QUESTION_FORMS 2 (ANSWER); G4 WITNESS_IN_ENGLISH 2
(LEARN); G5 MUST_ASK 2 (ASK); G6 STORE_READ 3 (READ); G7 NEXT_SESSION 2 (ANSWER, asked in a second loop that shares
the first loop's store and brain). Scoring: wave 2's 3-valued rule for ANSWER / ASK / LEARN, verbatim. READ (new):
RIGHT = READ_COMPLETED and the reply names every key item with its amount and no other ingredient; WRONG =
READ_COMPLETED otherwise; anything else UNDETERMINED. UNDETERMINED is never WRONG.

Disclosure: before writing the G6 phrasing pool the builder saw three phrasings run on the live loop:
"What do we have in stock?" and "what've we got on hand then" gave LIST_PARTS with the right items; "What do we
have on hand?" gave FIND_SHARED_PART with a wrong reply. All three are kept in the pool.

### 4.2 Faces-16 (X2-F16), 16 items

Each item: witnessed batches teach the recipe; then one plain sentence states stock and a face; then a question.
Only the question is scored (3-valued). Keys are computed by the owner's rules: x_eff = min(Purpose, Wisdom,
Power) x stock; yield = min over ingredients of x_eff / requirement; recipe Purpose Absent -> ASK; an ingredient
face at Absent -> ASK.

H1 WISDOM_STATED 3 (ANSWER; e.g. "we have 12 cups of flour but I barely know how to use it" -> Wisdom Rising);
H2 POWER_STATED 3 (ANSWER; "the yeast is getting old" -> Power Waning); H3 RECIPE_PURPOSE_ABSENT 2 (ASK);
H4 INGREDIENT_PURPOSE_ABSENT 2 (ASK); H5 PEAK_STATED 2 (ANSWER, a Peak face: the answer must not move);
H6 TWO_FACES 2 (ANSWER, two faces on two ingredients); H7 NOT_A_FACE 2 (ANSWER, a sentence about an ingredient that
states no face: the reader must not invent one). In H1, H2 and H6 the stated face changes the answer (the decoy rule:
the face-starved ingredient has the most raw stock), so an arm that ignores faces answers WRONG.

The faces reader (`helm_faces_in.py`) is new, deterministic and lexicon-only (`helm_faces_lexicon.json`, every
row with its source). A sentence with a face cue word that matches no lexicon row is NOT guessed: the turn asks
(CLARIFY_FACE_UNREAD) and writes nothing. The generator's phrasing pool is written apart from the lexicon and
includes paraphrases the lexicon does not hold (stated count in the generator); a missed face is a measured miss.
The faces reader belongs to the ENGLISH_IN switch (off = no plain-English reading at all).

### 4.3 Cascade exam (X2-CASC), 64 chains

World: recipe trees with exact Fractions in HELM's own recipe algebra (v7.6: Theta, Y_T = min x_i / a_i, the
Limiting Reagent). Every inner node has a recipe (coefficients) and a STORED delivered value (what the brain
remembers it made). Every leaf is a GROUND stock cell with a stored record. A descent re-derives a node from its
children and compares with the stored value (the level receipt: eta stored vs epsilon re-derived). A mismatch
marks the level DIRTY; the re-derived value is used (repair); a stored ground record that fails its receipt is
UNKNOWN and the thought answers UNDETERMINED naming that cell. The licensed brain's learned book is NOT used here
(its four fixed supports cannot hold trees 3-6 deep); the cascade exam tests the STOPPING RULE and how the eye,
atlas, store and triad work with it.

THE DECOUPLING-STOP RULE (primary, FULL). At a parent, a child prerequisite is NOT descended (stop reason
DECOUPLED) only if ALL hold:
 (a) ABSORBED: its ratio v_c / a_c >= (1 + m) * Y_T, m = 1/20 (LM-T6's frozen margin) — it is Excess Capacity;
 (b) CONSOLIDATED: its cell is COVERED with a passing receipt in the store (a cube whose receipt digest matches);
 (c) every face of every ground cell under it is at Peak (when TRIAD is on; vacuous when off).
Every other child is descended: a BINDING child (the Limiting Reagent or within the margin) is always descended
(coupled = passes a perturbation one for one). Other stop reasons: GROUND (a raw leaf), BLOCK_UNRESOLVED (absent,
no producer), FUSE (a cycle, or depth beyond the fuse). This is stricter than LM-T6's A8, which stopped at a
CONSOLIDATED child even when it was binding and so missed 531 of 800 deep faults (DECOUPLING_STOPPED_EARLY).

FUSE vs CAP — where each number applies (reconciled):
- The owner's HORIZON = 12 (dwp_engine_v2/depth.py:103, spec 7.55) is the FUSE of the live rule in FULL and
  every one-off arm: a descent needing depth > 12 fires the fuse = Structural Deadlock (diagnostic). A cycle
  (a node's signature already on the descent stack) fires the fuse at once.
- Canon's 5 (Chapter_27:59, Chapter_05:87, FULL_MANUSCRIPT_v2:6412; LM-T6 `CAP = 5`) is used only as the cap of
  the CASCADE_FIXED_CAP comparison arm (the old primary rule).
- DESIRE_BOUND 12 is not touched (no Desire loop runs here).

Families: C1 CLEAN 16 (no plant, depth 3-5); C2 PLANT_BIND 8 (a deep stored value on the binding path is half of
what its recipe makes, and the wrong value has propagated up); C3 PLANT_ABSORBED 8 (a small drift, at most m of
what the parent needs, inside an absorbed, consolidated subtree: the true answer is unchanged); C4
STALE_CONSOLIDATION 8 (a binding ground record corrupted UPWARD so it looks absorbed; its receipt no longer
matches; the stored values above it carry the inflated value and the consolidation flags are stale); C5
RETURN_ATTACK 8 (a planted return message arrives for a descended node after the true one: DECOY, STALE,
DUPLICATE, PROFILE_ONLY, 2 each); C6 FACE_SHOCK 8 (a ground cell with plenty of raw stock but a Rising or Waning
face: with faces it is binding); C7 DEADLOCK 4 (a cycle: the right outcome is the fuse firing, key UNDETERMINED);
C8 DEEP6 4 (a solvable chain 6 deep: the fixed cap 5 cannot reach it; the fuse at 12 can).

Score per chain: RIGHT / WRONG / UNDETERMINED against the key. GOOD = RIGHT, or UNDETERMINED where the key allows
it (C4: storage cannot give the true amount back; C7: the fuse is the right outcome). Steps = descents (child
levels opened). Every stop and every descent records its reason.

### 4.4 X2 seed band rule (written here so no amendment is needed)

Input: H3 = sha256 of the exact UTF-8 bytes of the owner's R1W3 sign line (no trailing newline). Cuts as X0 and
X1: k1 = int(H3[0:16],16), k2 = [16:32], k3 = [32:48], k4 = [48:64].

| Part | Band | Slot | k |
|---|---|---|---|
| X2-GB | X0's Gate B band + 4,000,000 (world seeds 1,004,000,001 to 1,104,000,000; slot 100,000; 1,000 slots) | X0 layout | k1 mod 1,000 |
| X2-TB | X0's draw band + 20 draws (d from 5,970; 60-draw windows; 33 slots) | X0 layout | k2 mod 33 |
| X2-D34 | X0's depth band + 4,000,000 (row bases 1,654,000,000 to 1,743,999,999; slot 2,000,000; 45 slots) | X0 layout | k3 mod 45 |
| X2-CCE language | 1,806,000,001 to 1,807,000,000 | 1 | k4 mod 1,000,000 |
| X2-E16 | 1,808,000,001 to 1,809,000,000 | 1 | k4 mod 1,000,000 |
| X2-F16 | 1,810,000,001 to 1,811,000,000 | 1 | k1 mod 1,000,000 |
| X2-CASC | 1,812,000,001 to 1,813,000,000 | 1 | k2 mod 1,000,000 |

Used table = X0's table + X0's own fresh ranges + X1's nine fresh ranges (SEED_DERIVATION_X1.json) + X1's Task B
window 7,760-7,819 as used draw indices. Gap rule unchanged: every X2 range widened by 1,000,000 on each side must
not meet any used range or any other X2 range; every number below 2^31 - 1. Step rule: s <- (s + 1) mod N inside
the same band, at most N steps, every step recorded; a band with no free slot = STOP (no other band is tried,
nothing is generated). The five 1,000,000-wide bands start at 1,806,000,001, which is more than 1,000,000 above
X1's highest language-type seed (1,804,932,603), and are 1,000,000 apart from each other, so their first slot is
free by construction. Text rule: every E16 / F16 turn, normalised, must differ from every string constant of the
packaged English tests, the live trace, the voice, the faces lexicon file, every X1 English-16 turn and the
builder's fixtures; step rule = next slot.

## 5. Pairs (the cooperation test)

A pair is planned only where both parts are exercised on the same exam and switching both off is defined.
16 pairs, 18 pair runs:

- Gate B (E1 and X2-GB): RPM_GATE x LACUNA_CADENCE (2 runs: gate-off brain with round-robin cadence, registered
  in-process like wave 1's gate-off arm).
- English-16: ENGLISH_IN x VOICE, ENGLISH_IN x CUBE_STORE, VOICE x CUBE_STORE (3 runs).
- Faces-16: ENGLISH_IN x TRIAD, ENGLISH_IN x VOICE, TRIAD x VOICE (3 runs; ENGLISH_IN x VOICE is the same pair as
  on English-16, read on both exams).
- Cascade: every pair of CASCADE, EYE, ATLAS, CUBE_STORE, TRIAD (10 runs).

NOT_IN_WAVE (reason stated): RECIPE_MATH x anything (with recipe math off there is no recipe yield for the gate
or the cadence to act on: the pair is not defined); Task B pairs and depth pairs (wave 1's Task B gate-off and the
depth arms are marked copies of sealed wave-1 code; a combined arm needs a new copy of sealed code, a later build);
CCE_SKIN pairs (the skin is identical by construction, H5).

Pair metric per exam (a count with a fixed denominator): Gate B = panel-1 plain right + new right (of 32);
English-16 and Faces-16 = items RIGHT with a PLAIN reply (of 16); Cascade = GOOD chains (of 64).
Pair margin = 1/8 of the denominator (4, 2, 2, 8; wave 1's 4 of 32 as a ratio). PROPOSED.

Losses (exact): L(a) = M(FULL) - M(-a); L(ab) = M(FULL) - M(-a-b); expected E = L(a) + L(b); room R = M(FULL).
Pair word per exam: CEILING_NOT_READABLE if E > R - margin (no room for "more than the sum" to show);
else SYNERGY if L(ab) >= E + margin; INTERFERENCE if L(ab) <= E - margin; else ADDITIVE.
Across exams: INTERFERENCE if any; else SYNERGY if any; else ADDITIVE if any; else CEILING_NOT_READABLE.
A pair word is READ only when both parts' wave-3 single words are EARNED_KEEP (the owner's "earned parts");
otherwise the numbers are reported and the word is PAIR_NOT_READ.

## 6. Rows, gates, words

- Instrument rows I1-I9 carried from wave 2 with X2 in X1's place and the R1W3 approval; I10 NEW (PROPOSED): the
  X2 seal record shows every seed inside its band, the overlap check PASS against X0 + X1, and the seed source is
  the owner's R1W3 line hash.
- Hard gates H1-H8 carried (E16 parts read on the new English-16; H8 = the triad at Peak and the voice change no
  English-16 answer, and the voice changes no Faces-16 answer). NEW (PROPOSED): H9 cascade clean answers — on C1
  every arm answers the key; H10 cascade no invention — every ground value read is a stored record; H11 cascade
  and Faces-16 replay — FULL twice, identical; H12 the eye never writes knowledge — stock and ledger values are
  unchanged by every eye action (it may only withdraw a consolidation flag and whisper); H13 atlas — every
  accepted return in an ATLAS-on arm passed `ReturnStack.resume`.
- Per-switch word as wave 2: HARMFUL (any LOSS, checked first) / EARNED_KEEP (a WIN, no LOSS) / NEUTRAL / NOT_EXERCISED
  / INCOMPLETE (never a pass). New per-exam comparisons (PROPOSED): on English-16 and Faces-16, wave 2's
  ENGLISH_IN rule shape (RIGHT margin 2 of 16 and WRONG not more) for ENGLISH_IN, TRIAD and CUBE_STORE, and wave 2's
  VOICE rule (PLAIN margin 2, FACT_KEPT not fewer) for VOICE; on the Cascade exam, GOOD margin 8 of 64 with WRONG
  not more (LOSS if the off arm has 8 more GOOD or FULL has 8 more WRONG).
- DECOUPLING word (FULL against CASCADE_FIXED_CAP; PROPOSED marks): CASC-1 the fuse never fires on a solvable chain
  in FULL (C1-C6, C8); CASC-2 FULL finds every planted fault that matters on C2 (LM-T6's frozen A8 rule, carried);
  CASC-3 on the clean and absorbed chains (C1 + C3, 24 chains) FULL is RIGHT with strictly fewer descents than
  FIXED_CAP on at least 12 of 24 (half) and never more on any chain. Word: FUSE_MISFIRE if CASC-1 fails;
  DECOUPLING_STOPPED_EARLY if CASC-2 fails or a FULL stop turned a chain WRONG that FIXED_CAP got RIGHT;
  DECOUPLING_NO_SAVING if CASC-3 fails; else DECOUPLING_EARNED.
- Marks for FULL (reported, a miss is a finding): wave 2's marks on E1, E2, X2; English-16 RIGHT >= 10 and WRONG = 0;
  Faces-16 RIGHT >= 10 and WRONG = 0 (PROPOSED); CASC-1/2/3.
- Verdict PASS / FAILURE / INSTRUMENT_ERROR as wave 2. Claim ceiling SYNTHETIC_ONLY.

## 7. What wave 3 may and may not license

May (only with PASS): one word per part (one part off at a time, everything else equal), the DECOUPLING word, and
one cooperation word per earned pair, on synthetic worlds only.

Never: anything outside synthetic worlds; that the voice sounds natural to people; that real reagents carry a
triad; that the faces reader understands English beyond its lexicon; that the cascade worlds are the licensed
brain's learned book; growth (parked); statistical superiority (one run); any claim about T beyond its frozen c21 /
c27 numbers; cooperation for any pair not run or not read.

## Amendment D1 (written 2026-10-19 after the first freeze `27eab7e8...`, before any exam code; reason: two owner rulings arrived)

Source: `OWNER_APPROVALS_20261018.md`, block "Rulings (2026-10-19 early, verbatim)" (file sha256 at reading
`40e944f576ca148d821163632a7b3dd4d9a2dbb96193c8b8eff8bd4f4050fffc`). Owner's words, verbatim:
"Unpark growth; and I think we the drive loop was HELM'S point of attention within a geodesic simplex of the 7
foundations which are only categories of correlated subject matters whether unresolved cascades of DWP, And or ASOM
of a misaligned BIAS the 7 foundation were to be randomly mixed matched and pair amongst the 7 cas faculties"

### D1.1 DRIVE_LOOP becomes a wave-3 switch (RB-I2), whatever RB-I1c's word

Check against RB-I1's design (`Documents\Codex\2026-10-15\helm_rb_i_faculties_design_v1\DRIVE_LOOP.md`):
(a) filing of unresolved items under each Foundation: ABSENT — RB-I's pull is p_k = (1 - s_k)^2 from a satisfaction
number s_k that decays each tick and rises only by a measured gain; nothing is filed under a Foundation.
(b) random Foundation x faculty pairing: ABSENT — RB-I's table gives each drive ONE fixed faculty (F2 curiosity,
F7 FIT/pondering, F5 imagination, F6 verify, F4 asking, F1 integration, F3 consolidate).
Both are built in wave 3 as the DRIVE_LOOP switch. RB-I1c's reading is still cited when it reports; it no longer
decides whether the switch exists.

DRIVE_LOOP ON (FULL; the owner's design):
- Attention = a point a on the open 7-simplex over F1..F7 (Correction 4: every part > 0, sum 1), starting at the
  barycenter.
- Each unresolved item is FILED under the Foundation whose category of subject matter it belongs to. Item kinds in
  this exam (all real wave-3 objects): DWP_CASCADE (an unanswered cascade chain), ASOM_MISALIGNED_BIAS (a stale
  consolidation flag whose receipt no longer matches), LACUNA (a ground cell with no record: needs a question),
  NO_EVIDENCE (a never-probed cell: needs a look). The generator files each item by its subject matter; the filing
  correlates with the kind but is not a fixed map (stated in the generator).
- Pull: q_k = (n_k + 1/64) / sum_j (n_j + 1/64), n_k = unresolved items filed under F_k (open simplex). The
  attention moves one Fisher-Rao geodesic step toward q (slerp on the sphere, tau = 1/4, RB-I §3.1 verbatim); the
  Foundation whose coordinate rose most gets the tick (ties by order F1..F7).
- Pairing: the 7 Foundations are paired with the 7 CAS faculties (curiosity, pondering, imagination, verify,
  asking, integration, consolidate) by a SEEDED random permutation. The paired faculty tries the oldest item filed
  under the chosen Foundation. Restart-fallback discipline: only when the paired faculty cannot act on that item
  (NO_PROGRESS) is the pairing for that Foundation re-drawn (seeded swap, at most 6 re-draws per item), exactly like
  the restart fallback that fires only when the exact start leaves rows unexplained.
- Idle only: the pull is CUT while HELM is in conversation. Each session has awake windows (a user turn); during
  them the drive loop takes no tick (hard gate H14).
DRIVE_LOOP OFF (the mechanism-free baseline): Foundations in round-robin order F1..F7 (empty ones skipped), the
faculty paired by round-robin rotation (faculty index = Foundation index + tick, mod 7), no pull, no restart.
Which faculty can act on which item kind (a frozen capability table, OUR_CONVENTION, stated in the code before any
run): DWP_CASCADE <- pondering (runs the cascade with FULL's rule; resolved only if GOOD); ASOM_MISALIGNED_BIAS <-
verify (re-checks the receipt and withdraws the flag; resolved only if the record truly mismatched);
LACUNA <- asking (a question naming the exact missing cell; resolved only if it names the right cell);
NO_EVIDENCE <- curiosity (reads the cell's record and classifies it; resolved only if the class is right).
Imagination, integration and consolidate act on none of these kinds here (they make NO_PROGRESS): stated now.

Exam X2-IDLE (new, sealed in X2): 16 idle sessions, each a backlog of 8-16 items and an idle tick budget smaller
than the backlog needs under round-robin. Metric: items resolved within the budget (of the exam total; GOOD);
WRONG = a resolution whose check fails (must be 0: faculties never invent). Comparison DRIVE_LOOP: GOOD margin 1/8
of the total items, WRONG not more (PROPOSED). Seed band: 1,814,000,001 to 1,815,000,000, slot k3 mod 1,000,000
(same gap and step rules; 1,000,000 above the CASC band). DRIVE_LOOP is exercised only on X2-IDLE: no pair with it
is planned (no other switch is exercised there); stated now. Reported only: thrash and fixation flags and
restlessness (RB-I §6), re-draws per item, ticks per Foundation.

### D1.2 Growth: separate line RB-G8 (NOT in wave 3)

Growth is UNPARKED by the owner, trigger = curiosity (F2). It is NOT a wave-3 switch: growing changes parameter
counts, which would confound every one-part-off comparison. Growth runs as its own line, RB-G8 "growth at the point
of curiosity", on the laptop first, 0 USD, frozen first, by a separate builder. It may join a later wave only after
it earns a word in its own frozen test.

### D1.3 Counts after D1

Exact list: RECIPE_MATH, RPM_GATE, LACUNA_CADENCE, RESTART_FALLBACK, CCE_SKIN, TRIAD,
ENGLISH_IN, VOICE, CUBE_STORE, ATLAS, EYE, CASCADE, DRIVE_LOOP = 13 switches, 13 one-off arms, 1 swap arm.
Pairs unchanged: 16 pairs, 18 pair runs. Exams: E1, E2, X2 {GB, TB, D34, CCE, E16, F16, CASC, IDLE}.
FACULTIES as a separate switch (the RB-I1 faculties without the new pairing) is NOT_IN_WAVE: the drive loop's
pairing now carries the faculties; RB-I1c's word, when it reports, is cited beside DRIVE_LOOP.
