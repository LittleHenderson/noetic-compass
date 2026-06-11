# CAS Harness Pre-Speech / Causal Solution Round Table

Date: 2026-06-11
Status: design brief and next-experiment gate
Claim ceiling: pre-speech comply/refuse detection and causal compliance-state control remain `OPEN` / `NOT LICENSED` until the v5 gates below pass.

## Plain-English Verdict

The old detector could tell, after the answer was already forming, whether the model had complied or refused. That is useful, but it is not the flagship claim.

The big win would be:

1. Catch the model's comply/refuse stance before it speaks.
2. Prove that the hidden stance causes the final answer, not just correlates with it.
3. Use CAS Harness to catch hallucination and prompt-injection risk before bad text becomes trusted output.

The foundational documents do point to a working solution, but not as a magic hidden-state theorem. The solution splits into two lanes:

1. Product lane now: a Topos Integrity Gate that checks whether a requested action is admissible before the answer is trusted. This can power a marketable Instruction Integrity Review lane in shadow mode.
2. Research lane next: a v5 pre-speech and causal proof experiment that tests whether W0 hidden state really predicts and controls comply/refuse behavior under payload-controlled conditions.

## Agent Round Table

### Helmholtz: TKS / Noetic Semantics

Finding: comply/refuse should not be treated as a single crude bit. In CAS terms, it is a typed production state.

Useful foundations:

- `^2` and `^3` are attraction and aversion toward a specific Idea.
- Refusal has register structure:
  - `^3^P|T`: goal-level or policy refusal.
  - `^3^P|A`: analytical refusal.
  - `^3^P|f`: learned preference or RLHF-style refusal.
- Reliable refusal is a recipe, not one scalar. A candidate recipe from the clarifications is:
  - `Theta(Omega_refusal) = 1*^3^P|T + 2*^3^P|A + 1*^3^P|f + 1*^8^P|T -> Omega_refusal`.
- Missing refusal ingredients are lacunarity.
- Wrongly aimed ingredients are leakage.
- Weakest required ingredient is the limiting reagent.

Implication: the next detector should estimate refusal readiness as a recipe with prerequisites, not only train a binary `COMPLIED` / `REFUSED` classifier.

### Dewey: Noetic Topos / Formal Gate

Finding: Noetic Topos supports a local-to-global integrity gate.

Model each run as local tiles:

- system policy
- developer policy
- user task
- retrieved evidence
- injected or untrusted spans
- proposed claim
- proposed tool call
- optional model-state observation

A proposed answer or action should be trusted only if those tiles glue into one coherent global section. If a hostile span says "ignore prior instructions," it does not glue with higher-authority policy. If a claim has no source support, it does not glue with evidence. If a tool call is outside permission, it does not glue with power/authorization.

Operational gates:

- Coverage Gate: every claim/action must be covered by source evidence, task intent, policy authority, tool permission, and D/W/P prerequisites.
- Gluing Gate: local tiles must agree on overlaps; contradictions and task drift block trust.
- Pullback Stability Gate: summaries, subtasks, and tool calls inherit parent constraints.
- Admissibility Gate: a transition is valid only when the typed intermediate state exists.
- Omega Gate: collapse partial truth to `ACCEPT`, `FLAG_FOR_HUMAN_REVIEW`, or refusal/suppression policy, never fake certainty.

Boundary: the section-retraction result licenses output-side audit better than hidden-state recovery. It does not prove that a linear activation probe is reading pre-speech intent.

### Huygens: Probe / Experiment Design

Finding: current Qwen evidence is still blocked for strict pre-speech and causal claims.

Known result:

- Dataset: `304` rows, `COMPLIED=161`, `REFUSED=143`.
- Global W0 hidden readout accuracy: `0.852459`.
- Text-hash baseline: `0.885246`, which beats hidden state.
- Within-payload gate: blocked. Only `overt_5` had both labels with enough rows, and that payload scored chance.
- v4 matched-prompt gate: blocked with `G_matched=2`; needs `G_matched>=40`.

Implication: the bottleneck is not "try a cleverer classifier." The bottleneck is a clean payload-controlled design.

### Laplace: Product / Claim Boundary

Finding: the marketable slice is Instruction Integrity Review, not "we already prevent hallucinations and prompt injection."

Safe customer framing now:

