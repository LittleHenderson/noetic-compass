# CJT / CAS-Ohm -- STATE OF EVIDENCE (clean-room reconstruction, 2026-09-02)

```
Prepared by      the clean-room successor (Claude), Phase A of the owner handoff
Repository       C:/Users/wakil/OneDrive/Desktop/tksCAS   (worktree C:/tmp/tksCAS-cjt-ohm-cleanroom-reset-v1)
Parent           branch research/cmb-r1-rgm02-v1, HEAD 1e58d7254d97c88effa609f7ad05ee2fca9b1aee (pushed)
This branch      research/cjt-ohm-cleanroom-reset-v1, created from that HEAD
Companion files  CJT_OHM_CLAIM_LEDGER.json (242 claims, authoritative), CJT_OHM_CLAIM_TABLES.md (rendered),
                 CJT_OHM_ARTIFACT_MANIFEST.json (259 paths), p6/P6_RESOLUTION.md (Phase B),
                 CJT_MECH_0_DESIGN_BRIEF_v0_1.md (Phase C, not authorized)
Authorization    NOTHING in this document authorizes a run, a spend or a claim.  No GPU was used.
                 Spend this phase: local CPU numpy under two minutes; AWS Bedrock audit tokens
                 est. USD 0.0308 (receipted).
```

Status words follow the handoff vocabulary: `VERIFIED / SUPPORTED_NARROWLY / REFUTED /
RETIRED_BY_IDENTITY / INVALID_BENCH / UNVERIFIED / CHAT_REPORTED_ONLY / OPEN`. The law behind each
word is in the ledger header. "Unverified" never means "false".

---

## 0. How this record was built, and what it does NOT yet have

- Twelve reader agents extracted claims from committed artifacts only (0R, D0, S0, D1, precedence
  closure, EX1, Path B, CJT-DEV / Tier C, the deterministic controller and Gate 1A, the eta-epsilon
  lane, the spec sheet / CHANGELOG cross-check, governance). Three independent lens agents audited
  the P6 script. Every reader was told the previous builder's defect record and ordered to copy
  numbers verbatim and to say where each number physically lives.
- **Every claim then passed a deterministic mechanical check**: each cited artifact path was tested
  at HEAD, and each numeric key number was searched verbatim in the committed files and, failing
  that, in the claim's commit messages. The ledger's resolution law (header) turned the results into
  statuses; 18 statuses were changed by that law, every change recorded on the claim.
- **What is missing: second-agent adversarial verification.** The per-claim verifier fan-out (226
  agents) and the completeness critic failed on the account's session usage limit. Five verdicts
  landed (GOV-01..05; all `TOO_STRONG`, `VERIFIED -> SUPPORTED_NARROWLY`) and are applied. The
  ledger header states this; no claim pretends to have been adversarially verified when it was not.
  The run can be resumed with the recorded workflow id when the owner wants the tokens spent.
- Successor-made claims (P6 and record gaps) are in the ledger as `CR-*` with their receipts.

## 1. Exact repository state

| item | value |
|---|---|
| parent branch / HEAD | `research/cmb-r1-rgm02-v1` / `1e58d7254d97c88effa609f7ad05ee2fca9b1aee`, identical to `origin/research/cmb-r1-rgm02-v1` |
| clean-room branch | `research/cjt-ohm-cleanroom-reset-v1` from that HEAD; worktree `C:/tmp/tksCAS-cjt-ohm-cleanroom-reset-v1` |
| relation to `master` | 820 commits ahead of local `master` (`4c9e0ac4`); no merge attempted or proposed |
| line endings | global `core.autocrlf=true`: worktree files are CRLF, committed blobs LF. Digest pins in this directory are on LF-normalised bytes or git blob ids |

## 2. Commits located and missing

All fifteen SHAs the handoff names exist and are ancestors of HEAD:
`e4327512` `fc7ceb48` `66a01122` `3bbcd2c1` `cbffa4a0` `90b601a4` `a47b951b` `60727805` `8b5c2ee3`
`90248303` `8572aabd` `4825a37d` `269dfd11`, plus `61a3576d` and `1e58d725`.
Further lane commits located and read: `05db7b75` `47259705` `dc185d46` `db95f2fc` `f16bd500`
(0R / D0 / S0 rulings); `15307b70` (EX1 closure ruling); `01b7224c` and the Path B series
`ea5951dd`..`3bbcd2c1`; the CJT-DEV series `9229d8b4`..`f0c70de7`; Tier C `9a1752b9` `ab7afd1f`
`5c1ceb3d`; controller `c6eb3f4e`..`83f57d6f`; Gate 1A `49664dac`..`3182e062`; eta-epsilon
`836c9783` `eb8cf2cd` `44128fb2` `4879d25d`.

