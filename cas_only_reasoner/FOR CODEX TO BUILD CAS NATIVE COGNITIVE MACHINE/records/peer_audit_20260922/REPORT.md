# Independent audit of the parallel CAS work

**The fixes and published test counts reproduce, but the self-correction list is
incomplete.** The merge left four additional passing tests deleted. The legacy
CAS-Ohm module still emits invalid arithmetic and misleading classifications.
The book has unresolved rules and an unsupported numerical observation claim.

This report audits **`626cc84b574e60217a103b72d2f09388d7aa5e34`** on
`research/helm-3.0-cas-lab`, including its merge and both numeric-hardening commits.
It does not substitute the older HEAD stated in parts of the package. The original
worktree was clean at entry and remained untouched; its local and remote heads
still matched this audited commit at the closing check. Work was performed in
the isolated `codex/helm-peer-audit-20260922` branch.

The review uses three independent areas plus a separate package/test reproduction
check. Git objects, raw command results and negative probes are retained here.
Production code, books, owner decisions and original receipts were not changed.
No model, inference, training, GPU computation or cloud job ran in this audit.

## Findings requiring action

### 1. P1 — An invalid tolerance produces a false successful classification

At `noetic-compass-scaffold/noetic-compass/api/cas_ohm/quantifiers.py:386`,
`delta_current(100, 0, tolerance=float('nan'))` returns a residual of `100.0`
with **`WITHIN_TOLERANCE`**. The comparisons with NaN both fail and execution
falls into the successful-looking default. Validate finite inputs, tolerance
and the subtraction result before assigning a sign.

The original package already disclosed a NaN prediction producing this sign.
The tolerance route is an additional unreported entry point. This is an inherited
defect left open by the September hardening, not a newly introduced regression.
The module is a declared prototype; no actual downstream model/control incident
is claimed. Evidence: `ohm/FINDINGS.md` OHM-A1 and `ohm/boundary_failures.txt`.

### 2. P2 — The numeric hardening does not check calculation results

At `quantifiers.py:317`, **finite** inputs `i_pred(1e308, 1e-308)` return `inf`.
At `:572`, `r_hidden(1e308, 0.1, 2)` emits uncensored infinite apparent resistance
and magnitude. Subtraction can overflow too. The sum-overflow guard in `r_total`
does not cover these paths. Check results and refuse or explicitly censor
unrepresentable quantities. These inherited defects are reproduced before and
after both fixes. Evidence: OHM-A2, source identities and all outcomes in
`ohm/results.json`.

### 3. P2 — Interval mode can bypass the zero-denominator guard

At `quantifiers.py:521–572`, `r_hidden(8, 0, 2, i_obs_interval=(1, 2))` raises
**`ZeroDivisionError`**. Reversed intervals also pass. The interval path must
validate ordered bounds, compatibility with the supplied point and the actual
division denominator. Invalid observations should produce an intentional
refusal/censored record. This does not license clipping valid small positive
values; a valid small-positive-interval control succeeds. Evidence: OHM-A3.

### 4. P2 — “Exact” numeric records are not consistently exact

At `quantifiers.py:735–745`, `admissible_trend` converts supported Decimal inputs
to float despite promising exact comparisons. Two valid separated intervals
near 1.0 collapse to the same float and produce `NO_TREND` instead of `RISING`.
At `:664`, a Decimal immediately below 2.5 is classified Q1 but serialized as
`i_q_exact='2.5'`; replaying that saved value produces Q2. Preserve the value
actually used for classification and avoid unreported rounding. Evidence:
OHM-A5/A6 and the full executable Decimal examples in
`ohm/contract_boundary_probes.py`.

The companion OHM report also records malformed trend intervals, mismatched rule
labels, invalid band/inversion inputs, and qualified observations about callers
supplying values outside the API's declared types. Those are kept separate from
the valid-typed-input failures above. No external ingestion path is asserted.

### 5. P2 — Four more passing regression tests remain deleted

The merge removed four functions from
`tests/test_notation_compiler_nesting_and_defects.py`, in addition to the three
help-text guards already disclosed and restored. The missing tests cover:

- Serialization of the error for a 1,000-term flat chain.
- Allowed function names, including `fn Noetics`, versus reserved bindings.
- Avoiding a false cross-Domain warning through a same-Domain function call.
- Avoiding the alias warning when `Worlds` is an emergent-result label.

**All four original bodies pass at both the merge and frozen head: 8/8
invocations.** Current tests only partly overlap their assertions. Restore the
four tests intentionally. This is a confirmed loss of protection, not a claim
that the protected compiler behavior currently fails. Full parent-path union:
zero missing files; keeping every filename did not preserve every test body.
Evidence: `merge/REPORT.md`, exact original sources and `merge/merge_results.json`.

### 6. P2 — The pinned book does not provide one component rule

`Appendix_B_Component_Datasheets.md:59` makes an involution flip conditional on
an explicit breakdown rule. `Appendix_A_Notation_Quick_Reference.md:40/:121`
and `Appendix_C_CCDL_Language_Reference.md:549` still make that flip automatic.
The new conditional wording was not reconciled with the old rule.

Likewise, Appendix C:447 allows two or more inputs for XOR/XNOR, while Chapter
10:115–116 and Appendix B:389–390 specify two. Three-input parity and
“exactly one” are different predicates. Resolve the rule or publish precedence
before treating either interpretation as uniquely canonical. These findings
are separate from the two already-disclosed CJT/op-amp sentences.
Evidence: BOOK-AUDIT-1/2 in `book/findings.json`.

