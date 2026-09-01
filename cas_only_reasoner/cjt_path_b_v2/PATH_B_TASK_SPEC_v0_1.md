# PATH B — Operation-Graph Task Specification v0.1 (CJT-T2)

**Status:** DESIGN FOR OWNER REVIEW — no generator built, no dataset produced,
no GPU authorized by this document. Development-only, non-claim-bearing.
**Branch:** `research/cjt-dev-p1-s7d1-fivearm-v1` (new dir `cjt_path_b_v2/`).
**Prerequisite satisfied:** the label protocol's Tier-A requirement (beat
matched controls in the controlled domain) was met by CJT-DEV-P1.3:
`PROMISING_DEV_SIGNAL`, S3 0.7340 beating every registered control by
0.034–0.080 (commit `f0c70de7`). That result is a development triage label;
it licenses starting Tier-B design and nothing more.
**Owner constraints honored:** no third binder for the v1 task; the v1
protected split stays closed and is NOT recycled; PATH B gets a NEW protected
derivation.

---

## 1. The scientific question PATH B enables

The v1 task's answer function was **class-bijective**: one question type ↔ one
operation class ↔ one matching clause whose object is the answer. On that
task, "the CAS profile helps" and "a task-aligned 4-way type label helps" are
indistinguishable — which is why `CAS-specific` is prohibited on v1 regardless
of result.

PATH B breaks that marriage. When the answer is a **relational computation
over an operation graph** — not the identification of one operation — a
per-clause type label is useful only as *routing/typing information*, and any
equally-distinguishing labeling is equally useful **by construction**. The
honest questions v2 can ask:

- **Q-B1 (typing value under composition):** does per-clause operation typing
  help multi-hop relational reading at all? (S3 vs S0/S6)
- **Q-B2 (identity vs distinguishability):** does the *specific* CAS labeling
  help beyond ANY information-matched relabeling? (S3 vs S-PERM, S-ALT)
  — expected honest outcome is a TIE; a tie here is a *finding*, not a
  failure.
- **Q-B3 (future, Tier C, not this spec):** does CAS *structure* (involution
  pairs, composition algebra) help beyond flat typing? Requires
  structure-bearing profile encodings; explicitly out of scope for v0.1.

## 2. Formal task: operation graphs

### 2.1 Ontology (unchanged operation classes)
Entities: minds `M`, ideas `I`, parts `P` (disjoint vocabularies per split
bundle). Operation instances (the four v1 classes, kept):

```
^2 attract(m, i)        mind m is drawn toward idea i
^3 avert(m, i)          mind m is repelled by idea i
^6 decompose(i, [p1,p2,p3])   idea i is composed of parts
^8 trigger(a, b, m)     idea a brings idea b to mind m
```

### 2.2 Passage = operation graph
A passage is a set of `K` operation instances (`K` in 6..9) rendered one
clause each, in a discourse order that is part of the formal trace. Graph
constraints (all enforced by the generator and verified by executable checks):

- **G-multi:** at least two instances of the SAME class with different
  objects (same operation → different answers).
- **G-overlap:** at least one entity is the object/target of instances of
  ≥2 DIFFERENT classes (same answer under different operations).
- **G-chain:** at least one 2-hop chain exists (e.g., `^3(m, x)` and
  `^2(m, y)`; or `^8(a, b, m)` feeding `^2(m', b)`), so composition
  questions are constructible.
- **G-order:** for at least one mind, two same-class instances occur at
  different discourse positions (order-dependent questions constructible).

### 2.3 Question families (the bijection break)
Every question's answer is computed by the **frozen graph solver** from the
formal trace. No question is answerable by "find the unique clause of class c
and return its object". Families for v0.1:

- **QB-REL (relational disambiguation):** "which idea was the mind that
  recoiled from X drawn to?" — final hop is ^2, but MULTIPLE ^2 instances
  exist; the ^3 relation selects the mind. Same op → different answers.
- **QB-COMP (2-hop composition):** "which idea came to the mind that was
  drawn to X?" — compose ^2 (select mind) then ^8 (select triggered idea).