**Missing.** The four audit files the handoff names under `REFERENCE/AUDITS/` (`CJT_OHM_0R_cbffa4a0_GLM_AUDIT.md`,
`CJT_OHM_D1_DESIGN_ATTACK_AUDIT...`, `PRECEDENCE_CLOSURE_AUDIT...`, `TRIGGER_CONFORMANCE...`) do not
exist under any name (`CR-REC-01`); that directory holds two CMB audits only. The GLM audits of this
lane exist only as the builder's summaries inside findings files, spec-sheet rows and commit
messages. The only committed external audit record in the lane is
`CJT_PREC_CLOSURE/audits/deepseek-r1_audit.md`. The controller documents the handoff places at
`cas_only_reasoner/RECURSIVE_CJT_BIAS_CONTROLLER_v0_2.md` / `v0_3.md` live at
`docs/research/RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md`, `..._v0_2_CANDIDATE.md`, `..._v0_3_CANDIDATE.md`.

**Record-discipline gaps.** `4825a37d`, `61a3576d` and `1e58d725` touched neither the spec sheet
nor CHANGELOG (`SHEET-02`, `CR-REC-02`); the whole lane appears in the spec sheet only as §11
change-log rows, never as a §4 capability, §7 negative or §10 frontier row (`SHEET-16`); EX1 has no
sheet row at all (`EX1-17`); the eta-epsilon weight-learning study and its owner audit have no sheet
record (`ETAEPS-18`). This commit adds §7.20 (P6) and one change-log row; the rest is listed as
owner-visible work, not silently repaired.

## 3. The claim ledger -- by lane, with the load-bearing statuses

Full table: `CJT_OHM_CLAIM_TABLES.md`. Counts: 242 claims -- `VERIFIED` 57, `SUPPORTED_NARROWLY` 90,
`REFUTED` 18, `RETIRED_BY_IDENTITY` 5, `INVALID_BENCH` 13, `UNVERIFIED` 34, `CHAT_REPORTED_ONLY` 3,
`OPEN` 22.

### 3.1 CJT-OHM-0R -- the formal package (`OHM0R-01..20`)
- Additive weight law `W_eff = W0 + s*sum alpha_j dW_j` = output mixing (C1 `8.882e-16`, C14
  `2.373e-16` re-executed): **`RETIRED_BY_IDENTITY`** (`OHM0R-01`). Note kept: FINDINGS §9 and the
  `cbffa4a0` message say C14 `2.807e-16` while the committed receipt says `2.373e-16`; the sheet row
  credits "convex-hull identity `1.7e-16`" to the package when it is GLM's figure.
- Ratio-only controller reproduces `alpha` and `I_total` exactly (C12 `0.0`): **`VERIFIED`**. Equal
  ratios give identical outputs, so `V`/`R` are not identifiable from routing (C7): **`VERIFIED`**
  (`OHM0R-02/03`). Common-mode cancels from `alpha`, not from `I_total` (C4/C6): **`VERIFIED`**.
- Hard mask gives exact `0.0` where softmax floors at `6.388e-24` (C9): **`VERIFIED`**, governance not
  CAS arithmetic (`OHM0R-07`). Composition differs from mixing only at non-linear sockets (C8...):
  **`VERIFIED`** (`OHM0R-08`). CAS-law alphas do not break mixing equivalence more than Dirichlet
  alphas (`OHM0R-10`): **`VERIFIED`**.
- Cascade span residual: `0.2096`/`3.0e-16` was GLM's reimplementation (`OHM0R-12` **`UNVERIFIED`**
  as a package figure); committed standalone `0.054458`, full-package `0.0746`; the gate is
  **`INVALID_BENCH`** for CAS (all-random Basis; 15 random systems min `0.026937` mean `0.047810`
  max `0.071911`; `s = 0.7` dial flips it at `s <= 0.05`) (`OHM0R-13/14`, `S0-05/06`).
