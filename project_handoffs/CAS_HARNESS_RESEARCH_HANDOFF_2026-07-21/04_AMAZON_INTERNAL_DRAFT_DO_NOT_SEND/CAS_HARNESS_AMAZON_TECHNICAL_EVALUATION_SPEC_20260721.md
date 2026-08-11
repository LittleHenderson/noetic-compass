# CAS Harness Amazon Technical Evaluation Specification

> **DISTRIBUTION PAUSED - INTERNAL REVIEW DRAFT - 2026-07-21**
>
> This document is not approved for external distribution. It is a conservative
> engineering review packet, not a customer-production acceptance authority,
> certification, sales claim, provider receipt, or legal opinion. No standing
> `ACCEPT` exists in the project record. Customer-production `ACCEPT`, universal
> open-weight support, CAS-specificity, and execution above 20B remain `OPEN` or
> `NOT LICENSED` as scoped below.

## Document control

| Field | Value |
|---|---|
| Document ID | `cas-harness-amazon-technical-evaluation-spec-20260721` |
| Status | `DISTRIBUTION PAUSED - INTERNAL REVIEW DRAFT` |
| Snapshot date | 2026-07-21 America/Los_Angeles |
| Canonical source | `docs/external/amazon/CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md` |
| Claim manifest | `docs/external/amazon/CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json` |
| Release pointer | `docs/external/amazon/LATEST.json` |
| Protected source commit | `81b5c18bd83e1f01ccd398dcad3865a674335b7f` |
| Protected source tree | `4aa8b6dbd8d5f78345a3acd84f4c0e4716244908` |
| Protected branch at packet creation | `master` |
| Authoring branch | `codex/amazon-eval-spec-20260721` |
| External approval | `OPEN` |

`LATEST.json` binds the final SHA-256 values of this source and its manifest.
The packet must be regenerated if either file changes.

## 1. Purpose and review question

CAS Harness is a white-box research and engineering system for inspecting
open-weight language models whose runtimes expose hidden states and related
internal tensors. It captures activations, runs predefined semantic probes and
controls, records causal or conditioning experiments where available, and
packages the reported result into a reviewable Evidence Packet.

This packet asks Amazon software, machine-learning, interpretability, security,
and infrastructure reviewers to evaluate four narrower questions:

1. Are the reported hidden-state results methodologically credible at their
   stated evidence tiers?
2. Can the Evidence Packet design become useful model-governance infrastructure
   once identity, durability, provenance, and computation-honesty gates close?
3. What architecture is required for real dense and mixture-of-experts model
   execution at 20B through 300B scale?
4. Is a TKS/CAS semantic target useful beyond conventional probes, matched
   taxonomies, and strong text baselines?

This document does not ask reviewers to accept a universal cognition theory or
a production-readiness claim.

## 2. How to read the evidence classes

The packet separates three classes that must not be collapsed:

- **Demonstrated research result**: a local report or packet exists with exact
  bytes and a SHA-256 hash. This does not imply independent replication,
  customer-production readiness, or a standing `ACCEPT`.
- **Diagnostic or apparatus evidence**: a component, test, planner, runtime
  observation, or packet mechanism exists. It does not establish a scientific
  model claim or frontier execution.
- **Engineering objective**: an intended capability with an explicit closure
  contract. It remains `OPEN` or `NOT LICENSED` until the contract is met.

The word `LICENSED` is reserved for the project's evidence-governance status.
It does not mean a legal license, certification, or regulatory approval.

## 3. Current bounded technical description

CAS Harness is designed to attempt introspection on every legally accessible
open-weight model whose runtime can expose internal tensors. Universality is an
engineering objective, not a claim that one adapter already supports every
architecture.

An unknown model should enter `DISCOVERY_CAPTURE`: inspect the architecture,
select or generate an adapter, run a canary activation capture, and calibrate
the semantic and control layers. Missing calibration closes the customer-grade
verdict, not the research program.

The intended stable interface is a shared Probe IR and a versioned TKS-derived
semantic target. Architecture hooks, tensor shapes, model-specific maps, and
dense/MoE/recurrent/multimodal execution backends must adapt per model family.

## 4. Demonstrated research results, with boundaries

### 4.1 Cross-model Foundation-28 summaries

The 2026-07-19 corrective claim matrix reports held-out Foundation-28 readout
and readable-prefix likelihood shifts on six model points. Evidence depth is
not uniform.

