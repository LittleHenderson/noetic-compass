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
3. **Confirm LIVE mode is actually real.** Agent A is shipping a one-shot health check at `https://noetic-compass-api.onrender.com/atlas/live/health/realmode` in parallel with this script. The endpoint returns the worker manifest, and you want `is_real_model: true` before you call this a live-model demo.
   - **If that endpoint is live:** hit it once in a separate tab. If the body is JSON with `is_real_model: true`, the worker is hot and you can demo LIVE.
   - **If `is_real_model: false` or the endpoint 404s:** the worker is on the milestone-1 fake stream. Do NOT call this "real model" in front of the stakeholder. Switch the demo to Replay (Section 4) and frame it as "this is a recorded Pythia-160M trace; live mode requires the RunPod worker to be hot."
   - **If Agent A's endpoint did not land:** click LIVE manually in the cockpit, then open Chrome DevTools → Network → find the SSE stream under `/atlas/live/session/<id>/events`, expand it, and look at the first event named `manifest`. The field `is_real_model` is the source of truth. Same decision rule as above.
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
- **Curved edges drawing back across the scene.** "Those edges are Mode 7 — they connect the token the model just emitted to the earlier neurons that pushed it toward that choice. It is an attribution path, not a metaphor."

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

Show:

- **A trace ID** in the `evidence_ref` JSON block. "Every visual element here has an ID. That ID maps to a stored evidence packet."
- **The yellow caveat note** that reads "v0.0: dashboard wrap pending. Below is the fixture-backed `evidence_ref` payload only — full Evidence Packet rendering lands in a follow-on round."
- **Read the caveat out loud.** "We are showing what we have, and we are labelling what we don't. The drawer ships the lookup IDs today; the full packet (sample-level proof, validated stage artifact) lands when the API wrap is done."

This is the honesty surface. Don't gloss it. The investor wants to see whether you over-claim — show them you don't.

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
- **Evidence Drawer shows "fetch failed" or a network error in the `evidence_ref` payload.** Say plainly: "The evidence-fetch endpoint is one of our known surfaces in the alpha. The IDs are still real — those map to stored artifacts on our side — but the wrap that loads the full Evidence Packet hasn't shipped yet. The yellow caveat in the drawer says exactly that." This is the same honesty surface as the drawer itself.
- **Viewer asks "is this actually running a model?"** Switch to Chrome DevTools → Network → expand the SSE stream under `/atlas/live/session/<id>/events` → find the first `manifest` event. Point at `is_real_model: true`. Then point at `model_id: "EleutherAI/pythia-160m"` and `worker_version`. That's the live attestation.
- **Viewer asks "could you be faking the activations?"** Three answers, in order: (1) the worker source is `live-trace-worker/app/runtime/pythia_runner.py`, you can read it; (2) the manifest event carries `is_real_model: true` only when the real-Pythia runner is wired; (3) the `/atlas/live/health/realmode` endpoint exists specifically to attest this, and we ran it before this meeting.
- **Cockpit lock-up or blank scene.** Hard-refresh once. If it doesn't recover, this is a deployment incident, not a demo failure. Say "looks like we caught a Render deploy mid-rollout; let me show you the recorded version" and switch to REPLAY.

---

## Section 5 — One-page handout

Hand this to the stakeholder at the end. Fits on a single page.

---

**Atlas Viewer — Alpha v0**

Atlas Viewer is a real-time interpretability surface for language models. Every visual element on the screen — neuron, token, attribution edge — ties back to a verification artifact, so a reviewer can ask "where did that label come from?" and get a traceable answer.

**What you just saw:**

- A small open-source language model (Pythia-160M) generating text token-by-token, with its internal layers and neurons visible in 3D.
- A live attribution overlay (Mode 7) drawing connections from each generated token back to the earlier neurons that pushed the model toward that choice.
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
| Full Evidence Packet wrap (richer drawer content) | Follow-on round | Not yet shipped | The yellow caveat in the drawer is read aloud verbatim (Section 2, Evidence Drawer beat) |
| Concordance harness across OLMo / Qwen | Roadmap | In-flight | Mentioned in the close as next-up, not as available today |

## Appendix B — File references (for the demo runner)

- API proxy: `noetic-compass-scaffold/noetic-compass/api/routes/atlas_live.py`
- Worker SSE stream + 24-token cap: `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/event_stream.py:110`
- Worker manifest schema (`is_real_model` field): `noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/manifest.py:53`
- Cockpit shell: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/AtlasViewerShell.tsx`
- LIVE / REPLAY buttons: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/ControlBar.tsx:431-453`
- Evidence Drawer (with yellow caveat note): `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/components/cockpit/EvidenceDrawer.tsx`
- Baseline evidence numbers: `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/lib/casBenchmarkEvidence.ts`
- Replay fixture (fallback): `noetic-compass-scaffold/noetic-compass/atlas-viewer/test-fixtures/pythia_160m_reference_trace.json`
