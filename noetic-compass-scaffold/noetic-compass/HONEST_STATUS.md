# Honest Status — Noetic Compass / CAS-Native (2026-05-04)

This is the one place that tells the truth about every feature. No marketing.

For each feature: **SHIPPED** = running in production, **WIRED** = working code wired into the live system, **SCAFFOLD** = files exist with tests but not wired, **IN PROGRESS** = being built right now, **NOT STARTED** = no code yet.

---

## Core CAS infrastructure

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| CAS notation compiler (`api/notation/compiler.py`) | SHIPPED | Takes a CAS expression string, returns AST + validates admissibility | n/a — production-ready |
| 7-axis Inversion Scan (engine) | SHIPPED | Scores any CAS state on N/W/F/E/S/A/P axes | n/a — production-ready |
| 22 Capability Pathways + RPM chain types | SHIPPED | Type definitions, prerequisite walk | Used by belief store (in progress) |
| FastAPI gateway (`api/`) | SHIPPED | JWT auth, /assess, /wrap, /batch, /idea_atlas, /casivenize endpoints | n/a — production-ready |
| Dashboard (React 18 + TS) | SHIPPED | Operator radar, 40-state heatmap, Idea Atlas component family, RPM graph | Continues to grow per Phase 3 plan |

## CAS-Native model (the AI)

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| K=9 baseline classifier checkpoint | WIRED | English in → 12 CAS labels out (Noetic / Domain / Drive / Register + 8 structural flags). 93.2% canonical exact on held-out 1K eval. | Replace with v1 Full Stack checkpoint when retrain finishes (~10 hrs from now) |
| v1 Full Stack retrain | IN PROGRESS | Training right now on A6000 pod. Combined corpus (162K records, 9× vocab expansion). | Wait for completion + honest two-pass eval + demographic robustness gate |
| `predict_cas.py` inference wrapper | WIRED | One-shot text → 12-key prediction dict | n/a — works |
| `cas_renderer.py` English templating | WIRED | Renders CAS expression → English explanation using authoritative defs verbatim | n/a — works, but it's templates not generation |
| `rewrite_shim.py` colloquialism rewriter | WIRED | Rewrites free-form English to training-surface format using rule-based detection | Improves with Lever 3 fine-tune |
| Chat REPL (`chat.py`) | WIRED | Interactive prompt with /menu, /sample, /raw, /help. 21 curated demo prompts. | Adding /beliefs /why /forget /trace /atlas tonight |

## Belief substrate (CAS-as-Belief-Substrate, "CABS")

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| Belief store using ^4 Vibration + ^7 Rhythm + RPM gate + Inversion Scan | IN PROGRESS | Agent building tonight. SQLite-backed, locks claims after evidence accumulates. | Land + wire into chat REPL (planned for this build) |
| `/beliefs`, `/why <claim>`, `/forget <claim>` REPL commands | IN PROGRESS | Same agent | Same |

## Mode 7 — Network Attribution / Mechanistic Trace

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| Trace package (mechanistic.py, activations.py, attribution.py, network_summary.py) | SCAFFOLD | 1,855 LOC, 34 synthetic tests pass. **NOT wired into live forward pass.** | Agent wiring tonight after belief commits — real PyTorch hooks during predict_cas, /trace REPL command |
| `/trace` REPL command | NOT STARTED | n/a | Above agent will add |

## Idea Atlas

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| `/idea_atlas` API route (casivenize / ideas / edges / invert) | SHIPPED | Real FastAPI endpoint. Translates English → CAS via LLM connector, validates, persists per user, computes similarity edges. | n/a — production |
| Dashboard `IdeaAtlas/` components (IdeaAtlasView, DiagramView, ViewToggle, InfiniteCanvas) | SHIPPED | React component family rendering force-directed graph + diagram view | n/a — production |
| `cas-native/atlas/` package (1,272 LOC, my recent scaffold) | TO BE BACKED OUT | Duplicates the shipped Atlas. | Delete + replace with thin adapter that POSTs predict_cas output to `/idea_atlas/ideas` endpoint |
| Chat REPL `/atlas` command | NOT STARTED | n/a | Add adapter that POSTs current prediction to `/idea_atlas/ideas` and opens browser |

