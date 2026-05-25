# Atlas Viewer Live-Verified Alpha Walkthrough

Date: 2026-05-25
Audience: alpha partner, investor, technical reviewer, or product evaluator
Demo URL: https://atlas-viewer-app.onrender.com/cockpit
Verified API proof: https://noetic-compass-api.onrender.com/atlas/live/health/realmode
Verified live model: EleutherAI/pythia-160m

This is the meeting script. Use it directly. It tells you what to say, what to show, what not to say, and how to prove the cockpit is connected to real Pythia weights.

## The One-Sentence Pitch

Say this:

> Atlas Viewer lets you watch a real language model run, token by token, while CAS Harness labels what is happening inside the model and ties the visual story back to verification evidence.

Do not say this:

> Atlas proves we fully understand every neuron.

Reason: the product is a live model audit surface. It is not a completed theory of every neuron in every model.

## Before The Meeting

Do this 5-10 minutes before the call.

1. Open the cockpit:

```text
https://atlas-viewer-app.onrender.com/cockpit
```

2. Open the real-weight proof endpoint in another tab:

```text
https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

3. Confirm the proof body says:

```json
{
  "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
  "is_real_model": true,
  "fake_runtime_env": false,
  "model_loaded": true,
  "load_error": null,
  "manifest_is_real_model": true,
  "model_id": "EleutherAI/pythia-160m",
  "worker_version": "m2-real-pythia"
}
```

What this means in plain English:

> The RunPod worker is up, fake mode is off, Pythia-160M is loaded in memory, the model manifest says it is real, and there is no recorded load failure.

If any one of those fields is wrong, do not call the demo live. Say:

> Live mode is not verified right now. I can show the recorded replay path, but I will not call it live.

4. Have the cockpit ready on screen. Keep DevTools closed unless someone challenges whether it is connected.

5. Keep the live invite code ready but do not show it on screen.

## What The Live Badge Means

If the badge says:

```text
Live - complete - EleutherAI/pythia-160m - actual weights
```

Say this:

> Live means this session streamed through the API into the RunPod worker. Complete means the stream finished. EleutherAI/pythia-160m is the model that ran. Actual weights means the worker reported real Pythia weights loaded, not fake runtime mode.

Then immediately point to the realmode proof endpoint if asked.

Do not say:

> The badge alone proves everything.

Say instead:

> The badge is the UI label. The proof is the realmode endpoint plus the SSE manifest and token events.

## 5-Minute Walkthrough

### 0:00-0:30 - Open With The Product

Show the 3D cockpit.

Say:

> This is Atlas Viewer. The model is Pythia-160M, a small open-weight transformer. We use a small model first because it is cheap enough to inspect live and detailed enough to show the full stack. The 3D scene is not decoration. It is a live visual surface driven by the model run.

Then say:

> The point is not that Pythia is the smartest model. The point is that we can prove the audit pipeline is connected to actual model internals before we scale to bigger architectures.

Do not say:

> This is how every AI model thinks.

Say instead:

> This is the verified alpha path for Pythia-160M. Other model families need their own adapters and validation runs.

### 0:30-1:30 - Prove It Is Actually Connected

Click LIVE and run a short prompt.

Good prompt:

```text
The library was empty except for
```

Say:

> I am pressing LIVE now. The browser is not talking directly to RunPod. The browser talks to noetic-compass-api, the API checks the alpha gate, the API opens a worker session, and the worker runs Pythia-160M.

If asked for proof, show this:

```text
https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

Say:

> This endpoint is the connection proof. It only passes when fake mode is off, the real Pythia model is loaded, the manifest says real model, and there is no load error.

Then point to the tokens streaming.

Say:

> These tokens are arriving from the live worker over Server-Sent Events. The first stream event is the model manifest. The later events are token events. The UI animates from those events.

Do not say:

> Trust me, it is live.

Say:

> We do not ask anyone to trust the label. We expose the proof fields.

### 1:30-2:15 - Explain The 3D Neural Map

Point to the layer stack.

Say:

> Each horizontal layer is a transformer layer. The glowing points are neuron coordinates inside that layer. When a token is selected or generated, the scene shows which coordinates are active, which ones are on the active trace, and which ones overlap with CAS cover sets.

If you detach a layer, say:

> Detaching a layer lets us inspect one layer without losing where it belongs in the stack. The layer card tells us its layer number, and the rest of the stack stays available for context.

Do not say:

> This shows every neuron-level fact perfectly.

Say:

> This is an inspection view. It shows the coordinates and scores the current worker emits. Strong claims come from the validated tests, not from the visual alone.

### 2:15-3:00 - Explain Blindspots In Everyday English

Use this exact phrasing:

