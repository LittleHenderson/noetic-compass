# PREREGISTRATION v0.3B — CANDIDATE (append-only amendment to v0.3A)

Status: **CANDIDATE — AWAITING OWNER APPROVAL.** Documentation only. No model, no GPU,
no run, no claim ledger change.

## What this document is

`PREREGISTRATION_v0_3A.md` is the governing preregistration. Its Section 1 contains the
old label rule ("No LLM assigns claim-bearing labels. A human labels each sense.
>= 240 distinct verb senses."). The owner amended that rule on 2026-08-30. A lower-level
label document cannot silently override the preregistration, so this file records the
amendment **append-only**:

- `PREREGISTRATION_v0_3A.md` is NOT modified. Its content at the time of this amendment
  has SHA-256 (line endings normalized to LF):
  `39cb1cdd08929699c30ea7e8104a2d1d5a57d55789ab5f0db304afad51941df4`
- Everything in v0.3A stays in force EXCEPT the parts this amendment names.
- This candidate becomes the governing text only when the owner approves it.

## Amendment 1 — label authority (replaces v0.3A §1's label protocol)

OLD (v0.3A): "No LLM assigns claim-bearing labels. A human labels each sense."

NEW (owner amendment, 2026-08-30): **"No LLM OUTPUT ALONE has claim-bearing label
authority."** The owner approves rules and audits a blinded sample. The owner does NOT
label the full inventory.

Authority classes and flow (full spec: `labels/LABEL_AUTHORITY_SPEC_v1.md`):

```
RESOURCE_RULE_DERIVED   --owner audit + signed promotion-->  RESOURCE_GOLD
CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD
MODEL_PROPOSED / WEAK_LABEL / ABSTAIN / CONTROLLED_TEMPLATE_FIXTURE : never claim-bearing
```

- A deterministic engine emits candidates only. Determinism freezes a judgment; it does
  not validate the judgment. No deterministic labeling engine may promote its own output
  to gold.
- Gold exists only via `labels/owner_gated_promotion.py`: owner-signed approval (key held
  outside the agent environment) + audit receipt (sequential gate: 0 major errors PASS;
  1–2 repair-and-resample; 3+ reject) + matching digests.
- Model consensus grants no authority; agreement changes audit priority only.

## Amendment 2 — Tier A uses CAS-trace ground truth by construction

Tier A does not begin with 240 natural-language word senses. It begins with formal CAS
records whose labels exist before any English is produced:

```
CAS state or CNCM trace -> CAS-Sem graph -> controlled language realization
-> optional AI paraphrase -> preservation checks -> frozen evaluation item
```

Full spec: `labels/CAS_TRACE_GOLD_SPEC_v1.md`. The Phase 0B template generator is retired
from evaluation (`CONTROLLED_TEMPLATE_FIXTURE`) because its generator and round-trip
checker shared one verb-to-class lookup (circular). The new design requires an
INDEPENDENTLY IMPLEMENTED preservation check, shared vocabulary across classes, held-out
templates and vocabulary, and surface-matched minimal pairs, so the label comes from the
underlying trace, not the spelling.

## Amendment 3 — Tier B labels are candidates until promoted

Tier B (natural-language transfer) uses a frozen machine-readable lexical resource. The
deterministic engine emits `RESOURCE_RULE_DERIVED` candidates. Only after the owner's
blinded risk-based audit (~48 visible judgments + all high-risk items, per
`labels/OWNER_AUDIT_PROTOCOL.md`) and a signed dataset approval does
`RESOURCE_RULE_DERIVED -> RESOURCE_GOLD` happen, via the promotion program.

The ">= 240 senses" quota of v0.3A §1 is subordinated to the ABSTAIN discipline: build all
clean candidates first, run a development-only pilot, run a power calculation, freeze the
final balanced sample size before protected data or hidden-state results are opened. If
the smallest class cannot supply the frozen minimum cleanly: `INSUFFICIENT_CLEAN_LABEL_COVERAGE`.

## Unchanged from v0.3A

Splits grouped by sense; the baseline family; fixed balanced random partitions; SCMPE-v1
(now parameterized in `labels/SCMPE_GENERATION_SPEC.md`, tolerances owner-to-freeze);
independent layer selection; >= 10 seeds + group bootstrap; Claims A/B/C/D separation
(only B licenses "CAS-specific"); the second-stage utility test pre-registered not
executed; the GPU-first/cloud-first compute law; the governance rules (owner-signed phase
gate, deterministic claim promotion, Claude is NOT the research governor).

## STOP

No claim-bearing work begins until the owner approves this candidate and signs a phase-0
record.
