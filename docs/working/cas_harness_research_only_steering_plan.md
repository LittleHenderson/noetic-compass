# CAS Harness Research-Only Steering Capability Plan

Date: 2026-07-29
Status: later research proposal; disabled by default; not implemented

## Boundary

This document does not enable steering, activation intervention, model
loading, a live worker, provider access, or enforcement. The current product
increment remains a deterministic `shadow` / `none_shadow_only` text scanner.

Any future steering prototype must start behind an absent-by-default feature
flag:

`CAS_RESEARCH_STEERING_ENABLED=false`

Changing that flag, adding an executor, or running a model requires a separate
owner decision and a prospective research lock. No result from this research
lane may create `ACCEPT`, alter a production verdict, or become a production
defense claim.

## Proposed research sequence

1. Freeze one local model revision, tokenizer, corpus, prompt split, layers,
   token positions, intervention operators, endpoints, thresholds, uncertainty
   rules, and failure rules before observing claim-bearing results.
2. Implement offline activation capture and a no-op path first. Verify that
   capture alone does not change outputs beyond the frozen tolerance.
3. Add narrowly scoped intervention operators with explicit dose and sign.
   Preserve raw activations, logits, generations, seeds, and environment
   manifests in a research Evidence Packet.
4. Run matched controls: no-op, random vector, wrong layer, wrong token,
   wrong sign, and shuffled labels.
5. Require bidirectional dose-response evidence plus intervention-removal or
   patch-back checks. Measure utility, fluency, safety, and unrelated-task
   damage alongside the target endpoint.
6. Audit the exact packet independently and report model/revision-specific
   evidence only. Generalization and product claims remain open.

## Promotion stop conditions

The research lane remains disabled if there is drift, missing provenance,
control failure, weak or non-monotonic effects, material collateral damage,
unbounded compute, network dependence, or incomplete evidence retention.

Even a successful research result does not authorize a live enforcement
worker. That later step requires a new product threat model, evaluation
program, operational review workflow, rollback design, privacy/security
review, and explicit owner authorization.