> A blindspot means the model may be under-reading a kind of concern in the situation. It does not mean the model is evil. It does not mean the output is automatically wrong. It means: this is a concern the audit says may need extra attention before trusting the answer.

Then give examples:

> "Possible blindspot: choice, consent, responsibility, or control" means the model may be missing whether someone has real choice, permission, responsibility, or control.

> "Possible blindspot: harm, stress, safety, health, or survival" means the model may be underestimating harm, stress, burnout, safety, health, or survival concerns.

> "Possible blindspot: rules, boundaries, safeguards, or constraints" means the model may be missing the rules or limits that should govern the answer.

If they ask what F1, F2, F3 means, say:

> F1 through F7 are CAS drive labels. We do not lead with those labels because new users should not have to decode them. We lead with the plain-English sentence first, then show the CAS source underneath as provenance.

Plain-English map:

```text
F1 Unity     -> inclusion, protection, or connection
F2 Wisdom    -> missing facts, context, or uncertainty
F3 Vitality  -> harm, stress, safety, health, or survival
F4 Connection-> trust, empathy, relationship damage, or social pressure
F5 Agency    -> choice, consent, responsibility, or control
F6 Structure -> rules, boundaries, safeguards, or constraints
F7 Purpose   -> larger goals, meaning, or long-term consequences
```

Do not say:

> CAS found the model's morality.

Say:

> CAS is flagging a model-internal pattern that maps to a human-readable audit concern.

### 3:00-3:40 - Explain Confidence

Say:

> Confidence is not a vibe score. It is not a promise the model is right. For blindspots, confidence is cover-level evidence: how strongly the targeted CAS neuron cover changed the measured margin when ablated.

Then say:

> Cover-level means a small set of neurons is evaluated together. It is not a claim that one individual neuron means one human concept by itself.

Use this example:

> If four coordinates form a cover for F5 Agency, and suppressing that cover drops the measured margin, the cover earns evidence. The UI can show the members of that cover, but the confidence belongs to the cover, not to one special neuron.

Then add this boundary:

> The live run tells us whether the current token overlaps a calibrated cover. The confidence number comes from the Stage 27F Pythia cover calibration, not from inventing a new score on the fly for every token.

Confidence bands:

```text
80-95%  high    -> strong cover-level ablation drop
60-79%  medium  -> measurable cover-level ablation drop
40-59%  low     -> weak or intermittent cover-level ablation drop
unavailable     -> not enough evidence to score
```

Do not say:

> 85% confidence means the model is 85% wrong.

Say:

> 85% high means the cover-level intervention produced a strong measured drop under this calibration method.

### 3:40-4:30 - Explain CAS vs Baseline

Say:

> The reason CAS matters is not the vocabulary. The reason CAS matters is that it beats comparison methods on measured jobs.

Then use these allowed claims.

Internal state readout:

> CAS hidden-state probes scored 78.6% on the Pythia-160M Foundation probe, 89.8% on the Pythia-160M 40-element probe, 90.6% on OLMo-1B, and 82.0% on Qwen2.5-1.5B. The text-only baseline was 28.9 to 39.7 percentage points lower.

Plain English:

> If CAS were only surface wording, the hidden-state probe would not beat text-only guessing by that much.

Causal removal:

> When the CAS-related internal direction was removed, the Foundation readout dropped from 78.6% to 3.57%. That 3.57% is exact 1-in-28 chance. Random same-rank ablations had mean disruption 0.000 and max 0.000.

Plain English:

> Remove the CAS direction and the signal dies. Remove random directions and it does not.

Output effect prediction:

> CAS-conditioned likelihood shifts moved in the predicted direction: Pythia-160M +0.283, Pythia-1B +0.554, OLMo-1B +0.604, Qwen2.5-1.5B +0.796. The raw-CAS-symbol control on Qwen was near null at -0.0002.

Plain English:

> CAS is connected to output behavior, not just labels on a chart.

Accept/suppress verification:

> On Stage 22.4 diagnostic rows, accepted accuracy was 98.16% for OLMo at 71.73% coverage and 99.49% for Qwen at 74.57% coverage.

Plain English:

> CAS is strongest when it accepts only the rows it has enough evidence to judge. Coverage is reported separately so we do not pretend every row is solved.

Inversion coverage:

> Stage 22.6/22.7 produced numeric inversion proxy attribution for 4,704 of 4,704 OLMo/Qwen diagnostic rows. That is a numeric proxy rate of 1.000.

Plain English:

> Earlier, the inversion field was reserved but blank. Now it is measured for every row in that diagnostic set. It is proxy-level attribution, not a full semantic theorem.

Do not say:

> CAS is better than every interpretability tool.

Say:

> CAS has validated advantages on these measured jobs: hidden-state readout, causal removal, output shift prediction, accept/suppress verification, and inversion proxy coverage.

