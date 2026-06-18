# CJT/PCBA Fit Analysis for CAS Forex and the Larger CAS Ecosystem

Date: 2026-06-17
Source reviewed: `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md`
Status: Implementation triage, not product validation

## Bottom Line

Yes, parts of the CJT/PCBA blueprint can be implemented into CAS Forex and the larger CAS ecosystem. The right first move is not to add `CJT<>` as production compiler authority. The right first move is an evidence-only diagnostic sidecar that explains cause, bias, effect, gain, operating region, and failure mode for existing CAS events.

For CAS Forex, CJT/PCBA should initially make the system better at explaining and auditing trades. It must not create a new path to `ACCEPT`, live orders, human unlock, or real-money routing. It can only add suppression, `FLAG_FOR_HUMAN_REVIEW`, or `LIVE_LOCKED` pressure until validated.

For the larger CAS ecosystem, CJT/PCBA is strongest as a structural explainability and visualization layer around existing CAS traces, Evidence Packets, matched controls, instruction-integrity checks, and agent workflows. Compiler syntax, prediction heads, attention gating, audio signatures, and governance-standard claims remain `OPEN` until their own evidence gates close.

## Implementable Now

### 1. Evidence-only CJT diagnostic schemas

Add optional schemas such as `CjtRegion`, `CjtObservation`, and `CjtCircuitDiagnostic`.

Recommended fields:

- `cause_ref`: source event or CAS state.
- `bias_ref`: context, model, macro condition, risk condition, operator setting, or prior evidence.
- `effect_ref`: proposed trade, decision, output, lock, or failure.
- `beta_estimate`: observed amplification or attenuation score.
- `beta_source`: how the score was estimated.
- `region`: `cutoff`, `active`, `saturation`, or `breakdown`.
- `claim_ceiling`: `OPEN`, `FLAG_FOR_HUMAN_REVIEW`, `SUPPRESS`, or `LIVE_LOCKED`.
- `evidence_refs`: packet IDs, trace IDs, model signals, broker tickets, or backtest run IDs.
- `notes`: concise diagnostic explanation.

Landing zones:

- `cas-forex/cas_forex/schemas/evidence.py`
- `cas-forex/cas_forex/schemas/forecast_harness.py`
- broader CAS Evidence Packet schemas

This is low risk because it is additive and optional.

### 2. CAS Forex diagnostic mapping

CJT terminology maps naturally onto the existing CAS Forex proof spine:

- Forecast disagreement: differential-pair imbalance.
- Weak edge versus baselines: cutoff.
- Excess confidence from one model: high gain with insufficient support.
- Macro shock: saturation or breakdown warning.
- Drawdown breach: power-management overload.
- Broker disconnect during open trade: circuit fault.
- Margin reject: power rail failure.
- MT5/MT4 execution mismatch: fill mismatch / short circuit.
- Harvester repeated loss signature: beta drift.
- High lacunarity loser: gappy bias path.

These diagnostics should be written into Evidence Packets and proof reports, but they should not approve trades.

### 3. Proof UI circuit panel

Add a CJT/PCBA panel to the CAS Forex proof UI and larger Atlas/proof views.

It should show:

- Cause -> Bias -> Effect flow.
- Operating region.
- Gain/beta estimate.
- Evidence links.
- Gate outcome.
- Whether the diagnostic only explains, suppresses, flags, or locks.

This fits the existing proof/audit UI direction better than a live trading cockpit. It gives users a human-readable circuit view of why the system acted.

### 4. Harvester and post-trade learning

The harvester can use CJT diagnostics to classify failure patterns:

- "Cutoff" means the forecast did not conduct into a trade because evidence was too weak.
- "Saturation" means the system was maxed out or overconfident.
- "Breakdown" means a hard safety boundary failed or nearly failed.
- "Beta drift" means an edge that used to amplify profit is now amplifying losses.

Promotion must still require backtest evidence, paper evidence, evidence anchoring, human approval, and next-session-only promotion.

### 5. Larger CAS matched-control and safety experiments

CJT/PCBA can improve the research ecosystem as experiment structure:

