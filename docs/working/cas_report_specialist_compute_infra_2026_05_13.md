# The CAS Report — Specialist Brief: Compute and Infrastructure

**Date:** 2026-05-13
**Lane:** What a 1T-parameter CAS-Native model would TAKE — money, hardware, time.
**Anchor:** Stage 3 baseline (`docs/working/candidate_e/stage3_wrapup_2026_05_13.md`) — 150M model, ~$0.50 per stage on RunPod A6000, ~$10 cumulative compute through Stage 3.

---

## 1. TL;DR

- **1T CAS-Native is institutional-scale work, not garage-scale.** Realistic model-training compute: **$60M–$150M**. Corpus generation (the cost the user has not yet faced): **$30M–$150M**. Total program: **$100M–$300M**, multi-year.
- **Hardware required:** ~8k–16k H100s for the training run (or B100 equivalents), plus a separate, almost-as-large data-generation cluster. This is OpenAI / Anthropic / Google / Meta / xAI infrastructure. Not rentable end-to-end on RunPod.
- **Timeline:** 24–48 months from a green-lit institutional commitment. Past the end of Codex's earlier trajectory table.
- **The institutional path is the only path.** Stage 3 + Living Thought Atlas + a credible 300M-700M validation is the pitch artifact. The 1T number is the destination on the slide, not next quarter's invoice.
- **Going from $10 to ~$100M is roughly four orders of magnitude.** The cost gap from the user's current experience to a real 1T run is bigger than the gap from a laptop to Stage 3, done twice.

---

## 2. Training compute estimate — walking up the scaling curve

Dense-model assumptions: Chinchilla-optimal tokens ≈ 20× params. FLOPs ≈ 6 × params × tokens. Realized H100 throughput ~150 TFLOPs/s BF16 (35–50% MFU). GPU-hour cost $2 (deep institutional lease) to $4 (mid-tier cloud). Corpus costs listed separately and detailed in §3.

| Scale | Params | Tokens (20×) | FLOPs | H100-hours | Cluster + wall-clock | Compute (low) | Compute (high) | Corpus (rough, §3) |
|---|---|---|---|---|---|---|---|---|
| Current | 150M | ~1B | 9 × 10^17 | ~2 | 1× A6000 × 1 hr | ~$0.50 actual | ~$1 | ~zero |
| Validation | 700M | 14B | 5.9 × 10^19 | ~110 | 8× H100 × 14 hr | ~$1.8k | ~$5k | ~$25k–$100k |
| Capability | 7B | 140B | 5.9 × 10^21 | ~11k | 64× H100 × 7 days | ~$25k | ~$90k | ~$0.5M–$3M |
| Emergence | 70B | 1.4T | 5.9 × 10^23 | ~1.1M | 1024× H100 × 45 days | ~$2.2M | ~$8.8M | ~$5M–$30M |
| Near-frontier | 300B | 6T | 1.08 × 10^25 | ~20M | 4096× H100 × 200 days | ~$40M | ~$160M | ~$15M–$80M |
| **Target** | **1T** | **20T** | **1.2 × 10^26** | **~220M** | **~8192× H100 × 1 year** | **~$60M** | **~$150M** | **~$30M–$150M** |

Reference points: GPT-3 175B ~$5-10M. LLaMA-65B ~$5M. Rumored GPT-4 ~1.8T MoE ~$60-100M. A 1T DENSE model on H100 lands comfortably in the GPT-4 cost band, with the corpus on top.

**The bullet that matters:** $10 → $1.8k (Stage 3 → 700M) is personal budget. $1.8k → $25k (700M → 7B) is partner-funded. $25k → $2–9M (7B → 70B) is institutional. Past 70B is a named program with a budget number on a 10-K line.

---

## 3. The Chinchilla problem — the load-bearing cost the user has not yet faced

Current Path D corpus: ~3K records / ~2.5 MB. Chinchilla-optimal at 1T: ~20T tokens. That is roughly **40,000× more corpus than exists**. Raw internet text does not work — CAS-Native by design needs CAS-shaped pairs, structured-prediction targets, compiler-validated round-trips.

Three options. None of them cheap:

**Option A — Generate with frontier LLMs.** At Wave 2.5 actuals (~$0.006/certified record, ~700 tokens/record), 20T tokens of certified data ≈ **$170M just in inference fees**, before audit and filter rebuilds. At loose bulk quality ($0.001/record), ≈ **$30M–$50M** but quality risk compounds (the v0 audit already showed shape-without-content slipping through).

**Option B — Bootstrap.** Train a 100B CAS-Native (~$2–9M compute) and use it to generate the 20T-token corpus for the 1T run (~$20–60M inference on owned cluster). Cheaper than Option A, but bootstrap-loop quality collapse is a known failure mode and has never been validated for a brand-new architecture.

**Option C — CAS-annotate a frontier corpus.** Take a 20T-token English corpus and run CAS extraction / compiler validation as preprocessing. ~$5–20M. But annotation quality depends on the annotator; if a frontier LLM is the annotator, you are using a foreign model in the pipeline.

