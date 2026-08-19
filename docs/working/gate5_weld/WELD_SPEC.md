# Gate-5 WELD — five CAS links driven as one machine

**Status of this document: v2, rewritten in response to an adversarial review that
found the v1 success criterion to be untestable.** Every v1 criterion is either
replaced or re-derived; §8 answers each review point individually and names what
changed in the code.

- Runnable loop: `docs/working/gate5_weld/cas_weld_loop.py`
- Machine-readable result: `docs/working/gate5_weld/weld_run_report.json`
  (`schema: cas_gate5_weld_loop.v2`)
- Captured stdout of the run this document reports:
  `docs/working/gate5_weld/weld_run_stdout.txt`

**Headline, stated before anything else.** This loop demonstrates **MECHANISM,
not EFFICACY**, and its measured status is **`MECHANISM_PARTIAL`**: every
preregistered criterion is satisfied by *some* injection, and **no single
injection satisfies all of them**. The specific blocker is named in §6.3. Nothing
in this document is a claim that the loop improves a model.

**Do not read the title as a validation claim.** The five links have *different*
validation status. Link 1 runs from an authored fixture unless `--with-readers`
is given; the J1 crosswalk is authored and has never been tested; the epsilon
bridge is REAL and PARTIAL (its stance-matched non-CAS control was never run).
See the REAL-vs-STUBBED table in §7.

---

## 1. The loop

```
STAGE 1  READ      model output text     -> circuit reading (12-part signal path)
JOINT J1           circuit reading       -> CAS expression the compiler consumes
STAGE 2  COMPILE   expression            -> CompilationArtifact (accept / reject)
STAGE 3  DIAGNOSE  perturbed object ONLY -> the NAMED broken axis          [BLIND]
STAGE 4  CORRECT   the DETECTED axis     -> corrected expression   (dispatcher)
JOINT J2           corrected expression  -> epsilon realization prefix
STAGE 5  MEASURE   prefix                -> likelihood shift   [--with-model only]
```

### Per-stage contract

| Stage | Consumes | Produces | Real module |
|---|---|---|---|
| 1 READ | output text (`real_outputs.jsonl`) | `CircuitReading(path[], main)` over the 12-part wiring vocabulary | `gate2_closure/independent_bank/l2_wiring.read_batch` (only under `--with-readers`) |
| J1 | `CircuitReading` **or** 40E cells named directly | drive-tagged state literals + binary transitions | adjudicated by `api.notation.compiler.compile_expression` |
| 2 COMPILE | expression string | `CompilationArtifact(.valid, .error, .result)` | `api.notation.compiler.compile_expression` |
| 3 DIAGNOSE | **the perturbed object alone** | a named axis, or nothing | `api.notation.compiler` (typecheck) + `belief.inversion_gate.run_inversion_scan` + `cas_engine.InversionScanner` |
| 4 CORRECT | the **detected** axis + the **localized** element | corrected expression | `api.notation.inversion.invert_expression` |
| J2 | corrected expression | epsilon realization prefix | `run_stage9_40e_eta_epsilon_bridge.readable_prefix` (40E) / `run_open_weight_eta_epsilon_bridge.readable_prefix` (F28) |
| 5 MEASURE | prefix + continuation | mean-logprob margin and deltas | `run_open_weight_eta_epsilon_bridge.mean_logprob_continuation` |

### Blindness invariants (enforced in code, asserted in the report)

1. **No detector is ever passed the injected axis.** `detect_blind()` has no
   `axis` parameter. Stage 4 is driven by `detection.detected_axis`; if detection
   names nothing, the chain **stops** — it does not fall back to ground truth.
2. **No detector's input contains the pre-injection object.** Every scan takes
   one object. The v1 concatenation `f"{clean_expr} {inj.inverted}"` is gone.
3. **Axis `P` is stripped from every "which axis was named" computation.**
   `axis_p_check` fires only because two other axes fired; it is a derived
   verdict, never an independent naming.

---

## 2. Joint J1 — circuit reading → compilable CAS

**What is REAL.** The emission mechanism and its adjudication. Every string J1
produces is handed to the real compiler, which accepts or rejects it. Arrows are
strictly binary in the grammar (`A -> B -> C` is rejected), so a path is emitted
as consecutive binary transitions.

