# CAS Harness — Thorough Synopsis

**Date:** 2026-06-30 · **Framework:** CAS v7.7 · **Classification:** Confidential
**Compiled from:** the consolidated investor spec sheet (`docs/legal_drafts_20260607/CAS_HARNESS_SPEC_SHEET_current.md`), the production TODO (`docs/working/cas_harness_production_todo.md`), the matched-taxonomy / closure-methodology docs (`docs/working/cas_harness_mtc_*`, `cas_harness_original_closure_methodology_20260526.md`), the scaffold code (`cas-native-agent-swarm-scaffold/`, `noetic-compass-scaffold/`), the go-to-market / legal drafts (`docs/working/cas_harness_{ai2,amazon,alpha_partner,launch_security}_*`, `docs/legal_drafts_20260607/`), and the instruction-integrity research thread (`docs/working/cas_harness_*roundtable*`, `agent_exchange/inbox_claude_2026_06_09_harness_launch.md`).

> **Claim-status discipline:** This document preserves the project's reserved-language verdict words exactly — `ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, `SUPPRESS`, `LICENSED`, `NOT LICENSED`, `OPEN`, `GREY`, `NULL`, `ENGINEERED NOT VALIDATED`. A strong research result is not automatically a production feature.

> **Naming note:** "CAS Harness" the **product** described here is unrelated to `cas-forex/cas_forex/forecast/harness.py`, a forex-backtest harness in a different subproject.

---

## 1. What CAS Harness Is — In One Paragraph

CAS Harness is a **white-box, cross-model AI-interpretability and auditing platform**. You give it an open-weight large language model (one whose weights you can load); it (1) **reads** cognitive structure out of the model's hidden-state activations, (2) **proves** that structure is causally load-bearing for the model's behavior (by ablating it and watching behavior collapse), (3) **conditions** the model's next-token output by feeding the detected structure back in as a readable prefix, and (4) emits an **audit-grade Evidence Packet** — a tamper-evident, cryptographically hash-chained, externally-anchored record that an outside party (even a regulator) can independently re-verify. Its marketing line is "the **black-box flight recorder for AI cognition**" — but mechanically it is the *opposite* of black-box: it **requires** hidden-state access and cannot onboard closed-API models (Claude, GPT, Gemini). It is built on the **Cognitive Architecture System (CAS) v7.7** and grounded in a formal math result (Proposition 5.6 of the "Noetic Topos" paper).

---

## 2. Origin & Strategic Position

**Origin (a scientific question, not a product idea).** It grew out of R&D adjacent to the **CAS-Native** flagship (a from-scratch transformer built *on* CAS). The originating question was:

> *"If a random open language model — one that's never heard of CAS — is probed for CAS-shaped structure, will the structure be there? If yes, is CAS describing something universal about how cognitive systems represent meaning, rather than something we invented?"*

Foundation-28 held-out readout and eta->epsilon likelihood conditioning replicated on six model points across three architecture families on ONE frozen English synthetic fixture. Causal support is model- and tier-specific, NOT six-model. Static weight-geometry evidence exists only for Pythia-2.8B. No 20B axis is closed and no verdict is validated causally across models.

