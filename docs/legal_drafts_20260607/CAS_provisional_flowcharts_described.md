> **DRAFT — must be reviewed by a registered patent attorney/agent before filing; not legal advice.**
> **Public disclosure of these contents may start statutory bars — keep confidential.**
>
> **Purpose of this document.** It re-describes each provisional flowchart as **text + a mermaid diagram** so an attorney or technical illustrator can produce clean, filing-grade figures. **The diagrams cannot be reproduced as the original raster images here** — this captures each figure's *logic and numbered elements* instead. Element numbers (10, 12, 14, …) match the reference numerals used in `CAS_provisional_patent_updated.md` §5. The legacy figures in `CAS_Provisional_Flowcharts.pdf` are stylistically degraded and several labels are unreadable; treat the descriptions below as the corrected source of truth and **re-draw** rather than trace.
>
> **Reconciliation note.** These descriptions are updated to the **current** build: three-verdict vocabulary (`ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS`), **six** proof chips, **GOVERNANCE-mode tamper-evident** anchoring (not immutable), the `ACCEPT`-requires-anchor downgrade gate, and the new **Fleet** figure (H1). Where a legacy figure asserted a headline result (e.g., a standing `ACCEPT`, specific effect sizes), the description **drops the result and keeps the mechanism**, with values marked **[VERIFY]**.

---

# CAS Provisional — Flowcharts Re-Described (Text + Mermaid)

**Figure index**
- **Figure A1** — η→ε conditioning bridge (two-pass, weight-frozen).
- **Figure B1** — Non-oracle runtime verification stack (accept / suppress).
- **Figure C1** — Evidence Packet assembly + authenticated delivery (six chips, three verdicts).
- **Figure D1** — Multi-layer trace + readout-position blind-spot disambiguation.
- **Figure E1** — Matched-control causal localization (head-level + sparse-neuron-cover).
- **Figure F1** — Generation Readiness Gate (four-tier, zero-parameter, non-mutating).
- **Figure G1** — Two-bridge hidden-content detector (η₁/η₂) — **PROTOTYPE**.
- **Figure H1** — Sharded-Fleet execution (NEW; per-worker sub-harness + anti-misattribution + conservative-default gate).
- **Figure F2** — Integrity chain + WORM anchoring detail (NEW; supports Mechanism F).

---

## Figure A1 — η→ε Conditioning Bridge

**Caption:** Two-pass read–realize–condition loop; **no weight modification**. Identity relations: ε∘η = id; η∘ε ≠ id. The realized prefix is ordinary input tokens, attended to by all later positions by construction.

**Logic (numbered elements):**
1. **ENGLISH PROMPT** → enters a **FOREIGN OPEN-WEIGHT MODEL** (e.g., Pythia/GPT-NeoX, OLMo, Qwen). First (baseline) pass.
2. **(10) Hidden-state capture** — capture activations at a mid-depth band (~**[VERIFY 39–50%]** of depth) at **[VERIFY token position(s)]**.
3. **(12) Embedding map η** — trained linear/logistic probe → typed class label.
4. **(14) Realization map ε** — template/lookup emits a readable natural-language prefix for the label.
5. **(16) Prefix concatenation** — prefix + original prompt.
6. **(18) Second forward pass** — same model, prefixed input.
7. **(20) Likelihood scorer** — log-likelihood shift of the target class (prefixed vs. unprefixed); plus null-control (raw-notation prefix ≈ 0) and partner-margin conditions.

```mermaid
flowchart TD
    P[ENGLISH PROMPT] --> M[FOREIGN OPEN-WEIGHT MODEL<br/>Pythia / OLMo / Qwen — first pass]
    M -->|first pass| C10["(10) Hidden-state capture<br/>mid-depth band ~VERIFY 39-50%"]
    C10 --> E12["(12) Embedding map η<br/>trained probe → typed class label"]
    E12 -->|label| R14["(14) Realization map ε<br/>template → readable NL prefix"]
    R14 --> X16["(16) Prefix concatenation<br/>prefix + original prompt"]
    X16 --> S18["(18) Second forward pass<br/>same model, prefixed input"]
    S18 --> L20["(20) Likelihood scorer<br/>Δ log-likelihood of target class<br/>+ raw-notation null control + partner margin"]
    L20 --> OUT["Output: measured Δ-likelihood toward identified structure<br/>(weights unchanged; prefix attended by all later positions)"]
```

---

## Figure B1 — Non-Oracle Runtime Verification Stack

**Caption:** Runtime accept/suppress using **non-oracle** signals; **gold labels at calibration only**, never at inference. Every suppression carries a reason. *(Headline metrics from the legacy figure are **offline-validation** numbers, not production — keep them out of the figure or label them as such.)*