**What is AUTHORED.** `COMPONENT_CROSSWALK` — 12 rows lifted out of the book's
prose and block-diagram listings (`Appendix_B_Component_Datasheets.md`,
`Appendix_D_CCB_Reference_Designs.md`) into a data structure for the first time.
It has **never been empirically validated**. The drive tag (`F5`) is also
authored: a reading carries no drive.

**The construct-smuggling surface, named plainly.** Under `--entry reading` a
PCBA component code *selects which validated 40E cell gets realized*. The
alphabet downstream is validated; the *choice* of cell is not, and PCBA component
types returned `NULL_ATLAS_V0` at pythia-1b and `GREY_ATLAS_V0_INSUFFICIENT_EVALUABLE`
at pythia-2.8b and gpt-neox-20b. Saying "a component code never becomes a
steering target" would be true only of the label's alphabet, not its content.

**Mitigation, not a disclaimer.** The default `--entry both` runs a second,
**construct-free** arm whose cells are named directly in the 40E space
(`--cells ^2^P,^6^C,^9^O`). In the run reported here the two arms reach
**identical criterion outcomes** on all three injections, so no conclusion in
this document depends on the falsified vocabulary.

---

## 3. Joint J2 — corrected expression → epsilon prefix

The choke point from the mapping brief: `condition_prefix()` accepts only
gold / probe / partner **labels**, and `readable_prefix(label)` raises
`ValueError` on an expression like `^3^P_{F5}`. J2 is the missing adapter:

```
compile the expression with the REAL compiler
  -> read the verdict off the artifact
     -> marshal into a flagship label space
        -> call the flagship realizer (verbatim flagship bytes)
```

**J2 routes by axis, because the two label spaces see different coordinates.**

| Corrected axis | Space | Label | Realizer |
|---|---|---|---|
| N, W, P | 40E | `^n\|D` from `dominant_operator` + `dominant_domain` | `run_stage9_40e_eta_epsilon_bridge.readable_prefix` |
| F | F28 | `Fk\|R` from `dominant_drive` + an authored register | `run_open_weight_eta_epsilon_bridge.readable_prefix` |

Routing is not decoration. **The 40E label does not carry the drive**, so
realizing an F-axis correction in 40E would be a silent no-op: corrected and
uncorrected prefixes would be byte-identical. Both spaces are validated label
spaces (40E: +1.412 mean-logprob delta at 20B; F28: the 6-point ladder).

**Relations have no 40E element.** A transition `A -> B` compiles to
`kind: relation`. J2 realizes its **target** state and records
`realized_from: "relation.target"`. A relation is not a 40E element and the
realizer was never designed to take one.

**Flagship bytes, not a reimplementation.** Neither flagship imports in this
checkout (transitive import `evaluate_probe_dataset` is absent from
`live-trace-worker/scripts/` — the directory holds `evaluate_40_element_probe.py`).
`load_flagship_symbols()` AST-extracts the named top-level symbols and executes
those bytes, pinned by sha256:

- 40E `run_stage9_40e_eta_epsilon_bridge.py` — `92e6fd525bb9e247ee04640ad3f2b95f07b7ae29c48784606cf37dc3f32cf8bf`
- F28 `run_open_weight_eta_epsilon_bridge.py` — `f52fbbe33ae28d08eeb932902a2be1d0ce209204ed57dece28b98b6bb5b76faa`

Extraction is name-matched, so a symbol defined twice at top level would silently
shadow the intended one. **Duplicates are now a hard error**, not last-wins.

---

## 4. THE PREREGISTERED SUCCESS CRITERION

An **injected** fault must satisfy every clause below. A clause that cannot
return `False` is not a criterion, so each one is stated together with the
concrete way it fails.

| # | Criterion | How it can fail (and does) |
|---|---|---|
| **a** | A **blind** detector names the injected axis, unambiguously, having never seen the axis and never seen the pre-injection object in its own input. | It fails whenever the perturbation leaves no co-presence and produces no compiler diagnostic. **Observed: the single-literal N injection is NOT detected.** |
| **a2** | Blind leave-one-out localizes the perturbed element (multi-element structures only). | Zero candidates, or more than one, are both failures. |
| **b** | The dispatcher, driven by the **detected** axis, restores the structure; it recompiles; and **no wrong axis also restores it**. | `f(f(x)) == x` is a theorem, so restoration alone proves nothing. The falsifiable half is the mis-correction control: if another axis also restored the structure, the axis *name* would carry no information. |
| **c1** | Both arms realize through J2 and the prefixes **differ**. | Fails as `c0_identical_prefix` when the realizer's space does not see the coordinate the correction changed (exactly what would happen if an F correction were realized in 40E). Degrades to `c2_uncorrected_unrealizable` when the injected form does not compile — **c2 does not count toward the headline.** |
| **d1** | No **wrong-axis** "correction" reproduces the true corrected prefix. | Fires when a wrong axis' transform *contains* the correct one. **Observed: axis `P` = N∘W∘F reproduces the F28 prefix, so d1 FAILS on the F injections.** |
| **d2** | An **exhaustive** sweep of the whole label space finds exactly one label reproducing the true prefix, and it is the true one. **The pool INCLUDES the true label** — that is the positive control. | Fails if the realizer is not injective, in which case any "corrected" structure would look right. |

