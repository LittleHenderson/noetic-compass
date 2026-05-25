# Atlas Viewer — Alpha v0 Demo Script (5-minute walkthrough)

**Date:** 2026-05-24
**Audience:** investor or technical reviewer
**Deployed URL:** https://atlas-viewer-app.onrender.com/cockpit
**Mode:** LIVE (preferred) with Replay fallback
**Backend:** atlas-viewer-app (Render) → noetic-compass-api (Render, `/api/atlas/live/*`) → RunPod live-trace worker (Pythia-160M, 24-token cap)

---

## Section 1 — Setup checklist (do this 10 minutes before the meeting)

Work top to bottom. Anything red, stop and decide whether to demo LIVE or fall back to Replay before the stakeholder joins.

1. **Browser.** Chrome or Edge, latest stable. Not Safari — Three.js plus the Server-Sent Events stream behave unevenly in Safari at the moment.
2. **One clean tab.** Pre-load `https://atlas-viewer-app.onrender.com/cockpit`. Wait for the 3D scene to render and the control bar to show LIVE / REPLAY buttons. If the page shows "Failed to load Atlas Viewer fixtures," hard-refresh once.
3. **Confirm LIVE mode is actually real.** PR #48 ships `/atlas/live/health/realmode` (worker + API proxy) plus a one-shot verification script at `noetic-compass-scaffold/noetic-compass/scripts/verify_atlas_live.py`. **Real-mode is not just `is_real_model: true` — that field alone can be true on a cold worker that has never loaded weights.** Real-mode means all proof fields hold simultaneously:
   - `verdict: "REAL_PYTHIA_WEIGHTS_LOADED"`
   - `is_real_model: true`
   - `model_loaded: true` (Pythia weights actually in memory, not just "demo mode not forced")
   - `load_error: null` (no prior load failure recorded)
   - `fake_runtime_env: false` (`LIVE_TRACE_DEMO_MODE` not set)
   - `manifest_is_real_model: true`
   - plus `model_id == "EleutherAI/pythia-160m"`

   Decision tree:
   - **Preferred — run the script:** `python scripts/verify_atlas_live.py`. Exit 0 + green checklist → demo LIVE. Exit 1 → read which line is red, see below.
   - **Automated browser/API proof:** from `atlas-viewer/`, run `ATLAS_LIVE_E2E=1 npx playwright test e2e/live.api.spec.ts --project=chromium` for realmode only. Add `ATLAS_LIVE_INVITE_CODE=<alpha-code>` to also create a gated LIVE session and assert the SSE stream emits a `manifest` with `is_real_model: true` plus `token` events. This test is intentionally opt-in and fails on fake-mode.
   - **Any red on the real-mode proof fields → demo as Replay, not LIVE.** Most common failure: `model_loaded: false`. That means the worker is reachable but hasn't loaded Pythia yet — the first LIVE click in the cockpit will warm-load (slow, may time out). Either warm the worker first by hitting `/atlas/live/session` once, then re-run the script, or demo Replay and frame it as "this is a recorded Pythia-160M trace; live mode requires the RunPod worker to have warm weights."
   - **`load_error` is a non-null string:** Pythia tried to load and failed (HF download timeout, etc.). The error message tells you what failed. Demo Replay.
   - **Manual fallback if the script can't run:** the SSE `manifest` event carries `is_real_model` and `model_id` only — `model_loaded`, `load_error`, and `fake_runtime_env` come from the `/atlas/live/health/realmode` endpoint, not from the SSE stream. So do both: (a) hit `https://noetic-compass-api.onrender.com/atlas/live/health/realmode` in a tab and confirm the proof fields green; (b) click LIVE in the cockpit, open Chrome DevTools → Network → find the SSE stream under `/atlas/live/session/<id>/events`, expand the first event named `manifest`, and confirm `is_real_model: true`. Both must be true.
