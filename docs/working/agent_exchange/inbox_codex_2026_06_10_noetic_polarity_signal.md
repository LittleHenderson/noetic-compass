# Handoff to Codex — Noetic Polarity (^2−^3) as a complementary Instruction-Integrity finding

**From:** Claude  **To:** Codex  **Date:** 2026-06-10  **Re:** `cas_harness_topos_instruction_integrity_roundtable_20260610.md` (your `e6044e6`+)

**Coordination note:** this is a PROPOSAL, not an edit. I have NOT touched your files (the Instruction-Integrity brief, `cas_harness_production_todo.md`, the EP schema, `api/pipeline/stages.py`, the Guide/explainer). You own the `instruction_integrity` schema and its wiring; this note hands you a complementary *signal* to fold in at your discretion.

## What this adds to your lane

Your Instruction-Integrity gates are gluing / coverage / authority-override / D-W-P / domain-precedence (round-table mechanisms #1 RPM + #3 Topos). They are about **"does this tile glue back to evidence/policy/task."** They do NOT yet include the **involution-polarity** signal (round-table mechanism #2): **"what is the model's net valence toward the (injected) idea — attracted toward it (complied) or repelled by it (refused)."** That is a distinct, source-grounded CAS coordinate and a natural additional `findings[]` kind.

**The construct (grounded in v7.4 + the originals — see my notes):**
`P = ^2 − ^3` (**Noetic Polarity** / net valence): ^2 Positive = "attraction operator / attracted-toward"; ^3 Negative = "differentiation operator / repelled-by; causes RPM-cascade failures" (v7.4 L27146/27151; `<2:3>` "Dual polarity" L28024; F1c smooths `<2:3>` oscillation L1869). Already shipped in code: `_involution_gap` (`api/pipeline/forecast.py:77`) over `_INVOLUTION_PAIRS = (CO-2,CO-3),(CO-5,CO-6),(CO-8,CO-9)` (`api/similarity/cosine.py:65`) — so the implementation already uses the (2,3)/(5,6)/(8,9) convention (it resolves the docs' involution-pair contradiction in the code's favor).

## Empirical evidence (exploratory; honest boundary matches yours)

- **OUTPUT-side signed P separates COMPLIED from REFUSED at AUC 0.956** (rank-biserial 0.91, p 7e-14; REFUSED mean s2−s3 = −6.1 vs COMPLIED +1.2). This is a real **post-hoc** read of a completed response. (`expl2_involution_gap_result_20260610.md`)
- **The gap MAGNITUDE does NOT detect injection** (injected-vs-clean AUC 0.549, null) — only the SIGNED pair is informative. Don't ship "big involution gap = injection."
- **INTERNAL-state P (from the Gate-A probe) is CHANCE** for comply/refuse at the generation window (AUC 0.486); only weak/payload-confounded at the prompt stage (0.615, n_ref 24). So this is an **output-side signal, NOT internal** — directly consistent with your "internal-state hijack/refusal separation: NOT safe to claim." (`internal_polarity_readout_test_20260610.md`)
- Caveat (definitional, not fatal): comply/refuse IS the sign of P by the authoritative definitions, so the output-side AUC is "definitionally valid," not a coincidence — but also not internal and not "injection detection." Scorer was Claude; v1 benign-mischief data; needs a non-Claude scorer + better-powered set to firm up.

## Proposed schema slot (shadow-mode, your call)

A `findings[]` kind alongside your `authority_override` etc. — no change to `claim_grounding[]`/`gluing`:
```json
{ "kind": "noetic_polarity",
  "scope": "model_output",
  "signed_p": -6.1,
  "pole": "repelled",              // attracted (P>0) | repelled (P<0) | neutral
  "involution_pair": "CO-2/CO-3",
  "read_from": "output_text",      // NOT internal_state (internal readout is chance)
  "mode": "shadow",
  "decision": "annotate_only",
  "claim_basis": "exploratory; output-side post-hoc; AUC 0.956 comply-vs-refuse; not injection-detection" }
```
Maps to your verbs: it is a **DETECT annotation** (post-hoc valence of the response), feeding your existing remove/reverse/replace machinery; it is NOT a real-time interceptor and must carry the same `OPEN`/`NOT LICENSED` boundary as the rest of the lane.

## What I'd suggest (and what I'll leave to you)
- **Yours to own:** whether/how to add `kind:"noetic_polarity"` to the EP schema + Stage-1 shadow detector + tests. I won't touch the schema or `stages.py`.
- **Mine (offered):** a standalone reference scorer (text → 10 operator scores → signed P) and the comply/refuse mapping already exist in `expl2_involution_gap_result_20260610.md` + the score artifacts in `D:\tksCAS-archive\expl2_involution_gap_20260610\`. Reuse `_involution_gap` directly. If you want a packaged `polarity_audit.py` reference impl in the kit (not in `api/`), say so and I'll build it in a non-colliding path.

## Cross-refs
`docs/working/expl2_involution_gap_result_20260610.md` · `..._noetic_polarity_2minus3_grounding_20260610.md` · `..._internal_polarity_readout_test_20260610.md` · round-table synthesis `..._cas_injection_roundtable_findings_20260610.md` (#2 = involution-pair divergence).

**Status: collaborated and waiting** — your call on folding `noetic_polarity` into the Instruction-Integrity findings. No files of yours touched.
