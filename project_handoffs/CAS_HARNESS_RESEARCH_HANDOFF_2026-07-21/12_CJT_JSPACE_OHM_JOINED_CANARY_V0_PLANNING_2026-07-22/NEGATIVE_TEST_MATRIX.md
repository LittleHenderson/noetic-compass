# CJT/J-Space/CAS-Ohm Joined Canary V0 — Negative-Test Matrix

Status:

`PLANNING_ONLY / NO_EXECUTION / SHADOW / NONE / NOT_LICENSED`

The future implementation must assign stable error codes and retain a
create-once failure receipt for every row below. “Reject” means stop the
affected condition or run before claim-bearing output; it never means delete
the unfavorable evidence.

| ID | Injected defect or adversarial case | Required fail-closed result | Required retained evidence |
|---|---|---|---|
| SCHEMA-001 | Unknown or missing factor enum | Reject condition before model access | Canonical invalid payload, schema/version hash, error code |
| SCHEMA-002 | Duplicate JSON key or non-finite number | Reject canonicalization | Raw bytes, parser/canonicalizer identity, failure receipt |
| SCHEMA-003 | Duplicate `condition_id` with different bytes | Abort run as identity collision | Both payload hashes and create-once ledger |
| SCHEMA-004 | Base grid is not exactly 2,205 unique cells per seed | Abort freeze/execution | Expected/observed factor-product and duplicate/missing cell list |
| MAP-001 | `C` and `I_internal` have no frozen relationship | Reject protocol | Observation-map validation receipt |
| MAP-002 | `V_ext` is silently copied from `alpha` | Reject protocol/condition | Variable provenance and mismatch report |
| MAP-003 | Bias manipulation changes `V_ext` or `C` beyond budget | Mark Bias identification failed | Intended/measured Bias, drive/cause shifts, interval |
| MAP-004 | Baseline, normalization, direction sign, or output functional missing | Reject condition | Missing binding list and protocol hash |
| RPM-001 | RPM trace absent but result says intact | Reject condition | Trace validator failure |
| RPM-002 | Prerequisites reordered but labelled intact | Reject condition | Ordered identities, observed order, mismatch |
| RPM-003 | Wisdom ablation collapses Power only because of subspace containment | Withhold prerequisite conclusion | Containment analysis and matched-rank controls |
| RPM-004 | Wisdom probe is stronger than Power probe | Withhold prerequisite conclusion | Decodability/rank comparison |
| RPM-005 | Restored and sham paths are indistinguishable from claimed intact effect | Fail RPM gate | Paired contrasts and intervals |
| ADAPTER-001 | Model layer count was guessed rather than read from exact config | Reject adapter qualification | Config/model hashes and enumeration report |
| ADAPTER-002 | Unknown architecture is treated as GPT-NeoX or dense by fallback | Enter `DISCOVERY_CAPTURE`; customer verdict fails closed | Architecture fingerprint and unsupported-feature list |
| ADAPTER-003 | MoE model is treated as dense total-parameter execution | Reject capacity/execution plan | Expert topology and active/total accounting |
| ADAPTER-004 | Wrong tuple/output tensor selected | Reject adapter qualification | Shape/dtype/device and baseline-equivalence diff |
| ADAPTER-005 | Token/chat-template/padding position differs from frozen mapping | Reject condition | Exact text/token/template hashes and mismatch |
| ADAPTER-006 | No-hook adapter changes baseline logits/generation | Reject adapter | Baseline functional-equivalence artifacts |
| HOOK-001 | Invalid layer/token/unit coordinate | Reject before or at hook attach | Coordinate validator receipt |
| HOOK-002 | Hook never fires | Mark condition `FAILED_CLOSED` | Expected/observed fire count and raw hook log |
| HOOK-003 | Hook fires more than registered | Mark condition `FAILED_CLOSED` | Fire sequence, call sites, tensor identities |
| HOOK-004 | Hook fires but tensor is unchanged | Mark intervention unrealized | Before/after tensor hashes and displacement |
| HOOK-005 | Realized displacement has wrong sign or wrong magnitude | Fail intervention arm | Intended/realized vectors, norms, angle, interval |
| HOOK-006 | Off-target displacement exceeds budget | Fail causal-control gate | Registered off-target measurements |
| HOOK-007 | Hook remains attached after condition | Abort run and quarantine subsequent rows | Cleanup check and affected condition IDs |
| HOOK-008 | Model parameters/files mutate | Abort run | PRE/POST parameter/file inventory |
| CAUSAL-001 | Random or orthogonal control moves output as much as intended direction | Fail specificity gate | Paired mediator/output effects and intervals |
| CAUSAL-002 | Wrong sign/layer/token behaves like intended arm | Fail pathway gate | Complete arm comparison |
| CAUSAL-003 | Hidden mediator moves but generated behavior does not | Do not claim output control | Same-transaction hidden/output artifacts |
| CAUSAL-004 | Behavior moves without registered mediator movement | Do not claim registered-path mediation | Same-transaction hidden/output artifacts |
| CAUSAL-005 | Ablation silently no-ops | Fail arm, not pass | Hook-fire and nonzero tensor-change proof |
| PROMPT-001 | Injection presence is used as attack-success label | Reject dataset/rubric | Axis-correlation audit |
| PROMPT-002 | Safe refusal is labelled successful hijacking | Reject label and route ambiguity to review | Raw generation and rubric trace |
| PROMPT-003 | Ignored injection is collapsed into refusal | Reject label | Independent outcome axes |
| PROMPT-004 | Ambiguous reviewer disagreement coerced to favorable class | Reject analysis | Reviewer records and `AMBIGUOUS_HUMAN_REVIEW` receipt |
| PROMPT-005 | Attack/template/payload family appears in fit and evaluation | Abort claim-bearing analysis | Group split and overlap report |
| PROMPT-006 | Exact or near duplicate crosses split threshold | Fail leakage screen | Normalized prompt hashes and threshold-crossing pairs |
| PROMPT-007 | Character 3–5-gram or strongest surface baseline matches/beats internal detector | Keep prompt-injection detection `OPEN / NOT_LICENSED` | Surface and hidden metrics with grouped intervals |
| PROMPT-008 | Length, encoding, domain, or payload metadata explains signal | Fail internal-specificity gate | Stratified/matched control results |
| JSPACE-001 | Historical detached vectors presented as live Jacobian evidence | Reject evidence class | Artifact provenance and graph-retention status |
| JSPACE-002 | TKS D3 is silently replaced by A124 or compact CAS | Abort semantic analysis | Exact definition arm texts/tokens/hashes |
| JSPACE-003 | Sparse-cone implementation/hash differs from freeze | Reject execution | Implementation hash and deterministic replay |
| JSPACE-004 | Haar, pseudo-definition, random-direction, or surface control missing | Keep J-Space claim `NOT_LICENSED` | Expected/observed control ledger |
| BRIDGE-001 | Eta-to-epsilon readable prefix is called activation steering | Reject claim mapping | Lane type and intervention-absence receipt |
| BRIDGE-002 | Readable wording effect lacks semantic-matched non-CAS/irrelevant controls | Fail bridge-specificity gate | All prefix-arm likelihoods |
| OHM-001 | `R=V/I` is computed on one row and used as self-fit proof | Reject analysis | Fit/evaluation provenance |
| OHM-002 | `G_eff` interval contains zero | Emit `R_eff=UNAVAILABLE` | Slope interval and reciprocal decision |
| OHM-003 | `g_B` interval approaches/crosses zero | Emit `r_pi_CAS_derived=UNAVAILABLE` | Paired denominator and Fieller interval |
| OHM-004 | Infinity, clipping, or zero substitution is used for unavailable ratio | Reject package | Raw values and serialization failure |
| OHM-005 | Nonlinear competitor wins but linear Ohm label is forced | Reject Ohm label | Held-out curve competition |
| OHM-006 | Operating region or sign is unstable across seeds/groups | Fail scope | Grouped intervals and stability report |
| STATS-001 | Repeated prompts or seeds counted as independent clusters | Reject inference | Cluster-unit audit |
| STATS-002 | Calibration/selection/evaluation leakage | Abort analysis | Data-access and split provenance |
| STATS-003 | Multiplicity family or threshold changed after outcomes | Abort claim-bearing result | Anchored protocol versus executed analysis diff |
| STATS-004 | Expected arm/cell count differs from observed | Mark run incomplete | Full count and missing/extra/duplicate lists |
| RECEIPT-001 | Missing raw artifact but summary receipt says pass | Reject condition/run | Expected member manifest |
| RECEIPT-002 | Artifact byte/hash mismatch | Quarantine artifact and fail verification | Expected/observed hashes |
| RECEIPT-003 | Partial run is silently analyzed as complete | Reject analysis | Completion ledger and failure receipts |
| RECEIPT-004 | Duplicate or overwritten create-once receipt | Abort verification | Filesystem/object version history |
| RECEIPT-005 | Failed or negative outcome is omitted | Reject package | Expected condition ledger and gap report |
| RECEIPT-006 | Independent receiver cannot reconstruct metric from raw data | Keep result `NOT_LICENSED` | Receiver error and missing dependency/artifact list |
| SECURITY-001 | Worker identity/certificate does not match lease | Reject fragment | mTLS/signature/lease evidence |
| SECURITY-002 | Worker submits unleased or replayed shard | Reject fragment and record replay | Lease fencing counter and shard identity |
| SECURITY-003 | Checkpoint resume changes deterministic output outside tolerance | Fail resume gate | Pre-loss/post-resume comparison |
| SECURITY-004 | Worker or host loss cannot recover complete evidence | Fail durability gate | Fault-injection transcript |
| SECURITY-005 | Off-host copy cannot be read and reverified | Fail retention gate | Recovery-read failure |
| 300B-001 | Planner or estimated receipt count presented as execution | Reject 300B claim | Evidence-class validator |
| 300B-002 | Small-model distributed success presented as 300B result | Reject 300B claim | Exact model/parameter/revision identity |
| 300B-003 | Shard fragments are complete but approximation error is unbounded | Fail 300B scientific gate | Reconstruction/error measurements |
| 300B-004 | One expert subset is measured but total MoE model is claimed | Reject scope | Routing/expert coverage ledger |
| CLAIM-001 | Smoke pass is promoted to semantic or product license | Reject promotion | Gate/status provenance |
| CLAIM-002 | Pythia-only pass is promoted to universal support | Reject promotion | Architecture replication ledger |
| CLAIM-003 | Joined research receipt enters customer verdict/proof-chip path | Block ingress and raise security incident | Routing/authorization audit |
| CLAIM-004 | System or operator self-issues `LICENSED` without promotion review | Reject status mutation | Authority and audit log |

## Minimum test-fixture classes

The implementation must include:

- a deterministic toy transformer with known layer/token hooks;
- a synthetic CJT/CAS-Ohm generator with known null, affine-equivalent,
  reciprocal, saturating, Hill, piecewise, monotone, denominator-unsafe, and
  RPM-confounded worlds;
- a prompt-bank fixture where character surface features intentionally win;
- a bank with attack presence separated from follow/refuse/ignore outcomes;
- an MoE-shaped adapter fixture;
- partial, duplicate, replayed, corrupted, and resumed receipt/shard fixtures;
- a distributed small-model parity and fault-recovery fixture.

Passing these fixtures proves only that the apparatus can detect planted
properties and failure modes. It does not prove those properties exist in a
real model.