4. **DevTools open, silent.** Network tab visible. Filter by `atlas/live`. You will not narrate from this — it is your evidence if a viewer asks "is this really running?"
5. **Invite code in clipboard, not on screen.** The LIVE path is gated by an `X-Atlas-Invite-Code` header (see `api/routes/atlas_live.py`). The cockpit attaches this from the user's session; if the request 401s in Network, your invite code is missing or expired. Re-fetch from the project alpha allowlist and reload.
6. **Backup ready.** Keep this script open in another tab. If LIVE fails mid-meeting, switch to the wording in Section 4.

---

## Section 2 — Beat-by-beat narrative (5 minutes)

The full demo runs from one tab on `/cockpit`. Don't switch tabs unless you are showing the evidence trace in DevTools.

### 0:00 — 0:30 · Landing (30s)

> "This is Atlas Viewer. It shows what's happening inside a small language model while it generates text. The 3D scene is the model's layers and neurons. The mapping you see — those colored connections, the highlighted neurons — is our cognitive framework projected onto the model's internal state."

Visual: cockpit loaded, neural-net scene visible at rest, control bar at the top.

What you are setting up: "watch what happens inside the model" plus "the visualization is grounded, not decorative."

### 0:30 — 1:30 · LIVE prompt and stream (60s)

1. Click the **LIVE** button on the control bar (top left of the playback segment).
2. Use **Prompt 1** from Section 3 ("The shoreline at dawn was").
3. Tokens start streaming.

Point at three things as they happen:

- **Tokens, left to right.** "These are tokens the model is producing in real time. Capped at 24 tokens per session right now."
- **Neurons lighting up in the layer stack.** "Each pulse is a probe firing on one of Pythia-160M's actual residual-stream activations as that token is generated."
- **Curved edges drawing back across the scene.** "Those edges are Mode 7 — token-to-token attention attribution. For each token the model just emitted, the edges point back to the earlier tokens in the prompt that the model attended to most heavily when producing it. It is a real attention path, derived from the model's last-layer attention pattern, not a metaphor and not a neuron-to-neuron link."

Say once, plainly: "Pythia-160M is a 160-million-parameter model. It is small, on purpose, so we can show every layer. It will produce coherent text on simple prompts and stumble on harder ones — both are useful."

### 1:30 — 2:30 · CAS vs baseline evidence (60s)

Open the left panel's evidence card (titled "CAS beats the baseline on the validated jobs below"). Walk through these three rows from `casBenchmarkEvidence.ts`:

1. **Internal state readout.** "When we probe the model's hidden state for our framework's categories, the probe scores 78.6% on Pythia and 89.8% on the 40-element readout. A text-only baseline is 28.9 to 39.7 percentage points lower. If the signal were just in surface wording, the hidden-state probe could not beat text by that much."
2. **Causal removal.** "When we remove the cognitive direction from the model's internals, the readout collapses from 78.6% to 3.57%. That is exact 1-in-28 chance. Random ablations had zero disruption. That's the causal test."
3. **Accept/suppress verification.** "When the verifier accepts an output, it is 98–99% accurate on OLMo and Qwen at roughly 72–75% coverage. The coverage matters — we are not pretending to score everything; we are flagging which outputs to trust, suppress, or review."

End with the boundary card under it: "These are validated benchmark claims, not a claim that the framework controls every model, every token, or every failure mode."

(Translation note for technical reviewers who ask: the framework being projected onto the model is the Cognitive Architecture System — a typed state space of ten primitives, four domains, seven drives, four registers. Every probe targets a coordinate in that space.)

### 2:30 — 3:30 · Evidence Drawer (60s)

Click a neuron in the 3D scene (or any active token in the timeline). The Evidence Drawer slides in from the right.

Show one of two states depending on what the drawer fetches:

- **If a trace ID is present and the API returns an Evidence Packet** (the happy path PR #46 enables): the drawer displays the full packet — schema_version, trace_id, input/output, provenance, hashes, claim_levels, copy_slot_trace, caveats. "Every visual element here has a trace ID. That ID is sent to `/evidence/<trace_id>` on the API. What you see below is the actual stored Evidence Packet — sample-level proof, hashed for integrity."
- **If there is no trace ID, or the fetch fails:** the drawer shows the local reference metadata with one of these explicit labels at the top — "Evidence Packet fetch failed; showing only the local reference metadata," or "Evidence Packet requested; showing local reference metadata while packet data is unavailable," or "Local replay metadata only; not presenting this as a verified Evidence Packet." "When we don't have a packet, we say so plainly. We do not paint a local fixture as a verified trace."

Read whichever label is showing out loud. **This is the honesty surface.** Don't gloss it. The investor wants to see whether you over-claim — show them you don't. The fallback label literally reads "not presenting this as a verified Evidence Packet" — that's the point.

### 3:30 — 4:30 · Method knob change (60s)

Open the right panel's Method Knobs section. Two paths depending on what shipped:

- **If Agent B's knob-proof work is merged** (control bar shows the method-toggle wiring to the worker, e.g., LIVE re-runs when you toggle): pick one knob — for example, `inversion_scan.severity_threshold`, or `foundation_probe.layer_range`. Change it. Run a second LIVE session with **Prompt 4** (same prompt as before if you want a clean comparison). Show that the trace visibly differs — different neurons light, different Mode 7 edges. "Same prompt, different method config. The trace responds. That means the visualization is reading the worker, not playing back a canned recording."
- **If Agent B is not yet merged:** say "for the alpha demo we are showing two pre-recorded traces side-by-side here — the full method-knob proof lands when Agent B's worker wiring merges." Then either skip ahead to 4:30 or, if you have the two-trace toggle locally, show that.

### 4:30 — 5:00 · Close (30s)

> "Three sentences. One: Atlas Viewer is a real-time interpretability surface for language models, with every visual element grounded in a verification artifact. Two: next on the roadmap is the concordance harness — does the visualization tell the same story across model families like OLMo and Qwen — plus a scenario library that covers ethics-relevant prompts. Three: we are asking you for [pick one before the meeting: alpha-partner intros, a follow-up technical session with your team, or a check-in in eight weeks when the concordance harness lands]."

End on the cockpit, not on a slide.

---

## Section 3 — Prepared prompts

All prompts are bounded by the 24-token cap in `live-trace-worker/app/runtime/event_stream.py:110` (`max_new = min(req.max_new_tokens, 24)`). Keep continuations short.

### Prompt 1 — Easy narrative (use for opening LIVE beat)

- **Text:** `The shoreline at dawn was`
- **max_new_tokens:** 24
- **Expected:** a quiet descriptive continuation. Pythia-160M handles this kind of soft narrative prompt without obvious mode collapse.
- **Point at in UI:** token-by-token emission, neurons firing across multiple layers, Mode 7 edges curving back to earlier tokens (especially the article "the" and the noun "shoreline").
- **Failure mode:** if the continuation goes into a loop ("the the the the"), keep going — the loop itself is useful evidence that this is a 160M-parameter model, not GPT-4. Acknowledge it: "this is what a small model looks like when it loses the thread; we're showing the inside of that, not hiding it."

### Prompt 2 — Reasoning-light, structured (alternate opener)

- **Text:** `When the alarm rang, she`
- **max_new_tokens:** 24
- **Expected:** action-oriented continuation. Pythia tends to commit to a verb quickly.
- **Point at in UI:** the early-layer burst as the model commits, then progressive narrowing in the later layers.
- **Failure mode:** generic continuation — fine, that's the baseline for a 160M model. Don't oversell.

### Prompt 3 — Honest stumble (intentionally hard)

- **Text:** `The square root of 144 is`
- **max_new_tokens:** 24
- **Expected:** Pythia-160M will probably NOT say "12." It may emit a number that is wrong, drift into prose, or pick up an unrelated phrase. That's the point.
- **Point at in UI:** the model commits early to a token that is the wrong answer; the inversion-risk readout in the narration strip may spike. Pause and say: "This is the honesty surface. A 160M-parameter model is not a calculator. The interesting thing is that the visualization shows you exactly where in the network the wrong commitment formed."
- **Failure mode if it accidentally gets it right:** still fine. Run it again with a slightly harder prompt: `The cube root of 729 is`. If a viewer says "couldn't you cherry-pick prompts that make the model look smart," your answer is "no — and here is one we expect to fail, and we're showing it on purpose."

### Prompt 4 — Framework-relevant (ethics flavor, for the close)

- **Text:** `A safety system refuses to act because`
- **max_new_tokens:** 24
- **Expected:** a continuation that resembles a refusal-style justification. The model is small, so it will not produce a sophisticated argument — it will produce the shape of one. That shape is what we want to expose.
- **Point at in UI:** the narration strip's `inversion risk` readout, and the Mode 7 edges hitting the refusal-shaped tokens. "What we are showing is the model's internal commitment to a refusal-shaped output, not whether the refusal is correct. That separation — internal commitment vs. external evaluation — is what the framework is for."
- **Failure mode:** continuation goes off-topic. Acknowledge it: "small model, fuzzy continuation; the framework still labels the internal state, which is the actual product surface."

### Prompt 5 — Backup short prompt

- **Text:** `The library was empty except for`
- **max_new_tokens:** 24
- **Expected:** noun-phrase continuation, very clean.
- **Point at in UI:** good token-by-token flow, useful if you need to re-anchor after a stumble.

---

## Section 4 — Failure recovery

Memorize these. Don't read them — say them.

- **LIVE button greyed or unavailable.** "We're falling back to a recorded trace. Production live mode requires the RunPod worker to be hot, and right now it isn't. What you're about to see is real Pythia-160M activations, recorded earlier, replayed here — same visualization, same evidence trace." Click REPLAY, walk through Prompt 1's recorded fixture (`atlas-viewer/test-fixtures/pythia_160m_reference_trace.json`), and proceed with Sections 2.2 onward using the fixture.
- **Token stream stalls mid-prompt.** Hard-refresh the page. If LIVE still stalls on the second attempt, fall back to REPLAY using the wording above. Do not let a stalled stream sit on screen for more than 15 seconds.
- **Evidence Drawer shows "fetch failed" or surfaces the local-only label.** Say plainly: "The drawer just told us itself — read the label." Then read whichever explicit fallback the drawer is showing: "Evidence Packet fetch failed; showing only the local reference metadata," or "Evidence Packet requested; showing local reference metadata while packet data is unavailable," or "Local replay metadata only; not presenting this as a verified Evidence Packet." Per PR #46 the drawer fetches by trace_id from `/evidence/<trace_id>` on the API; when the fetch fails or no trace_id is present, the drawer says so in plain text. The IDs that ARE present still resolve to stored artifacts on our side; the labeled fallback is the honesty surface, not a bug.
- **Viewer asks "is this actually running a model?"** Run the verify script live: `python scripts/verify_atlas_live.py`. The checklist must include `verdict = REAL_PYTHIA_WEIGHTS_LOADED`, `is_real_model`, `model_loaded`, `load_error = null`, `fake_runtime_env = false`, `manifest_is_real_model`, and `model_id`. If you'd rather show it in the browser, open Chrome DevTools → Network → expand the `/atlas/live/health/realmode` request that the cockpit fired; the response body has the proof fields. The SSE `manifest` event alone is NOT enough — it only carries `is_real_model`, which can be true on a cold worker that hasn't loaded weights.
- **Viewer asks "could you be faking the activations?"** Three answers, in order: (1) the worker source is `live-trace-worker/app/runtime/pythia_runner.py`, you can read it; (2) the `/atlas/live/health/realmode` endpoint exists specifically to attest real-mode (it requires real Pythia weights loaded right now — not just "demo mode not forced"), and we ran the verify_atlas_live.py script before this meeting; (3) per PR #48, the endpoint surfaces `load_error` separately so a real load failure on RunPod can't masquerade as success.
- **Cockpit lock-up or blank scene.** Hard-refresh once. If it doesn't recover, this is a deployment incident, not a demo failure. Say "looks like we caught a Render deploy mid-rollout; let me show you the recorded version" and switch to REPLAY.

---

## Section 5 — One-page handout

Hand this to the stakeholder at the end. Fits on a single page.

---

**Atlas Viewer — Alpha v0**

Atlas Viewer is a real-time interpretability surface for language models. Every visual element on the screen — neuron, token, attribution edge — ties back to a verification artifact, so a reviewer can ask "where did that label come from?" and get a traceable answer.

**What you just saw:**

- A small open-source language model (Pythia-160M) generating text token-by-token, with its internal layers and neurons visible in 3D.
- A live attribution overlay (Mode 7) drawing connections from each generated token back to the earlier tokens the model attended to most when producing it — token-to-token attention attribution, not neuron-to-neuron links.
- A framework projection: our Cognitive Architecture System labels the model's internal state in a typed coordinate space (ten primitives × four domains × seven drives × four registers).
- An Evidence Drawer that exposes the trace ID behind any visual element and labels what is shipped today vs. what is still in the follow-on round.
- A direct claim against baselines: the framework's probe beats text-only by 28.9–39.7 percentage points on internal readout; causal removal drops the readout to chance (3.57%); the accept/suppress verifier scores 98–99% accuracy at 72–75% coverage.

**What's underneath:**

- A 596-page mathematical reference (Cognitive Architecture System v7.7) defining the typed state space, the operator algebra, the inversion taxonomy, and the production semantics.
- Validated stage artifacts (probe scores, ablation results, likelihood shifts) on Pythia, OLMo, and Qwen model families.
- A peer-review paper in preparation; an AI misalignment incident database with structural analysis using the same framework.

**What to ask us about:**

- The concordance harness (in progress) — does the visualization tell the same story when the same prompt runs on OLMo-1B or Qwen-2.5-1.5B?
- The scenario library — what does an ethics-flavored prompt look like when fed through the visualization?
- Alpha partner access — who on your side would benefit from a hands-on session?
- Where to send your interpretability or audit team for a deeper technical session.

Contact: little.henderson@noeticcompass.com · noeticcompass.com (public) · Atlas Viewer alpha: https://atlas-viewer-app.onrender.com/cockpit (gated)

---

## Appendix A — Dependencies on other agents' work

This script is honest about what is and isn't shipped today.

| Dependency | Agent | Status as of 2026-05-24 | What this script does if it doesn't land |
|---|---|---|---|
| `/atlas/live/health/realmode` endpoint | Agent A | In-flight | Falls back to manual DevTools manifest check (Section 1, step 3) |
| Method-knob proof (re-run on knob change) | Agent B | In-flight | Switches the 3:30–4:30 beat to "two pre-recorded traces side-by-side" framing (Section 2) |
| Full Evidence Packet wrap (richer drawer content) | PR #46 shipped trace_id fetch | Drawer now fetches `/evidence/<trace_id>` and renders the packet when present, with explicit labeled fallback when absent | When the drawer falls back, the demo runner reads the actual fallback label verbatim (Section 2, Evidence Drawer beat) |
| Concordance harness across OLMo / Qwen | Roadmap | In-flight | Mentioned in the close as next-up, not as available today |

## Appendix B — File references (for the demo runner)

- API proxy: `noetic-compass-scaffold/noetic-compass/api/routes/atlas_live.py`
- Worker SSE stream + 24-token cap: `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/event_stream.py:110`
- Worker manifest schema (`is_real_model` field): `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/manifest.py:53`
- Cockpit shell: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/AtlasViewerShell.tsx`
- LIVE / REPLAY buttons: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/ControlBar.tsx:431-453`
- Evidence Drawer (fetches packet by trace_id per PR #46; renders explicit fallback label when no packet): `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/EvidenceDrawer.tsx`
- Realmode verification script: `noetic-compass-scaffold/noetic-compass/scripts/verify_atlas_live.py` (per PR #48)
- Baseline evidence numbers: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/lib/casBenchmarkEvidence.ts`
- Replay fixture (fallback): `noetic-compass-scaffold/noetic-compass/atlas-viewer/test-fixtures/pythia_160m_reference_trace.json`
