# SOURCE AUDIT

Read status is honest. "Existence-confirmed" means the file is on disk
(checked this session). "Read first-hand" means I read the content this
session. "Carried" means the constraints below come from a secondary
source (the spec sheet, the directive, or memory), NOT from reading the
primary this session — and must be re-read before the phase that relies
on them.

## Source hierarchy

| # | Path | Role | Status this session |
|---|------|------|---------------------|
| 1 | `cas_only_reasoner/cas_reasoner.txt` | Project authority / capability boundary | Existence-confirmed. NOT read first-hand. Read before Phase 1. |
| 2 | `cas_only_reasoner/ETA_EPSILON_BRIDGE_v1.md` | Formal/empirical/proposed separation | Read first-hand (authored this session). |
| 3 | `docs/whitepapers/monograph/noetic_topos2/chapters/ch05_legacy_collapse.tex` | Formal section-retraction ONLY | Read first-hand (verbatim). |
| 4 | `cas_only_reasoner/RESEARCH_PAPER_CAS_OHM_1_0_v0.2.pdf` (293,406 bytes) | Neural response-model + calibration limits | Existence-confirmed. NOT read first-hand this session. Read before Phase 5. |
| 5 | `cas_only_reasoner/CAS_Ohm_Quantification_Guide-1.pdf` (2,610,388 bytes) | Design vocabulary + diagnostic workflow | Existence-confirmed. NOT read first-hand this session. Read before Phase 5. |
| 6 | code, raw outputs, manifests, test receipts | Empirical status source of truth | To be produced per phase. |

## Constraints carried from sources 4 and 5 (verify first-hand before Phase 5)

These come from `docs/CAS_HARNESS_SPEC_SHEET.md` and the owner directive,
not from re-reading the PDFs this session:

- CAS-Ohm is a profile-specific response PROPOSAL. Not physical Ohm's
  law. Not an attention measure. Not a causal law.
- The response equation `y_hat = a / r_eff` is admissible only after
  calibration WITH uncertainty and evaluation on a DISJOINT held-out
  split. Deriving `r = a/y` from a sample and testing on that same
  sample is circular and rejected.
- A residual can rank follow-up probes. It cannot prove a hidden cause,
  resistance, bypass, or policy from its sign alone.
- Flow and produced effect must not be collapsed. A correct flow reading
  with a wrong effect points to bias, gain, saturation, breakdown, or
  semantic-transformation fault.
- CAS-Ohm numbers are design scores / calibrated values / observed
  ratings, not direct "voltmeter readings." Cause and Drive are separate
  roles.

## Status of the CAS-Ohm instrument in the repository (carried)

- Described as OPTIONAL instrumentation OUTSIDE the reasoning loop.
- No board imports it. Source synthetic. NO live model measured.
- Therefore the weight-learning work here is a NEW neural experiment,
  not activation of an existing capability.

## Conflict rule

When sources conflict: preserve the conflict, state which source governs
which question, do not silently harmonize.