**Loop-level status vocabulary**

- `MECHANISM_DEMONSTRATED` — at least one injection satisfies **a, a2, b, c1, d1, d2**.
- `MECHANISM_PARTIAL` — every criterion is satisfied by *some* injection, but no single injection satisfies all.
- `MECHANISM_INCOMPLETE` — some criterion is never satisfied.

**None of this is evidence of efficacy.** Efficacy requires stage 5 on a model
*plus* the stance-matched non-CAS control at the likelihood level (§5).

**Disclosure about the prereg itself.** The expected outcome of each injection was
established by probing the modules *before* this specification was frozen, and
each expectation is written into the script as
`preregistered_expectation` and printed at runtime. This is disclosed rather than
presented as a blind forecast.

---

## 5. Stage 5 — and the leak that governs how to read it

Stage 5 is `--with-model` only; the symbolic loop runs at zero GPU and zero API
cost. Three things about it are load-bearing.

**5.1 The 40E prefix contains its own scored continuation, verbatim.**
`readable_prefix` (`run_stage9_40e_eta_epsilon_bridge.py:668`) embeds
`- Readable meaning: {element_phrase(label)}`, and `element_phrase` is exactly
the continuation the flagship scores. A margin measured that way is partly string
copying. The loop **audits this at runtime** rather than asserting it
(`leak_audit`): 40E → `True`, F28 → `False` for all seven drives. This is
inherited from the flagship and **bears on how the +1.412 headline should be
read** — it is precisely what the never-run stance-matched control would have
exposed.

**5.2 Stage 5 therefore measures on the leak-free F28 arm.** The F28 prefix uses
`DRIVE_PREFIX_GLOSSES` while the scored continuation is `DRIVE_PHRASES`; there is
no verbatim containment. Lexical overlap is not zero and is not measured here.
The 40E arm is available but is **preregistered as not counting as evidence**.

**5.3 The stance-matched non-CAS control is now in the code.**
`stance_matched_control_prefix()` carries the same English content with every CAS
token removed. **Preregistered reading: if this control reproduces the lift, the
effect is English content, not CAS structure.** It is authored, and it is the
control the flagship never ran (spec-sheet NOT-LICENSED item 23).

**5.4 The v1 stage-5 wiring could not have run.** `ProbeShardConfig` has ten
required fields; v1 passed one, and `load_open_weight_model` returns a
**three**-tuple that v1 unpacked into two. Both are fixed. Stage 5 remains
**NOT RUN** in this report.

---

## 6. What the run actually did

Command: `python cas_weld_loop.py` (no `--with-model`, no `--with-readers`).
Exit 0. Three stubs declared, five disclosures recorded.

### 6.1 Detection — blind

| Injection | Structure | Blind detector that bit | Named |
|---|---|---|---|
| **F** on one bundle element | `^1^C_{F5} ^6^C_{F5} ^8^C_{F3} ^6^E_{F5} ^9^O_{F5}` | `run_inversion_scan` on the perturbed bundle **alone** | `F`, unambiguous |
| **N** on one isolated literal | `^9^C_{F5}` | *none* | **nothing** |
| **W** on a cross-domain transition | `^8^E_{F5} -> ^6^C_{F5}` | compiler typecheck → `DIAGNOSTIC_TO_AXIS` decode | `W`, unambiguous |
| **A** on the pathway array | `pathway[4] = [0.20,0.10,0.10,0.90]` | Rust `InversionScanner` | `['A']`, unaided |

Why the F detection is legitimate and not selection-on-outcome: J1 tags **every**
element with the same drive, so an F-flip on one element necessarily makes a
drive involution pair co-present. That is stated a priori from the construction,
not chosen after seeing a result. Leave-one-out then localized the perturbed
element **correctly** in both arms (index 2 in the reading arm, index 0 in the
construct-free arm).