> CAS Harness runs a shadow Instruction Integrity scan over prompts and model outputs, persists the findings in the Evidence Packet, and routes unsupported or risky material to `FLAG_FOR_HUMAN_REVIEW` without changing the final verdict.

Do not claim yet:

- hallucination detection as a final production verdict
- hallucination prevention
- prompt-injection prevention/removal/reversal
- harmful-instruction inversion as automatic repair
- live pre-speech interception
- causal compliance-state control
- payload-independent comply/refuse detection

## The Working Solution

### Lane 1: Topos Integrity Gate

This is the product lane we can build and sell honestly first.

Before trusting an answer, CAS Harness builds a table of local tiles:

- source spans and hashes
- authority level for each instruction
- trust boundary for each span
- user task and any competing injected task
- policy conflicts
- evidence support for each generated claim
- tool permission and provenance
- D/W/P prerequisites
- domain precedence features: `P > C > E > O`
- admissible transition id
- failed intermediate states
- gluing residuals: contradiction, unsupported join, task drift, hidden semantic jump
- Omega-style truth state for each predicate

Then it asks:

1. Is this action covered by the right sources and authority?
2. Does it glue with the user's real task and the policy hierarchy?
3. Did an untrusted span try to replace the task?
4. Are there missing prerequisites?
5. Is there leakage toward a harmful side product?
6. Is the final action admissible?

If the answer is uncertain or unsafe, route to `FLAG_FOR_HUMAN_REVIEW`. In shadow mode, CAS Harness records the finding and does not change the model output. In later CAS-owned surfaces, it can quarantine untrusted spans from active context while preserving the raw span in the Evidence Packet.

This is useful for hallucination and prompt-injection risk because both can be treated as local-to-global failures:

- Hallucination risk: the claim does not glue to evidence.
- Prompt-injection risk: a low-authority span tries to override a high-authority span.
- Tool-abuse risk: the proposed action does not glue to permission and provenance.
- Secret-exfiltration risk: the proposed answer leaks across a trust boundary.

### Lane 2: Pre-Realization Refusal Recipe Probe

This is the research lane needed for the big hidden-state claim.

Instead of asking "can a probe classify `COMPLIED` / `REFUSED` globally?", ask:

> Before token 1, can W0 estimate whether the refusal recipe is already sufficiently present, inside the same payload classes, beating text baselines?

Primary recipe features:

- `^3^P|T`: policy/goal refusal readiness
- `^3^P|A`: analytical refusal readiness
- `^3^P|f`: preference/RLHF refusal readiness
- `^8^P|T`: principled trigger for refusal
- `^2` / `^3` polarity margin
- D/W/P prerequisite satisfaction
- coverage/gluing score
- lacunarity score
- leakage score
- limiting-reagent score

Plain English: do not look for a single red light. Look for whether all the parts of a reliable refusal engine are already assembled before the model starts speaking.

## v5 Experiment Gate

### Lane A: W0 Pre-Speech Detection

Use Qwen first only if the capture can be balanced inside payload classes.

Target design:

- Model: `Qwen/Qwen2.5-1.5B-Instruct`.
- Feature: W0 prompt-final pre-generation vector only for the primary pre-speech claim.
- Candidate bank: `800` prompts from `10` domains x `10` carrier topics/domain x `8` payload classes.
- Final detection set: at least `400` labeled rows.
- Payload floor: at least `5` payload classes with `COMPLIED>=40` and `REFUSED>=40` each.
- Grouping: 5-fold cross-validation grouped by carrier/topic so one carrier cannot appear in both train and test.
- Labels: accepted verifier labels only: human, `llm_consensus_3of3_xfam`, or `llm_majority_2of3_xfam`.

Pass gates:

- W0 balanced accuracy `>=0.75`.
- Within-payload restricted permutation p `<0.001`.
- W0 beats text-hash baseline by `>=0.15` balanced accuracy.
- W0 beats payload/domain/length baselines by `>=0.15` balanced accuracy.
- Every testable payload class has balanced accuracy `>=0.70`.
- Shuffled-label hidden control mean balanced accuracy `<=0.60`.

If text wins again, the pre-speech hidden-state claim remains `OPEN` / `NOT LICENSED`.

### Lane B: Live Causal Intervention

This is the proof that the state causes behavior.

Design:

- Hold out `80` prompts never used to train the W0 readout.
- For each heldout prompt, run `8` paired seeds under `4` conditions:
  - no-op hook
  - `+refusal` steer
  - `-refusal` steer
  - random same-norm steer
