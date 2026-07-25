# CAS Harness — One-Page Executive Summary

**Date:** 2026-06-30 · **Framework:** CAS v7.7 · **Confidential / NDA-Gated**
**Companion:** full detail in `cas_harness_synopsis_20260630.md`.

---

**What it is.** CAS Harness is a **white-box, cross-model AI-auditing platform**. Give it an open-weight language model and it (1) **reads** cognitive structure from the model's hidden activations, (2) **proves** that structure is causally load-bearing by ablating it and watching behavior collapse, (3) **conditions** the model's next-token output by feeding the structure back as a readable prefix (the η→ε bridge), and (4) emits a tamper-evident, hash-chained, S3-anchored **Evidence Packet** any third party — including a regulator — can independently re-verify. Tagline: "the black-box flight recorder for AI cognition." Mechanically it is the opposite of black-box: it **requires** hidden-state access, so closed-API models (Claude, GPT, Gemini) cannot be onboarded.

**Why it could matter.** It turns model internals into **audit-grade evidence artifacts** for two markets at once — developers (pre-deployment evaluation, hallucination root-causing, CI quality gates) and enterprises (EU AI Act / NIST AI RMF / SR 11-7 compliance evidence, vendor procurement, AI-error legal defense, board risk reporting). Every audit also **harvests real-model training data** for the sister product, CAS-Native.

**What is proven (LICENSED).** Across **six open-weight model points in three architecture families** (Pythia/GPT-NeoX 160M→20B, OLMo-1B, Qwen2.5-1.5B):
- **Detection** — CAS structure is linearly readable from hidden states. GPT-NeoX-20B 40-Element held-out readout 95.625% (4,284/4,480; descriptive Wilson 95% CI 94.986-96.186), against word-level text controls of 49.241% (CountVectorizer 1-2 grams) and 50.0% (HashingVectorizer 1-2 ngrams). No character-level n-gram control was run on this row, so `control_proof` is PARTIAL and no hidden-beats-all-surface claim is licensed.
- **Causal role** — ablating the structure collapses readout (107× signal-to-noise at 20B); head-level + **sparse MLP-neuron-cover (112/112, p < 10⁻³³)** with necessity *and* sufficiency.
- **Conditioning** — the η→ε bridge shifts next-token likelihood; strongest result **+1.412 at GPT-NeoX-20B (40-Element)**, the project record. Raw-symbol controls stay null, so the effect is structural, not symbol recognition.
- **Audit chain** — disk-persisted, append-only hash-chained, five-check verify endpoint with live S3 round-trip, mechanical WORM (S3 Object Lock, Governance mode), and an **ACCEPT-requires-WORM gate**.
- Validated **up to 20B parameters on two cognitive axes** under two named methodologies (`S7-F28-BALANCED-BRIDGE`, `S9-40E-ORIGINAL-BASELINE-READOUT`).

**What is NOT yet proven (the honest boundaries).**
- **No standing `ACCEPT` verdict exists** — the only prior one was a withdrawn overclaim; the honest verdict is `FLAG_FOR_HUMAN_REVIEW`. Per-customer production ACCEPT is **NOT LICENSED**.
- **CAS-specificity is OPEN** — detection proves the model encodes the distinctions, *not* that they are CAS-specific vs a generic semantic partition. Two fixture NULLs and one blind comparator = **GREY**; no clean matched-comparator win yet.
- **Nothing above 20B is validated** — the Fleet build targets 300B+ and a 314B run is in flight, but **"300B = ENGINEERED, NOT VALIDATED."**
- **Single-instance durability only**; **no SOC 2 / ISO 42001 certification**; anchoring is **tamper-evident, not immutable**.
- Hidden-content, instruction-integrity, and pre-speech detection are **prototype / shadow / OPEN**.

**Path to launch (engineering, not research).** Kill the SSH-tunnel dependency (run the worker behind a real production route) → accounts/billing/quotas/RBAC → declutter the audit-console UI → compliance minimum (privacy/terms/retention/DSAR) → phased rollout (internal smoke → private alpha → paid NDA beta → public). Alpha is live today on Pythia-160M.

**IP.** US Provisional **64/037,173**, filed **04/13/2026**; utility/PCT conversion due **≈ 04/13/2027**. Eight CAS-Harness-specific mechanisms are candidates for separate filings (held from disclosure).

**Bottom line.** A genuinely working, causally-validated, audit-grade interpretability pipeline up to 20B parameters — whose defining discipline is that it labels its own NULLs, GREYs, withdrawn verdicts, and unvalidated scale *out loud*, because that honesty is the product. Detection is the licensed core; uniqueness and frontier scale are open, funded research, not closed claims.