**Logic (numbered elements):**
1. **MODEL OUTPUT** enters.
2. **(10) Signal extraction (non-oracle)** — stable / conflicted / uncertain / drifting / ensemble-agreement (in one embodiment, 2-of-3 across focus / final / mean-over-sequence readouts).
3. **(12) Decision function** — pre-registered thresholds, calibrated offline. Branches to **ACCEPT** (output proceeds) or **(14) SUPPRESS + reason code**.
4. **(16) Mode parameterization** — HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE; rows outside calibrated coverage route to human-review/suppress, never low-confidence accept.

```mermaid
flowchart TD
    O[MODEL OUTPUT] --> SX["(10) Signal extraction — non-oracle<br/>stable / conflicted / uncertain / drifting / ensemble-agreement"]
    SX --> DF{"(12) Decision function<br/>pre-registered thresholds<br/>calibrated OFFLINE on gold labels"}
    DF -->|accept| ACC[ACCEPT — output proceeds]
    DF -->|suppress| SUP["(14) SUPPRESS + reason code"]
    MODE["(16) Mode parameterization<br/>HIGH_PRECISION / BALANCED / MAX_COVERAGE_TRIAGE<br/>out-of-coverage → human-review or suppress"] -.governs.-> DF
    ACC --> NOTE["Calibration-time only: gold labels set thresholds.<br/>Inference-time: NO oracle."]
    SUP --> NOTE
```

---

## Figure C1 — Evidence Packet Assembly + Authenticated Delivery

**Caption:** Versioned, validated, reproducible, **tenant-scoped authenticated** audit artifact — the portable deliverable. Carries one of three verdicts and six proof chips. *(Reserved language: never "irrefutable / proven / guaranteed / certified.")*

**Logic (numbered elements):**
1. **INSPECTION** enters.
2. **(10) Packet assembly** — versioned schema; includes `trace_id`, the CAS expression, input, output, detected labels, causal-test results, verdict, provenance, hashes, and the **six proof chips** (`model_proof`, `cas_readout`, `causal_proof`, `control_proof`, `output_proof`, `packet_proof`). *(Legacy "15-field" count is **[VERIFY]**.)*
3. **(12) Schema validation** — reject malformed.
4. **(14) Rendering** — human-readable / markdown.
5. **(16) Reproducibility key** — `trace_id` (+ artifact hashes) → regeneration (bit-identical where deterministic).
6. **(18) Authenticated delivery** — REST + JWT, path-traversal guard, size cap, schema round-trip, **tenant-ownership scoping**, reviewer drawer.
7. **VERDICT** — exactly one of `ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS`; a customer-safe `ACCEPT` requires all six chips present/verified **and** the Figure F2 anchor gate.

```mermaid
flowchart TD
    I[INSPECTION] --> A10["(10) Packet assembly<br/>versioned schema + trace_id<br/>+ six proof chips"]
    A10 --> V12["(12) Schema validation — reject malformed"]
    V12 --> R14["(14) Rendering — human-readable / markdown"]
    R14 --> K16["(16) Reproducibility key<br/>trace_id → regeneration (bit-identical if deterministic)"]
    K16 --> D18["(18) Authenticated delivery<br/>REST + JWT, path-traversal guard, size cap,<br/>schema round-trip, TENANT-OWNERSHIP scoping, reviewer drawer"]
    D18 --> CHIPS["Six proof chips:<br/>model_proof · cas_readout · causal_proof<br/>control_proof · output_proof · packet_proof"]
    CHIPS --> VER{Verdict}
    VER --> ACC[ACCEPT — needs all six chips + F2 anchor gate]
    VER --> FLAG[FLAG_FOR_HUMAN_REVIEW]
    VER --> SUP[SUPPRESS]
    D18 --> OUT["Output: portable, third-party-verifiable evidence object per inspection<br/>(evidence-type vs claim-support labeled per claim)"]
```

---

## Figure D1 — Multi-Layer Trace + Readout-Position Blind-Spot Disambiguation

**Caption:** Separates **model-side** weakness from **readout-position** weakness. Answers "when can the tool NOT read this model/class?"

**Logic (numbered elements):**
1. **(10) Multi-layer capture** — activations at all layers (or a defined set).
2. **(12) Per-layer probe confidence** → confidence profile.
3. **(14) Trace classification** — stable-like vs. problem-like **[VERIFY classifier]**.
4. **(16) Blind-spot disambiguation rule** — branches to **MODEL-SIDE weakness** (low at all layers) or **READOUT-POSITION weakness** (high at some layers, missed by default readout).