- Use differential pairs for matched-control comparisons: same input, two bias profiles, compare output divergence.
- Use CSB-style safety boards as a shadow audit around prompt-injection, instruction-integrity, and prerequisite-bypass checks.
- Use CMB-style memory boards as an indexing metaphor for Evidence Packet memory, not as a claim about biological memory.
- Use CPMB-style power management for compute/session budgets, overload brakes, and persistent lock states.

## Implement Later

### CJT compiler syntax

The blueprint proposes syntax such as `CJT< cause | bias => effect >`. This should be implemented only in a research/compiler branch after the grammar, semantics, IR serialization, and validation rules are pinned down.

Do not route production CAS Forex through this syntax yet. CAS Forex already has live-money-sensitive gates. A new compiler primitive should not touch them until it has its own parser tests, invalid-form tests, round-trip serialization tests, and formal claim boundaries.

### CJT analytical engine

Characteristic curves, gain-bandwidth, noise, small-signal analysis, and Fisher-Rao beta estimates are interesting, but they need measured traces and labels. First collect CJT observations as data. Then fit the analytical layer.

### CjtPredictionHead and attention gating

Do not add model-head or attention-gating claims until there are CJT-labeled traces and an evaluation target. This belongs in CAS-native research, not CAS Forex execution.

### Audio signatures

Sonification can be a visualization experiment, but it should not be a proof, safety, or governance claim.

## Do Not Implement Yet

- Do not claim compiler-enforced safety from CJT fuses or current limiters.
- Do not claim CJT prevents prompt injection.
- Do not claim regulators require CCB diagrams.
- Do not claim CJT is a governance standard.
- Do not use CJT diagnostics to unlock live trading.
- Do not let CJT diagnostics produce live broker `ACCEPT`.
- Do not treat a CJT visualization as WORM evidence.
- Do not use CJT/PCBA to change the current CAS Forex status: real-money/live routing remains `NOT LICENSED`.

## First Implementation Pass

Recommended first PR for CAS Forex:

1. Add `cas_forex/schemas/cjt.py` with `CjtRegion`, `CjtDiagnosticKind`, `CjtClaimCeiling`, `CjtObservation`, and `CjtCircuitDiagnostic`.
2. Export those schemas from `cas_forex/schemas/__init__.py`.
3. Add optional `cjt_diagnostics: list[dict]` to `ForexEvidencePacket` and `ForecastHarnessReport`.
4. Add a small `cas_forex/cjt_diagnostics.py` mapper that converts existing forecast, macro, risk, broker, and post-trade conditions into diagnostics.
5. Wire diagnostics into backtest/paper Evidence Packets only.
6. Add tests proving diagnostics serialize, appear in packet chains, and cannot produce `ACCEPT`.

Acceptance criteria:

- Existing tests still pass.
- A CJT diagnostic can only add explanation, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or `LIVE_LOCKED`.
- No code path can convert a CJT diagnostic into live broker permission.
- `paper_trading=True`, `live_mode=False`, and real-money/live routing remain `NOT LICENSED`.

## Larger CAS Ecosystem Pass

Recommended first larger-CAS pass:

1. Add optional CJT sidecar fields to generic Evidence Packet records.
2. Add a circuit-style explanation panel in Atlas/proof UI.
3. Add a matched-control experiment template for differential-pair bias comparisons.
4. Add a prompt-injection shadow-screen experiment that emits `FLAG_FOR_HUMAN_REVIEW`, not "prevention" claims.
5. Start a compiler research branch for parsing `CJT<>`, but keep it disconnected from production gating.

## Plain-English Map

- Cause: the incoming push, like a market signal, prompt, or event.
- Bias: the steering context, like model state, macro news, risk posture, or system constitution.
- Effect: what came out, like a trade proposal, suppression, lock, or answer.
- Beta/gain: how strongly the context amplified or weakened the input.
- Cutoff: the signal did not get through.
- Active: the signal got through in a controlled way.
- Saturation: the system is maxed out and cannot respond proportionally.
- Breakdown: a hard boundary failed or is at risk.
- Differential pair: compare the same input under two steering contexts.
- Power management: safety budgets and overload brakes.

## Final Recommendation

Implement CJT/PCBA as an evidence-and-visualization layer first. It can immediately improve audit clarity in CAS Forex and the larger CAS ecosystem. Keep compiler syntax, model-head integration, safety-enforcement claims, and governance claims in a separate `OPEN` research lane until evidence catches up.