**The forbidden-model question the user has not yet faced.** Memory `feedback_no_foreign_architecture_cas_only.md` is unambiguous about *production serving*. Does it extend to *corpus generation*? Wave 2.5 already uses Haiku as drafter — precedent says no. Strict reading would force Option B (bootstrap-only). Surface this as an explicit user decision: "no foreign weights in serving" vs "no foreign models anywhere." The financial gap between readings is roughly $100M.

**At what scale does corpus cost exceed training cost?** Crossover lands between 7B and 70B:
- Option A certified: crossover already at 7B.
- Option A bulk: crossover near 70B.
- Option B bootstrap: crossover near 100B–300B, contingent on quality not collapsing.

**Past ~70B, the corpus is the program, not the model.** Most program effort becomes data engineering and audit, not GPU hours.

---

## 4. Inference infrastructure — serving 1T live for the Atlas

The Living Thought Atlas renders live thought formation, replay, ghost branches, Inversion Replay. Hard constraints at 1T:

- **Memory.** Weights at fp16 ≈ 2 TB; int8 ≈ 1 TB; int4 ≈ 500 GB. Per replica: **24–32 H100s** in one rack with InfiniBand.
- **KV cache.** Per-token KV ~250 KB; a 4K-context turn ~1 GB per request. 32 concurrent users ≈ 32 GB of KV pressure — tractable.
- **Single-turn latency.** 1T dense forward ~250–500 ms per 100 output tokens at standard TP serving + compiler ~5–50 ms + trace assembly ~10–30 ms. Realistic per-turn: **600–1200 ms**. Chat-pace yes; live 30 fps Atlas rendering only if streaming is per-token, not per-utterance. The current `<500 ms` performance target is for the existing Wrap pipeline, not 1T generation.
- **Throughput.** ~20–40 concurrent users per replica at int8. A 5–10-attendee live demo fits one replica.
- **Cost per query.** 24 H100s × $4/hr × 3-sec request ≈ **$0.08 per turn** at full load, ~$0.50 at low concurrency. GPT-4 API lands at ~$0.05–0.20 per turn. So 1T CAS-Native is in the GPT-4 cost band, with the load-bearing advantage that *every reply ships with a full Mode 7 trace included*, where GPT-4 ships zero traceability for the same money.

---

## 5. Parallelization patterns specific to CAS-Native

Where the architecture is *easier* than a standard transformer:
- **Tiny heads replicate freely.** 9 typed slot heads, 40-dim Δ°₃₉ simplex, 7 Drive heads, 4 Register marginals — together well under 1% of parameters at 1T. Zero communication overhead.
- **Standard TP/PP for the backbone.** No CAS-specific tricks required at the transformer trunk.
- **Pointer-generator copy attention** parallelizes like normal attention.

Where it is *harder*:
- **Compiler validation is the serving bottleneck.** `api/notation/compiler.py` is CPU Python. At 1T-scale concurrent serving, compiler will dominate throughput unless (a) the Rust port (`cas-engine/`, already in `CLAUDE.md` Phase 1) replaces it, or (b) validation moves off the critical path (async; Atlas tolerates post-hoc admissibility verdict).
- **Trace assembly per-utterance is currently atomic.** At 1T with 200 positions × top-5 ghost branches, this must become position-parallel and pre-cached, not request-blocking.

Net: CAS-Native is *more* serving-friendly than a standard transformer in the head stack, *less* serving-friendly in the compiler-validation path. The fix is engineering (Rust compiler + async), not architecture.

---

## 6. Per-utterance trace volume at 1T

From schema (`docs/working/cas_trace_schema_v0_2026_05_13.md`):
- Per-position record at "full" capture today: ~700–900 bytes.
- At 1T (~96 decoder blocks instead of 6): +~720 bytes for `layer_l2`. New total: **~1.5–2 KB per position**.
- 200 output positions × 1.8 KB = **~360 KB per utterance "full"**.
- Plus encoder + attribution + admissibility + summary + timing: **~400 KB per utterance**.

At `capture_level="raw"` (full simplex trajectory + full LM logits per position):
- LM logits per position at 50k vocab × 4 bytes = 200 KB; × 200 positions = **~40 MB per utterance**. Unworkable for live UI.

**Atlas rendering thresholds:**
- WebGL handles 5k–50k nodes interactively before mandatory LOD culling.
- 1T per-utterance: ~200 positions × (1 main + 3 ghost slot + 5 ghost LM + 5 ghost copy) ≈ **3,000 nodes**. Comfortable.
- 20-turn session: ~60,000 nodes. **LOD culling mandatory at session level.**
- Cross-session Idea Atlas: millions. The Atlas is structurally a graph database (Neo4j-class) at that scale.

**Sampling crossover.** "Full" capture is reasonable up to ~30B–100B. Past that, `raw` capture explodes and must be replaced with summaries + on-demand re-decoding from saved replay seeds. The v0 schema already flagged `replay_seed_state` for v1+; at 1T, per-position seed is ~24 KB (96-layer × hidden 8192 × bf16), so a 200-position utterance is ~5 MB of replay seed — keeping seeds for every utterance multiplies trace storage by 10–20×.

---

## 7. The institutional path