- Total causal outputs: `80 x 8 x 4 = 2560`.
- Judge all outputs through the accepted cross-family label path.

Intervention:

- Train direction `d` on train folds only:
  - `d = mean(W0_REFUSED) - mean(W0_COMPLIED)`, or a frozen ridge-logistic coefficient.
- Apply the hook before token 1 at the final prompt position.
- Conditions:
  - `h += alpha*d`
  - `h -= alpha*d`
  - random same-norm vector
  - projection removal / necessity ablation
- Freeze gain `alpha` on calibration prompts before heldout testing.

Pass gates:

- `+refusal` increases prompt-level `REFUSED` probability by at least `+0.20` versus no-op.
- Prompt-level sign-flip permutation p `<0.001`.
- 95% bootstrap CI lower bound `> +0.10`.
- `+refusal` beats random same-norm steer by `>=0.15`.
- Random same-norm steer absolute shift `<=0.05`.
- `-refusal` moves the opposite way: `REFUSED` shift `<= -0.10` or `COMPLIED` shift `>= +0.15`.
- `IGNORED` rate must not rise by more than `0.10`.
- Malformed/repetitive/empty output rate must not rise by more than `0.05`.

Only after Lane A and Lane B pass can CAS Harness start discussing a scoped `LICENSED` internal pre-speech causal claim for that model, layer, capture protocol, and verifier path.

## Prompt Injection Removal / Reversal / Inversion

The foundations suggest a safe staged path:

1. Detect structural risk as a gluing/coverage failure.
2. Quarantine untrusted spans from the active model context in CAS-owned surfaces.
3. Preserve raw spans and hashes in the Evidence Packet.
4. Build a safe replacement task from the surviving high-authority, well-covered sections.
5. Use inversion to generate matched adversarial controls first.
6. Only after external/red-team proof, promote narrow repair wording.

Current claim boundary:

- `LICENSED` as a design direction and shadow risk triage.
- `NOT LICENSED` as automatic prompt-injection removal, harmful-instruction repair, or hallucination prevention.
- `OPEN` for live enforcement beyond CAS-owned surfaces.

## Product Shape

Next marketable slice:

**CAS Harness Instruction Integrity Review**

What the UI should show:

- `instruction_integrity.mode: shadow`
- `verdict_effect: none_shadow_only`
- prompt findings grouped separately from model-output findings
- finding kind
- authority level
- span hash
- redacted excerpt
- failed gate: coverage, gluing, pullback stability, admissibility, or Omega
- `activation_detection.status: unavailable` for closed APIs
- `DETECTION ONLY` for compatible post-hoc activation detection
- Evidence Packet hash and `/verify` link

Customer-safe message:

> This is triage evidence. It can route risky or unsupported material to `FLAG_FOR_HUMAN_REVIEW`. It is not yet a prevention, removal, final `ACCEPT`, or causal hidden-state claim.

## Immediate Next Work

1. Build the hosted Instruction Integrity Review card in the deployed CAS Harness path.
2. Run the hosted authenticated proof: prompt scan, model-output scan, Evidence Packet persistence, `/verify`, UI display.
3. Expand the benchmark with clean, injected, control, refused, complied, ignored, hallucinated, and grounded examples.
4. Write the v5 prompt-bank builder and screener for balanced same-payload `COMPLIED` / `REFUSED` capture.
5. Write the v5 group-aware W0 analyzer with text/payload/domain baselines and restricted permutation gates.
6. Write the Qwen live steering script using the existing forward-hook pattern.
7. Write paired causal statistics over prompt-level behavior shifts.
8. Keep public claims at shadow triage until WORM-backed verifier policy and external/red-team gates pass.

## Bottom Line

CAS/TKS v7.4 and Noetic Topos do provide the architecture for a broader, more marketable product: treat hallucination and prompt injection as failures of coverage, gluing, admissibility, and provenance before trusting the answer.

They do not yet prove that CAS Harness can read and causally control a model's hidden comply/refuse state before speech. That stricter claim becomes testable with the v5 gates above. Until those gates pass, the honest public product is Instruction Integrity Review with `FLAG_FOR_HUMAN_REVIEW`, Evidence Packet persistence, and strict `OPEN` / `NOT LICENSED` boundaries around prevention, removal, live interception, and causal proof.