| Model | Held-out F28 readout | Reported readable-prefix mean shift | Causal status in corrective matrix |
|---|---:|---:|---|
| Pythia-160M | 78.571% | +0.2828 | PASS on named matched-intervention row |
| Pythia-1B | about 82.398% | +0.5542 | Model-specific result not located |
| Pythia-2.8B | 85.884% | +0.583173 | Model-specific result not located |
| OLMo-1B | 90.604% | +0.603692 | Model-specific result not located |
| Qwen2.5-1.5B | 82.015% | +0.796003 | Model-specific result not located |
| GPT-NeoX-20B | 86.862% | +0.596413 | Partial, captured-vector post-hoc ablation |

This table supports only a bounded reported readout and likelihood statement on
one frozen English synthetic fixture. It does not support six-model causal
closure, independent-lab replication, natural-corpus generalization,
multilingual generalization, CAS-specificity, or universal model support.

The static-weight geometry result reported at 2.83 times random expectation
with p=.0099 is specific to Pythia-2.8B. It is not a second replicated tier at
the other five model points.

### 4.2 GPT-NeoX-20B Foundation-28 packet

Protected source contains packet
`S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`, SHA-256
`4FA6555754DF7E8A51CFBEB6FE4A59EFD8DF46CB6E7FD83A3926524B3330BD47`.
It reports:

- held-out readout 86.8622% at layer 40;
- readable-prefix likelihood shift +0.596413 over 112 cases, 90/112 positive;
- raw-symbol control +0.002524;
- captured-vector label-cover ablation 51.0369% to 38.5945%, a 12.4424
  percentage-point drop;
- same-size random-control mean drop 0.0749 percentage points and wrong-cover
  drop 0.1152 percentage points;
- final packet verdict `FLAG_FOR_HUMAN_REVIEW`.

Important bounds recorded inside the packet:

- the ablation is post-hoc on captured hidden vectors, not a live model
  forward-pass intervention;
- the model revision and independent weight hash are absent;
- several source reports point to a historical `C:\tmp` archive rather than
  files in this protected checkout;
- packet integrity is `present_only_not_verifier_clean` on this host.

### 4.3 GPT-NeoX-20B 40-Element reports

Protected source contains exact local reports for the original Stage 9 40E
run:

- probe report SHA-256
  `9CE9AF525FDD6FC47B6EB3C39C29F514096BD391C21DBEE22A1941A8B5E85E03`;
- subspace-ablation report SHA-256
  `A4D06B1AD28A54BDC3F4A48CDBD70986D6B1B45D7C303567F4BF92CFBABD5B2D`;
- eta-to-epsilon bridge report SHA-256
  `CE7672A04C8C2B0D52735334436F4EBA11B5A923AEC76D6058B7E071E62DFF13`;
- historical packet SHA-256
  `2B402931B35F7527D0BAF76467A9812D7C8D9DA232688C2A106238B5B5C7CF6D`;
- historical verifier report SHA-256
  `79D140F0D5028578D8C776EB6069CBAD53A4733E0553004AA9ECB8366374A5F0`.

The reports record:

- 8,320 samples, with 3,840 train and 4,480 test rows;
- layer-2 hidden readout 95.625% and macro-F1 95.617%;
- confirmed text-only baseline about 49.241% and shuffled-label results near
  chance;
- targeted subspace disruption 95.625% to 66.8973%, a 28.7277
  percentage-point drop;
- same-rank random mean disruption 0.0681 percentage points and maximum
  0.2679 percentage points;
- readable-prefix mean shift +1.41205 over 80 cases and partner margin
  +2.881239;
- raw-symbol shift +0.013817.

The preregistered 40E causal gate required at least a 30-point drop or a final
accuracy no greater than 65%. The reported result missed that gate. The 40E
causal tier remains `OPEN`.

### 4.4 Pythia-160M protected packet row

Protected source also contains a regenerated Pythia-160M 40E packet, SHA-256
`64A9DE4D56CE0BEE14CA8108CF97B92DF23AD11CA4D4784AC0CBAF4AD0788C87`,
whose effective verdict is `FLAG_FOR_HUMAN_REVIEW`. Its probe and ablation
reports are independently bound in the manifest. It must not be conflated with
the separate historical original-TKS40 89.799% row in the corrective matrix.

### 4.5 2026-07-21 Pythia-160M TKS definition-anchor diagnostic