**Two-product strategy.**
- **CAS-Native** = "our model, transparent by construction" (trains weights on CAS targets from scratch).
- **CAS Harness** = "your model, we make it inspectable" (reads CAS structure out of a foreign model's existing weights).

**The harvest dimension.** CAS Harness is also a **data-harvest engine for CAS-Native**: every audit on a model-we-don't-own produces real prompts, outputs, activations, CAS readouts, and verdicts — the diverse real-model corpus CAS-Native needs. The capture layer (`api/services/cas_harness_harvest.py`) writes an append-only JSONL record per audit, joinable to the synthetic-data-generator corpus on `trace_id`. The Harness is designed to *fund itself and feed the model* simultaneously.

---

## 3. The Mathematical Core — the η→ε Bridge

| Map | Direction | Role |
|---|---|---|
| **η (eta)** | structure → realization | **Reads** the CAS class out of hidden states (balanced-logistic linear probe on per-axis fixtures) |
| **ε (epsilon)** | realization → tokens | **Writes** the detected CAS structure back as a readable English prefix for the model |

Two load-bearing properties:

- **Section-retraction identity:** `ε ∘ η = id` (read-then-realize round-trips), but `η ∘ ε ≠ id` (realize-then-reread may lose information). Prerequisite satisfaction is **one-directional** — which is why conditioning *by ε-realization* works while steering by raw hidden-state ablation behaves only as a one-directional map.
- **Proposition 5.6 (counit surjectivity):** the pullback of the counit ε along any morphism is surjective. Applied to transformers: a prefix token is attended to by every later position *by construction* (a structural property of self-attention, not a tuned hyperparameter). The theorem **predicted the bridge mechanism before any experiment ran.**

> **Implementation honesty:** both η and ε are computed **offline** by the capture/probe worker (`run_stage9_40e_eta_epsilon_bridge.py` and its F28 sibling). The service-side module (`cas_harness_evidence_bridge.py`) does **not** compute η or ε — it normalizes/verifies the worker's packet and emits the proof chips.

Three framework-internal diagnostics are validated: a **lacunarity gate** (factorization-gappiness, range 0.793 → 0.0016), a **fractal classifier** (Stabilizing/Amplifying/Oscillatory/Neutral orbit verdicts), and a **weight-geometry alignment** test.

---

## 4. How It Works End-to-End

```
ENGLISH PROMPT
   → FOREIGN OPEN-WEIGHT MODEL (Pythia 160M/1B/2.8B, GPT-NeoX-20B, OLMo, Qwen, …)
       → multi-layer hidden-state capture
       → COGNITIVE-AXIS PROBES (η)  [balanced-logistic linear classifiers]
       → MULTI-LAYER TRACE / BLIND-SPOT DETECTOR / REALIZATION LAYER (ε)
       → prepend realized structure to the original prompt
   → FOREIGN MODEL second forward pass with the prefix
   → LIKELIHOOD SHIFT in next-token distribution
   → EVIDENCE PACKET MERGE (6 proof chips + verifier report)
   → DISK PERSISTENCE → HASH CHAIN → 5-CHECK VERIFY → S3 ANCHOR → WORM (Governance)
   → ACCEPT-REQUIRES-WORM GATE
   → AUDIT CONSOLE UI (three-state trust surface)
   → VERDICT: ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS
```

**The actual code that runs this:**

- **`live-trace-worker/`** — the real worker. Loads Pythia-160M (or another open-weight model), streams token-by-token generation with layer probes over SSE, stamps an `is_real_model` provenance flag. Falls back to a demo path if PyTorch is unavailable.
- **`cas_harness_scale_planner.py`** — plans layer/shard worker assignments by model size (single_worker → small_distributed → distributed → enterprise_distributed).
- **`cas_harness_fleet_executor.py`** — orchestrates the distributed worker pool: registration, heartbeats, job leasing with token expiry, fragment receipt, readiness gate before the verifier.
- **`cas_harness_evidence_bridge.py`** — pure transform mapping Evidence Packets into six proof chips (no verdicts created here).
- **`cas_harness_harvest.py`** — append-only JSONL harvest corpus, provenance-conscious (absent/false `is_real_model` ⇒ recorded as **demo fallback**, never silently treated as real training data).
- **`cas_harness_verdict_runner.py` / `cas_harness_audit_sessions.py`** — verdict computation and audit lifecycle.

The **CAS-Native agent swarm scaffold** (`cas-native-agent-swarm-scaffold/`) is a separate reference implementation of the *governance* pattern: agents communicate in CAS-validated structured expressions through a **bridge** that enforces a **Claim Map** (LICENSED / FRAMEWORK_PREDICTED / NOT_LICENSED tiers) and a hash chain — defense-in-depth where the agent's own authority check is the first line and the bridge is an independent second line. Four reference agents (Orchestrator, CustomerService, Marketing, Audit) demonstrate scope enforcement and human-review gates.

---

## 5. What It Has Empirically Validated (the Evidence Ladder)

Foundation-28 held-out readout and eta->epsilon likelihood conditioning replicated on six model points across three architecture families on ONE frozen English synthetic fixture. Causal support is model- and tier-specific, NOT six-model. Static weight-geometry evidence exists only for Pythia-2.8B. No 20B axis is closed and no verdict is validated causally across models.

**5a. Cognitive-structure detection (readout above text baseline):**

| Axis | Classes | Model | Probe Accuracy | Lift over text baseline |
|---|---:|---|---:|---:|
| 28 Foundations | 28 | Pythia-160M | 78.6% | +28.9 pp |
| 28 Foundations | 28 | Pythia-2.8B | 85.9% | — |
| 28 Foundations | 28 | GPT-NeoX-20B | 86.86% | — |
| 28 Foundations | 28 | OLMo-1B | 90.6% | — |
| 28 Foundations | 28 | Qwen2.5-1.5B | 82.0% | — |
| 40 Elements | 40 | Pythia-160M | 89.8% | +39.7 pp |
| **40 Elements** | **40** | **GPT-NeoX-20B** | **95.625%** | **+46.4 pp** |

> **Honest caveat on the 95.625% headline:** the readout **peaks at layer 2 of 44** (an early-layer peak, consistent with reading near-surface lexical features), and the "+46.4 pp lift" is measured against a deliberately *weak* bag-of-words baseline (≈49.24%). The shuffled-label control passes cleanly (2.62% vs 2.5% chance), so it's not fitting noise — but the **LICENSED reading is the narrow one**: *"the model linearly encodes the label distinction above a surface-text classifier,"* **not** *"CAS-specific cognition at 95.6%."*

**5b. Readout-causal validation (ablate the subspace, watch accuracy collapse):** Five axes collapse to exact chance under subspace ablation with clean random nulls. Notable: 40-Element at GPT-NeoX-20B drops **95.625% → 66.897%** (28.73 pp), random-matched controls 0.068 pp mean — a **107× signal-to-noise ratio**. The pre-registered gate (≥30 pp drop / ≤65% floor) was **narrowly missed** by 1.27–1.90 pp and documented openly as a near-miss (not a pass).

**5c. Likelihood conditioning via the η→ε bridge** (probe-readable Δ = how much the prefix shifts next-token likelihood toward the CAS expectation):

| Model | Axis | Probe-readable Δ | Cases |
|---|---|---:|---:|
| Pythia-160M | F28 | +0.283 | 81/112 |
| Pythia-2.8B | F28 | +0.583 | 92/112 |
| OLMo-1B | F28 | +0.604 | 87/112 |
| Qwen2.5-1.5B | F28 | +0.796 | 83/112 |
| GPT-NeoX-20B | F28 | +0.596 | 90/112 |
| **GPT-NeoX-20B** | **40E** | **+1.412** | **80** |

The **40E result at 20B is the single strongest bridge result in the project record** (1.77× the prior Qwen record, 2.37× the same-model F28 result). Raw-CAS-symbol prefixes stay null at every scale (−0.020 to +0.003), confirming the effect is **ε-realization, not symbol recognition**.

**5d. Component-level causal localization:**
- Head-level: 78% → 19% (p = 0.0323), 100% sufficiency recovery via path patching.
- **Sparse MLP-neuron-cover: 112/112 at p < 10⁻³³**, bit-exact patch-back.
- Output-side drive-local steering: Pythia-160M +0.85, Pythia-1B +0.84, **Qwen2.5-1.5B +0.90 (56/56 unanimous, p = 1.4×10⁻¹⁷)**. Bounded to the drive-local eraser-channel method; global/universal-cover steering was **empirically falsified** (too coarse).

**5e. Other closed tiers:** factorization (lacunarity, F28 down to 0.006715 at 20B), six pre-registered framework predictions held, cross-scale (4 Pythia/GPT-NeoX points), cross-architecture (3 families on F28), weight-geometry alignment (Pythia-2.8B at 2.83× random, p = 0.0099), multi-layer trace + blind-spot detection, runtime-safe accept/suppress (87.6% accept at 99.78% accuracy, 0.22% silent error).

---

## 6. The Audit-Grade Integrity Chain (the real differentiator)

Each **Evidence Packet** carries a **verdict** — `ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS` — plus **six proof chips** (model / readout / baseline / causal / control-cover / output-bridge), each SHA-256-committed. Five layers:

1. **Disk persistence** — bit-identical reload proven (single-instance restart-survival only).
2. **Append-only hash chain** — each entry fingerprints the previous; tampering shatters all later fingerprints, detectable in linear time.
3. **Five-check verify endpoint** (`/evidence/{trace_id}/verify`) — payload hash + log entry + chain continuity + local anchor manifest + **live S3 round-trip**. Never returns a silent "OK."
4. **External anchoring with mechanical WORM** — S3 Object Lock in **Governance mode**, ~30-day rolling retention; `HeadObject` confirms `ObjectLockMode = GOVERNANCE` and retention is in the future.
5. **ACCEPT-requires-WORM gate** — an explicit ACCEPT requires all three retention proofs (anchor written, re-read+hash-matched, Object Lock active) or is **auto-downgraded to FLAG_FOR_HUMAN_REVIEW**.

**Two crucial honesty points the docs hammer repeatedly:**
- The anchor is **tamper-EVIDENT, not immutable**. Governance mode is operator-overridable by a principal holding `s3:BypassGovernanceRetention`. The guarantee is that any override is **detected on the next verify call** — *not* that deletion is physically prevented.
- **No `ACCEPT` verdict stands in the entire project record.** The one previously reported (2026-05-28, Stage 9 40E) was a **pre-fix overclaim** from a candidate-only `control_proof` and has been **WITHDRAWN**; the honest WORM-retained verdict is `FLAG_FOR_HUMAN_REVIEW`. Per-customer production `ACCEPT` verdicts remain **NOT LICENSED**.

---

## 7. The Big Open Question — Is CAS *Specific*?

Every closed tier above proves the model **linearly encodes whatever distinctions the CAS labels track, and that encoding is causally load-bearing.** None proves the recovered structure is **CAS-specific** rather than one coherent relabeling of generic semantic structure. That claim is **inherently comparative** — earned only against cardinality-matched rival taxonomies. This is the **Matched-Taxonomy Control (MTC)**, and its record:

- **MTC v1 — NULL (text leakage).** Surface text leaked the answer key (text baseline 100%). Rejected before activation capture. Build error.
- **MTC v2 — NULL (meaning removal).** Aggressive de-leakage stripped the leak *and* the meaning; CAS recoverability collapsed to chance. A **meaning-removed** fixture, not a signal-absent one. Motivated the **TKS-Meaning Preservation Rule**.
- **MTC Condition-3 (GPT-NeoX-20B, 2026-06-03) — GREY.** First comparator to clear both fixture-validity gates and run blind. CAS did **not** beat the cardinality-matched control by the pre-registered margin (archived run: `cas_element` hidden acc ≈ 6.53% vs matched control ≈ 84.72%). **A GREY is not a pass.** Scoped to the comparator; does **not** touch the 40E detection or η→ε bridge.
- **F28 vs GoEmotions-28 (Pythia-2.8B, 2026-06-15) — BLOCKED_CAS_NOT_RECOVERABLE, with real off-gate signal.** CAS-Foundation hidden-minus-text lift **+13.9 pp** vs GoEmotions **+0.4 pp** (CAS carries internal structure the rival does not; scrambled-CAS null at chance 3.9%) — **but +13.9 pp missed the pre-registered +20 pp floor**, which was *not* retuned post-hoc.

**Net claim ladder (verbatim from spec §9.8.1):**
1. **Detection** — "CAS structure is linearly readable from activations." **LICENSED** (narrow reading; signal-vs-leakage adjudication *Stage LSA* still **OPEN**).
2. **Comparative speciality** — "CAS outperforms tested matched non-CAS systems." **NOT yet supported** (one blind comparator = GREY).
3. **Probabilistic speciality** — "repeated matched-comparator wins make CAS likely non-arbitrary." Reachable but **not yet earned** (needs one clean blind *win*).
4. **Absolute uniqueness** — "no system can ever match CAS." **Explicitly disclaimed, not the target.**

**Detection is the licensed core; uniqueness/speciality is OPEN and honestly labeled.** The "universal rather than something we invented" framing is treated as an **open research question, not a closed claim.**

---

## 8. Scale & the Fleet Build

For models too large for one worker, the **Fleet build** shards the model across **N Probe Workers**, coordinated by a **Fleet Executor** (stitches per-worker chips, reconciles shard seams, coordinates cross-worker ablation) and a **Scale Planner** (worker/layer assignment). Each sub-harness commits a **fragment SHA-256** of its raw activation tensor so the aggregator can prove no worker swapped tensors; **raw activations never cross the wire** — only chips, hashes, verdicts. A **conservative-default verifier gate** emits a fleet ACCEPT only if *every* worker reports ACCEPT, all fragment hashes verify, and topology is complete; any SUPPRESS/FLAG/timeout forces the whole fleet verdict down.

> **Scale honesty:** the Fleet is engineered toward **300B+** and is mid-execution against a **314B BF16 community checkpoint** (third-party HF conversion of a JAX original, carried with an explicit converted-checkpoint provenance schema). But **"300B" is ENGINEERED, NOT VALIDATED** — *no detection, causal, or bridge result above 20B is licensed.* Product vision extends to "audit open-weight models up to 4 trillion parameters," with lanes: `<=20B` (validated), `20B–300B` (engineered, not size-validated), `300B–4T` (`EXPERIMENTAL_NOT_VALIDATED` behind gates), `>4T` (refused).

---

## 9. Research Frontiers (prototype / OPEN — NOT LICENSED for production decisions)

- **Hidden-content / suppression detection (two-bridge).** η₁ reads internal hidden states, η₂ re-probes emitted text; their divergence is classified into **seven typed hiding shapes** (withheld content, self-censored, latent capability, suppressed reasoning, frame manipulation, persona drift, involution content). Output is a *bounded typed-class assignment* that cannot confabulate beyond the seven-class set. **Prototype tier; no confirmatory gate has closed.** Spike experiments show it currently acts as a **behavioral-divergence detector, not a hijack detector** — it fires on *any* off-task behavior (hijack-comply and safe-refusal both separate from clean baseline; injected-but-ignored stays at baseline), so it **cannot yet distinguish "model was hijacked" from "model safely refused."** Requires an injectable instruct model ≥~1.5B (Pythia-160M = 0% injection compliance, unusable for this).

- **Instruction Integrity (Topos Integrity Gate).** Treats hallucination and prompt injection as **evidence-gluing failures**: a generated claim is allowed only if it "glues back" to source evidence, task intent, the P≻C≻E≻O domain hierarchy, and CAS prerequisites — else routes to `FLAG_FOR_HUMAN_REVIEW`. Seven hallucination signatures and seven prompt-injection signatures enumerated. **Status: Stage 1 shadow-mode prototype** (findings written to the Evidence Packet, verdict capped at `FLAG_FOR_HUMAN_REVIEW`). **LICENSED** only as a *design direction*; "detects/prevents hallucination," "prevents prompt injection," "neutralizes harmful instructions" are **NOT LICENSED**.

- **Pre-speech / causal compliance detection.** Can a probe on the prompt-final hidden state (W0, before token 1) read comply/refuse stance *before the model speaks*, and can steering it *causally flip* behavior? On Qwen2.5-1.5B the W0 within-class probe **FAILED** (≈0.56 ≈ chance — stance appears graded until realization), and ^2−^3 direction steering **failed its controls**. **NOT LICENSED**; pre-registered v5 gates (Lane A detection + Lane B causal steering) are **OPEN**. (A CAS-PCBA bias/vibration injection lane returned **FAIL / BLOCKED_SURFACE_LEAKAGE** — surface controls dominated the hidden signal.)

---

## 10. The Code Reality — Real vs Stub vs Demo

| Real / validated | Stub / prototype / demo |
|---|---|
| Activation capture (incl. 20B), six axis probes, multi-layer trace, blind-spot detector, ε-realization, likelihood scorer | Hosted **always-on customer audit path** (demo-fallback / Pythia replay until a real hosted GPU worker runs) |
| Evidence Packet builder + verifier + three-lock gate; disk store (single-instance); hash chain; five-check verify; three-state UI; S3 anchoring **active in production**; HeadObject WORM | Two-bridge hidden-content detector (**prototype**) |
| Fleet apparatus (Probe Workers + Executor + Scale Planner + topology gate + fragment SHA-256) | Frontier (>20B) **audit results** (infrastructure live, **no results licensed**) |
| Harvest corpus (real, provenance-conscious, append-only) | Instruction Integrity (**shadow only**) |
| State substrate (Sqlite + Postgres verified against real PG 16.4; durable single-host restart-survival proven on Render) | Multi-instance / host-loss durability (**NOT proven** — one Postgres, no replica/failover) |
| CRM lead-capture spine + Airtable provider code; honeypot + rate limiter | Accounts/billing/quotas/RBAC (**OPEN**, not merged); external CRM sync (**not yet operational**) |

**Biggest engineering gap to production:** kill the **SSH tunnel** — the live worker can currently depend on a laptop staying connected. No public launch until the worker runs behind a real authenticated production route with health checks and restart recovery.

---

## 11. Product, Go-to-Market & Security State

- **Markets (dual).** *Developer*: pre-deployment evaluation, hallucination root-causing, structured prompt engineering, distillation verification, adversarial debugging, cross-model migration audits, CI quality gates. *Enterprise*: regulatory-compliance evidence (EU AI Act, NIST AI RMF, ISO/IEC 42001, NYC AEDT, FDA SaMD, SR 11-7), vendor procurement, AI-error legal defense, board AI-risk reporting, red-team integration, M&A due diligence. Outreach briefs exist for **AI2** ("turn your black box into a glass house") and **Amazon** (honestly framed as *complementary* to internal interpretability tooling, not a replacement).
- **Pricing:** **not yet set.** Billing stubbed; suggested tiering Free (demo/reference packets) / Paid (live audits) / Enterprise (large models + reserved GPU).
- **Launch phases:** internal smoke → private alpha → paid NDA beta → public. Current alpha is **live** (Pythia-160M real weights verified at `/atlas/live/health/realmode`; Audit Console M1 *correctly refuses to invent a verdict*).
- **Security posture (honest, pre-paid-production):** several **HIGH-risk** items OPEN — cross-tenant read, client-side mint secret / quota bypass, no RBAC, no durable security audit log, CORS open to `*.vercel.app`, localStorage Bearer token. Verified-safe: no XSS sink (JSX auto-escaping, no `dangerouslySetInnerHTML`), owner-scoped audit sessions (foreign reads 404), fail-loud cross-tenant guards. **No SOC 2, ISO/IEC 42001, or any third-party certification held.**

---

## 12. IP & Legal

- **Patent:** US Provisional Application **No. 64/037,173** (Utility—Provisional), filed **04/13/2026** (Conf# 1346, Patent Center# 75259715). Priority date locked; **conversion (utility or PCT) deadline ≈ 04/13/2027** or the priority date is lost. CAS v7.5/v7.6/v7.7 and the Fleet/300B architecture are **new matter added after filing** — not covered by this provisional; they need their own filing or inclusion in the utility application.
- **In-process method filings** (held from disclosure): the η→ε bridge on foreign open-weight transformers; the two named methodologies `S7-F28-BALANCED-BRIDGE` and `S9-40E-ORIGINAL-BASELINE-READOUT`; the Audit-Grade Integrity Chain composite; the Fleet build + fragment-SHA-256 merge; the framework-predictive preflight diagnostics; the TKS-Meaning Preservation Rule; the MTC pre-registration infrastructure; the converted-checkpoint provenance schema.
- **Distribution:** the spec sheet is **NDA-gated** (one-way alpha-partner NDA, 3-year base, trade-secret survival indefinite). Standing disclaimers: no certification, nothing is legal advice, a scoped-validation ACCEPT ≠ a customer-production ACCEPT, and **no "certification / guaranteed / 100% / world-first / only" claims.**

---

## 13. The Honest Bottom Line

**What CAS Harness *is* today (LICENSED):** a working white-box auditing pipeline that reads CAS-labeled cognitive structure out of six open-weight models across three families, proves that structure is causally load-bearing (head-level + sparse-neuron-cover, with necessity *and* sufficiency), conditions next-token output via the η→ε bridge (strongest result +1.412 at 20B on the 40-Element axis), and emits disk-persisted, hash-chained, five-check-verified, WORM-anchored Evidence Packets that any third party can re-verify — validated **up to 20B parameters on two cognitive axes under two named methodologies.**

**What it is *not* yet (NOT LICENSED / OPEN):** it has **no standing `ACCEPT` verdict**; **CAS-specificity is unproven** (two fixture NULLs + a GREY comparator; detection ≠ uniqueness); **nothing above 20B is validated** ("300B = ENGINEERED, NOT VALIDATED"); durability is **single-instance only**; hidden-content detection, instruction integrity, and pre-speech causal detection are **prototype/shadow**; and the product still needs to **kill the SSH tunnel, add accounts/billing/quotas/RBAC, declutter the UI, and complete a compliance minimum** before paid public launch.

The defining cultural feature of the program is its **honest-NULL discipline**: the nulls, the GREY, the withdrawn ACCEPT, the near-miss ablation gate, and the "tamper-evident not immutable" caveat are all documented *precisely because* selectively reporting only the wins would void the audit-grade differentiator that is the product's entire reason to exist.