### 4:30-5:00 - Close

Say:

> The live proof shows Atlas is connected to real Pythia weights. The benchmark evidence shows CAS is not just naming states; it predicts internal labels, causal removals, output shifts, and accept/suppress decisions better than controls in the validated tests. The alpha ask is simple: help us test this on more scenarios and more model families.

Then stop talking. Let them ask questions.

## What Not To Claim Yet

Do not claim these:

```text
CAS works on any model.
CAS gives mathematical certainty.
CAS identifies single monosemantic neurons.
CAS fully solves interpretability.
CAS controls every output token.
Atlas proves all blindspots in all contexts.
The 3D scene alone proves the science.
```

Use these instead:

```text
CAS is validated on the model families and jobs listed in the evidence panel.
The live alpha is verified end-to-end on Pythia-160M.
Blindspot confidence is cover-level evidence, not single-neuron certainty.
The visualization is an inspection surface; the benchmark claims come from measured probes, ablations, controls, and replication.
External models need adapters and validation before we claim support.
```

## What Is Calibrated Today

Calibrated in the current live alpha:

```text
Live model connection: EleutherAI/pythia-160m actual weights
Live path: Atlas UI -> noetic-compass-api -> RunPod worker -> SSE token stream
Realmode proof: fake mode off, model loaded, no load error, real manifest
Blindspot cover scope: F1-F7 CAS drives with Stage 27F Pythia-160M cover coordinates and clean_margin / targeted_drop calibration
Confidence type: cover-level targeted_drop / clean_margin
Runtime blindspot behavior: live token activity overlapping calibrated cover coordinates
Evidence panel: validated benchmark numbers from CAS Harness artifacts
```

Not calibrated yet:

```text
Live OLMo/Qwen adapters in Atlas Viewer
Unfamiliar outside models attached by a user
Every method knob as a live runtime intervention
Full semantic inversion theorem
Single-neuron monosemantic meanings
Production license/billing/onboarding flow
```

If asked why this matters, say:

> A serious audit product has to separate what is live, what is validated, what is proxy-level, and what is not ready yet. That is how we avoid demo theater.

## Common Questions And Good Answers

### "How do I know this is actually connected?"

Answer:

> The realmode endpoint proves the worker has real Pythia weights loaded right now. The LIVE stream then emits a real-model manifest and token events. The UI animates from those stream events.

Show:

```text
https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

### "What is special compared to Neuronpedia or TransformerLens?"

Answer:

> Neuronpedia is a strong feature browser. TransformerLens is a strong research library. Atlas Viewer is a live audit cockpit: it connects a running model, CAS labels, blindspot interpretation, benchmark evidence, and traceable Evidence Packet behavior in one user-facing surface. The unique claim is the integrated live audit workflow, not that the 3D view replaces researcher tooling.

### "What does baseline mean?"

Answer:

> Baseline means the comparison opponent. It is what CAS has to beat before we can say CAS added value. In our evidence panel, examples include text-only guessing, random same-rank ablations, raw-CAS-symbol controls, and accepting everything.

### "What does blindspot mean?"

Answer:

> A blindspot is a possible concern the model may be under-reading. It is an audit warning, not a moral diagnosis and not automatic proof the output is wrong.

### "What does confidence mean?"

Answer:

> For blindspots, confidence means how strong the cover-level ablation evidence is. It does not mean probability of truth, and it does not mean one neuron has one meaning.

### "Can we test our own model?"

Answer:

> That is the product direction, but not the live alpha claim. Today the live verified model is Pythia-160M. Outside models need an adapter, a capture path, and validation before we present them as supported.

### "What would make CAS fail?"

Answer:

> CAS would fail if it did not beat baselines, if ablations did not change the measured signal, if random controls behaved the same as CAS covers, or if replication failed across rows, prompts, seeds, or model families. That is why those tests are part of the Evidence Packet story.

## Emergency Wording

If live mode is down:

> Live mode is not verified right now, so I am not going to call it live. I can show the replay path, which uses recorded Pythia activations, but the live proof requires the RunPod worker to report REAL_PYTHIA_WEIGHTS_LOADED.

If the model gives a bad answer:

> That is acceptable for the demo. Pythia-160M is small. We are showing the internal audit trace, not pretending the small model is a frontier assistant.

If confidence is unavailable:

> Unavailable means the system does not have enough calibrated evidence to score that row. We would rather show no number than invent one.

If someone asks whether this is "AI psychosis":

> The safeguard against self-delusion is measurement. CAS has to beat baselines, survive ablation tests, fail random controls, predict output effects, and replicate. Where those tests exist, we show the numbers. Where they do not exist yet, we do not claim support.
