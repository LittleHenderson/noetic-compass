# WELD v2 adversarial audit

Audit basis: repository commit
`34442035c69e7feccd6c3b67447568776fe3528f`. This review does not alter WELD
v1/v2 and does not reinterpret their outputs as validation.

## Findings

### 1. The negative changes the tested algorithm — fatal for a fixed-pipeline claim

`Case` stores a caller-selected `localizer` at
`cas_weld_loop_v2.py:532-537`, and `run_case` dispatches it at line 595.
Positive cases select `localize_blind`, while NEG-3 selects
`localize_naive_lowest_min` at lines 733-757. The report confirms NEG-3's
`uses_real_detector` is `false` at `weld_v2_run_report.json:397-413`.

NEG-3 therefore proves that a different localizer can fail. It does not show a
negative outcome from the same frozen algorithm used for positives.

### 2. “Sealed” truth is accessible in the actor process — fatal for blindness

`FaultRecord` is an ordinary in-process object with public fields at
`cas_weld_loop_v2.py:344-359`. The actor-side `Case` also contains its expected
verdict at lines 532-537. `inspect.signature` checks at lines 491-502 constrain
formal parameters only; they do not constrain globals, closures, object
fields, imports, or filesystem reads.

The program later reads truth at line 628 and publishes it at line 675. Most
decisively, `tamper_check` reads the same ground truth and sends it to `repair`
at lines 770-812. This demonstrates accessibility, not sealing. Separate
process phases and external truth custody are required.

### 3. Rust runtime provenance is unbound — fatal for replay identity

The runner performs ambient `import cas_engine` at
`cas_weld_loop_v2.py:62`. It records no resolved extension path, binary hash,
package/runtime version evidence, `Cargo.lock` hash, or scanner-source hash.

The current machine exposes a concrete replay hazard: `pip show cas-engine`
reports editable package version `0.1.0` pointing to the older OneDrive
checkout; the module exposes no `__version__`. The isolated commit's
`Cargo.toml` says `0.1.1`. The installed `.pyd` SHA-256 is
`b7c60b9b6bd70e9e24acce734cf71ef100c90da8952d930731ce7d06a379ee0c`.
A module name is not a runtime identity.

### 4. Python duplicates Rust decision values — high drift risk

Python declares `SEVERITY_THRESHOLD = 0.05` and `SATISFACTION_FLOOR = 0.5` at
`cas_weld_loop_v2.py:82-83`. It uses the former to decide fired axes at line
214 and the latter to construct repairs at lines 332-333. The specification
admits the mirroring at `WELD_SPEC_V2.md:78-79`.

Even if a later verdict calls the Rust scanner, Python has already made
scientifically material classification/repair choices. The successor must
accept a closed final enum from one pinned Rust executable and keep numerical
decision rules out of Python.

### 5. The subset baseline is not a verdict-bearing matched control

The v2 controls enumerate or sample same-size repair subsets at
`cas_weld_loop_v2.py:415-470`. They operate beside the authored case, do not
receive an independently committed expected outcome, and cannot independently
fail the overall paired verdict. The report states that exactly one subset
clears the axis, yielding the transparent `1/C(7,k)` result
(`weld_v2_run_report.json:142-158`, `440-456`).

This is a useful combinatorial check. It is not an information-matched control
case passed through the same end-to-end pipeline.

### 6. No prospective immutable freeze separates specification from results

The directory contains the specification, runner, preregistered expectations,
stdout, and JSON report together. The specification narrates the observed
results (for example `WELD_SPEC_V2.md:208-270` and `326`). There is no prior
commit/WORM anchor, five-file input manifest, result-absence check, or runtime
binding that mechanically demonstrates freeze-before-result order.

### 7. It is not yet a model-facing capability test

The v2 specification itself marks J1, J2, and Stage 5 `ABSENT` at
`WELD_SPEC_V2.md:360-362` and says the loop establishes no efficacy. The
experiment is a transparent one-axis numeric construction. It cannot support
a claim about model reading, CAS compilation, epsilon realization, or
likelihood improvement.

## Audit verdict

WELD v2 may be described as a real engineered demonstration of its narrow
code path. It must not be described as validated, blind, fixed-pipeline,
runtime-replayable, or model-facing. The correct ceiling is:

`REAL / ENGINEERED / NOT_VALIDATED`

Gate 5 remains open. WELD v3 addresses the protocol defects but remains
`NOT_RUN`; it does not retroactively validate v2.