$100M–$300M total program is institutional spend. The user's personal-budget posture cannot reach it. Plausible patrons in rough fit order:

- **Amazon (user's employer).** Closest natural patron — AWS has the H100 inventory and strategic interest in differentiated AI safety capability. Pitch: "Make AI reasoning inspectable in a way GPT-4 cannot, on AWS infrastructure, for AWS enterprise customers." Vehicles: AWS internal research budget, Bedrock differentiated capability, Q-Business reasoning audit.
- **Anthropic.** Mission-aligned (interpretability is their stated north star). Likely partner/co-author, not full funder.
- **Google DeepMind.** TPU pool, mech-interp budget. Likely partner.
- **DARPA / similar defense interpretability programs.** Multi-million to tens-of-millions scale. Defense IP encumbrance is a real consideration.
- **NSF / NIH AI interpretability grants.** $1–5M cap. Useful for 700M–7B validation, not 70B+.
- **Meta FAIR alignment.** Compute pool exists. Open-weights culture clashes with USPTO #64/037,173 — poor fit at 1T, decent at 7B paper scale.

**What deliverable convinces them?** Per `project_cas_native_demo_v0_amazon_pitch_target_2026_05_13.md`: the Stage 3 demo + Living Thought Atlas + 300M-700M scaling validation. Without the 1T destination on the slide, the entry-point looks like "small interesting experiment." With it, the entry-point looks like "first verifiable step toward inspectable frontier AI." Same demo, different framing — the 1T speculation is the destination, not the next deliverable.

---

## 8. Phased compute escalation

| Step | Scale | Program cost | Funding | Validates |
|---|---|---|---|---|
| Done | 150M | ~$10 cumulative | Personal | Structural prior holds at 150M |
| Next 6 mo | 300M–700M | ~$5k–25k + ~$25k–100k corpus | Personal + first small grant | Scaling holds for CAS-Native specifically |
| Year 1 | 7B | ~$25k–90k + ~$0.5–3M corpus | Amazon internal / NSF / partner | Emergence onset; first paper |
| Year 2-3 | 70B | ~$2–9M + ~$5–30M corpus | Institutional named program | Frontier viability |
| Year 3-5 | 1T | ~$60–150M + ~$30–150M corpus | Full institutional commitment | The destination |

Each step is a separate pitch. None skippable — frontier-scale patrons do not commit to $100M without prior-stage validation. **Highest-leverage move right now:** make the 300M-700M validation cheap and unambiguous. It converts the Stage 3 result into the first artifact that crosses the institutional-funding threshold.

---

## 9. Inference engineering hot-takes at 1T

Serving the Atlas live at 1T is its own engineering program. Subproblems with named owners:

- **Streaming per-position trace to the UI.** SSE or WebSockets; cannot wait for full-utterance trace assembly. Today atomic; at 1T must be incremental.
- **Caching simplex trajectories across utterances.** A user's recurring CAS pattern doesn't change rapidly turn-to-turn. Cache server-side; ship deltas.
- **Sub-100 ms Inversion Replay.** Click-a-node-to-replay needs either (a) cached decoder hidden state at every recent position (multiplies trace storage ~10×) or (b) blazing 1T inference. (a) is cheaper; real tradeoff.
- **Multi-user concurrency.** ~20–40 per replica at int8. Public beta with hundreds requires multiple replicas. Standard scale-out.
- **Cost per demo.** 90-min 5-attendee 200-turn demo: ~$10–100. 500-attendee unveiling with 3 personal turns each: ~$200–2000. Public beta 10k users × 30 turns/week: ~$50k–500k/week — needs a funding plan.
- **Atlas-as-graph-database.** Per-session Atlas ~60k nodes; per-user-lifetime grows linearly. At population scale this is Neo4j-class, not per-session JSON. Design for it now; retrofitting later is expensive.

---

## 10. Open infra questions

1. **Does "no foreign pretrained models" extend to corpus generation, or only the serving graph?** Wave 2.5 precedent says pipeline-permissive. The user has not stated it explicitly. ~$100M financial difference.
2. **Is bootstrap data generation quality-viable for CAS-Native specifically?** Never validated for a new architecture. "Model collapse" is a known risk. Probably a paper-sized question on its own, settled at 7B scale before committing 1T to the bootstrap path.
3. **At what specific parameter scale does corpus cost exceed model-compute cost?** §3 estimates 7B–70B depending on Option A/B/C. Tightening requires Path D unit-economic measurement at 700M and 7B intermediate runs.
4. **Can the Rust compiler (`cas-engine/`) sustain per-token admissibility at 1T serving throughput?** The Atlas live-rendering vision depends on yes. Never measured at 1T-class request volume.
5. **Replay seed state retention policy.** Always vs only-on-flagged-utterances is a 10–20× storage decision. Not free.

---

**Document ends.** The architecture, emergence, and safety lanes belong to the parallel specialist docs. The compute-and-infra line is honest about cost; the destination is real; the path is institutional. The Stage 3 demo + Living Thought Atlas + 300M-700M validation is the artifact that crosses the threshold from "interesting experiment" to "fundable program." The 1T number is what makes the slide worth presenting.