- The GLM audit "PASS" of `cbffa4a0`: **`UNVERIFIED`** as an audit record -- builder summary only
  (`OHM0R-15`); its finding F1 (epsilon inside `split_flow`) is real and repaired (`OHM0R-16`
  **`VERIFIED`**).
- Typed diagnosis vs a generic full-state MLP: **`OPEN`**, never tested (`OHM0R-06`).

### 3.2 CJT-OHM-D0 (`D0-01..19`, `SHEET-09`)
- All 720 channel permutations: D5 shuffled == D4 with permuted parameters, worst residual
  `0.0000e+00` (`D0-01` **`SUPPORTED_NARROWLY`**; script committed, extractor did not record a
  re-execution). `D_ANON_FACTORIZED == D5 == D4`: **`RETIRED_BY_IDENTITY`**. `D0_DESIGN_INVALID`:
  **`INVALID_BENCH`**, owner-ratified.
- Sparsity dial `0.7283 -> 0.0019` vs `0.9688 -> 0.9578`, the `4.44e-16` training-curve identity,
  the first script's `9.27` / hard-coded "ZERO": **`UNVERIFIED`** (no committed artifact or not
  reproduced) (`D0-04/06/07/09`). The `1.33e-01` divergence was the builder's `perm` vs `perm^-1`
  bug: **`SUPPORTED_NARROWLY`** (`D0-08`).
- Epsilon: `GATE_EPS_NOT_A_SIDE_CHANNEL` **`REFUTED`** (`0.820000` recovery at the registered floor;
  `D0-12`, `S0-11` **`VERIFIED`**); replacement `GATE_EPS_EXACT_COLLISION` **`OPEN`** (`D0-13`).
- Owner law "type must govern mechanism", the eight properties, the fairness rule, D1's eight
  requirements: **`SUPPORTED_NARROWLY`** as document facts (`D0-14..17`, `GOV-03/04`, verifier
  downgraded from `VERIFIED`). The surviving hypothesis "same flow, different cause, different
  repair": **`OPEN`** (`D0-19`).

### 3.3 CJT-CASCADE-S0 (`S0-01..19`, `SHEET-10`)
- `S0_DO_NOT_BUILD_AS_A_CAS_BENCH`: **`INVALID_BENCH`**. Order absorbed on all 24 orderings at
  `0.0000e+00`: **`RETIRED_BY_IDENTITY`** (`S0-08`). Span gate blind to order (commuting diagonal
  stages still pass at `6.7e-03`-`7.9e-03`): **`VERIFIED`** (`S0-09`, re-executed). Gate cannot license
  `CAS_OHM_VALUE` or `SEQUENTIAL_CASCADE_COMPOSITION_VALUE`: **`REFUTED`** (`S0-10`).
- Attack-side B1/B2/B3 figures (world-generator-as-status-dial etc.): **`UNVERIFIED`** -- no
  committed artifact (`S0-13..16`). The fresh-GLM closure audit result: **`OPEN`** -- directive
  committed, no result record found (`S0-19`).

### 3.4 CJT-OHM-D1 and the precedence chain (`D1-01..20`, `PREC-01..18`, `SHEET-11/12/17/19`)
- B1: zero-call closed form == 4-call oracle over 200,000 items, shortfall `1.845175e-14`, agreement
  `1.000000`: **`VERIFIED`** (`D1-01`, re-executed). Mask-only fraction `0.501350`: **`VERIFIED`**.
  `D1_DO_NOT_BUILD`: **`INVALID_BENCH`**, owner-ratified (`D1-15`, `SHEET-11`).
- Precedence chain non-absorption: K=5 `4.6108e-02` (119 x 120), signed `4.0097e-02` (x 3840), flat
  `0.0000e+00`: **`VERIFIED`** (`D1-03/04`); K=4 `0/23`, min `1.0558e-01` (24 perms) / `6.8768e-02`
  (384 signed), flat `23/23`: **`VERIFIED`** (`D1-05`, `PREC-01`).
