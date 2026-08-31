# GATE 1A — Scope and Claim Boundary (FROZEN)

Anchor: Gate 0 frozen at `83f57d6f724505f2c2c68593b2625c36c3e07a4d`.
Branch: `research/cjt-gate1a-static-neural-v1`.
Status: Gate 1A = documentation and experiment freezing ONLY. Gate 1B (any neural
execution) requires the owner-signed phase-approval record.

## What this gate is

Gate 1A freezes the SMALLEST neural experiment that can answer a real, falsifiable
question — **CJT-T1, the Static Dual-Stream CJT Coupler** — before any GPU is
touched. Every architectural, data, control, threshold, and cost decision is frozen
here so that Gate 1B cannot drift, rescue, or retrofit.

## The one question Gate 1B will answer (v3 license law — Gate 1A.1)

> Does S3 (the coupled arm) beat **EVERY** control — S0 plain, S1 attention-only,
> S2 profile-only, S4 corrupted-label, S5 random-label, S6 matched-capacity, S7
> single-alternative-taxonomy — on protected data under identical conditions?

Interpretation table (frozen; no post-hoc rescue; the executable form is
THRESHOLDS_AND_STATUS_LAW.yaml v3's decision tree):

| Outcome | Reading |
|---|---|
| S3 fails the gate vs any of S0/S1/S2 | The plain, attention-only, or profile-only arm matched or beat the coupler. `COUPLER_NOT_SUPERIOR_TO_SIMPLER_ARMS`. Nothing licensed. |
| S3 beats simpler arms + S6, ties S7 | Generic semantic structure helped. Nothing licensed. |
| S3 beats simpler arms + S7, ties S6 | Extra architecture/capacity helped. Nothing licensed. |
| S3 beats shuffled/random only | A stable side channel may help. Nothing licensed. |
| S3 beats ALL SEVEN controls | `TASK_ALIGNED_LABEL_AUXILIARY_VALUE_LICENSED` — task-aligned construction-gold process labels added value beyond every registered control, in the four-Noetic restricted slice, static dense setting, on a task whose surface ceiling B1 = 1.00. NOT "CAS-specific" (prohibited on this dataset regardless of result). |
| S3 loses or ties broadly | Static CAS coupling NOT supported. Record it. Do not rescue it by changing metrics. |

## Restricted-slice law (naming discipline)

This experiment uses the FOUR currently governed construction-gold Noetic operation
classes: `^2` attraction/approach, `^3` aversion/withdrawal, `^6` decomposition,
`^8` triggering. It is a **four-Noetic restricted slice**. It is NOT a CAS-40 neural
system, NOT a full simplex demonstration, and may not be described as either unless
Domain labels are also produced by the same construction-gold process under
owner-approved rules.

## Honest ceilings (REQUIRED reading before interpreting any Gate 1B number)

Two structural facts bound what this experiment can ever show, disclosed here so no
result can outgrow them:

1. **Informational redundancy AND an exact surface ceiling.** The CAS stream `p_i`
   is a deterministic function of the clause text (the package's own independent
   checker recovers every label by regex, 100%, zero exclusions). `p_i` therefore
   adds ZERO information beyond the text; any S3 gain can only be an
   optimization/bottleneck effect of the frozen encoder — never new information.
   TWO registered surface baselines make this exact (owner audit section 6):
   **B0**, the class-blind co-occurrence floor (train `3867/6000 = 0.6445`, val
   `668/1000 = 0.6680`; attract/avert at the distractor-forced coin flip
   0.4805–0.5269; Q_PART/Q_TRIGGER near ceiling), and **B1**, the full
   deterministic surface-grammar parser reading only passage + question text —
   the TASK CEILING, measured at exactly `6000/6000 = 1.0000` on train and
   `1000/1000 = 1.0000` on val (`SURFACE_BASELINES_CANDIDATE.json`). The task is
   exactly surface-solvable BY CONSTRUCTION. A positive S3 result therefore means
   *task-aligned labels helped a frozen encoder reach a surface-computable
   function* — never that CAS supplied information absent from the language.
2. **S7 circularity limit — owner PATH A taken (Gate 1A.1).** The dataset's answer
   function is DEFINED over the CAS classes, so any task-aligned 4-class taxonomy
   is necessarily a near-relabeling of CAS (rejected by the orthogonality rule);
   every admissible S7 taxonomy is misaligned with the answer function by
   construction — and the registered S7's head verbs change across template
   families, making its labels unstable across splits (a recorded handicap).
   Consequently: S7 is renamed SINGLE_ALTERNATIVE_TAXONOMY (never "SCMPE-v1");
   the claim is renamed **TASK_ALIGNED_LABEL_AUXILIARY_VALUE**; and the words
   **"CAS-specific" are PROHIBITED on this dataset regardless of result**. A
   genuine CAS-specificity test requires PATH B — real SCMPE-v1 (≥1000 matched
   partitions) on a v2 dataset whose answer function is not class-bijective —
   deferred to a separate registration. PATH A is recorded as the working
   disposition consistent with the owner's audit framing of v1 as a bounded
   optimization/mechanism experiment; owner ratification is requested at signing.

## Claims frozen for Gate 1

- **Claim A (readable CAS structure):** a registered neural representation or
  adapter can use the four construction-gold CAS operation classes on held-out
  templates and vocabulary. Establishes decodability/usability ONLY.
- **Claim B — renamed TASK_ALIGNED_LABEL_AUXILIARY_VALUE (Gate 1A.1, owner PATH
  A):** the coupled architecture improves held-out task performance beyond the
  plain, attention-only, profile-only, corrupted-label, random-label,
  matched-capacity, AND single-alternative-taxonomy controls — all seven gates
  required (THRESHOLDS_AND_STATUS_LAW.yaml v3). It can NEVER license the words
  "CAS-specific" on this dataset, whatever the numbers.
- **Not active in Gate 1:** Claim C (causal steering/intervention utility), Claim D
  (learning speed, retention, selective plasticity), recursive RPM advantage, ASOM
  regulation advantage, CAS-Ohm compute efficiency, full CJT-Transformer capability.

## CAS-Ohm in Gate 1

For this static dense experiment: `I_total := 1`. Gate 1 measures relative routing
and coupling only; there is no instrumented variable absolute compute flow, so none
is claimed. This is NOT a permanent CAS-Ohm ban: CAS-Ohm adaptive-compute claims
begin at Gate 2, when the architecture has measured varying compute (expert
evaluations, branches, retrievals, generated tokens, tool calls, FLOPs, latency).

## Compute boundary

Gate 1A (now): allowed locally — documentation, schemas, hashing, deterministic
dataset generation, round-trip verification, manifest construction, tiny non-neural
unit tests. PROHIBITED — model loading, hidden-state extraction, training, GPU
experiments, protected-evaluation reads, claim promotion.

Gate 1B (after owner signature): ALL claim-bearing neural work on AWS GPU
(SageMaker/EC2; Bedrock prohibited for claim-bearing runs). No silent local CPU
fallback — fail closed `GPU_REQUIRED`. Every job records model, code, data,
container, seed, hardware, duration, output, and cost digests.

## Even a Gate 1B win is bounded

A Claim-B license from Gate 1B does NOT establish recursive advantage. Gate 2 must
compare the recursive CAS controller against a matched generic hierarchical
controller; if CAS does not beat that killer control, the honest conclusion is that
adaptive hierarchy helps and the CAS ontology is decorative.
