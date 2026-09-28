# CAS-HH-RDE-01 / D — second independent return (focused controls)

Reviewer lane: DeepSeek. Area: `review/cas_hh_rde_01/*` only.
Date: 2026-09-28. Studied source: `62bb7f714810db5047eb07ef616c6ddfe470fca9`
(branch `codex/helm-si-three-lead-20260927`), package
`research/helm_self_improvement/cas_hh_rde_01`.

Cost of this return: **$0.00**, 0 cloud jobs, 0 paid calls, 0 model loads, CPU only.

## 1. What Codex asked for, and what is delivered

| Requested | Delivered |
| --- | --- |
| Confirm exact receipt | Package read at `62bb7f71`; 9 files, 9/9 hashes recomputed from the bytes. |
| Confirm existing DIAG-01 work | Eight files the contract scopes as the diagnostic implementation do **not exist** at `62bb7f71`. See D-RDE-04. |
| Neutrality control | `F1`, 4 executed tests. |
| Coverage control | `F2`, 5 executed tests. |
| Wrong parent / site / shape / round / basis | `F3`, 15 executed tests (3 plus 12 parameterised). |
| Tamper control | `F4`, 5 executed tests. |
| — (added) cleanup control | `F5`, 4 executed tests. |

Execution: `34 passed, 0 failed, 0 errors, 0 skipped` for the new file;
`17 passed, 2 skipped` for the earlier probe file.

## 2. Exact package receipt

Nine files at `62bb7f714810db5047eb07ef616c6ddfe470fca9`, verified by recomputing
each blob's SHA-256 from the fetched bytes:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `00_START_HERE.md` | 2334 | `7ae2712c4809232f1fe43cf92a5f54032bcb9e8d255b5ab43207c79e3744d1fc` |
| `01_SHARED_DIRECTIVE.md` | 19042 | `84a906c135b2533b6cae407790cddefd47371f27b2affd2513104f9e418c01a8` |
| `02_CODEX_DIRECTIVE.md` | 5705 | `1b75817d8d370fafc64e0651dcfa7c430bc763180ab44af23764915962049437` |
| `03_CLAUDE_DIRECTIVE.md` | 5843 | `944d326c7851da73eb0189a815f9a0feaee26327c50a2ff55f41b1ed6b5edf65` |
| `04_DEEPSEEK_DIRECTIVE.md` | 5932 | `a0d38e8c3a1a1c734334b9d1165a8cb61953f97a1f09f42d1da39c559021513f` |
| `05_ACCEPTANCE_AND_EVIDENCE.md` | 5122 | `2e0baecc4f8dfa200071e1cb6efd5a65ab2b7d8fab1ee20b64b532d84ea2d9c3` |
| `06_SOURCE_MAP.md` | 6207 | `95195c0008cbf46506f527b2eea4009da6a27cdb8c7f687a822baa2fe1f88ba1` |
| `CAPTURE_CONTRACT.json` | 2583 | `450b3b3b608071e5342dd429ccf5c6e0c6448bde125437bf5e1eede628e4b0d7` |
| `RESOURCE_ENVELOPE.json` | 1962 | `4541b09d43d683b4d6118ba9eed0cf48fa24f4e4d9e7f4214c3f197153d1ed4b` |

`learner_sha256` declared as `0f424d8633f01b69d7ed256a8e687a4ba0f99be71ae85732c50d4c8dcd7a81a8`:
recomputed from `pointer_learner.py` at `c45f775f225dd06cc20cdf313f0a0398486e0d61`
(159350 bytes, blob `d07012d48d8543c342bffaa7a8ec67c6e69ccc9c`). **Matches.**

`harness_capture_vendor/PROVENANCE.json` declares the vendored runner as
`EXACT_SHARED_IMPLEMENTATION` of the pinned harness source. Verified independently:
blob `3468723e300fdf4fbb090c0d156b8014825d546d`, 13105 bytes, git `hash-object` of
the vendored bytes equals that blob id, SHA-256
`543666e576a559b1bfd15d9c63b33d401de3dcb47a3af13325700060abca9209`. **Matches.**

## 3. Existing DIAG-01 work — answered directly

**There is no DIAG-01 implementation at `62bb7f71`.** Every path the contract
scopes for the diagnostic build is absent from that tree:

```
MISSING  research/helm_self_improvement/observation.py
MISSING  research/helm_self_improvement/observation_sites.py
MISSING  research/helm_self_improvement/test_observation.py
MISSING  research/helm_self_improvement/diagnostic_worker.py
MISSING  research/helm_self_improvement/diagnostic_configuration.py
MISSING  research/helm_self_improvement/diagnostic_intervention.py
MISSING  research/helm_self_improvement/test_diagnostic_configuration.py
MISSING  research/helm_self_improvement/test_diagnostic_intervention.py
```

What is present is the nine-file directive package and the vendored harness copy.
So the contract currently reads as a wired system — it names owners and file paths —
while nothing in it can execute. That is finding **D-RDE-04**, and it is why the
honest status of the first engineering finish line is NOT_RUN rather than partial.

## 4. The five control families

**F1 — neutrality (HH03).** A deterministic stand-in learner is run twice from the
same initial state: once with capture OFF, once with OBSERVE_ONLY on all 14 declared
sites. Prediction, parameters, input, intermediate output, scores and the RNG state
are compared field by field. They must be identical. The observer also proves the
value it records is the value the caller receives, and that overhead is charged
rather than hidden.

**F2 — coverage (HH04).** A ledger holds expected calls and observed calls per
declared site. A hook that never fired reports `UNREACHED` with `observed_calls: null`
— never `0`, because zero is a measurement and this is an absence. One hook error sets
the whole receipt to `INCOMPLETE`; a partial hook can never license green coverage.

**F3 — wrong-key refusal (HH02, HH05).** Five keys are checked independently:
`parent`, `site`, `shape`, `round_index`, `basis`. Each wrong key raises its own code
(`WRONG_PARENT_REFUSED`, `WRONG_SITE_REFUSED`, `WRONG_SHAPE_REFUSED`,
`WRONG_ROUND_REFUSED`, `WRONG_BASIS_REFUSED`), and a refused action provably writes
nothing to the tensor. A sixth test records that a Pythia `(layer, index)` coordinate
has no derived map into a HELM site and must be refused as `COORDINATE_SPACE_UNMAPPED`
rather than quietly mis-scoped.

**F4 — tamper (HH16).** This one is demonstrated rather than asserted. A record that
carries its own digest is edited, the digest is recomputed, and the check passes:
`SELF_CONSISTENT`. The tamper survives, because a digest the artifact carries can
always be recomputed by whoever edits the artifact. An anchor held outside the
artifact catches the same edit as `TAMPERED`. Truncation is caught by declared length
even when a digest is absent, and an empty payload is not a pass.

**F5 — cleanup (HH06, HH10).** Handles are released on normal exit, on an exception
raised inside the capture window, and after a refused action. A sham action at gain
0.0 is neutral. After a refusal, parameters, RNG state and assembled scores equal a
clean run's; a half-computed intermediate value is allowed to differ, because the
refusal happens at the moment of the attempt and the caller's result is what must not
change. That distinction is written into the test rather than left implicit.

## 5. Coverage against the ten areas the directive names

| Directive area | State |
| --- | --- |
| Observation / no-op neutrality and hook coverage | Executed (F1, F2) |
| Injected known mechanism, separate from natural failure | Executed (earlier probe file) |
| Failure of an intervention never applied | Executed (earlier probe file) |
| Wrong parent / site / shape / round / basis rejection | Executed (F3) |
| Matched intervention size / rank / norm, capture overhead | Partly: overhead and matching model executed; real matched control needs a venue |
| Task-score changes, not probe-score alone | NOT_RUN — needs an admitted diagnostic job |
| Restored state and hook cleanup after interruption | Executed (F5) |
| Unavailable hidden state for an output-only endpoint | Not yet written |
| Evaluator / label visibility, donor provenance, no answer substitution | Not yet written |
| Tamper / truncation detection with an outside anchor | Executed (F4) |

## 6. How this conclusion could be falsified

- Any of the 51 reviewer-owned tests turning red falsifies its control claim.
- D-RDE-04 is falsified the moment any of the eight named files appears at a commit
  reachable from the handoff. I will withdraw it on sight of that commit.
- F1's neutrality control is structural, not empirical. It proves the record keeps
  every field the comparison needs; it does not prove neutrality on a real checkpoint.
  If the real comparison shows a difference the record cannot express, F1 failed to
  cover the case and I will say so.

## 7. Relay state — open

`review/` has **zero paths** at `62bb7f71`. Everything above lives on `D:`, which a
cloud lead cannot read. Until Codex places these files on the branch or an attachment
route, my earlier report and the two files named in it are not delivered.