A separate paid RunPod research execution completed on pod `nppakqiaux91mk`,
which was stopped after the evidence bundle was recovered and verified off-pod.
The run used frozen diagnostic source commit
`da00bd9407e7e82662b53edd77980040e34eacf4` and exact model revision
`EleutherAI/pythia-160m@50f5173d932e8e61f858120bcb800b97af589f46`.
The exact-revision GPU hook-equivalence preflight passed. A bounded eight-prompt,
two-layer operational canary also passed and its recovered receipt was
independently hash-verified before the full run proceeded.

The full capture produced a 109,414,103-byte raw NPZ, SHA-256
`454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6`,
with evaluation and definition tensor shapes `[3080, 12, 768]` and
`[3, 28, 12, 768]`. The report binds 3,164 token-ID hashes. The recovered
33-file inventory is SHA-256
`B44E4457DE6763BC41A27AA1B746CBABA19A753F788F472B2FE4EF9546624A93`.
Layer 1 was selected from validation data under the frozen shared-layer policy.

The sole preregistered primary estimand was Stage-7-test full-28 accuracy for
D3 minus A124 under mean pooling. The result was +0.00425170068 (+0.425
percentage points), with paired clustered-bootstrap 95% CI
[-0.0012755102, +0.0102040816]. Because the interval crosses zero, the primary
comparison is **inconclusive**. D3 test accuracy was 9.9065%, A124 was 9.4813%,
and the D3 character 3-5-gram TF-IDF baseline was 10.5442%.

The prespecified changed-8 slice favored A124: D3 minus A124 was -1.9345
percentage points, 95% CI [-3.4748, -0.5900]. The unchanged-20 negative-control
slice favored D3: +1.3690 percentage points, 95% CI [+0.8368, +1.9094]. These
opposing slices are consistent with moving 28-way decision boundaries and do
not identify a causal own-class definition effect. The Stage-7 evaluation bank
was generated from D3 glosses, so source-generator alignment is a material bias.
The result therefore does not establish that original TKS definitions are
semantically superior to A124.

This run is permanently `NOT_LICENSED_DIAGNOSTIC_ONLY` with
`claim_eligible=false`. It does **not** validate semantic probes, universality,
prompt-injection detection, output control, 300B execution, production
readiness, or an `ACCEPT` verdict. The off-pod local recovery is present, but an
independent object-store mirror or escrow remains `OPEN`. Amazon distribution
remains paused.

## 5. Withdrawn ACCEPT and root-cause boundary

The historical GPT-NeoX-20B 40E packet and verifier bytes above contain
machine-readable `ACCEPT`. That verdict is withdrawn.

The corrective root-cause analysis found that historical verifier logic treated
a candidate control-cover inventory as validated matched-ablation evidence. A
passing-status set admitted both `present` and `verified`, so class counts could
satisfy the control gate without the matched control having run. Once other
gates appeared green, the verifier emitted `ACCEPT`.

Commit `337d0c29b0822228dbfbb35dfc9873ca69453f1d` corrected the control-proof
invariant. A separate policy problem also affected the 20B record: the
preregistered causal threshold was missed while an older verifier used a
different SNR guard.

Therefore:

- historical bytes are retained for forensic integrity;
- their effective verdict is `FLAG_FOR_HUMAN_REVIEW`;
- WORM or packet retention cannot revive the withdrawn verdict;
- no standing `ACCEPT` exists;
- any external recipient of the old claim requires a direct correction.

## 6. Diagnostic and product-path evidence

The protected code snapshot includes the API, Evidence Packet schemas, audit
console, scale planner, Fleet scheduler, worker scripts, and verification code.
Their presence establishes apparatus, not scientific or production closure.

A point-in-time 2026-07-16 handoff reported protected commit `81b5c18b`, tree
`4aa8b6d`, Render deployment `dep-d9cei8d8nd3s738mism0`, and readiness with a
real Pythia-160M worker plus S3 Object Lock `GOVERNANCE` mode and 31-day
retention. This packet did not re-query those mutable providers on 2026-07-21,
so those facts are historical observations, not current runtime claims.

The same handoff reported all nine customer-production evidence gates `OPEN`.
Customer-production `ACCEPT` remains `NOT LICENSED`.

Evidence integrity is currently bounded:

- Governance retention is operator-overridable by a sufficiently privileged
  AWS principal;
- the retention window is time-bounded;
- multi-instance/host-loss durability is not established by the research
  packet chain;
- worker identity and computation honesty are not independently verified;
- receipt counts are not substitutes for durable raw fragment bytes and
  independent reconstruction.