The W target is selected by a rule fixed on the **reading** — *the first
transition whose two cells sit in different domain tiers* — never by pre-testing
which fault the typechecker would catch.

The axis-A detection is the one **genuinely unaided** detection in the loop:
given only the perturbed array, no hint, the Rust scanner returns exactly `['A']`
(resistance 0.857143 = 6/7, severity 1/7). It is also the one that cannot reach
J2.

### 6.2 The negative control fired

The single-literal N injection is **preregistered to fail** and does:
`run_inversion_scan('^9^C_{F5}')` returns clean, nothing is named, and the chain
**stops before correction**. This is included so the report contains criteria that
returned `False`. The v1 script could not produce a `False` anywhere.

The reason is structural and worth stating: **the string-plane detectors are
co-presence detectors.** A substitution inside one isolated object leaves nothing
to co-occur with.

### 6.3 The blocker — d1 fails on the only c1 injection

The F injection is the only one reaching mode `c1` (both arms realize, prefixes
differ: `F3|A` vs `F5|A`). It passes **a, a2, b, c1, d2** and **fails d1**:

> A `P`-axis "correction" of `^8^C_{F3}` yields `^9^E_{F5}` — wrong noetic, wrong
> domain, **right drive**. Realized into F28, which sees only the drive, it is
> byte-identical to the true correction.

This is a real limitation, not an artefact: **the epsilon realizers are lossy
projections of the expression**, so a prefix-level matched control cannot separate
corrections that agree on the projected coordinate. The strict criterion is kept;
a sub-analysis excluding axes whose transform *contains* the detected one is
reported as **explanation, not as the criterion**.

### 6.4 Criterion matrix (identical in both arms)

| Injection | a | a2 | b | c | d1 | d2 | verdict |
|---|---|---|---|---|---|---|---|
| F, bundle element | ✅ | ✅ | ✅ | ✅ `c1` | ❌ (`P`) | ✅ 1/28 | FAIL |
| N, isolated literal (negative control) | ❌ | – | ❌ | ❌ | – | – | FAIL (expected) |
| W, cross-domain transition | ✅ | – | ✅ | ✅ `c2` | ✅ | ✅ 1/40 | FAIL (c2 only) |

`criteria_satisfied_by_some_injection = {a:✅ b:✅ c1:✅ d1:✅ d2:✅}`,
`injections_passing_every_criterion = NONE` → **`MECHANISM_PARTIAL`**.

### 6.5 String-plane coverage — measured, not claimed

v1 asserted "5 of 7". The loop now **measures** it by probing each axis against
the shapes it actually emits:

- reading arm: `['N', 'F']` — **2 of 7**
- construct-free arm: `['W', 'F']` — **2 of 7**

matching the review's independent finding exactly. The reasons:

- **E and S are hardcoded placeholders** (`axis_e_check` / `axis_s_check` return
  `clean=True, placeholder=True`), so a "clean" verdict from `run_inversion_scan`
  is silently a five-axis verdict.
- **A is not a string detector at all.** `axis_a_check(rpm_satisfied)` is a bare
  `if/else` that restates its own argument. It has been **removed from the
  detector bank**; `rpm_satisfied` is now derived from the Rust scanner's verdict.
  v1's `diagnose_string_plane` also never passed `rpm_satisfied`, silently
  defaulting A clean on every scan — that is a third always-clean axis, now fixed
  by passing the argument explicitly everywhere.
- **W cannot fire on any drive-tagged literal.** `inversion_gate.py:72`
  `_DOMAIN_RE = r'\^([PCEO])\b'` — the `_` of `_{F5}` is a word character, so the
  `\b` never matches and `_extract_domains` returns `[]`. The loop reports both
  the drive-tagged scan (silent) and a **disclosed** drive-tag-stripped scan
  (fires `W`), and marks the stripped one `counts_toward_detection: false`. This
  is a genuine defect in `inversion_gate.py`, reported here rather than patched.
- **P is derived**, never an independent naming.

### 6.6 Live false-negative path in the primary detector

`axis_n_check` and `axis_f_check` treat any lowercase `x` as an integrator
(`inversion_gate.py:106`, `:187`) and suppress their flags. Any prose, identifier
or comment containing an `x` silently disables both. Every string this loop scans
is now run through `integrator_guard()` and the result is in the report. In this
run: no integrator characters present, no suppression.