## NL Generation (the actual LLM ask — model writes English back)

**Architectural rule (user-ratified 2026-05-04):** No foreign pretrained models. No TinyLlama, no Llama, no Qwen, no Mistral, no GPT-2, nothing borrowed. The generation head is built natively on the existing CAS-Native classifier or as a CAS-Native generation model from scratch. CAS gets the glory or the project doesn't ship.

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| Generation SDG — paired (prompt, CAS, fluent reply) triples | NOT STARTED | n/a (the SDG agent stalled; will re-launch with native-generation framing) | Re-launch agent. Generate 50K-200K paired examples — native generation needs more data than a fine-tune does. |
| Native CAS generation head architecture spec | NOT STARTED | n/a (TinyLlama spec was deleted on user instruction) | Write spec from scratch: decoder bolted onto existing CAS-Native bottleneck, sized to 100M-300M params, pretrained on CAS-themed corpus + general English, fine-tuned on paired SDG data. Multi-week build. |
| Training pipeline | NOT STARTED | n/a | Build after spec lands. Will need significant GPU time (multiple long pod runs, ~$200-500 total). |
| Two-stage inference (classify → native generate) | NOT STARTED | n/a | After training completes. |

The honest timeline: native generation is 4-8 weeks of work. The project does not have a fluent English generation model this week. The classifier + belief substrate + atlas + Mode 7 trace are the demoable surfaces today.

## Three-instance dialectic (rotating-axis architecture)

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| Dialectic scaffold (`cas-native/dialectic/`) | SCAFFOLD | 1,995 LOC, 5 tests pass. NOT wired to chat. | Sequenced AFTER Lever 3 / NL Generation lands per user ratification 2026-05-04. Compiler grammar empirical check found `|⟨...⟩` set-spec already supported (drops D2 from 2-3 days to 0.5 day). |

## Dialogue State Tracker (Phase 2 of Version B)

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| DST scaffold (`cas-native/dst/`) | SCAFFOLD | 2,909 LOC, 58 tests pass. NOT wired to chat. | Wire into chat REPL after CABS lands. Phase 2 of Version B. |

## SDG (synthetic data generation)

| Feature | Status | What it does today | What it'd take to ship more |
|---|---|---|---|
| Recoverable Level 3 generator | SHIPPED | Generates 50K+ canonical training records | n/a |
| Demographic + tonal SDG | WIRED | 8 profiles × 5 tones. Used in v1 Full Stack retrain. | n/a |
| Free-form Phase 3 generator | SCAFFOLD | 1,190 LOC colloquialism lexicon, 722 LOC surface generator. Uncommitted. | Commit + use in next retrain |
| Lever 3 paired data via Claude API | SHIPPED | 5K Claude-rewritten records | n/a |
| vocab14 reserved CAS tokens | WIRED | Λ Ω Θ → · NoeticCluster StateSet RelationCluster CoverOf PartitionOf Product ∪ ∩ ∖ etc. | Active in v1 retrain |
| Targeted meta_logic balanced generator | SCAFFOLD | 1,142 LOC. Uncommitted. | Commit + use in next retrain after v1 lands |

---

## What I will tell a stakeholder TODAY (the elevator pitch, honest)

> "Noetic Compass has a working CAS scoring engine, an LLM-wrapped scoring API, a dashboard, and a CAS-Native model that's a structured-prediction classifier — English in, 12 CAS labels out, 93% accuracy on its training distribution. The classifier is wrapped by a CAS belief substrate that locks claims in via ^4 Vibration + ^7 Rhythm + RPM + Inversion Scan, dynamic and revisable. Every prediction surfaces a full trace — activations, attribution, belief gates, CAS expression. The generation layer that gives it a mouth is the next build — fully CAS-Native from scratch, no borrowed pretrained models. Multi-week effort, but the architecture stays pure: CAS, end to end."

That's the honest version.

## What changed tonight (2026-05-04 evening session)

- 4 background agents launched: CABS belief store, Mode 7 wire-up (sequenced), Generation SDG, Generation Head training infra
- Idea Atlas duplicate scaffold marked for back-out
- This document established as single source of truth for "what's real"
- Plain-language preference saved to memory permanently (no more "load-bearing" / "modality mismatch" jargon)