```mermaid
flowchart TD
    C10["(10) Multi-layer capture (all layers)"] --> P12["(12) Per-layer probe confidence → confidence profile"]
    P12 --> T14["(14) Trace classification<br/>stable-like vs problem-like"]
    T14 --> R16{"(16) Blind-spot disambiguation rule"}
    R16 -->|low at all layers| MS[MODEL-SIDE weakness]
    R16 -->|high at some layers, default readout missed them| RP[READOUT-POSITION weakness]
    MS --> ANS["Auditable answer: when the tool cannot read this model/class<br/>(trace-classifier lacunarity ~VERIFY 0.0016)"]
    RP --> ANS
```

---

## Figure E1 — Matched-Control Causal Localization

**Caption:** Necessity + sufficiency + **bidirectional** control, **matched-control validated**, bit-exact patch-back. **Bounded to sparse-cover granularity — NOT single-neuron monosemantic.** Two parallel tracks: head-level and neuron-cover.

**Logic (numbered elements):**
- **Head-level track:** **(10) Necessity** — ablate heads → accuracy drops **[VERIFY 78%→19%]** (matched control does not). **(12) Sufficiency** — path-patch → recovery **[VERIFY →100%]**.
- **Neuron-cover track:** **(14) Identify sparse cover** (~**[VERIFY 1% width, e.g., 32/3072]**). **(16) Bidirectional control** — ablate → margin inverts; amplify → margin grows; polarity-flip → classification reverses. **(18) Patch-back** → bit-exact (err 0.0).

```mermaid
flowchart TD
    subgraph HEAD["HEAD-LEVEL"]
        N10["(10) Necessity: ablate heads<br/>accuracy drops VERIFY 78%→19%<br/>matched control does NOT"] --> S12["(12) Sufficiency: path-patch<br/>recovery VERIFY →100%"]
    end
    subgraph COVER["NEURON-COVER"]
        I14["(14) Identify sparse cover<br/>~VERIFY 1% width (e.g. 32/3072)"] --> B16["(16) Bidirectional control:<br/>ablate → margin inverts<br/>amplify → margin grows<br/>flip → classification reverses"]
        B16 --> PB18["(18) Patch-back → bit-exact (err 0.0)"]
    end
    HEAD --> CONC["All manipulations pass VERIFY 112/112 at p<10⁻³³ with matched controls.<br/>Bounded to sparse-cover granularity — NOT single-neuron monosemantic."]
    COVER --> CONC
```

---

## Figure F1 — Generation Readiness Gate (four-tier, zero-parameter, non-mutating)

**Caption:** Zero-parameter, **non-mutating**, four-tier action policy. Foreign-model forward path unchanged; default unattached; opt-in.

**Logic (numbered elements):**
1. **(10) Signal intake** — lacunarity + inversion flags + RPM/prerequisite satisfaction + Verification-Stack decision (+ gap / domain-confidence) **[VERIFY exact list]**.
2. **(12) Fixed (non-learned) decision policy** — zero learnable parameters → exactly one of **ALLOW / CAVEAT / CONSTRAIN / SUPPRESS**.
3. **(14) Audit trail** — action + contributing signals as reason codes.

```mermaid
flowchart TD
    S10["(10) Signal intake<br/>lacunarity + inversion flags + RPM satisfaction<br/>+ Verification-Stack decision"] --> P12{"(12) Fixed decision policy<br/>ZERO learnable parameters"}
    P12 --> ALLOW[ALLOW]
    P12 --> CAVEAT[CAVEAT]
    P12 --> CONSTRAIN[CONSTRAIN]
    P12 --> SUPPRESS[SUPPRESS]
    ALLOW --> AUD["(14) Audit trail — contributing signals as reason codes"]
    CAVEAT --> AUD
    CONSTRAIN --> AUD
    SUPPRESS --> AUD
    AUD --> NOTE["Foreign model forward path unchanged. Default unattached. Opt-in.<br/>Verdict map: allow→ACCEPT (if provenance complete) · caveat→FLAG ·<br/>constrain→FLAG (triage) / SUPPRESS (license-grade) · suppress→SUPPRESS"]
```

---

## Figure G1 — Two-Bridge Hidden-Content Detector (η₁/η₂) — PROTOTYPE TIER

**Caption:** Compares internal vs. emitted structure to surface withheld content. **Prototype — disclose as preliminary; not licensed for production accept/suppress.**

**Logic (numbered elements):**
1. **MODEL RUN** enters.
2. **(10) Internal profile** — η₁ reads hidden states → typed-class profile.
3. **(12) Emitted profile** — same typed-class reader (η₂) on emitted text → typed-class profile.
4. **(14) Divergence test** — class present internally but absent in emission → **WITHHELD-CONTENT FLAG** (typed-class granularity) **[VERIFY metric/threshold]**.