---

## 7. REAL vs STUBBED

| # | Link | Status | What is real | What is not |
|---|---|---|---|---|
| 1 | **READ** text → circuit | **STUBBED by default** | `l2_wiring.read_batch` under `--with-readers`; vocabulary byte-checked against `l2_wiring.CODES` | Default run uses `FIXTURE_READING`, **authored**, not a disk replay — `l2_wiring_report.json` stores only aggregates, so no per-item path exists to replay. Its J1 rejection count (0/4) is a property of the authored path, **not an observed outcome**. |
| J1 | reading → CAS expression | **REAL mechanism, AUTHORED table** | emission adjudicated by the real compiler | `COMPONENT_CROSSWALK` (book prose, zero empirical support); the `F5` drive tag |
| 2 | **COMPILE** | **REAL** | `compile_expression`, engine `rust+python` | — |
| 3 | **DIAGNOSE** | **REAL, and blind** | compiler typecheck + `run_inversion_scan` + Rust `InversionScanner` | effective string coverage is 2/7; E/S can never fire; W can't fire on drive-tagged literals |
| 4 | **CORRECT** | **REAL for N/W/F/P; ABSENT for E/S/A** | `invert_expression`, driven by the *detected* axis | E/S/A raise `DeferredAxisError` — **no string corrector exists to dispatch to**. Axis A is correctable on the numeric plane only, and that correction is a **hand-written re-scoring**, not a solver output. |
| J2 | corrected expr → epsilon prefix | **REAL** | flagship bytes, sha256-pinned, dual-space routing | register (`|A`) is authored; relations realize their *target*, which is a projection |
| 5 | **MEASURE** | **NOT RUN** | code path constructs `ProbeShardConfig` correctly and calls the real `mean_logprob_continuation` | needs a GPU/pod; the 40E arm carries a verbatim continuation leak; the stance-matched non-CAS control has never been run at any scale |

Loud stubs emitted at runtime (also in `report.stubs`): STAGE 1 reader call;
STAGE 4 corrector for axes A/E/S; STAGE 5 likelihood measurement.

Disclosures recorded (`report.disclosures`): authored fixture reading;
component construct in the causal path; `axis_a_check` is not a detector;
axis-A correction is hand-written; the F28 gloss table disagrees with `CLAUDE.md`
(it maps F5 to *"ordered form … reliable structure"* while `CLAUDE.md` names F5
Agency and F6 Structure — flagship bytes are executed verbatim, so this is
reported, not silently corrected).

---

## 8. Adversarial review response

Every finding, and what changed.

### FATAL

**(d) The matched control could not fail.** Correct, and worse than stated: v1
drew from `pool = [c for c in ALL_40E if c != true_cell]` and counted prefix
equality, so `epsilon_match_count == 0` was an algebraic identity and the
reported `chance_rate_1_over_39` was never the null. **Removed entirely.**
Replaced by two controls that can and do fire: **d1** wrong-axis (fires on `P`,
observed) and **d2** an exhaustive sweep whose pool **includes** the true label
and reports a positive control (`positive_control_true_label_reproduces: true`,
1/40 and 1/28 observed). The field `chance_rate_1_over_39` no longer exists in
the report, and `report.removed_in_v2` names the deletion.

**(a) for axis N — the detector was handed the answer.** Correct. The
concatenation `f"{clean_expr} {inj.inverted}"` is **deleted**. Detection now
scans the perturbed object alone. The consequence is exactly what the review
predicted: `run_inversion_scan('^9^C_{F5}')` names nothing, so the N injection is
now a **preregistered negative control that fails (a)**. The MECHANISM headline no
longer rests on it — the surviving detections are F (co-presence in a
uniform-drive bundle) and W (compiler diagnostic).

**(a) for axis W — the axis name was hardcoded.** Correct: v1 executed
`detected_axis = axis`. **Deleted.** The compiler's message is now decoded through
a published table, `DIAGNOSTIC_TO_AXIS`, keyed on the diagnostic *text*
(`domain descent violated`, `reverse dependency violated`,
`bidirectional relation requires matching domains` → `W`; everything else → no
axis), sourced from `compiler.py:3378-3390`. The table decodes the detector's own
message and never sees the injection parameter. The `\b` defect that makes the W
*string* detector structurally unable to fire on drive-tagged literals is
confirmed, reported, and the workaround is labelled and excluded from the
detection verdict.

