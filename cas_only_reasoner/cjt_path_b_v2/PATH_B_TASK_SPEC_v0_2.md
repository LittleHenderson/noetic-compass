# PATH B — Operation-Graph Task Specification v0.2 (CJT-T2)

**Status:** DESIGN FOR OWNER REVIEW — supersedes v0.1 after a 19-finding
adversarial design review (all confirmed, 0 refuted:
`SPEC_V0_1_REVIEW_FINDINGS.json`; v0.1 preserved). No generator built, no
dataset produced, no GPU authorized. Development-only, non-claim-bearing.
**Owner constraints:** no third binder; v1 protected split stays closed;
PATH B gets a NEW protected derivation.

---

## 0. What the review changed (read first)

1. **The S-PERM "identity vs distinguishability" experiment was a theorem,
   not an experiment** (finding #7): with profiles entering only through the
   learned linear `W_r`, a class permutation `P` satisfies
   `(W_r g)·(P p) = (Pᵀ W_r g)·p` — S-PERM's loss landscape IS S3's under
   reparameterization. The tie is architecturally guaranteed.
   **Consequence (honest):** at the level of flat 4-class labels consumed
   through a learned linear map, "the specific CAS labeling vs any
   equally-distinguishing labeling" is NOT a testable question. What remains
   testable in v2: (a) **does typing help at all under the bijection break**
   (S3 vs S0/S6), and (b) **label-quality dose-response** (exact S3 vs
   partial/soft S-ALT vs none). The specificity question proper moves to
   **Tier C** (structural profile geometry that a learned linear map cannot
   absorb — e.g. frozen involution-respecting embeddings with frozen
   read-in), which requires its own owner-approved design.
2. **The answer-key gate was dishonest in both directions** (findings #1,
   #2): the real leak channel is the COMPOSITE of profiles + candidate-clause
   membership + discourse positions + question anchors (channels every arm
   receives), and a hand-coded adversary passes vacuously while type priors
   alone beat a naive ceiling. v0.2 gates on the **trained-adversary profile
   increment**, per family, and adds the B-MEMBER reference.
3. Frozen-architecture reality: **K ≤ 6 clauses** (MAX_IDEAS = 6; findings
   #8/#13), new-verb plumbing (finding #19), per-family gating (#4, #5),
   totalized interpretation law (#11), and family-level repairs (#3, #5,
   #9, #10, #12, #14–#18) — all folded in below.

## 1. Scientific questions v0.2 can honestly ask

- **Q-B1 (typing value under the bijection break):** does per-clause
  operation typing help relational/compositional reading at all?
  Comparison: S3 vs S0, S6 — reported against **B-MEMBER** (see §6), not
  against uniform, because typing may complete a symbolic shortcut; the
  B-KEY profile-increment gate (§2.4) bounds how much of S3−S0 can be
  shortcut-borne before the pilot may run.
- **Q-B2 (label-quality dose-response):** exact typing (S3) vs honest
  partial semantic typing (S-ALT, Δ.2 protocol, information-MISMATCHED by
  construction and reported as such) vs none (S6). Expected shape:
  S3 ≥ S-ALT ≥ S6; deviations are findings.
- **Q-B3 (Tier C, NOT this spec):** structural CAS geometry beyond flat
  typing. Explicitly deferred; requires frozen read-in design to escape the
  #7 reparameterization theorem.

## 2. Formal task

### 2.1 Ontology
Entities: minds `M`, ideas `I`, parts `P` — disjoint vocabularies, disjoint
per split bundle. Operations (classes unchanged): `^2 attract(m,i)`,
`^3 avert(m,i)`, `^6 decompose(i,[p1..p3])`, `^8 trigger(a,b,m)`.

### 2.2 Passage = operation graph, K ∈ 4..6
`K ≤ 6` honors the frozen `MAX_IDEAS = 6` (findings #8/#13). Rendering: one
clause per instance; discourse order is part of the formal trace.
Graph constraints (generator-enforced, checker-verified):
- **G-multi:** ≥2 instances of the same class with different objects, AND
  after excluding entities named in the question, the final-hop class still
  has ≥2 candidate objects — in **100% of passages** (closes #4's 5%
  loophole and the anchor-exclusion sub-hole).
- **G-overlap:** ≥1 entity is the object of instances of ≥2 classes.
- **G-chain:** ≥1 two-edge chain usable by a composition question.
- **G-order:** ≥1 mind with two same-class instances at different discourse
  positions (checked by **CHK-8**, §2.4).
Worked feasibility example at K=6 (recorded so the constraint set is known
satisfiable): `^2(m1,i1); ^3(m1,i3); ^2(m1,i2); ^6(i1,[p1,p2,p3]);
^6(i2,[p2,p4,p5]); ^8(i3,i2,m2)` — multi (two ^2 of m1), overlap (i2 is ^2
object and ^8 surfaced idea), chain (^3→^2; ^8), order (m1's ^2s at
positions 1 and 3).

### 2.3 Question families (four; QB-XOP demoted per #16)
Answers computed only by the frozen graph solver; per-family **uniqueness
constraints are explicit** (finding #14):

- **QB-REL:** "which idea was the mind that ⟨averted-verb⟩ from X drawn
  toward?" Uniqueness: exactly one mind has a ^3 edge to anchor X; that mind
  has ≥2 ^2 edges is FORBIDDEN unless the question further selects (v0.2
  rule: that mind has exactly one ^2 edge; other minds carry the extra ^2
  edges that break bijectivity).
- **QB-COMP (2-hop):** "which idea came to the mind that was drawn to X?"
  Uniqueness: exactly one mind with ^2(m,X); exactly one ^8(·,b,m) for that
  mind.
- **QB-INT:** "which part lay inside both X and the idea that ⟨attract⟩ed
  M?" Uniqueness: exactly one shared part between the two referenced ^6
  lists. **Shortcut law (finding #3):** every QB-INT passage contains ≥2
  part tokens that each occur in ≥2 ^6 lists, exactly one of which is shared
  by the two QUESTION-REFERENCED ideas — so "return the twice-occurring
  part" does not solve the family; the residual surface shortcut is
  REGISTERED in the B0-SURF suite, not denied.
- **QB-ORD:** balanced "after"/"before" wordings (finding #5): "which idea
  was M drawn to after|before ⟨avert⟩ing from X?" Uniqueness: M has ≥2 ^2
  edges, exactly one on the required side of M's ^3(X) clause.
  **Order-recoverability gates (finding #9):** CHK-8 (counterfactual:
  swapping the two relevant clause positions changes the frozen solver's
  answer, for 100% of QB-ORD items) + **PRB-POS** (pre-P1, on-instance: a
  linear probe from the frozen h_i must decode clause discourse index at
  ≥90% val accuracy; failure ⇒ the QB-ORD family is DROPPED and recorded,
  not papered over).

**D-XOP (dataset property, was QB-XOP):** enforced by CHK-2, not a family.

### 2.4 The seven owner requirements → executable gates (per family × split)
All thresholds apply **PER FAMILY, PER SPLIT**, with per-family
candidate-uniform references (finding #5). All are deterministic programs
run before GPU; any failure ⇒ `PATHB_CONSTRUCTION_FAILED(<check>)`.

| # | Requirement | Gate |
|---|---|---|
| 1 | same op → different answers | **CHK-1:** G-multi (incl. anchor exclusion) holds in 100% of passages |
| 2 | same answer under different ops | **CHK-2:** per split, ≥30% of distinct answer entities are answers under ≥2 different solver-trace final-hop class-sets (defined per finding #17: the class-set of answer-producing edges in the frozen solver's trace), with ≥3 distinct class-pairs represented |
| 3 | operations compose | **CHK-3:** ≥50% of questions are edge-NECESSARY multi-edge: removing any used edge changes the solver's answer (counterfactual necessity, finding #12) |
| 4 | relations/order/context decide | **CHK-4:** the REGISTERED v2 single-op matcher (oracle-parsed final-hop class; evaluated under ALL registered tie-breaks — first-match, last-match, expected-random — and scored at its BEST tie-break, finding #15) ≤ per-family uniform + 0.05, per family |
| 5 | unseen verbs and forms | **CHK-5:** zero clause-verb AND zero clause-template-form overlap between train and val/protected; **question surfaces included** — question templates use only their own family's registered inventory; v1 verbs appear NOWHERE (finding #10's carve-out deleted) |
| 6 | controls equally/honestly informed | **CHK-6:** S-ALT admitted under the Δ.2 magnitude protocol on the NEW inventory (alignment REPORTED, information-mismatch DISCLOSED — the "equal information" reading is retired per the #7 theorem; S-PERM covers exact-equal-information as a sanity theorem, not an experiment) |
| 7 | profile is not a disguised answer key | **CHK-7 (rebuilt, findings #1/#2):** B-KEY is a TRAINED adversary (registered model class + budget, fit on train, scored on val) whose inputs are the HONEST no-clause-text set: profile sequence, discourse positions, candidate-clause membership matrix, shuffled candidate list, question type + question anchor identities + final-hop-class cue. **Gate = profile increment:** acc(B-KEY) − acc(B-KEY minus profiles) ≤ 0.05 per family. Absolutes reported, never gated alone |
| — | order-dependence real | **CHK-8:** QB-ORD counterfactual (above) |

**Candidate-order law (finding #2):** the candidate list of every example is
shuffled by a per-passage seeded permutation (model and adversary alike see
the same shuffle) — the first-mention index-arithmetic channel is dead.

## 3. Surface realization, splits, power (finding #18)

- **Verbs:** 10 NEW verbs per class (40 total; v1's 16 retired everywhere,
  clause AND question surfaces). Allocation per class: family A 3, B 3,
  C 2, D 2. Sense-in-context frozen at registration (v1 audit protocol).
- **Forms:** 6 clause-template forms per class (active/passive/relative/
  nominalized/cleft/fronted): A 2, B 2, C 1, D 1 — val and protected are
  zero-shot lexically AND syntactically, with the thinness acknowledged.
- **Transfer floor-guard (finding #18):** before P1, an S0 pre-flight (100
  updates) must reach val ≥ per-family uniform + 0.05 on ≥2 families; else
  emit `PATHB_TRANSFER_FLOOR` and STOP for owner review (do not burn the
  five-arm run into an all-arms-floor repeat).
- **Sizes (frozen at owner approval):** train 12,000 / val 1,500 /
  protected 1,500.
- Construction-gold law retained verbatim (trace-first, deterministic
  rendering, independent round-trip parser over graph+order, exclusion not
  relabeling). HashPRNG, canonical LF writers, `.gitattributes` — v1
  infrastructure reused where it is inventory-independent.
- **Plumbing note (finding #19):** v2 registers its OWN `assemble_v2`
  profile sources on the new inventory; v1's `s7_taxonomy_label` (16-verb
  regex) is not reused.

## 4. New protected derivation
Unchanged from v0.1: family D, fresh vocabulary bundle, derivation
commitment (`PUBLIC_SEED_PATHB_<date>` or salt) registered before
generation; protected generated in-memory, digested, never written; v1
protected never touched.

## 5. Arms (frozen P1.3 machinery; no third binder)

| arm | profile | role |
|---|---|---|
| S0 | none | baseline |
| S3 | exact operation one-hot | the candidate signal |
| S6 | uniform | zero-information control |
| S-PERM | frozen permutation of S3 | **sanity theorem control** (finding #7): by equivariance, `|S3 − S-PERM| ≥ 0.02` stable in EITHER direction ⇒ `PILOT_PIPELINE_FAILURE` (two-sided, finding #11) — never a scientific finding |
| S-ALT | Δ.2-protocol WordNet control on the NEW 40-verb inventory | the honest partial-typing dose point; its CAS-alignment magnitude reported, its information mismatch disclosed |

**Interpretation law (TOTAL, finding #11)** — every outcome has a branch:
1. `|S3 − S-PERM| ≥ 0.02` stable (either sign) → `PILOT_PIPELINE_FAILURE`.
2. All arms within 0.05 of the transfer floor → `READOUT_UNDERPOWERED_V2`;
   stop; no redesign without owner.
3. S3 ≈ S0 (< 0.02) → typing does not survive the bijection break:
   `NO_DEV_SIGNAL`, report, stop.
4. S3 > S0, S6 (≥ 0.02, ≥2/3 seeds) AND S3 − S0 exceeds the B-KEY profile
   increment measured in CHK-7 → typing helps beyond the registered
   symbolic shortcut: `PROMISING_DEV_SIGNAL` (dev label only).
5. S3 > S0 but within the B-KEY increment → `SHORTCUT_BOUNDED_SIGNAL`:
   typing's value is not distinguishable from the symbolic key; report,
   stop.
6. Dose-response readout (reported in all cases): ordering of
   S3 / S-ALT / S6, with seed spreads.
7. S-ALT > S3 stable → a finding to report and stop (no post-hoc probing).
`CAS-specific` remains PROHIBITED in every PATH B development report.

## 6. Baselines (roles frozen)
- **B1-GRAPH** (parser+solver): must equal 1.000 on train/val — integrity.
- **B-MEMBER** (finding #1): true classes + membership + positions +
  anchors, NO clause text — the symbolic-shortcut reference; profile-arm
  headroom is reported against B-MEMBER.
- **B-KEY** (trained, §2.4) with its profile-increment gate.
- **B0-SURF:** registered surface-heuristic suite (incl. the QB-INT
  repeated-part heuristic, registered per finding #3).
- **B-1OP:** the v2 single-op matcher of CHK-4.

## 7. Execution plan (nothing runs from this document)
1. Owner approves/amends v0.2 (decision points below) → frozen v0.3 with
   exact numbers.
2. CPU build ($0): generator, parser, solver, CHK-1..8 programs, B-suite,
   S-ALT construction, `assemble_v2`.
3. All gates green → PRB-POS + transfer floor-guard on-instance → P0 (P1.3
   gate battery re-frozen for v2) → P1 (5 arms × seeds 11/23/47 × schedule
   frozen at v0.3) on the standard self-terminating T4 pattern; $30/2h law.
4. Report under the total interpretation law; stop.

## 8. Owner decision points for v0.2 → v0.3
- **D1:** accept the Q-B2 reframe (dose-response; specificity relocated to
  Tier C) forced by the #7 equivariance theorem — or amend.
- **D2:** K ≤ 6 under frozen MAX_IDEAS (this spec), or register
  MAX_IDEAS = 9 as a data-shape amendment (tensor sizing only, mechanism
  unchanged) to allow richer graphs.
- **D3:** QB-ORD kept under PRB-POS + CHK-8 (this spec) or dropped now.
- **D4:** sizes / verb-and-form allocation (§3) — approve or resize.
- **D5:** protected derivation choice: public seed vs owner salt.
