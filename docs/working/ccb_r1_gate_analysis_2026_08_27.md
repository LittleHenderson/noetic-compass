# CCB-R1 — Gate Analysis: What Blocks Testing, and What Doesn't

**Date:** 2026-08-27
**Companions:** `cas_pcba_reasoning_audit_2026_08_27.md`, `ccb_r1_test_program_review_2026_08_27.md`, `cas_pcba_audit_source_verification_2026_08_27.md`
**Question asked:** what are the gates to testing CCB-R1, and do they hinder testing and experimentation?

---

## Verdict

**No. The gates block *claims*, not *runs* — and that is their stated design intent.**

> *"This split mirrors the CAS Core 8 invariant that structural consistency is never authorization; CAS-Ohm implements it as two independent axes so that no packet can drift from 'complete' to 'authoritative' by accumulation."*
> — Research Paper §9

Stages 0–4 are unblocked and running today. **Nothing in the corpus requires permission to experiment.** One gate has a trap that is easy to walk around, and one is a genuine forward-blocker for Stage 5 that is half-built already.

---

## The gate inventory

| Gate | Source | What it actually blocks | Stage 0–4 | Stage 5 |
| :--- | :--- | :--- | :---: | :---: |
| **Rule 9.2** Authenticated eligibility — *"always false in this candidate"* | Paper §9 | calling a result *authenticated evidence* | — | — |
| **Rule 9.1** Structural completeness | Paper §9 | recording a result as a complete *research packet* | ⚠️ | — |
| 5 registered hypotheses, `ring 4 / not licensed / held` | Paper §10 | product and causal claims | — | — |
| IP-attorney consultation | `cas_v7_7_rollout_plan.md:35-38` | arXiv, patent filing, disclosure beyond the dev team | — | — |
| `cas-ci-gate`, Claude Approvals | `.github/workflows/ci.yml` | merging code | — | — |

Nothing in that table blocks running an experiment. The `Gate` vocabulary in the
PCBA handbook (63 occurrences) turned out to be **logic gates** — circuit
components — not process gates. The handbook imposes no release process at all.

---

## The one trap: Rule 9.1 fails closed on simulators

Rule 9.1 requires *"at least one genuinely instrumented field (necessary but not sufficient)"* and fails closed on *"score-only, **zero-instrumentation**, missing-provenance, mixed-scale, unknown-profile, or tampered records."*

A deterministic Stage 0–4 simulator is **zero-instrumentation by construction**. It computes scores from a model; it does not measure an instrument. Pushed at the evidence layer, it will fail closed every time.

**Do not fight this. The paper already solved it.** It files its own synthetic work as a third category — *bounded software evidence* — and states the limit plainly:

> *"Synthetic known-fault boards — linear, cutoff, saturation, nonlinear, parallel, confounded, bypass — validate software behavior only; they are not experiments on a live model and cannot establish causal or empirical validity."*

Its own Gate 4 receipt is recorded exactly that way: *"65 passing CAS-Ohm test methods … zero authenticated Evidence-Packet eligibility paths."*

**Rule:** Stage 0–4 results are bounded software evidence. They are never research
packets and never authenticated evidence, and labelling them so is not a
limitation to work around — it is the honest category. The precedent is already
set in your own corpus.

---

## The one real forward-blocker: Rule 9.2, for Stage 5 only

Authenticated eligibility *"cannot become true until"* all six of these exist:

1. an independently admitted authority manifest
2. protected key lifecycle **and revocation policy**
3. trusted current-time receipt
4. materialized model/code/runtime dependency identities
5. authenticated instrument evidence
6. a reviewed packet policy

And the cheap route is explicitly closed: *"Deterministic in-repository fixture keys and caller-supplied replay time never satisfy those conditions."*

**None of this is research. It is infrastructure**, and it is a separate
workstream nobody has scheduled. If it is never built, Stage 5 experiments can
run but their results can never be *admitted*. That is the gate that could
actually cost you — and it sits in front of the evidence layer, not the lab.

### It is roughly half-built already

`scripts/sign_root_ci_protected_deploy_receipt.py` implements the hardest parts
for the deploy pipeline, exercised in CI on every push:

| Rule 9.2 requirement | Status in repo |
| :--- | :--- |
| protected key lifecycle | ✅ private key only via `CUSTOMER_PRODUCTION_SIGNING_KEY_PEM`, never in-repo; `KEY_ID = "gh-env-2026-07-14-01"` is a dated rotation convention |
| authority manifest | ✅ verifies *"the matching public key and exact subject grant"* |
| fail-closed behavior | ✅ *"The draft, issuer authority, or private key failed closed."* |
| revocation policy | ❌ not visible |
| trusted current-time receipt | ❌ not visible |
| materialized dependency identities | ~ partial — CI pins frozen sources |
| authenticated instrument evidence | ❌ needs a real instrument first |
| reviewed packet policy | ❌ not written |

So this is a **port of working code**, not a greenfield build. That materially
changes the cost of the Stage 5 decision, and it should be costed as such rather
than treated as a research blocker.

---

## An independent hit on Preserved Conflict 3.1

Building the Stage 1 simulator surfaced the scale conflict without looking for it.

- The handbook constrains `sat ∈ (0,1] and cutoff ∈ [0,1) — both live on the open simplex; sat=0 or cutoff=1 is rejected`.
- The guide's p.12 worked example runs `sat=8.5` with `I=4.0`.

Those are different normalizations. That is **Preserved Conflict 3.1 (scale and
saturation; direct numeric conflict)** in the paper's registry, re-derived from
first contact with the numbers.

`scripts/ccb_r1/cjt_sim.py` therefore makes scale an explicit, validated field
(`Scale.UNIT` / `Scale.DESIGN`) and refuses to silently harmonize the two. The
conflict is encoded in the code and pinned by a test rather than resolved by
whoever writes the next board.

**This is the argument for starting Gate 1 from the registry.** Eight conflicts
already carry locators and binding candidate rules; two of them
(**3.6 network rules**, located at guide pp.13–14, and **3.4 gain definition**)
sit directly under the CCB-R1 cascade and its truth firewall.

---

## What this means for sequencing

**Run Stages 0–4 now.** They are ungated. Record everything as bounded software
evidence.

**Decide Rule 9.2 separately, and later.** It is only required if you want Stage 5
results to be externally admissible. Cost it as a port, not a build.

**Do not let this analysis become its own gate.** It was written alongside a
working Stage 1 simulator and 19 passing golden traces, not before one. The test
program does not wait on it.