**The pipeline was not chained; (b) was an involution identity.** Correct on both
counts. Stage 4 now takes `detection.detected_axis`; when nothing is named the
chain **stops** and prints why. `f(f(x)) == x` is acknowledged in the docstring as
a theorem that proves nothing on its own, and (b) now additionally requires the
**mis-correction control**: no other implemented axis may restore the structure.
Observed: zero wrong axes restore, in both arms.

**"No criterion could return False."** Answered by construction: the report now
contains `a=False`, `b=False`, `c=False`, `d1=False` on real injections, and the
loop-level verdict is `MECHANISM_PARTIAL` rather than a pass.

### MAJOR

- **`axis_a_check(False)` is a pass-through.** Agreed. **Removed from the
  detector bank** and disclosed as `axis_a_check_is_not_a_detector`. The Rust
  `InversionScanner` axis-A detection — the one honest detection, as the review
  noted — is kept and elevated, and `rpm_satisfied` is now *derived* from it.
- **The W injection was selected by pre-testing detectability.** Agreed. The
  selection rule is now a property of the reading: *the first transition whose
  two cells sit in different domain tiers.* Detectability is never consulted.
- **"5 of 7" string coverage was wrong.** Agreed. Replaced by a runtime
  measurement: **2 of 7** in both arms, matching the review. `rpm_satisfied` is
  now passed explicitly everywhere so axis A is no longer silently defaulted
  clean.
- **Smuggled construct.** Agreed, and stated in §2 in the review's own terms: a
  component code *does* pick the cell. Added a construct-free arm, run by default,
  which reproduces every criterion outcome — so no conclusion depends on the
  falsified vocabulary.
- **Stage 5 could not run.** Agreed. All ten required `ProbeShardConfig` fields
  are now supplied, and the three-tuple return of `load_open_weight_model` is
  unpacked correctly. Still NOT RUN (needs a pod).
- **Stage 5's criterion was satisfiable by verbatim copying.** Agreed, and the
  loop now **audits it at runtime** instead of understating it: the 40E prefix
  contains its scored continuation (`True`), F28 does not (`False`). Stage 5
  measures on F28 and the stance-matched non-CAS control is implemented. §5.1
  states the bearing on the +1.412 headline.
- **Claim creep in the title/header.** Agreed. Both now read "five CAS links",
  with the differing validation status stated in the same breath and the
  REAL-vs-STUBBED table linked.
- **The "useful negative" rested on the same trick.** Agreed. The
  concatenation-based detector-clean statistic is **deleted**, not reinterpreted.

### MINOR

- `detected_axis or fired[0]` first-wins is gone: candidates are a **set**, and
  more than one non-derived candidate sets `ambiguous: true`, which fails (a).
- Sampling with replacement is gone: d2 is an **exhaustive, deterministic** sweep
  with no seed.
- The authored fixture is disclosed as authored, and its 0-rejection J1 outcome is
  explicitly labelled a property of the authored choice.
- The `'x'`-as-integrator false-negative path is guarded on every scanned string
  and reported (`integrator_guard`).
- `load_flagship_symbols` now **hard-errors on duplicate top-level symbols**, so
  name-matched extraction cannot silently shadow. Both flagship sha256s are
  pinned in the report; the missing `evaluate_probe_dataset` import is confirmed
  and is the stated reason for AST extraction.
- The bogus null field name is gone from the report schema (`v1` → `v2`).

---

## 9. What is still missing

1. **A string-level corrector for axis A** — the axis the loop most needs.
   `invert_expression(src, 'A')` raises `DeferredAxisError`, so axis A can be
   detected (genuinely, unaided) and corrected numerically by hand, but never
   reaches J2. E and S have neither a corrector nor a detector.
2. **A prefix-level control that survives lossy realization.** d1 fails because
   the realizers project the expression onto one coordinate pair. Closing this
   needs either a realizer that carries more of the expression, or a control
   defined on the expression rather than on the prefix.
3. **Stage 5 on a pod**, with the stance-matched non-CAS control. Until then the
   loop says nothing about efficacy.
4. **A validated component→Noetic crosswalk**, or the abandonment of the
   component entry. Today it is book prose in a Python dict.
5. **The return leg.** Nothing turns a named axis back into a component-level
   repair instruction in the reading's own vocabulary.
6. **`inversion_gate.py:72`** — the `\b` in `_DOMAIN_RE` disables axis W for every
   drive-tagged expression in the repository, not just in this loop.
