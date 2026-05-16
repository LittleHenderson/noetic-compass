# Glass House AI — strategy memo (provisional)

**Status:** strategy sketch. Captured 2026-05-16; refreshed
2026-05-16 after Stages 2–3.3 landed. Stage 2–3.3 partial evidence is
in. Cross-model evidence is still the gate before this memo becomes a
roadmap commitment.

**What's now confirmed (bounded):** in Pythia-160M, at layer 3, on the
noetic axis, CAS-aligned directions in the model's hidden states have
a measurable causal effect on the model's output that random
directions do not reproduce. The effect is real, modest in size, and
above a properly matched random null at p=0.0003.

**What's not yet confirmed:** that the same technique transfers to a
second model (OLMo, Qwen, Llama, etc.), that the effect generalizes to
other layers, that the other CAS axes (domain, register, drive) show
the same pattern. The product pitch is conditional on those next
results.

## What Stages 2–3.3 actually produced

A five-stage audit-laddered experiment on Pythia-160M:

| Stage | Question | Result |
|---|---|---|
| 2 | Can a small linear probe recover CAS labels from Pythia's hidden states? | Yes — but most of the signal is recoverable from the input text alone (TF-IDF baseline competitive). Probes are real, not magic. |
| 3.1 | Does ablating the noetic directions actually change Pythia's continuations? | Yes — measurable causal effect on forced-continuation generations. |
| 3.2 | Is the effect class-specific (ablating ^7's direction breaks ^7-class continuations more than ^2's)? | Mixed. +0.079 token-match disruption on same-class continuations, but per-class results uneven — ^7 and ^2 strong, ^3 and ^5 wrong-direction. |
| 3.2-control | Do random orthogonal directions reproduce the +0.079? | Random arm null (mean -0.009, p=0.82). Noetic arm non-zero (p=0.031). Direct comparison borderline (Welch p=0.086) — likely underpowered. |
| **3.3** | **Higher-power version: 30 random directions, permutation null matched to the noetic test shape.** | **Random null mean +0.0002. Noetic effect +0.079 is three orders of magnitude away from the null. Permutation p=0.0003. Direction-meaningful.** |

The audit cycle on every stage caught at least one overclaim before
publication. Final verdict survived two rounds of role-flipped audit
(Claude audits Codex, Codex re-audits Claude). This is what
"reserved language, validated, not preliminary" looks like in practice.

**Bounds that travel with every external statement:**

- Single model. Pythia-160M, 160M parameters. Smallest serious open model.
- Single layer. Layer 3 of 12. Probably not the only informative layer; we haven't tested others.
- Single axis. Noetic only — the 10 "Idea, Mind, Positive..." dimension. Domain, register, drive axes haven't been ablation-tested yet.
- Per-class unevenness. 8 of 10 noetic classes positive; ^3 (Negative) and ^5 (Female) show wrong-direction effects. The *population* effect is reliable; *every individual class* is not.
- Effect is modest. +0.079 token-match disruption is not "rewrite the output." It is "tilt the output in a measurable, statistically reliable way."
- Not yet cross-model. The entire memo's pitch depends on this transferring to at least one more open model.

## The product

A platform — working name **Glass House AI** — where a customer
connects an open-weight language model to our service, and we make its
internal reasoning inspectable in CAS terms. The customer gets:

- A dashboard showing, for any prompt, which CAS structures the model has in its head at each layer
- A causal test: ablate the detected structure, see if the output changes (the Stage 3.3 test, packaged)
- An exportable Evidence Packet per inspection — the same one already shipped in v1
- A per-thought trace they can replay, share, or hand to a regulator

This is the cross-model version of what Anthropic's NLA does only on
its own models — *conditional on the technique transferring*.

## How a customer onboards

Three flavors, picked by how they want to handle their weights:

| Path | What the customer gives us | What we do | Where weights live |
|---|---|---|---|
| **Hosted** | A Hugging Face model ID, or weights upload | Train CAS probes, run inspections, host dashboard | Glass House infra (encrypted) |
| **Bring-your-endpoint** | An HTTPS endpoint where they expose hidden states | Train probes against their endpoint, run inspections client-side | Customer infra |
| **Self-hosted** | Nothing — they install our toolkit | Sell the toolkit; sell optional cloud probe training | Customer infra |

Hosted is fastest to demo. Self-hosted is what regulated industries
(medical, defense, financial) will demand because they won't ship
weights anywhere.

## What happens on first connect

For each new model, a one-time **probe training pass**:

1. We feed the model the labeled CAS dataset (this branch's `pythia_probe_labels_*.jsonl` is the prototype).
2. For each layer, train a small linear classifier per CAS axis (noetic, domain, register, drive).
3. Validate on held-out data; record per-axis test accuracy and which layer is the most informative.
4. **Run the Stage 3.3 ablation test against a random-direction null** — confirm the probes are not just text-pattern matchers but actually point at causally relevant directions. This is the "probe validated" gate.
5. Save the trained probes alongside the model card in the customer's account.

After that, every inspection is fast: forward pass + probe inference +
optional ablation. Cheap enough to charge per call.

## Honest limits — put these in the marketing

1. **Closed API models cannot be onboarded.** Claude, GPT, Gemini do not expose activations. Glass House works on open weights only. That is fine — open-weight enterprise deployments (Llama, Qwen, Mistral, OLMo, plus fine-tunes) are a real and growing market.
2. **Probes are per-model.** Pythia probes do not work on Llama. The technique transfers (conditional on Stage 3 cross-model); the trained probes do not. The pitch is "any open model, after a one-time setup" — not "one platform, any model."
3. **Probe quality is bounded by the host model.** If the model does not internally factor along CAS axes, no probe training can manufacture that. Stage 2–3.3 showed Pythia-160M factors at all on the noetic axis. Other models, other axes, other layers — open question.
4. **The effect is modest and uneven across classes.** Stage 3.2 found 2 of 10 noetic classes go the wrong direction. The honest UI says "this model factors the noetic axis at p<0.001 with these per-class strengths"; not "this model perfectly factors CAS."
5. **Validation is required, not optional.** Untrained probes produce confident garbage. Step 4 of the onboarding (ablation against random-direction null) is the load-bearing validation gate. The UI must make "probe validated against random null" vs "probe preliminary, awaiting validation" visible and honest.
6. **Text-only baselines must be reported alongside.** Stage 2 found that most of the probe's accuracy was recoverable from the input text alone. The Evidence Packet must show "probe says X, text-only baseline says X" so customers know how much the probe is adding over surface lexical pattern.

## Why this is not just another AI startup

- **Anthropic's NLA works only on Anthropic's models.** Glass House is the cross-model version of that idea (conditional on Stage 3 cross-model). Different vendor, different audience, same kind of credibility play.
- **Regulators in finance, hiring, healthcare, and government are already asking for explainable AI.** A platform that produces a formal Evidence Packet for any open model's reply — with permutation-tested ablation results, not just attention heatmaps — is a compliance product, not just a research tool.
- **Complements CAS Native, doesn't compete with it.** CAS Native is "our model, transparent by construction." Glass House is "your model, we make it inspectable." Two products, one toolkit.
- **The methodology is now battle-tested.** Stages 2–3.3 are a worked example of "claim → audit catches overclaim → tighter test → final claim with bounds." That methodology is itself a product differentiator: customers see exactly what kind of evidence backs a "Glass House confirmed" stamp.

## Risks to flag for the IP / legal review

- **Weight handling.** Hosted tier must encrypt weights at rest and in transit, with key separation per customer. Self-hosted avoids most of this.
- **Probe ownership.** Probes are trained against a customer's model using our pipeline. Contract has to specify ownership — likely "Glass House owns the probe weights; customer owns the inspections."
- **Liability for inspection results.** If a probe says "this model shows register-imbalance" and the customer cancels a deployment based on that, are we liable? Probably need a "no warranty on business outcomes" clause and reserved-language discipline on confidence levels — same as the Evidence Packet's "tamper-evident, reproducible, independently inspectable" line.
- **Patent scope.** USPTO #64/037,173 covers CAS primitives. The cross-model probe technique plus the permutation-test validation gate is potentially a separate filing if it ends up being load-bearing IP. IP attorney consultation before any public marketing.
- **Reserved-language discipline in customer-facing UI.** Stage 2–3.3 lesson: "direction-meaningful at p<0.001 on this model/layer/axis" is defensible; "we can read the model's mind" is not. UI copy and Evidence Packet wording must enforce this.

## Realistic timeline (evidence-gated)

Every step still depends on the previous one producing a real result.

1. **Stage 2 (Pythia probe).** Done. Probes recover CAS labels; most signal is text-shape, but real signal above text-only baseline exists.
2. **Stage 3 series (causal validation).** Done. Direction-meaningful effect at p=0.0003 against matched random null, on Pythia-160M layer 3 noetic axis.
3. **Cross-model proof.** Not done. Does the same technique work on OLMo or Qwen with comparable numbers? ~1 week per additional model. **This is the next gate.**
4. **Three-model green light.** Only after three independent architectures show the technique works is the platform pitch defensible as cross-model rather than Pythia-specific.
5. **Cross-axis green light.** Domain, register, drive axes must each pass the Stage 3.3 ablation gate. Until then the pitch is "we inspect the noetic axis" — narrower but still useful.
6. **MVP platform.** Hosted-tier upload + probe train + Stage 3.3 ablation validation + inspect loop. 1–2 months engineering for a bare version, after the cross-model and cross-axis gates clear.
7. **Public launch.** After the MVP has produced probes that hold up under independent scrutiny on three or more popular models, on at least two CAS axes.

If cross-model fails, the pitch revises to "we wrap each model individually,
which is more expensive per onboard than we'd like, and the per-model evidence
quality varies." Either way, the next 1–2 weeks of engineering tells us which
shape the product has.

## What this memo is NOT

- Not a roadmap commitment yet. Stages 2–3.3 unlocked the *single-model bounded claim*. The full Glass House pitch is still conditional on cross-model.
- Not a marketing document. Reserved language (evidence levels, caveats, "validated vs preliminary," "matched random null at p=X") must stay throughout.
- Not a replacement for the CAS Native flagship build. The from-scratch model stays the north star (per `feedback_no_foreign_architecture_cas_only.md`); Glass House is a parallel SKU.
- Not authorized to share externally yet. IP attorney must review before any public statement about "cross-model interpretability platform." The bounded Stage 3.3 finding is also not authorized for external use until IP review.
