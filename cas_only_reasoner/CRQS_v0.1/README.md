# CRQS v0.1 — CAS Reasoning Qualification Standard

The qualification bench for any custom board or Mind. Four questions,
five outputs: how difficult was the test (TDG), what level of
reasoning was demonstrated (CAS-G), how strong is the evidence
(E-Tier), what to repair to reach the next level - plus deployment
authority (A-Level), which is computed separately because capability
is not permission. Reference-model comparison (RMB) stays separate
from the native grade and is NOT RUN by default.

## Run

    cd cas_only_reasoner/CRQS_v0.1
    python -m pytest      # 19 tests
    python run_demo.py    # qualify three Minds: cas-rr, kernel, CNCM

## The rules

- TDG: nine difficulty axes 0..4, DI 0..36, D0-D10 banding, with HARD
  FLOORS - a recursive task cannot be graded below D6, learning with
  held-out transfer cannot be below D8, self-modification cannot be
  below D9, novel research is D10. A beautiful DI cannot mislabel a
  recursive task as simple.
- CAS-G0..CAS-G10 (+CAS-GΩ, a research designation): strictly
  sequential - a level requires EVERY lower level.
- Three levels, never one average: Design Ceiling (topology),
  Demonstrated Level (tests, stable vs peak), Qualified Level =
  min(ceiling, demonstrated, evidence ceiling).
- E-Tiers: E0 Claimed through E6 Independently Replicated. A-Levels:
  A0 through A5. Reports combine: CAS-G6 / E5 / A0.
- Mandatory gates: seven zero-tolerance violations (authority,
  untraced mutations, invalid conclusions, branch leakage, RPM
  corruption, unsealed transitions, replay divergence) plus
  performance gates. Precision and coverage always appear together -
  answering UNKNOWN to everything scores zero.
- The Capability Vector: twelve dimensions 0.0-5.0; domain skills
  (English, mathematics, ...) reported separately.
- The repair ontology: fourteen failure signatures, and the mandated
  repair order (safety first, speed last).

## The honest result it produces for OUR machine

The assembled CNCM qualifies at CAS-G8 / E5 / A0 (design ceiling
CAS-G9). The G7 gate was cleared by CCB-T1 (typed tool intents, the
typed fault suite, adversarial variants); the G8 gate by the RLP
qualification suite (correction retention, delayed retention across
intervening work, structural transfer of a learned strategy to an
unseen fault of the same class, protected regression, and a
digest-identical stability run that earns the STABLE D8 flag). Peak
demonstrated D9 remains gated as not stable. The report derives the
next upgrade from the manifest itself: the CAS-G9 suite
(self-diagnosis, sandbox, reject-unauthorized, promote, parent
replay) plus a stable D9 demonstration. That is the standard working
as designed: no topology medals, and the next upgrade named
precisely.

## Layout

    spec/CRQS_SPEC_v0.1.md   20-chapter standard
    crqs/difficulty.py        axes, DI, banding, hard floors
    crqs/generations.py       CAS-G0..G10..GΩ
    crqs/vector.py            twelve-dimension capability vector
    crqs/evidence.py          E0-E6 tiers and evidence ceilings
    crqs/authority.py         A0-A5
    crqs/gates.py             hard and performance gates
    crqs/repair.py            failure signatures and repair ordering
    crqs/qualify.py           manifest -> the five outputs
    crqs/report.py            the section-10 report format
    crqs/workflow.py          the fifteen-step QUALIFY workflow
    fixtures/                 manifests for cas-rr, kernel, CNCM
    tests/                    19 tests