### 7. P2 — A book example labels an incorrect approximation as observed

`Chapter_16_Feedback_Systems.md:211` calls the gain exactly 3 and “observed,”
independent of whether forward gain is 12 or 10. Its own finite-gain formula
`A/(1+A*beta)` with `A=12`, `beta=0.333` gives **2.401921537229784**; at
`A=10` it gives **2.3094688221709005**. Including the displayed 1.5 stage also
does not give 3. The claim of drift immunity is not supported at these values.

This passage predates the audited changes and is byte-unchanged by OD-A; it is
not an agent-introduced regression. Label a limiting design approximation as
such, use the finite formula for the example and require an actual measurement
record before calling it observed. Evidence: BOOK-AUDIT-3 and the independently
computed rational values in `book/book_probe.json`.

### 8. P2/P3 — Reproduction instructions still contradict the corrections

`03_REPRODUCE.md` still gives 458 compiler tests, 48 Ohm tests and the withdrawn
demo/compiler comparison, while current results are 639 and 51 and the demo
files were the changing variable. OHM-4 says to combine **HEAD's** tests with old
code and expect 42/48. That result requires tests pinned to `86ba3d75`; current
tests with old code produce **44/51**. Pin implementation and test revisions
separately and synchronize the recipe with the correction.

GOV-3 also points to the wrong refusal document. The real paragraph is in
`CODEX_CONTINUATION_20260921.md:53–55`, not `VERIFICATION.md`. The refusal exists;
the citation is wrong. Original owner-chat authenticity and an unretained
intermediate book copy cannot be established from agent-written records alone.

The package's absence claims require branch scope. Its frozen compiler has no
Ohm operations and its frozen tree has no PCBA reader. The parallel
`eb9985566bd11a89f485d627186ef0efa7177f02` branch already has both. This audit
executed its declared board-to-compiler example: parse PASS, structure PASS,
exact result **3/1**, **NO_MEASUREMENT_PERFORMED**. That branch uses a different
`api/notation/cas_ohm.py` helper; the legacy module reviewed above is not thereby
integrated or validated. Do not rebuild completed work based on a project-wide
reading of a frozen branch's absence statement. See `parallel_branch_result.json`.

## What reproduced correctly

- **639 compiler cases passed**, including 454 help/canon cases; the original
  99-case compiler test file is byte-unchanged. One disabled-plugin configuration
  warning (`asyncio_mode`) remains; it is not a failed test.
- **348 lab cases passed** in the complete isolated checkout.
- Original CAS-Ohm suites reproduce **39/39, 48/48 and 51/51** at their exact
  revisions. First-fix tests against old code reproduce the six intended
  failures; current tests against old code reproduce seven.
- The restored historical help guards run successfully against byte-verified
  merged help text: **454 checks**, reported separately, not added to the
  current-suite count. The four additional missing guards pass **8** invocations.
- All **125 historical manifest hashes**, **19 current file identities**,
  **8 packaged before/after copies**, and **8 cross-repository canon files**
  match. The true book diff is **202 insertions / 95 deletions**; listing counts
  are **58 blocks / 42 names**.
- The corrected compiler comparison and actual withdrawal of content-based set
  identity reproduce. No additional lost production compiler behavior was
  established by the complete merge diff and targeted probes.

The deliberately independent boundary demonstration gives **7 failures and
1 error in 8 tests**. These are retained failures, not passing checks. All 50
numeric probe outcomes match the original August module as well as the pre-fix
September state, so their attribution is inherited, missed hardening.

## Answers to the audit package's three questions

1. **Is the mistake list complete? No.** The remaining deleted tests, numeric
   paths and additional book conflicts are not all in it.
2. **Are some claims stronger than the evidence? Yes.** Passing selected tests
   does not close all numeric boundaries. Reproduction prose remains stale.
   “No model ever ran,” “never pushed,” pre-merge execution timing and original
   owner identity cannot be proven from the local artifacts reviewed here.
   No evidence of misconduct or a new neural run was found or inferred.
3. **Can calculated values be mistaken for measured values? Yes, in the book
   wording above.** The module itself explicitly labels its examples fabricated
   and its status unvalidated. Its primitive scalar outputs also require the
   consumer to retain provenance; no measured Helm result is established.

`CLAIM_VERDICTS.json` covers every one of the **33 claims**: **26 REPRODUCES,
1 FALSE as written for the current reproduction command, 1 OVERSTATED,
5 UNVERIFIABLE at full stated strength**. “Reproduces” is bounded by revision
and tested cases. “Unverifiable” does not mean false. Neither is a scientific
acceptance label.

## Exact commands, failures and next step

See `REPRODUCE.md` for commands and environment. The first sparse checkout
omitted two help sources (339 cases instead of 639) and the lab export schema
(342 passes / 6 setup-dependent failures). One attempted sparse-path correction
was relative to the wrong working directory and reproduced the same six failures.
After materializing the exact committed inputs from the repository root, the
complete suites passed. All initial XML reports remain. These were audit setup
errors, not attributed to the other agent's implementation.

The next diagnostic command, from this audit CN directory, is:

```powershell
& 'C:\Python314\python.exe' -B records/peer_audit_20260922/ohm/contract_boundary_probes.py
```

It intentionally exits **1** against the frozen source and names the remaining
failures. Source fixes should happen in an owning implementation branch with
these cases converted into regressions. This audit does not merge divergent
branches, change book semantics or silently fix the evidence being reviewed.
