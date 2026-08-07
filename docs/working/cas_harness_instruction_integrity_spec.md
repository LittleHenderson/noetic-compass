# CAS Harness Instruction Integrity Shadow Specification

Date: 2026-07-29
Status: local product-development increment; shadow evidence only

## Purpose and lineage

This increment brings the previously verified branch-only Instruction
Integrity scanner, its clean/injected/control benchmark, and its Evidence
Packet field into the current CAS Harness development path. It also adds a
separately identified held-out adversarial/benign evaluation scaffold and an
explicit review-routing record.

The scanner is deterministic. It examines prompt, scenario, and output text
for a small declared set of instruction-integrity and unsupported-claim
patterns. It records hashes, redacted excerpts, evidence references, and
review reasons.

## Invariant claim boundary

Every report must have:

- `mode: shadow`
- `verdict_effect: none_shadow_only`
- `review_routing.automatic_action: none`
- `review_routing.live_blocking: false`
- `review_routing.auto_removal: false`
- `review_routing.automatic_accept: false`

`FLAG_FOR_HUMAN_REVIEW` is evidence-routing metadata. It is not a final CAS
Harness verdict and does not block, rewrite, remove, or accept anything.

Allowed statements:

- The current development build can run a deterministic shadow scan.
- It can persist that scan in an Evidence Packet.
- The frozen local fixtures exercise declared adversarial and benign cases.

Prohibited statements:

- CAS Harness prevents prompt injection.
- CAS Harness is a production prompt-injection defense.
- A fixture pass proves general detection, prevention, safety, or readiness.
- A scanner finding authorizes `ACCEPT`, suppression, removal, or live action.

Those claims remain open. No provider, network, model, paid, or live-worker
path is part of this increment.

## Finding and routing model

The initial finding kinds are:

- `authority_override`
- `secret_exfiltration`
- `role_confusion`
- `task_replacement`

Unsupported prevention/detection language is recorded separately under
`claim_grounding`. Missing proof produces `support_status: unavailable`.
Secret-like values are redacted from excerpts; source-span hashes remain for
traceability.

Review routing has only two routes:

- `none`
- `instruction_integrity_review`

The second route is a data-model recommendation for later review tooling.
There is no active reviewer team and no automatic action.

## Evaluation surfaces

The development benchmark is frozen at:

`noetic-compass-scaffold/noetic-compass/scenarios/instruction_integrity_benchmark_v0.json`

The separately identified held-out scaffold is frozen at:

`noetic-compass-scaffold/noetic-compass/scenarios/instruction_integrity_heldout_v0.json`

Both carry a canonical SHA-256 in runner output. The held-out scaffold is not
training data. A local run is evidence only for the exact fixture cases and
the exact scanner revision.

## Evidence Packet persistence

`EvidencePacket.instruction_integrity` is optional for schema compatibility.
Packets assembled by the current route populate it deterministically from the
packet input/output text and bind it to `trace_id`. This persistence does not
change the packet's claim levels or verification outcome.

## Promotion requirements

Any future live enforcement requires a new, separately authorized design and
must not be inferred from this shadow increment. At minimum it needs broader
independent adversarial evaluation, false-positive/false-negative analysis,
review operations, signed provenance, fail-closed behavior, and explicit
product/legal claim approval.