- **QB-INT (intersection):** "which part lay inside both X and the idea
  that captivated M?" — two ^6 edges + one ^2 edge; answer = set
  intersection (generator guarantees a unique element).
- **QB-ORD (order/context):** "which idea was M drawn to after turning away
  from X?" — among M's ^2 instances, the one whose clause FOLLOWS M's ^3(X)
  clause in discourse order.
- **QB-XOP (cross-operation reach):** the same answer entity is reachable
  via different operation routes in different passages; question wording
  does not reveal the route class mix.

Per-family balance is frozen in the dataset manifest. The candidate set
remains the passage's closed entity set (variable size), answer ∈ candidates.

### 2.4 The seven owner requirements → executable properties

| # | Owner requirement | Design mechanism | Executable check (pre-GPU gate) |
|---|---|---|---|
| 1 | same operation → different answers | G-multi + QB-REL/QB-ORD | **CHK-1:** for ≥95% of passages, the final-hop class has ≥2 candidate objects |
| 2 | same answer under different operations | G-overlap + QB-XOP | **CHK-2:** over each split, for ≥30% of distinct answer entities, the entity is an answer under ≥2 different final-hop classes |
| 3 | several operations must compose | QB-COMP/QB-INT | **CHK-3:** ≥50% of questions require ≥2 graph edges to solve (per the frozen solver's edge-usage trace) |
| 4 | relations/order/context decide, not op identification | all QB families | **CHK-4 (bijection-break proof):** the v1-style single-op matcher ("return the object of the unique class-c clause") scores ≤ 0.25 on every split |
| 5 | unseen verbs and sentence forms | §3 family design | **CHK-5:** zero verb overlap AND zero template-form overlap between train and val/protected surfaces |
| 6 | ordinary semantic controls equally informative | §5 information-match certificate | **CHK-6:** every registered non-uniform control is certified a class-distinguishing bijection (or matched-ensemble member) of the true typing |
| 7 | profile is not a disguised answer key | answers are graph computations | **CHK-7 (answer-key ceiling):** a solver given ONLY (profiles sequence, question type, candidate list — NO text, NO graph) must score ≤ candidate-uniform + 0.05 |

All seven checks are deterministic programs run before any GPU spend; any
failure stops PATH B construction with `PATHB_CONSTRUCTION_FAILED` and the
named check.

## 3. Surface realization and splits

- **Verb inventory:** 8 registered verbs per class (32 total), all NEW —
  the 16 v1 verbs are retired from clause rendering (they may appear in
  question templates only if frozen so). Sense-in-context frozen per verb at
  registration (v1 audit protocol reused).
- **Sentence forms:** ≥4 clause templates per class per family, spanning
  active / passive / relative-clause / nominalized forms.
- **Families:** A,B (train), C (val), D (protected) with BOTH verb-disjoint
  and form-disjoint surfaces (CHK-5). Entity vocabulary bundles disjoint per
  split (v1 law retained).
- **Construction-gold law retained verbatim:** the formal trace exists
  first; deterministic templates render it; the INDEPENDENT round-trip
  parser must recover the full operation graph + discourse order exactly;
  failed round-trips are excluded, never relabeled.
- **Sizes (provisional, frozen at v0.2):** train 8,000 / val 1,000 /
  protected 1,000. HashPRNG generation (version-independent), byte-canonical
  writers, `.gitattributes` LF pin — all v1 infrastructure reused.

## 4. New protected derivation (owner point 3)

- The v1 protected split remains CLOSED and is never read or recycled.
- PATH B registers a NEW derivation commitment before generation:
  `PUBLIC_SEED_PATHB_<date>` or `SALT_SHA256:<digest>` (owner's choice at
  spec approval), family D, fresh vocabulary bundle.
- The protected split is generated in-memory, digested, counted — never
  written (v1 law). One future read, only under a claim-bearing campaign's
  frozen machinery; no read in any development run.

## 5. Arms and the information-match certificate

All arms use the FROZEN P1.3 architecture (router + clause-local expert
binder) with no modification — PATH B changes the task, not the model
machinery (no third binder).

| arm | per-clause profile | information-match status |
|---|---|---|
| S0 | none | baseline |
| S3 | exact operation one-hot (`EXACT_OPERATION_IDENTITY` / `CONSTRUCTION_GOLD`) | the candidate signal |
| S6 | uniform (`UNIFORM_CONTROL`) | zero information |
| **S-PERM** | frozen permutation of S3's classes (`PERMUTED_OPERATION_IDENTITY` / `EXPERIMENTAL_CONTROL`) | **exactly equal information by construction** (bijection) |
| **S-ALT** | registered independent semantic taxonomy re-anchored on the NEW 32-verb inventory (WordNet construction-context senses; S7-Δ.2 magnitude-gate protocol reused) | certified class-distinguishing; equal typing information |

**CHK-6 certificate:** for S-PERM, bijectivity is trivial and recorded. For
S-ALT, the certificate requires its labeling to separate the four operation
classes with the same distinguishing power on the registered verb inventory
(a confusion-free mapping verb→class up to relabeling), verified by program.
If no honest S-ALT achieves that on the new inventory, S-ALT is dropped and
the fact recorded — S-PERM alone already carries the Q-B2 comparison.

**Interpretation law (frozen now):**
- S3 > S0, S6 and S3 ≈ S-PERM ≈ S-ALT → *typing helps; the specific CAS
  identity adds nothing beyond an equally-distinguishing labeling* — the
  expected, publishable-as-development honest outcome.
- S3 > S-PERM (stable, ≥0.02, ≥2/3 seeds) → an anomaly to be investigated,
  NOT a claim; report and stop.
- S3 ≈ S0 → typing does not survive the bijection break; report and stop.
- Vocabulary: development triage labels only (`PROMISING_DEV_SIGNAL` /
  `NO_DEV_SIGNAL` / `INCONCLUSIVE_DEV_SIGNAL` / `PILOT_PIPELINE_FAILURE` /
  `PATHB_CONSTRUCTION_FAILED`). `CAS-specific` remains PROHIBITED in all
  PATH B development reporting.

## 6. Baselines and references (frozen roles)

- **B1-GRAPH:** the frozen deterministic parser+solver — must score 1.000 on
  train and val (construction-gold integrity; also the answer oracle).
- **B0-SURF:** registered surface-heuristic family (no graph), reported as
  the task-specific reference (expected well below 1.0 this time — the
  gap B1−B0 measures how much the bijection break costs surface shortcuts).
- **B-TYPEONLY:** a solver given the TRUE per-clause classes and the graph
  edges but not the text — expected 1.000 (typing + relations suffice);
  documents that class information is *useful routing info* for every arm's
  fairness argument.
- **B-KEY (CHK-7):** profiles+question-type only — must be ≤ uniform+0.05.
- **B-1OP (CHK-4):** the v1 single-op matcher — must be ≤ 0.25.

## 7. Execution plan (all gated; nothing runs from this document)

1. **Owner approves/amends this spec** (v0.1 → frozen v0.2 with exact
   thresholds, sizes, verb inventory, derivation commitment).
2. CPU build ($0): generator + independent round-trip parser + graph solver
   + the seven CHK programs + S-ALT construction under the Δ.2 protocol.
3. CHK-1..7 all green → dev pilot on the standard self-terminating T4
   pattern (P0 smoke with the P1.3 gate battery incl. BINDING gates
   re-frozen for v2; then P1 five arms × seeds 11/23/47 × schedule frozen at
   v0.2). Ceilings: $30 / 2h per the standing pilot law.
4. Report with the frozen interpretation law; stop.

## 8. What this spec does NOT do

No model change; no third binder; no v1 protected read; no claim promotion;
no arXiv/public disclosure; no Gate 1B interaction. The claim-bearing version
of PATH B (if ever) requires its own preregistration under the Gate-1A
authority machinery (owner key, signed approvals, watchdog closure R.2C,
Gate 1A.2S) — none of which is touched here.