```mermaid
flowchart TD
    MR[MODEL RUN] --> H1["(10) Internal profile — η₁ reads hidden states → typed-class profile"]
    MR --> H2["(12) Emitted profile — η₂ same reader on emitted text → typed-class profile"]
    H1 --> DT["(14) Divergence test<br/>class present internally, absent in emission"]
    H2 --> DT
    DT --> FLAGW["WITHHELD-CONTENT FLAG (CAS-class granularity)"]
    FLAGW --> NOTE["PROTOTYPE TIER — disclose as preliminary.<br/>No confirmatory gate closed. Not licensed for production decisions."]
```

---

## Figure H1 — Sharded-Fleet Execution (NEW)

**Caption:** Frontier-scale audit of a model too large for one worker. Per-worker sub-harness; **fragment SHA-256 anti-misattribution**; **conservative-default** fleet gate; **raw activations never cross the wire**. Unified packet inherits the Figure F2 anchor gate.

> **[VERIFY orchestration vocabulary.]** The validated, code-grounded names are **Fleet Executor**, per-worker **sub-harness**, **Fleet Aggregator**, **fleet-topology verifier gate**. The user-supplied orchestration terms — **Scale Planner**, shard/layer **jobs**, **leases**, **receipts**, **merge-gate** — are shown as optional embodiments (dashed) and must be confirmed against the implementation before being recited in claims.

**Logic:**
1. **ENGLISH PROMPT** → **300B+ MODEL — SHARDED** across **Workers 1..N** (each holds a layer range; each has a hook).
2. **Planner** (optional "Scale Planner") assigns **layer-slice jobs**; workers (optional) **lease** jobs and return **receipts**.
3. **Per-worker SUB-HARNESS** — capture / probes / ablate / trace locally → **fragment SHA-256 commit** → **local chips + local verdict**.
4. Only **chips + hashes + local verdicts** travel the wire (no raw activations).
5. **FLEET AGGREGATOR** (optional "merge-gate") — validate fragment hashes (anti-misattribution), stitch multi-layer trace, reconcile shard seams, coordinate cross-worker ablation, recompute lacunarity.
6. **FLEET-TOPOLOGY VERIFIER GATE (conservative-default)** — any worker SUPPRESS → fleet SUPPRESS; any worker FLAG → fleet FLAG; any invalid fragment hash → fleet FLAG; any absent/timed-out worker → fleet FLAG; **only if all N ACCEPT + all hashes verify + topology complete** → fleet ACCEPT (preliminary).
7. **UNIFIED EVIDENCE PACKET** — six aggregate chips + fleet-topology manifest + per-worker fragment-hash list + per-worker local-verdict roll-up + preliminary fleet verdict.
8. → **Figure F2 anchor gate**: a preliminary fleet `ACCEPT` lacking any of the three anchor proofs is downgraded to `FLAG_FOR_HUMAN_REVIEW`.

```mermaid
flowchart TD
    P[ENGLISH PROMPT] --> SH[300B+ MODEL — SHARDED]
    PLAN["Planner (optional: Scale Planner)<br/>assigns layer-slice jobs;<br/>workers lease jobs, return receipts"] -.optional orchestration.-> SH
    SH --> W1[Worker 1<br/>Layers 1-20 + HOOK]
    SH --> W2[Worker 2<br/>Layers 21-40 + HOOK]
    SH --> WN[Worker N<br/>Layers .. + HOOK]
    W1 --> SHN1["SUB-HARNESS 1<br/>capture / probes / ablate / trace<br/>→ fragment SHA-256 commit<br/>→ local chips + local verdict"]
    W2 --> SHN2["SUB-HARNESS 2<br/>… → fragment SHA-256 → local chips + verdict"]
    WN --> SHNN["SUB-HARNESS N<br/>… → fragment SHA-256 → local chips + verdict"]
    SHN1 -->|chips + hashes + verdict<br/>NO raw activations| AGG
    SHN2 -->|chips + hashes + verdict| AGG
    SHNN -->|chips + hashes + verdict| AGG
    AGG["FLEET AGGREGATOR (optional: merge-gate)<br/>validate fragment hashes (anti-misattribution)<br/>stitch trace · reconcile seams · coordinate ablation · recompute lacunarity"] --> GATE{"FLEET-TOPOLOGY VERIFIER GATE<br/>conservative-default"}
    GATE -->|any worker SUPPRESS| FSUP[fleet = SUPPRESS]
    GATE -->|any FLAG / bad hash / absent worker| FFLAG[fleet = FLAG]
    GATE -->|ALL accept + all hashes verify + topology complete| FACC[fleet = ACCEPT — preliminary]
    FACC --> UP["UNIFIED EVIDENCE PACKET<br/>six aggregate chips + topology manifest<br/>+ per-worker fragment-hash list + per-worker verdict roll-up"]
    FSUP --> UP
    FFLAG --> UP
    UP --> F2[→ Figure F2 anchor gate<br/>preliminary fleet ACCEPT lacking any anchor proof → FLAG]
```