## 7. Engineering objectives and closure gates

### 7.1 Universal open-weight introspection

Status: `OPEN`.

Closure requires a versioned architecture adapter and Probe IR for each tested
family, canary tensor capture, model/revision and semantic-source hashes,
calibration, strong text and matched-taxonomy controls, uncertainty, causal
tests where claimed, and family-held-out replication. Unknown models enter
discovery; they do not receive invented customer verdicts.

### 7.2 Real 300B-class execution

Status: `NOT LICENSED`; execution evidence above 20B is absent.

A plan, layer count, worker count, or receipt count is not execution. Closure
requires:

1. a legally usable, pinned 300B-class model and exact revision;
2. real tensor, pipeline, or expert parallel placement without every worker
   loading the full model;
3. dense/MoE-aware memory and routing behavior measured on actual hardware;
4. cryptographic worker identity and plan-to-execution binding;
5. checkpoints, restart/resume, worker-loss fault injection, and deterministic
   fragment ownership;
6. durable evidence bytes, hashes, versions, and independent reconstruction;
7. a complete Evidence Packet under an immutable policy/preregistration hash;
8. no promotion beyond `FLAG_FOR_HUMAN_REVIEW` unless every required gate is
   independently satisfied.

The current UI also contains a diagnostic inconsistency: one 300B request uses
160 layers while the display plan says layers 0-119. That must be corrected or
made model-metadata-driven before a technical demonstration.

### 7.3 Prompt-injection detection

Status: `NOT LICENSED` for product claims.

The recorded Qwen prompt-injection W0 hidden-state balanced accuracy was
89.6875%, while character n-gram baselines reached about 92.5-93.1%. The
initial pass was withdrawn. Closure requires provenance-aware splits, adaptive
attacks, strong character/token/embedding baselines, architecture replication,
calibration, and independently useful incremental lift.

### 7.4 Output control

Status: `OPEN` / `NOT LICENSED` for general control claims.

Readable-prefix likelihood conditioning is demonstrated at named fixed-fixture
rows. It is not equivalent to reliable free-form behavior control. A separate
drive-local eraser implementation has a known coordinate-space mismatch between
the calibrated 3,072-wide MLP intermediate representation and a 768-wide
post-projection hook. It remains quarantined pending hook-fired, tensor-effect,
output-effect, matched-control, safety, and utility receipts.

### 7.5 CAS-specificity

Status: `OPEN` / `NOT LICENSED`.

The first blind matched-taxonomy comparator was `GREY`. Original TKS
definitions, a byte-different deployed payload, normalized rich definitions,
compact CAS summaries, coherent alternative ontologies, and shuffled/random
controls require a same-model, same-hook, same-split, same-seed comparison.

## 8. Uncertainty and reproducibility limits

The reported experiments use one frozen English synthetic fixture. Reported
Wilson intervals are descriptive binomial intervals for one fixed held-out
split. They do not include layer-selection uncertainty, multiplicity,
cross-seed variation, cross-dataset variation, or cross-validation.

This protected snapshot does not contain all raw activations referenced by the
older public evidence manifest. For example, its listed Pythia Foundation
activation manifest and NPZ are absent from this checkout. Several 20B F28
source artifacts remain referenced by historical absolute `C:\tmp` paths.

The 2026-07-21 definition-anchor raw NPZ, reports, receipts, and 33-file
inventory were recovered off-pod under
`C:\tmp\cas-tks-anchor-diagnostic-20260721\full_recovery`. They are not part of
the protected base tree, and no independent object-store copy or third-party
escrow has yet been verified.

Before external technical reliance, every claim row should supply:

- exact model and revision plus weight hash where legally possible;
- dataset, semantic-definition, crosswalk, split, and preregistration hashes;
- capture code commit and container/environment digest;
- all seeds, layer-selection policy, classifier/hyperparameters, and
  multiplicity policy;
- raw or escrowed activations and reports;
- exact rerun command and expected output hashes;
- independent reproduction status.

## 9. Questions for Amazon reviewers

1. What matched controls would distinguish a TKS/CAS semantic target from a
   generic coherent taxonomy?
2. What evidence would justify moving from a reported fixed-fixture result to
   a model-governance decision?
3. Which AWS execution substrate is appropriate for activation capture and
   dense/MoE parallelism while preserving customer weight isolation?
4. What identity, attestation, redundancy, and replay design would make worker
   results trustworthy?
