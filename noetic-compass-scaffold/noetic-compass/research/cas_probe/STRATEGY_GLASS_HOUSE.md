# Glass House AI — strategy memo (provisional)

**Status:** strategy sketch. Captured 2026-05-16 so the product shape
does not get lost while engineering focuses on Stage 1.1 probe capture.

**Gating evidence:** every claim in this memo is conditional on the
Pythia probe (Stages 2–3) actually surfacing CAS structure inside an
open model's hidden states, and on the technique transferring to at
least one other open model (OLMo or Qwen). If those don't work, the
product shape collapses to "CAS Native only" and this memo is wrong.

## The product

A platform — working name **Glass House AI** — where a customer
connects an open-weight language model to our service, and we make its
internal reasoning inspectable in CAS terms. The customer gets:

- A dashboard showing, for any prompt, which CAS structures the model
  has in its head at each layer
- A causal test: ablate the detected structure, see if the output
  changes
- An exportable Evidence Packet per inspection — the same one already
  shipped in v1
- A per-thought trace they can replay, share, or hand to a regulator

This is the cross-model version of what Anthropic's NLA does only on
its own models.

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

1. We feed the model the labeled CAS dataset (this branch's
   `pythia_probe_labels_*.jsonl` is the prototype).
2. For each layer, train a small linear classifier per CAS axis
   (noetic, domain, register, drive).
3. Validate on held-out data; record per-axis test accuracy and which
   layer is the most informative.
4. Save the trained probes alongside the model card in the customer's
   account.

After that, every inspection is fast: forward pass + probe inference +
optional ablation. Cheap enough to charge per call.

## Honest limits — put these in the marketing

1. **Closed API models cannot be onboarded.** Claude, GPT, Gemini do
   not expose activations. Glass House works on open weights only.
   That is fine — open-weight enterprise deployments (Llama, Qwen,
   Mistral, OLMo, plus fine-tunes) are a real and growing market.
2. **Probes are per-model.** Pythia probes do not work on Llama. The
   technique transfers; the trained probes do not. The pitch is "any
   open model, after a one-time setup" — not "one platform, any model."
3. **Probe quality is bounded by the host model.** If the model does
   not internally factor along CAS axes, no probe training can
   manufacture that. Stage 2 of this experiment tells us how well
   Pythia factors. Stage 3 (second model) tells us if the result is
   general or Pythia-specific.
4. **Validation is required, not optional.** Untrained probes produce
   confident garbage. The UI must make "probe validated" vs "probe
   preliminary" visible and honest.

## Why this is not just another AI startup

- **Anthropic's NLA works only on Anthropic's models.** Glass House is
  the cross-model version of that idea. Different vendor, same kind of
  credibility play.
- **Regulators in finance, hiring, healthcare, and government are
  already asking for explainable AI.** A platform that produces a
  formal Evidence Packet for any open model's reply is a compliance
  product, not just a research tool.
- **Complements CAS Native, doesn't compete with it.** CAS Native is
  "our model, transparent by construction." Glass House is "your
  model, we make it inspectable." Two products, one toolkit.

## Risks to flag for the IP / legal review

- **Weight handling.** Hosted tier must encrypt weights at rest and
  in transit, with key separation per customer. Self-hosted avoids
  most of this.
- **Probe ownership.** Probes are trained against a customer's model
  using our pipeline. Contract has to specify ownership — likely
  "Glass House owns the probe weights; customer owns the inspections."
- **Liability for inspection results.** If a probe says "this model
  shows register-imbalance" and the customer cancels a deployment
  based on that, are we liable? Probably need a "no warranty on
  business outcomes" clause and reserved-language discipline on
  confidence levels — same as the Evidence Packet's
  "tamper-evident, reproducible, independently inspectable" line.
- **Patent scope.** USPTO #64/037,173 covers CAS primitives. The
  cross-model probe technique is a separate filing if it ends up
  being load-bearing IP. IP attorney consultation before any public
  marketing.

## Realistic timeline (evidence-gated)

Every step depends on the previous one producing a real result.

1. **Stage 2 (Pythia probe).** Does CAS structure live in Pythia's
   activations at all? Days, after Stage 1.1.
2. **Cross-model proof.** Does the same technique work on OLMo or
   Qwen with similar accuracy numbers? ~1 week per additional model.
3. **Three-model green light.** Only after three independent
   architectures show the technique works is the platform pitch
   defensible.
4. **MVP platform.** Hosted-tier upload + probe train + inspect loop.
   1–2 months engineering for a bare version.
5. **Public launch.** After the MVP has produced probes that hold up
   under independent scrutiny on three or more popular models.

If Stage 2 fails outright, this memo is wrong and the product shape
collapses. If Stage 2 succeeds but the result doesn't transfer to a
second model, the pitch revises to "we wrap each model individually,
which is more expensive per onboard than we'd like." Either way, we
will know in days, not months.

## What this memo is NOT

- Not a roadmap commitment. Building Glass House AI is conditional on
  the technique working across models.
- Not a marketing document. Reserved language (evidence levels,
  caveats, "validated vs preliminary") must stay throughout.
- Not a replacement for the CAS Native flagship build. The
  from-scratch model stays the north star (per
  `feedback_no_foreign_architecture_cas_only.md`); Glass House is a
  parallel SKU.
- Not authorized to share externally yet. IP attorney must review
  before any public statement about "cross-model interpretability
  platform."