---

## Figure F2 — Integrity Chain + WORM Anchoring Detail (NEW; supports Mechanism F)

**Caption:** Five-layer tamper-EVIDENT integrity chain. **GOVERNANCE-mode, ~30-day rolling, operator-overridable** — **NOT immutable, NOT permanent, NOT COMPLIANCE-mode.** The `ACCEPT` verdict is gated on three anchor proofs; missing any → downgrade to `FLAG_FOR_HUMAN_REVIEW`.

**Logic:**
1. **Disk persistence** (single-instance restart-survival; **host-loss durability NOT proven**).
2. **Append-only hash chain** (each entry fingerprints the prior).
3. **Five-check verify endpoint** — payload hash · hash-log entry · chain continuity · local anchor manifest · external S3 round-trip; on any failure, name the failing check (never silent OK).
4. **External anchor** — S3 Object Lock **GOVERNANCE**, ~30-day rolling; `HeadObject` re-checks `ObjectLockMode==GOVERNANCE` and `RetainUntilDate` in future on each verify; **operator-overridable via `s3:BypassGovernanceRetention`** → guarantee is tamper-evidence on re-verify, not immutability.
5. **ACCEPT-requires-anchor gate** — needs (a) anchor written, (b) re-read hash-match, (c) retention active; missing any → **FLAG_FOR_HUMAN_REVIEW**.
6. **Three-state trust UI** — "S3 object verified" / "Anchored to S3" / "S3 verify failed"; never silently upgrades.

```mermaid
flowchart TD
    DP["Layer 1: Disk persistence<br/>single-instance restart-survival<br/>(host-loss durability NOT proven)"] --> HC["Layer 2: Append-only hash chain<br/>each entry fingerprints the prior"]
    HC --> V5{"Layer 3: Five-check verify endpoint<br/>1 payload hash · 2 hash-log · 3 chain continuity<br/>4 local anchor manifest · 5 external S3 round-trip"}
    V5 -->|any check fails| NAMED["partial_mismatch — names the failing check<br/>(never a silent OK)"]
    V5 -->|all pass| ANCHOR["Layer 4: External anchor<br/>S3 Object Lock GOVERNANCE, ~30-day rolling<br/>HeadObject re-check each verify<br/>operator-overridable (s3:BypassGovernanceRetention)<br/>→ tamper-EVIDENT, NOT immutable/permanent/COMPLIANCE"]
    ANCHOR --> GATE{"Layer 5: ACCEPT-requires-anchor gate<br/>(a) anchor written (b) re-read match (c) retention active"}
    GATE -->|all three present| ACC[ACCEPT permitted]
    GATE -->|any missing| FLAG[downgrade → FLAG_FOR_HUMAN_REVIEW]
    ACC --> UI["Three-state trust UI:<br/>S3 object verified · Anchored to S3 · S3 verify failed<br/>(never silently upgrades trust)"]
    FLAG --> UI
```

---

## Illustrator / attorney notes

- **Re-draw, do not trace.** The legacy raster figures are degraded; use these descriptions + mermaid as the corrected source.
- **Keep numerals consistent** (10, 12, 14, …) with §5 of the spec so the text's references resolve.
- **Honest labels only.** On Figure F2/H1, do not let "immutable / permanent / certified / guaranteed" re-enter; the anchor is **tamper-evident, operator-overridable, ~30-day GOVERNANCE**.
- **Prototype marking.** Figure G1 must visibly carry "PROTOTYPE — preliminary."
- **No headline results in figures.** Drop any standing-`ACCEPT` or effect-size claims from figure faces; those belong (with `[VERIFY]`) in the Example-Results prose, labeled offline-validation where applicable.
- **Fleet orchestration terms** (Scale Planner / lease / receipt / merge-gate) are shown dashed/optional pending implementation confirmation; the solid path uses the validated terms (Fleet Executor / sub-harness / Fleet Aggregator / fleet-topology gate).

**END — CAS_provisional_flowcharts_described.md — DRAFT for attorney/illustrator. Not legal advice. Keep confidential.**