5. What evidence-retention and independent-witness design is credible for
   long-lived third-party review?
6. Which natural, multilingual, adversarial, and held-out datasets should be
   required before cross-architecture claims are taken seriously?
7. Does a versioned Evidence Packet add practical value beyond existing
   interpretability notebooks, evaluation frameworks, and observability tools?

## 10. Distribution gate

Do not send this packet while any of the following remain true:

- `LATEST.json` hashes do not match the source and manifest;
- a claim lacks its exact artifact status and caveat;
- old `ACCEPT` language is not visibly retracted;
- mutable deployment facts are presented as current without fresh readback;
- the source is not reviewed against protected code;
- confidentiality and recipient authorization are unresolved;
- the current definition-anchor bundle has no verified independent object-store
  mirror or escrow;
- the PDF, if generated, has not passed visual inspection;
- project owner and required legal/IP reviewers have not approved release.

For broad outreach, prepare a separate nonconfidential 3-5 page brief first.
Do not assume that individual employees are authorized to accept NDA-restricted
or unsolicited confidential material on behalf of Amazon.

## Appendix A - controlling input hashes

| Input | SHA-256 | Role |
|---|---|---|
| Protected commit | `81b5c18bd83e1f01ccd398dcad3865a674335b7f` | Code snapshot |
| Protected tree | `4aa8b6dbd8d5f78345a3acd84f4c0e4716244908` | Exact source tree |
| Corrective claim matrix Markdown | `EF8C7E88BFD0FA8B08B15D229D11473D99D7CACAF8D206AC3621481EAE3BE1E4` | Claim authority input |
| Corrective matrix PDF | `163EAE696E24F26264B8D8187185DA1F7AD5E4577DE4A87F364BE9B7AE567524` | Reviewed render input |
| Corrected consolidated spec Markdown | `FD0243F9F5A210D49ECE7F7DDC8999638A69A06DB25FE3559D32B703FA1C70FD` | Superseded narrative input; distribution paused |
| Corrected consolidated spec PDF | `956328F4ADDAEAEEB6B9EA2AE83DC9180B7E1F3F8F0DD5A8A4D5F3D7E664FA9F` | Reviewed render input |
| Canonical production tracker | `C6A9289F042F2DA21914B2D9817509E4ECC36727818A8215BA8BA596DCD0DE72` | Point-in-time mutable operational input after the recovered-run update |
| Customer-production successor | `2A16D7C457246B57D941E3C81370C2B061F70A9D9E1EA84F3F02260764C121D0` | Point-in-time handoff input after the recovered-run addendum |
| TKS universality/licensing program | `B924ADC46D2A78E89379BC090F39AD29C48115F604A7C53F635266608F2076B7` | Objective and closure-contract input |
| TKS/CAS semantic registry candidate | `A68D1B431C98F51DCD61007FBD75595659486B0092292CD92A49392D58AEEF54` | Semantic provenance input |
| J-space/Ohm/300B analysis | `F932951A85643AAF1F2D2CC3C8C8DFB7A06DD11494122633F3A7F95CC1306FD6` | Capability-gap input |
| Protected public evidence manifest | `0CE64C1759459E9D942E71475C47BE18475A62A30295D5B8B2462CA57E056B50` | Historical diagnostic manifest; not current claim authority |
| Definition-anchor diagnostic source commit | `da00bd9407e7e82662b53edd77980040e34eacf4` | Frozen `NOT_LICENSED_DIAGNOSTIC_ONLY` source |
| Definition-anchor raw NPZ | `454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6` | Off-pod recovered local diagnostic artifact; 109,414,103 bytes |
| Definition-anchor JSON report | `0440462D278DA53B2FC217F252DFF0D295C878B356FD53BCCB38CC810407CDEF` | Off-pod recovered bounded result report |
| Definition-anchor 33-file inventory | `B44E4457DE6763BC41A27AA1B746CBABA19A753F788F472B2FE4EF9546624A93` | Off-pod recovered bundle inventory; independent object store `OPEN` |

## Appendix B - prohibited shorthand

Do not write any of the following without a newly closed evidence contract:

- "causally validated across six models";
- "works on any open-weight model";
- "universal interpretability";
- "validated at 300B";
- "immutable WORM evidence";
- "independently reproducible" when required raw artifacts are absent;
- "prompt-injection detector" as a closed product capability;
- "controls model output" as a general capability;
- "first ACCEPT" or any statement implying a standing `ACCEPT`.