- Universal claim "for all parameters": **`REFUTED`** (`U = 0` absorbs `5/23`) (`D1-08`, `PREC-02`).
  Type-blind read-ins absorb `0 / 1 / 5 of 23`, predicted before measured: **`VERIFIED`** (`PREC-06`,
  `D1-09`); the published `1, 2, 5` were fabricated (defect #20, corrected in `1e58d725`).
- Free lunch: original `0.201300` / `1.000000` **`REFUTED`** as fabricated (`D1-06`, `SHEET-19`);
  corrected 12-draw mean `0.2357` sd `0.1136` (chance `0.2500`), single draw `0.3802`:
  **`SUPPORTED_NARROWLY`** (`PREC-04`).
- Generic (measure-zero) non-absorption: **`SUPPORTED_NARROWLY`**, numerical not proved (`PREC-07`,
  `D1-10`). Visibility law `7/7`: **`SUPPORTED_NARROWLY`** (`PREC-12`, `SHEET-04` `VERIFIED` by
  re-execution of the 7 constructions); the DeepSeek R1 `PASS` on it is a committed different-family
  record whose trace is example-based, not a proof (`PREC-13`, `CR-REC-03`).
- Expressivity at matched capacity: **`OPEN`** / NOT DECISIVE (weakest relabelling `4.4291e-02` below
  the out-of-class floor `1.2469e-01`) (`PREC-08`, `SHEET-06`).
- Attack-side figures Req 6 `0.169`, Req 7 `0.354500-0.428025`, B8 `0.072425`, `r = 0.022389`:
  **`UNVERIFIED`** and non-load-bearing (`PREC-10/11/17`, `D1-11/14`, `SHEET-17`). B5 (3 floats), B7
  (one admissible `R`), B2/B3 (gap `0`): **`VERIFIED`** by receipt (`D1-13`, `PREC-09`).
- Owner label `ANCHORED_PRECEDENCE_NON_EQUIVARIANCE_PROVISIONAL`, explicitly **not** `LICENSED`,
  not CAS-Ohm, non-equivariance is not advantage: **`SUPPORTED_NARROWLY`** as a document fact
  (`PREC-16`, `D1-17` `OPEN` on value). The "observability vise" claim: **`REFUTED`** by owner ruling
  (`D1-16`). `CJT-PREC-0`: specification recorded, **`OPEN`**, not authorized (`D1-20`).

### 3.5 P6 order screen (`PREC-15`, `SHEET-03`, `GOV-20`, `CR-P6-01..09`) -- Phase B
- On entry: **`CHAT_REPORTED_ONLY`** (numbers in the commit message only).
- After reconstruction: numbers reproduce 16/16 (**`VERIFIED`** as training-fit values, `CR-P6-01`);
  "held-out" == training set 15/15 and 20/20 (**`VERIFIED`**, `CR-P6-02`); with a real held-out draw
  the positive control fails, `CONTROLS_FAILED_NO_VERDICT` (**`VERIFIED`**, `CR-P6-03`); "order
  matters / bag loses by `0.13-0.15`" **`REFUTED`** (`CR-P6-04`); an 84-parameter linear rule beats
  every arm held out `0.7108` vs `0.6875` (**`VERIFIED`**, `CR-P6-05`); the commit-message status
  word was never printed by the program (**`VERIFIED`**, `CR-P6-06`); specific `P > C > E > O` value
  **`OPEN`** with zero evidence for it (`CR-P6-07`); generic sequencing **`OPEN`** (`CR-P6-08`); P6
  **`INVALID_BENCH`** (`CR-P6-09`). Two different-family auditors: `P6_AUDIT_FAIL`, both.
  Full account: `p6/P6_RESOLUTION.md`.

### 3.6 CJT-EX1 (`EX1-01..18`)
- `NO_CJT_EXPERT_SPECIALIZATION_SIGNAL`, E2 CAS partition `0.78057` vs E4 meaningless fixed partition
  `0.780011` (`+0.000559`): **`SUPPORTED_NARROWLY`** (36/36 AWS runs, frozen status law; raw JSON
  re-aggregated by the reader). Success condition 4 "shuffling removes the advantage": **`REFUTED`**
  (`EX1-02`). The killer comparison E2 vs E1S is **`INVALID_BENCH`** as run -- the learned sparse
  router collapsed (`EX1-04/05`). Owner closed EX1 on the tie (`EX1-15`). What EX1 did not test
  (CAS experts vs a non-degenerate learned router): **`OPEN`** (`EX1-18`).

### 3.7 Path B recurrent graph executor (`PATHB-01..19`)
- Executor works: A0 `GRAPH_EXECUTOR_EARNED`, clean PRB-POS max `0.8478` below the `0.90` re-entry
  bar: **`SUPPORTED_NARROWLY`** (`PATHB-05/06`). A1: S0 `0.755259`, S3 `0.787259`; status
  `NO_PATH_B_OPERATION_SIGNAL` because SALT50 `0.7428` fell below S6 `0.7461`: **`SUPPORTED_NARROWLY`**;
  dose monotonicity **`REFUTED`** (`PATHB-11`). Profile ablation collapses S3 from `0.7873`:
  **`SUPPORTED_NARROWLY`** (`PATHB-10`). B-KEY shortcut clause compared against a hand-registered
  constant: **`REFUTED`** as a control (`PATHB-14`). Formal-path faithfulness (`0.3304` top-1 bridge
  agreement): **`OPEN`** (`PATHB-15`). Three-auditor raw audit, zero numerical discrepancies,
  committed as one consolidated JSON: **`SUPPORTED_NARROWLY`** (`PATHB-16`). The first P0 run was
  VOID (pid collision): **`INVALID_BENCH`** (`PATHB-03`); dataset regenerated with recorded digests:
  **`VERIFIED`** (`PATHB-02/04`). Licenses no CAS-specific claim (`PATHB-18`).

### 3.8 CJT-DEV-P1 and Tier C (`CJTDEV-01..18`)
- P1.0 and P1.2 `NO_DEV_SIGNAL`; P1.3 `PROMISING_DEV_SIGNAL` S3 `0.7340` (gold-clause top-1 `0.869`),
  dev label only, "CAS-specific" prohibited: **`SUPPORTED_NARROWLY`** (`CJTDEV-07/08`). Uniform
  profile S6 exactly invariant by construction (`CJTDEV-06`). Tier C C1 `NO_TRANSFORM_CONSUMES_STRUCTURE`
  (T0 `0.97449` / `1.0` / `0.377668`): **`SUPPORTED_NARROWLY`**; J not identifiable on the current
  task (`CJTDEV-14`); C2 must not run: **`INVALID_BENCH`** (`CJTDEV-15`); the J-track condition fails
  on the case J0 found: **`RETIRED_BY_IDENTITY`** (`CJTDEV-17`). Cumulative arc GPU spend recorded
  `1.708 USD` (`PATHB-17`).

### 3.9 Deterministic controller and Gate 1A (`RC0-01..20`)
- Test battery `246/246` re-executed: **`VERIFIED`** (`RC0-01`). Programmatic status
  `DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT`; Gate 0 frozen at
  `83f57d6f`; establishes **no** neural result and **no** CAS-specific advantage: **`SUPPORTED_NARROWLY`**
  (`RC0-04/05/07`). Gate 1A / CJT-T1 is a byte-frozen package with no neural execution:
  **`VERIFIED`** (`RC0-13`).
- Negatives that matter for the next design: receipt digests bind Windows working-tree bytes, not
  blobs (**`REFUTED`** binding, `RC0-12`); the S7 "alternative taxonomy" control in Gate 1A is an
  exact relabelling of the CAS classes (**`REFUTED`** as a matched non-CAS control, `RC0-16`) -- the
  very control the program most needs does not yet exist in a valid form; a spec/pre-registration
  digest contradiction (`RC0-17`); two freezes refuted after commit and repaired (`RC0-18`).

### 3.10 eta-epsilon / CAS-Ohm dose response (`ETAEPS-01..20`, `SHEET-15`)
- Formal bridge is section-retraction, not adjunction; harness eta/epsilon are not an instance of
  it: **`SUPPORTED_NARROWLY`** (`ETAEPS-01/02`). Phase 1 software right-inverse `9/9`:
  **`SUPPORTED_NARROWLY`**. Original Phase 2 gate **`REFUTED`** (failed). Phase 3 steering, Phase 4
  LoRA, Phase 6 readout-guided training figures: **`UNVERIFIED`** -- produced under a self-authorized
  amendment after a failed gate, and the reader cited no artifact paths so the mechanical check had
  nothing to search (`ETAEPS-09/11/13`). Phase 5 dose calibration (the handoff's "first-order relation
  ... quadratic better at high dose"): **`REFUTED`** as a CAS-Ohm claim (`ETAEPS-12`). Owner audit
  closure: goal-substitution violation, **`INVALID_BENCH`** (`ETAEPS-14/15`). Preregistration v0.3A:
  candidate, **`OPEN`** (`ETAEPS-16`). Spec-sheet capability 22 CAS-Ohm quantifiers: `NOT LICENSED`,
  never run against a model, zero callers (`ETAEPS-17`, `SHEET-15`).

### 3.11 The older activation-based precedence test (`SHEET-13/14`)
- Real GPT-NeoX-20B activations, 2026-08-18: domain separability rises to `0.5165-0.5638` (layers
  32-41), strict order fit ranks CAS `2/12` at its best layer (`r = +0.597`), inverts on layers
  13-20 and 43: **`SUPPORTED_NARROWLY`**, "presence, not specificity". The matched-taxonomy lever
  returned `INCONCLUSIVE BY DESIGN` (`SHEET-14` **`UNVERIFIED`**). This is the only prior evidence on
  the `P ≻ C ≻ E ≻ O` question and it does not license the order either.

### 3.12 Governance (`GOV-01..20`)
Laws and rulings are recorded as document facts (`VERIFIED` where the file states them verbatim
and no measurement rides on them; `SUPPORTED_NARROWLY` where a verifier judged the extraction too
strong). The DeepSeek R1 theorem audit record and its scope: `VERIFIED` as a record (`GOV-11`). The
second-auditor billing block: `SUPPORTED_NARROWLY` (`GOV-18`). Open audit items (third-party audit of
`a47b951b`; D1 items 8 and 9): `OPEN` (`GOV-15`).

## 4. Contaminated, superseded or otherwise uncitable numbers

Do not cite any of these as measurements:

| number | why |
|---|---|
| P6 `0.9689 / 0.9272 / 0.9471 / 0.8181` and the rest of the sixteen | training-fit, not held-out (`CR-P6-02`) |
| P6 "bag loses by `0.13-0.15`" | refuted on held-out (`CR-P6-04`) |
| P6 status `CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED` | never printed by the program (`CR-P6-06`) |
| P6 `chance = 0.25` | majority class is `0.36-0.37` (`CR-P6-05`) |
| cascade span `0.2096` vs `3.0e-16` | GLM's reimplementation, not the package (`OHM0R-12`, `SHEET-08`); the quantity is `VACUOUS` anyway |
| C14 `2.807e-16` (FINDINGS §9, `cbffa4a0` message) | receipt says `2.373e-16` (`OHM0R-01` note) |
| "convex-hull identity `1.7e-16`" credited to the package | GLM's figure (`OHM0R-01` note) |
| D0 `1.33e-01` | builder's `perm` vs `perm^-1` bug (`D0-08`) |
| D0 `4.44e-16` training-curve identity | no committed artifact, not reproduced (`D0-07`, `SHEET-18`) |
| D0 sparsity-dial series `0.7283 ... 0.0019` | no committed artifact (`D0-04`) |
| free lunch `0.201300` / `1.000000` | fabricated (coin flip vs tautology) (`D1-06`) |
| absorbed counts `1, 2, 5` | fabricated; true `0, 1, 5` (`PREC-06`) |
| single-draw free lunch `0.3802` | draw artefact; 12-draw mean `0.2357` (`PREC-04`) |
| Req 6 `0.169`, Req 7 `0.354500-0.428025`, B8 `0.072425`, `r = 0.022389` / `0.022779` | attack-side, unverified, non-load-bearing (`PREC-10/11/17`) |
| S0 attack-side B1/B2/B3 figures | no committed artifact (`S0-13..15`) |
| EX1 pre-launch `0.000084` bits | unverified (`EX1-10`) |
| eta-epsilon Phase 3/4/6 figures (`0.6009...`, `0.0563...`, `0.91`) | produced past a failed gate under self-authorization (`ETAEPS-09/11/13/14`) |
| every "GLM audit PASS" of the lane | builder-reported; no committed audit record (`OHM0R-15`, `CR-REC-01`) |
| the handoff line "sequencing appears useful in the reported P6 screen" | withdrawn |

## 5. Results safe to build on (committed artifact + re-executed or receipted)

- The algebra of CAS-Ohm as a control law: additive weight generation is output mixing; only
  `V/R` enters routing; `alpha` and `I_total` are distinct quantities; common-mode cancels from
  `alpha` only; hard masks certify exact zero (`OHM0R-01..04/07/09/10`).
- Permutation-symmetric architectures absorb type labels: D0 720/720, S0 24/24 -- and therefore
  label-shuffle-after-retraining is not a control (`D0-01/02`, `S0-08`, `GOV-06`).
- An externally anchored non-linear chain is NOT absorbed under tested groups (K=4 `0/23`, signed
  `6.8768e-02` min; flat `23/23`), with an explicit exceptional set (type-blind or severed positions)
  and a falsifiable visibility law that survived 7 constructions and one different-family audit
  (`PREC-01/02/06/12`, `D1-03..05/08/09`). Distinguishability only; value untested.
- D1's world is trivial under its own physics (closed form == oracle over 200,000 items) --
  a successor needs partial observability, costly probes, non-commutative actions (`D1-01`).
- P6's instrument is invalid; a held-out identity check and a capacity-matched mechanism-free
  baseline are mandatory (`CR-P6-02..05`).
- The deterministic controller's reference semantics exist and pass `246/246` with a programmatic
  status; they establish no neural result (`RC0-01/04/07`).
- The neural dev results that exist are narrow and honest: EX1 tie (`+0.000559`), Path B executor
  works but licenses no CAS claim, P1.3 `PROMISING_DEV_SIGNAL` is dev-only (`EX1-01`, `PATHB-05/08`,
  `CJTDEV-07`).

## 6. One recommended next design question

> **Does a mechanism-bound recurrent CJT controller reach verified next-tick recovery with fewer
> examples, fewer wrong actions and better transfer to unseen fault combinations than matched generic
> recurrent controllers, in a partially observed world where diagnostic probes cost budget, repair
> actions are state-dependent and non-commutative, and the gold outcome is produced by the
> environment and a verifier rather than by a type-to-repair table?**

Brief: `CJT_MECH_0_DESIGN_BRIEF_v0_1.md` (draft, not authorized). The transformer-substrate reading
of the same question, and what the six deaths imply about where CAS content can live at all, is in
`CAS_CJT_TRANSFORMER_POSSIBILITY_v0_1.md` (reasoning only).

## 7. Why it is non-vacuous

Every retired design attached CAS content to something a learner can rename (a module name, a
channel index, a stage order, a weight formula, a repair table). The one result that survived
attached it to an interface fixed from outside. CJT-MECH-0 attaches type to ports, contracts, legal
actions, memory access and commit authority -- all enforced outside the trainable network -- and
tests them by mechanism swap, not label swap. Its world is partially observed with costly probes and
non-commutative actions, so no closed form reaches the ceiling (the D1 death); its world family is
randomised in port semantics so the generator cannot be the status dial (the S0 death); held-out is
asserted non-identical and every table carries a capacity-matched mechanism-free baseline (the P6
death); CAS-Ohm enters only as a control law with independently grounded `V` and `R` (the identity
death); and a cardinality-matched non-CAS taxonomy is a registered arm from the start (the control
the whole program has never had -- note `RC0-16`: the existing "alternative taxonomy" is a relabelling
of CAS and must not be reused).

## 8. What could kill it at zero cost

1. Exhaustive search shows a fixed probe-then-act policy reaches the model-based-search ceiling
   under partial observability -- nothing for diagnosis to do.
2. The causal family cannot be randomised in port semantics without destroying the task -- the
   builder is authoring the answer.
3. The pre-training absorption test absorbs the typed controller -- ports and contracts were paint.
4. A linear / tree / kNN reader on raw observations or on provenance metadata reaches the ceiling.
5. Parameter and compute matching across M0-M7 cannot be made exact -- any gain is capacity.
6. The matched non-CAS taxonomy arm ties the CAS arm -- "typing helps" is all that is left.

## 9. Explicit statement

**No run, no spend and no claim was authorized by this reconstruction, and none was taken beyond
what the handoff itself instructed: local CPU numpy reproductions under two minutes each, and two
language-only audit calls on AWS Bedrock (est. USD 0.0308, receipted). No GPU was used, no neural
training occurred, no protected split was opened, no status was upgraded without an artifact, no
negative was deleted, and no committed file of the previous record was altered.**

## 10. Recommendation

```
DESIGN CJT-MECH-0, NO BUILD YET
```

with two conditions stated plainly: (1) the second-agent adversarial verification of this ledger
should be completed (one resumable workflow run) before any design detail is frozen, so the design
does not inherit an unverified extraction; (2) the owner rules on the question in section 6 first;
the brief is a draft and nothing in it is authorized.
