# Gate 5 Historical Recovery and Model Comparison Matrix v0.1

Document status: <code>DRAFT / OPEN / NOT FROZEN</code>

Decision status: <code>OPEN / KEEP_OPEN</code>

Engineering status: <code>RING 4 / STRUCTURE_ONLY RECOVERY CANDIDATE</code>

Experimental execution status: <code>NOT_STARTED</code>

Stage C status: <code>DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED</code>

License / disclosure / canon status:
<code>NOT LICENSED / HELD / NOT FROZEN</code>

Live / product route status: <code>unavailable / not authorized</code>

Authority boundary:
<code>PRIVATE RESEARCH ENGINEERING RECOVERY INVENTORY / NON_AUTHORITY</code>

This matrix decides what may be recovered from the historical handoff into the
current Gate 5 implementation base. It does not promote a historical result
into current evidence. It does not authorize a provider call, model load, GPU,
RunPod action, steering action, spend, disclosure, product route, scientific
verdict, <code>ACCEPT</code>, or <code>LICENSED</code> claim.

## Fixed roots and current-tree identity

Historical paths in this document are relative to:

<code>C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21</code>

Current paths are relative to:

<code>C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\project_coherence_model_smoke</code>

The initial implementation base inspected for this matrix was branch
<code>codex/project-coherence-model-smoke</code> at exact commit
<code>75713a7a6780c111cd8d81a1ef495de167f8d127</code>. The additive comparison
candidate is bound by its canonical source/test hashes below and by the future
enclosing Git commit; no self-referential future commit is embedded here.

## Historical handoff root verification

The verification was read-only. It enumerated every regular file under the
exact historical root, parsed the root <code>MANIFEST.json</code>, and
recomputed SHA-256 and byte length for each listed artifact.

| Check | Exact result |
|---|---|
| Physical regular files under the handoff root | <code>672</code> |
| Root manifest identity | SHA-256 <code>2F08EA69A6F353B8CA37560E9F63298D4BC6E455CD952F4627277E46C00977FA</code>; matches <code>MANIFEST.sha256</code> |
| Manifest artifact entries | <code>172</code> |
| Manifest-listed entries matching both SHA-256 and byte length | <code>170</code> |
| Manifest-listed entries with drift | <code>2</code> |
| Physical files not listed in the root manifest | <code>500</code> |
| Root <code>SHA256SUMS.txt</code> identity | SHA-256 <code>AA9063C1B6DA7182F2FBEECFDBE5D83290A783098ED25BF69C58D0EFBB27AF80</code>; equals the value recorded in <code>MANIFEST.json</code> |

The two exact drifted entries are:

| Relative path | Manifest bytes / SHA-256 | Observed bytes / SHA-256 |
|---|---|---|
| <code>06_REPRODUCTION_GUIDES/BUILD_AND_VERIFY_MANIFEST.ps1</code> | <code>34,312</code> / <code>CF5561BAB2C66D4285D0BA004DF825744E4BB5B6EE9135B8F80C1F7C300A0E63</code> | <code>34,915</code> / <code>8AF2ADFD9E66E18E3B28825779AFD1A9E9699834B4E216D451C6CC3B0EDCC7C4</code> |
| <code>START_HERE.md</code> | <code>9,072</code> / <code>FCDFF5FC2DEE48F19FAFD92BF80B940A9EDDD8117C81A5CEC2B785A26259E437</code> | <code>11,123</code> / <code>B273C1D210303659410DA2FE7E4B9513353C00DF5D9C10D393AC01D25390F42D</code> |

The root manifest is therefore not a closed-world inventory of the observed
handoff. In particular, these two later research status files are present but
are not root-manifest artifacts:

- <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/STATUS.md</code>
- <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/STATUS.md</code>

Attempt 11 and Gate 2 may be retained only as
<code>HISTORICAL EVIDENCE ONLY</code>. Their presence, local hashes, or
technical status cannot establish current Stage C evidence, current provider
identity, independent reproduction, current storage authority, or any Gate 5
decision.

## Classification rules

Each matrix row has exactly one controlling classification:

| Classification | Meaning |
|---|---|
| <code>CURRENT ALREADY SUPERIOR</code> | Keep the current implementation. Add only regression coverage or a narrow extension that does not replace its stronger controls. |
| <code>PORT AND REPAIR</code> | Recover the useful contract or research idea, but implement it on the current base with the stated repairs and tests. Do not copy the historical implementation unchanged. |
| <code>HISTORICAL EVIDENCE ONLY</code> | Preserve and verify the old bytes as research history. Never count them as a current run, current prerequisite, current provider receipt, or current Gate 5 result. |
| <code>REJECT</code> | Do not restore the historical behavior or use the artifact for the stated authority or execution purpose. Retention as audit history is still allowed. |

## Current structural recovery implementation checkpoint

The historical classifications below remain controlling. This checkpoint
records that their bounded software portions are now implemented through
replay-only or unavailable contracts. It supersedes older “no current module”
wording only for that structural portion. It does not convert any historical
row into current evidence or close any remaining live, scientific, trust,
licensing, or disclosure obligation.

| Matrix rows | Current canonical module | Source SHA-256 / bytes | Test SHA-256 / bytes | Current ceiling |
|---|---|---|---|---|
| A2, A5, D4 | <code>src/cas_harness_v2/comparison_model_protocol.py</code> | <code>D65A695C97465FFF8C31A6429EA2D4036606D7A1A182D6D2D71D498E30612252</code> / 59,909 | <code>C04E8F98F5DBF04A08E9C4C0C7221CAC79DC0CAA4BB595B35BFEB863FD6D9988</code> / 39,295 | Exact open/closed/replay identity and capability carriers; no model/provider call |
| D4 | <code>src/cas_harness_v2/comparison_adapters.py</code> | <code>DC7741461D8C4A2C567F798A2695282350C2EB0B63586B0F2C2DB5FC1AAC353F</code> / 32,441 | <code>238AE663163640A6AED2AB90DF618BA7E027DB830A7E06ACC53F793C2E77CF68</code> / 23,948 | Exact one-use replay and fail-closed unavailable adapters only |
| D4, D7 | <code>src/cas_harness_v2/comparison_shared_protocol.py</code> | <code>32942AB2C36CD4CAD8663509BA41BE6F6AEEEED71AFDD48F82D85255DD6B12AD</code> / 58,727 | <code>EB2F46724B7C6C887DC497E1EC42E6FD6181F58515B1AD016DC0D5E46E1537E0</code> / 25,778 | Frozen two-model protocol and exact three-role matched roster |
| D4, D7 | <code>src/cas_harness_v2/comparison_shared_runner.py</code> | <code>3E23440115CA6859926DB43E46ED74AFE4684A265A037224BA06B12ABDEC58AB</code> / 36,220 | <code>FBAD60A83AF5C8A0147057CC34942ED7DAF00ACC36C3A78E6198FAF79D722877</code> / 34,134 | Exact paired replay association; no verdict or composite |
| D1, D7 | <code>src/cas_harness_v2/comparison_prompt_injection_layers.py</code> | <code>9B5E99F7F256BDD3BCB522C48CAE426D66BEE39C3B221411A4C99A69A3AE54A4</code> / 65,684 | <code>716B17C8BAF675A417208B4386C06B9FC9A3F158BF600D94180C16297EAC8167</code> / 32,628 | Separate text/context, hidden-state, and runtime-policy artifacts; no aggregate verdict |
| B1 | <code>src/cas_harness_v2/surface_meaning_preservation.py</code> | <code>8AED0A46F9B4948DFCE7DD16AC98F2C433E8C3CB3DD650B68EADC497299B27BA</code> / 39,186 | <code>261845562D3D503B85330E1D8EC85903873CF767B440447AD64A256B21E5B20F</code> / 13,822 | Per-cell/per-axis receipts; no evaluator run or overall PASS |
| D5, D7 | <code>src/cas_harness_v2/comparison_departure_metrics.py</code> | <code>96FC7370E3AD2A3B228B49BAB1F2FBF5BC61C6D105A2BD2E3D028FCECC676A12</code> / 95,655 | <code>8F281E7204A9970EFC62106D64B8962C7FC18449617B8FDE704B759005D4656A</code> / 39,887 | Deterministic signed component metrics and matched-group uncertainty; no composite |
| B9, D6 | <code>src/cas_harness_v2/comparison_steering_protocol.py</code> | <code>D2BFF44260B7234852088248AD951AADF131A1FBC839EF4BB9ACF062E86DC5F3</code> / 66,571 | <code>6AC04085590C6A00E16EFD7A530988733B0B9AE6F9CCB571EA93D109A7797980</code> / 25,202 | Separately authorized plan; unavailable backend and zero-call canary |
| B9, D6 | <code>src/cas_harness_v2/comparison_steering_effects.py</code> | <code>C9267F04FA8175AAC5758CA689E8C836BB136356AEF50B0155B2E66EF2CD0C76</code> / 59,933 | <code>43F6609AB27FAB3ECB1F18A3C902FFAF03B3F8F6C6366E3AC789931FD12E9F95</code> / 28,949 | Open steering and closed policy effects remain distinct; no shared-mechanism claim |
| D7, E1 | <code>src/cas_harness_v2/comparison_execution_boundary.py</code> | <code>DFA7E8BB4E06005340CF3856C4B56B2BDA536816D0A0CB405BE86C18151DB647</code> / 26,519 | <code>9C84A7E4546CEA363DA6876D81C5F910425DCF8DC4221A1C59DA2F75B22A2CB6</code> / 17,690 | Blocked execution and zero spend are the only buildable state |
| A2, A5 | <code>src/cas_harness_v2/universal_probe_contract.py</code> | <code>BB6993F9406B1E89A4768F084287ED6A7FBC0EC83582A8264E39D1DAFCA474C2</code> / 113,027 | <code>EB86DB71A717CBC48497BB1F54D21DDD968B559F89B4DB3BF46243DCCB73E93D</code> / 43,698 | Config/replay semantic probes and zero-call canary; no universality license |
| C3, C4 | <code>src/cas_harness_v2/distributed_probe_contract.py</code> | <code>76EFE7D146630A199473C47C9E51A99E818132E6DA629412240507B6C65AA53C</code> / 129,922 | <code>6B591871C398D80222D4E7838536EC0637067DEFC531C56D001E6F17D6501473</code> / 69,948 | Ownership/fragment/checkpoint/reconstruction structure; no distributed execution |
| B2, B4, B5 | <code>src/cas_harness_v2/jspace_shadow_contract.py</code> | <code>9AEB7BE89B8D4AA4D5B4934B5D6BD8F6D8C784CEF631CED9E05BFCC62C76C6F2</code> / 77,777 | <code>3094612E9288FCBC182E78E979971F64A67F86DFEECAE9E0469BD71AF2D49F69</code> / 33,273 | Disabled vector JVP/VJP <code>SHADOW</code>; no import, autograd, verdict, or license |
| B3, B6, C5, C6, D2, E3 | <code>src/cas_harness_v2/historical_evidence_import.py</code> | <code>10BFC49EC483B1E202D933960D12B226127FF8C0BDA7EECC640C070C94E17296</code> / 47,363 | <code>9C42EF257406D0A8D0583F91F17C74677DA85D9F0DA950E18761112DC3E87232</code> / 29,170 | Read-only <code>HISTORICAL_EVIDENCE_ONLY</code>; no current result output |

The shared roster's fixed role order is <code>ADVERSARIAL_PRESENT</code>,
<code>CLEAN_ABSENT</code>, <code>CLEAN_NULL_ABSENT</code>. Layered detector
disagreement remains visible and has no aggregate verdict. Closed-model hidden
state is <code>unavailable</code>, not a failed model. Steering remains
unavailable and separately authorized. Universal/distributed/J-Space contracts
are unmeasured replay or shadow structure only.

Bounded focused checkpoints include 460/460 for the comparison slice excluding
the distributed module, 57/57 immutable-authority tests, 39/39 historical
import, 102/102 J-Space plus authority, 47/47 distributed, and 160/160 for the
distributed dependency union. They are local software receipts only.

The packaging candidate is 36 byte-mirrored Python files, 1,097 unique exports,
and 2,332,110 bytes. Harness is configured for 1,082 nodes at node-ID SHA-256
<code>E791E0A7960201323A94F8B0BC88F53AF611771118A369D332B36100D80B7928</code>.
Worker is configured for 719 nodes at node-ID SHA-256
<code>98F7152B532C713DD22DF910FB762CE92E281A350ACA4E1A3CF2113C84D3DBB5</code>.
Current same-process suite receipts are authoritative software-test PASS within
<code>STRUCTURE_ONLY / NON_AUTHORITY</code> only. Harness completed 1,082 nodes:
1,076 exact all-phase PASS, six exact setup skips retained as mismatch evidence,
3,240 ordinary reports, 163 passing subtests, zero warnings, errors, collection
errors, internal errors, or deselections, process/pytest 0/0, empty pycache, and
<code>3059.695080</code> seconds. The
elapsed time is observational only; it is not a bound or PASS condition. Its exact
node/ordinary/subtest/origin/pre-test/loaded digests are
<code>E791E0A7960201323A94F8B0BC88F53AF611771118A369D332B36100D80B7928</code>,
<code>60F1AB42E3BA883AA3C093F506C4B0896E498C1FC3258A887895C596AAA38F29</code>,
<code>6C2AFB12D8F1DBC529C9493967B1CBB06AE98228B318DA724D093D3C84721109</code>,
<code>3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A</code>,
<code>0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98</code>,
and
<code>DC4F9C8664415C211D257DFFBFD8D0DBC942F830C138C60D6AC3A0E8D4EAC768</code>
under <code>CANONICAL VALIDATED LOADED-MODULE RECORDS / NORMALIZED-PROJECTION V1 / EXACT VERIFIER SELF-RECORD BYTE COUNT AND SHA-256 NORMALIZED TO ZERO ONLY IN THE AGGREGATE DIGEST / ACTUAL VERIFIER BYTES REMAIN MANIFEST-BOUND AND REVALIDATED</code>.

Historical Harness attempt 3 remains exact and is not promoted as the current
receipt. It collected, started, and finished 1,082 nodes: 1,076 exact all-phase
PASS, the same six exact setup skips retained as mismatch evidence, 3,240
ordinary reports, 163 passing subtests, zero warnings, errors, collection
errors, internal errors, or deselections, process/pytest 0/0, and empty pycache.
Its elapsed time was <code>3350.340165</code> seconds. Its exact
node/ordinary/subtest/origin/pre-test digests are unchanged from the current
receipt above, and its loaded-code digest was
<code>B95348D54FD003715848CBD27B79D3D486DE182E3CF9717E176E5883C7675826</code>
under the same normalized-projection rule.

Worker passed 719/719 with 2,157 ordinary reports, no subtests, warnings, or
errors, process/pytest 0/0, empty pycache, and <code>106.254353</code> seconds.
Its exact digests are
<code>98F7152B532C713DD22DF910FB762CE92E281A350ACA4E1A3CF2113C84D3DBB5</code>,
<code>CF7F1676BAAA3E83999E758A35F311743B7B227DBD0A160EF79F85AA72477468</code>,
<code>4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945</code>,
<code>035EFFD9DC44C1FD2D9F07A3BE62EA1BF07E3FD17D5807323F8D1B58AE6B0FD6</code>,
<code>3696A5457FDF85823DAC360679C750DEC5B8A691207958EE0A1854A790A21A5E</code>,
and
<code>44A6B0A13CAA30860D3802C042455F72C90FFC6D15FA7503F3B159384EFF4C34</code>.
The current adapter/reconciliation receipt collected, started, and finished 99
nodes and recorded all-phase PASS for all 99. It emitted 297 ordinary reports
and zero subtests,
recorded zero skips, one warning, and zero errors, collection errors, internal
errors, or deselections, exited process/pytest 0/0, and left the isolated
pycache empty. Its elapsed time was <code>25.401532</code> seconds,
observational only and not a bound or PASS condition. Its exact digests are
<code>B84EB29C59563DD0270C3BD8B230D604D59A2E45D38B9E375C7FA697468D656B</code>,
<code>548361800978AF55EE04B8E45B71AE70A09BBBE015025C5D6BF428F8E2FD9C9F</code>,
<code>4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945</code>,
<code>3E1424E6BDBA7B6AE417189EF951E7502D108626EB5482277A627C9D6A29887A</code>,
<code>0CBCB82DCF24426A868CFCA8DBC334661D1504A23C882DD342D5EC6767B30D98</code>,
and
<code>B543CD078076717C80341B0B9C52F158CBD20B9BB3718E4128F81373AEEA1101</code>.
Its exact status is <code>AUTHORITATIVE SAME-PROCESS PASS / STRUCTURE_ONLY / NON_AUTHORITY</code>.
Worker and adapter use <code>CANONICAL VALIDATED LOADED-MODULE RECORDS / RAW RECORDS / NO PROJECTION</code>.

The prior adapter/reconciliation receipt remains historical only. It carried
the same 99-node identity, outcome counts, ordinary/subtest/origin/pre-test
digests, exits, warning shape, and empty-pycache result, with observational
elapsed time <code>47.452869</code> seconds and loaded-code digest
<code>5C860DD3A7F787DD0826920D134796F42E02C74C1A4123F256982DF29CA499C3</code>
under the same raw-record rule. It is not the current receipt.

Harness attempt 1 timed out at 3,600 seconds with no receipt. Attempt 2 ended
process/pytest 1 because of a stale manifest and produced no receipt. After the
manifest was rebuilt to 686 artifacts, targeted red-team checks passed 22 tests
plus 23 subtests; attempt 3 produced the historical Harness PASS recorded above.
An intervening integrated replay then failed during setup at
<code>tests/cas_harness_v2/test_diagnostic_phase_coordinator.py::test_clean_480_opens_exactly_one_aggregate_access</code>
because a literal 180-second host-throughput correctness gate remained. Its
focused reproduction observed <code>population_seconds = 192.38694559999567</code>
against <code>&lt; 180.0</code>. That failed integrated replay created no
authoritative Harness receipt, and no exact whole-attempt elapsed time is
claimed here. The post-correction Harness replay produced the current receipt
above. A later integrated verifier replay failed at adapter receipt validation:
its expected loaded-code digest still named historical
<code>5C860DD3A7F787DD0826920D134796F42E02C74C1A4123F256982DF29CA499C3</code>
while the current-tree receipt yielded
<code>B543CD078076717C80341B0B9C52F158CBD20B9BB3718E4128F81373AEEA1101</code>.
It produced no integrated PASS or authoritative integrated receipt; no replay
ordinal or exact whole-run elapsed time is claimed. The fresh
adapter/reconciliation replay produced the current receipt above. The bounded
suite ceiling remains 5,400 seconds and
carries no performance authority. The executed 565-node Harness, 719/719
worker, and historical adapter/reconciliation receipts remain unchanged
historical checkpoints only. The final integrated 12-suite verifier command
<code>C:\Python314\python.exe -I -B scripts/verify_project_coherence_gate5.py</code>
exited 0 and produced <code>PASS</code>: 686 hash-bound artifacts, 457
syntax-checked Python artifacts, 2,290 executable-shadow paths before and after
tests, all 12/12 suites, Harness 1,082 nodes plus 163 passing subtests and six
exact setup skips at loaded-code digest
<code>DC4F9C8664415C211D257DFFBFD8D0DBC942F830C138C60D6AC3A0E8D4EAC768</code>,
worker 719 at
<code>44A6B0A13CAA30860D3802C042455F72C90FFC6D15FA7503F3B159384EFF4C34</code>,
adapter/reconciliation 99 at
<code>B543CD078076717C80341B0B9C52F158CBD20B9BB3718E4128F81373AEEA1101</code>,
51 review criteria, all 22 required OPEN boundaries, and 1,258 same-run file
identities rechecked in postflight. Tool-observed wall time was 3,568.3
seconds; it is observational only and is not a bound or PASS condition. This
descriptive final-replay event assigns no inferred attempt ordinal and claims
no aggregate digest.

The stable current executable-shadow path count is 2,290. The exact ignored
<code>noetic-compass-scaffold/noetic-compass/.tmp</code> transient trace subtree
is excluded from path-count authority because it is not an admitted
import/executable authority surface. All cache, native, and symlink checks
remain.

## A. Provenance, adapters, and model capability

| ID | Feature | Historical source or evidence | Current equivalent | Classification | Historical defect or risk | Required change and tests | Gate 5 effect |
|---|---|---|---|---|---|---|---|
| A1 | Protected implementation snapshot as a code source | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/</code>, including the adapter, fleet, planner, Pythia runner, shard worker, and ablation files; snapshot name binds historical commit prefix <code>81b5c18b</code> | Current implementations under <code>noetic-compass-scaffold/noetic-compass/</code> plus current Gate 5 controls | <code>HISTORICAL EVIDENCE ONLY</code> | The snapshot is a selected historical implementation surface, not the current full repository, current dependency lock, or deployable authority. Several files contain known geometry, sharding, and no-op defects. | Compare file by file. Port only through separate reviewed changes. Require current-tree unit tests, known-fault tests, package parity, manifest coverage, and the final unchanged-tree Gate 5 verifier. | No current evidence or status changes. The snapshot cannot replace the current base. |
| A2 | Universal Probe IR, model discovery, and semantic observation contract | <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md</code> | Exact-model binding in <code>noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/model_loader.py</code>; narrow adapter in <code>noetic-compass-scaffold/noetic-compass/api/services/cas_harness_architecture_adapter.py</code> | <code>PORT AND REPAIR</code> | The historical document has a strong typed design for residual, attention, MLP, router, expert, recurrent, and multimodal observations, but no production implementation, generated adapter, sandbox, owning-rank proof, or current tests. | Add a versioned provider-neutral Probe IR. Bind model revision, architecture family, native path, semantic hook, pre/post location, layer, token, head/expert, owning rank, shape, dtype, quantization, transform, and adapter version. Implement config-only discovery, graph/signature inspection, bounded canaries, sentinel/non-empty checks, shape checks, zero/sham effect checks, ambiguity reports, and a fail-closed unavailable backend first. Test dense, encoder-decoder, MoE, SSM/recurrent, multimodal, remote-code rejection, and owning-rank cases with fixtures only. | Adds a design and software capability surface only. It does not license a model family or authorize execution. |
| A3 | Historical hard-coded architecture adapter | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/api/services/cas_harness_architecture_adapter.py</code> and <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/tests/test_cas_harness_architecture_adapter.py</code> | <code>noetic-compass-scaffold/noetic-compass/api/services/cas_harness_architecture_adapter.py</code> plus exact runtime checks in <code>noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/model_loader.py</code> | <code>REJECT</code> | Four hard-coded stack paths and model-type declarations are not universal discovery. Declared model type can be mistaken for verified compatibility; dimensions are recorded but not fully enforced; whole-block fallback changes semantics; router/expert and rank ownership are absent. | Do not copy or widen the name table. Replace it through A2 with generated, canary-verified adapter manifests. Add tests that reject false family names, wrong shapes, whole-block semantic substitution, missing projections, duplicate hooks, and non-owning-rank capture. | Prevents a false universality claim. Gate 5 remains open. |
| A4 | Exact Pythia/Qwen loading, hook binding, and intervention failure handling | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/live-trace-worker/app/runtime/pythia_runner.py</code> and <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/live-trace-worker/scripts/run_open_weight_cover_ablation.py</code> | <code>noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/model_loader.py</code>, <code>pythia_runner.py</code>, <code>ablation_probe.py</code>, and their current tests | <code>CURRENT ALREADY SUPERIOR</code> | The old runner could return a silent no-op when coordinates were absent, lacked the current exact runtime-object binding, and used an ablation hook whose 3,072-wide intermediate coordinates did not match a 768-wide post-projection tensor. | Keep current exact revision/artifact checks, local-only safe loading, geometry canaries, hook cardinality, paired RNG restoration, typed structural rejection, tensor-change receipts, and generic Qwen intervention refusal. Add only regression tests for every supported adapter introduced by A2. | No Stage C execution or steering authority. Current Stage C still requires zero generation and zero interventions. |
| A5 | Capability licensing based on measured support | Capability-state ladder in <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md</code> | Exact Stage C binding and current status surfaces in <code>docs/working/project_coherence/gate5/README.md</code>, <code>GATE5_WORKER_PROTOCOL_BINDING_v0.1.md</code>, and <code>stagec_qwen_prompt_injection_v0.1/README.md</code> | <code>PORT AND REPAIR</code> | The historical ladder correctly separates discovery, capture, readout, causal effect, distributed execution, recoverability, model capability, and universality, but it was not implemented as an exact model/revision/capability registry. Historical size-level planner labels contradict it. | Add a versioned capability report keyed by exact model, immutable revision, artifact set, adapter, tensor, backend, and test receipt. Make state transitions monotone and evidence-bound. Test model substitution, revision drift, unsupported closed-model hidden states, partial capability, stale evidence, and any attempt to infer support from name or parameter count. | Can report <code>present</code> or <code>unavailable</code> per capability after evidence exists. It cannot produce <code>UNIVERSALITY_LICENSED</code> or close Gate 5 by itself. |
| A6 | TKS semantic source authority and crosswalk conflicts | <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json</code> | <code>docs/working/project_coherence/CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json</code> and current Gate 0/1 source-control artifacts | <code>CURRENT ALREADY SUPERIOR</code> | The historical registry preserves important distinctions such as D3 versus A124 and A1-D10 versus A0-D9, but it is candidate-only, not owner-signed, and leaves conflicts unresolved. | Keep the current authority matrix and unresolved-conflict posture. Regression-test that historical aliases cannot collapse distinct definitions, index systems, World/Domain/Register, Foundation/Drive, Acquisition, or algebra conflicts. | No semantic promotion. Source authority remains open and not frozen where the current matrix says so. |

## B. Surface meaning and mechanistic shadow research

| ID | Feature | Historical source or evidence | Current equivalent | Classification | Historical defect or risk | Required change and tests | Gate 5 effect |
|---|---|---|---|---|---|---|---|
| B1 | TKS Surface Gate and Meaning Preservation Gate | <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/HISTORICAL_CLAIM_AND_AUDIT_CONTEXT/cas_harness_original_closure_methodology_20260526.md</code> and <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md</code> | Surface inventory and Stage C surface controls in <code>docs/working/project_coherence/gate1/v74/TKS_V74_SURFACE_INVENTORY_v0.1.json</code> and <code>docs/working/project_coherence/gate5/stagec_qwen_prompt_injection_v0.1/README.md</code>; no complete meaning-preservation receipt exists | <code>PORT AND REPAIR</code> | The historical method correctly says to remove answer-key wording without removing meaning and supports per-cell <code>meaning_bearing</code> versus <code>vocabulary_dependent</code> status. Its fixed 60% text ceiling and 20-point hidden lift are legacy thresholds; rater identity, independence, blinding, rubric freeze, power, and machine-verifiable receipts are incomplete. | Add versioned <code>SurfaceGateReceipt</code> and <code>MeaningPreservationReceipt</code>. Freeze exact definitions, crosswalks, paraphrase provenance, raters/evaluators, rubric, blind assignment, power, and per-cell disposition. Require decode-aware text, character, token, embedding, provenance, length, taxonomy, carrier, and payload-family controls. Test meaning deletion, vocabulary-only survival, rater leakage, evaluator substitution, row mixing, and overall-axis claims made from failed cells. | A future pass can support a narrow corpus/tensor claim only. It does not authorize Stage C, steering, semantic truth, or Gate 5 closure. |
| B2 | J-Space shadow protocol and strict source loading | <code>08_JSPACE_CAS_OHM_SHADOW_2026-07-21/START_HERE.md</code>, <code>IMPLEMENTATION_AND_TEST_REPORT.md</code>, and <code>cas-jspace-ohm-shadow-de1a117d.bundle</code> | Current Gate 5 preregistration/evidence controls plus no current J-Space runtime module | <code>PORT AND REPAIR</code> | The historical lane is disabled, shadow-only, and provenance-aware, but its receipt is metadata-only and local. It has no registered comparison basis, output functional, JVP/VJP intervention, multi-dose schedule, current WORM anchor, or current authorization. | Recover only the strict loader and quarantine pattern. Add exact source-bundle verification before import, a registered correspondence basis, dimension/rank checks, output-functional identity, matched controls, known-fault corruption tests, and a replay/unavailable backend. Keep the module disabled by default. | Adds a separate <code>SHADOW / NONE / NOT LICENSED</code> research lane. It cannot affect the Stage C detector verdict. |
| B3 | Exact J-Space/CAS-Ohm historical shadow baseline | <code>08_JSPACE_CAS_OHM_SHADOW_2026-07-21/research_shadow_baseline_final.json</code> and <code>08_JSPACE_CAS_OHM_SHADOW_2026-07-21/REVIEW_RECEIPT.md</code> | No current result equivalent | <code>HISTORICAL EVIDENCE ONLY</code> | The record explicitly says J-Space and CAS-Ohm are baseline-only and Jacobian inference is not computable from activations alone. It is local historical output, not a current execution or functional measurement. | Allow hash-bound archive import only. Test that import preserves original status, source identity, and <code>NOT_LICENSED</code>, and cannot enter a current Evidence Packet result slot. | No current scientific or Gate 5 effect. |
| B4 | Corrected vector JVP/VJP local-gate contract | <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_09_GPU_EXECUTION_FAILED_CLOSED_LOCAL_JVP_VJP/INVESTIGATION_local_vjp.md</code> and <code>PROPOSED_FIX_local_gates.md</code> | No current Gate 5 JVP/VJP implementation | <code>PORT AND REPAIR</code> | The investigation correctly diagnoses a near-zero scalar VJP denominator and proposes a vector adjoint comparison, but the repair is embedded in an old attempt line and its thresholds are not a current preregistration. | Implement a disabled shadow contract using explicit output functionals, vector adjoints, finite/dtype/shape checks, relative and absolute tolerances justified by calibration, independent corruption known-faults, and exact autograd/backend identity. Test zero-denominator, wrong tangent, wrong adjoint, detached graph, rank loss, dtype drift, and deliberate artifact corruption. | At most a technical shadow receipt. It cannot establish TKS meaning, injection detection, causal benefit, or Gate 5 closure. |
| B5 | Scalar VJP near-zero-denominator gate | Attempt 9 files under <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_09_GPU_EXECUTION_FAILED_CLOSED_LOCAL_JVP_VJP/evidence/</code> | None | <code>REJECT</code> | A scalar projection can make the reference denominator nearly zero and turn a numerically valid derivative into a false structural failure or unstable pass. | Do not port the scalar metric or inherit its thresholds. Add a regression fixture that recreates the failure and proves B4 fails closed or uses the preregistered vector contract. | Prevents a false Jacobian pass. No status change. |
| B6 | Attempt 11 technical Jacobian canary result | <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_11_TECHNICAL_CANARY_PASS_GATE1/STATUS.md</code> | No current result equivalent; current control surface is <code>docs/working/project_coherence/gate5/GATE5_ENGINEERING_EXECUTION_RECONCILIATION_v0.1.json</code> | <code>HISTORICAL EVIDENCE ONLY</code> | The exact file is outside the 172-entry root manifest. Its own ceiling is a technical Gate 1 pass: it lacks semantic, injection, output-control, universality, J-Space, CAS-Ohm, external-reproduction, and cryptographically authenticated provider/model-origin authority. | Preserve as a non-promotable historical receipt. Test archive import against current-status relabeling, provider relabeling, attempt replacement, and result-slot injection. | It cannot count as current Gate 5 or Stage C evidence. |
| B7 | CAS-Ohm typed dose-response and uncertainty model | <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md</code>, supplied CAS-Ohm guides, and the baseline-only shadow record | <code>docs/working/project_coherence/gate4/CAS_OHM_V1_SOURCE_AUDIT_AND_SPEC_v0.1.md</code>, <code>src/cas_ohm_v1/</code>, and <code>tests/cas_ohm_v1/test_cas_ohm_v1.py</code> | <code>CURRENT ALREADY SUPERIOR</code> | Historical material supplies useful response-profile language but no licensed measurement. Literal electrical-law analogies can hide unit, calibration, and outcome-definition conflicts. | Keep the current typed units, evidence classes, calibration profile, response-region/semantic-outcome separation, held-out resistance, uncertainty, exact identities, and known-fault tests. Extend only through a separately preregistered steering shadow protocol. | CAS-Ohm remains <code>OPEN / RING 4 / NOT LICENSED / HELD</code>. |
| B8 | Historical Pythia cover ablation and pooled shard readout | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/live-trace-worker/scripts/run_open_weight_cover_ablation.py</code> and <code>run_open_weight_probe_shard.py</code> | Current exact loader/runner/ablation files under <code>noetic-compass-scaffold/noetic-compass/live-trace-worker/</code> | <code>REJECT</code> | The old ablation clips intermediate coordinates against a post-projection width and may leave output unchanged. The shard readout pools top absolute values across scenarios/layers, loses sign and stable coordinate meaning, and is not a valid fixed-width hidden-state probe. | Do not restore coordinate clipping or pooled top-absolute readout. Test exact tensor identity, width, sign, feature order, hook firing, tensor mutation, output mutation, zero dose, wrong layer, and out-of-range coordinates. | Blocks false causal and steering claims. |
| B9 | Disabled activation-steering lane | Historical J-Space/JVP/VJP/TKS/CAS-Ohm designs above and the repaired current Pythia intervention safeguards | Stage C explicitly forbids steering in <code>docs/working/project_coherence/gate5/stagec_qwen_prompt_injection_v0.1/README.md</code>; no separate current steering module | <code>PORT AND REPAIR</code> | Historical steering concepts mix detection and intervention, lack a complete dose/control contract, and include silent no-op and geometry defects. | Add a separately versioned module that is disabled and unavailable by default. Require its own preregistration, phase authorization, exact activation coordinate, zero and multiple doses, smallest-effective-dose rule, wrong-layer, random-vector, sign-reversed, shuffled-vector, null, meaning-preservation, unrelated-task damage, hook-fired, activation-change, and output-change evidence. Test that Stage C authorization can never activate it and that unavailable backends make zero model calls. | No change to Stage C: zero generation and zero intervention remain mandatory. Any future steering run needs a separate authorization and claim lane. |

## C. Fleet, scale, sharding, and durable recovery

| ID | Feature | Historical source or evidence | Current equivalent | Classification | Historical defect or risk | Required change and tests | Gate 5 effect |
|---|---|---|---|---|---|---|---|
| C1 | Fleet control plane | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/api/services/cas_harness_fleet_executor.py</code> and its two historical fleet tests | <code>noetic-compass-scaffold/noetic-compass/api/services/cas_harness_fleet_executor.py</code>, <code>tests/test_cas_harness_fleet_executor.py</code>, and <code>tests/test_cas_harness_fleet_executor_contract.py</code> | <code>CURRENT ALREADY SUPERIOR</code> | Historical fleet code has leases, heartbeats, durable ledger concepts, and merge gates, but lacks the current active-job lease, configured inventory snapshot, replayable model attestation, and exact artifact/model validation. | Keep the current control plane. Add regression tests only when C4 introduces a real backend: lease/attestation replay, stale rank, duplicate fragment, conflict terminalization, and no replacement. | Software control evidence only. A fleet ledger does not prove that weights were sharded or executed. |
| C2 | Scale planner | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/api/services/cas_harness_scale_planner.py</code> and <code>tests/test_cas_harness_scale_planner.py</code> | Same current paths under <code>noetic-compass-scaffold/noetic-compass/</code> | <code>PORT AND REPAIR</code> | The planner uses parameter-count times bytes, a fixed overhead, even division, global size labels, and synthetic tensor-shard names. It omits topology, interconnect, KV/cache, activation peaks, quantization runtime, MoE/router/expert ownership, and measured exact-model evidence. | Replace size-level validation with topology- and exact-revision-specific measured profiles. Separate estimate, measured plan, and execution receipt. Test dense/MoE, pipeline/tensor/expert layouts, quantized and unquantized peaks, interconnect limits, OOM margin, impossible topology, and plan/execution drift. | A plan remains non-execution evidence and cannot raise a capability state without measured receipts. |
| C3 | Historical shard worker execution | <code>07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b/live-trace-worker/scripts/run_open_weight_probe_shard.py</code> | Current script has stronger identity checks but still is not proof of genuine model sharding | <code>REJECT</code> | Each worker loads the full model and only then selects layer hooks. Worker count and invented tensor-shard assignment therefore masquerade as distribution while multiplying memory. Optional revision and remote-code behavior also weaken the historical boundary. | Do not call this a distributed backend. Tests for any successor must inspect per-rank parameter ownership and fail if each rank owns a full-model copy or if a rank captures a non-owned tensor. | Prevents <code>DISTRIBUTED_EXECUTION_VERIFIED</code> from being claimed on false evidence. |
| C4 | True tensor/pipeline/expert distributed execution and fragment merge | Distributed design in <code>03_RESEARCH_AND_ARCHITECTURE_DOCS/CAS_HARNESS_TKS_UNIVERSALITY_LICENSING_PROGRAM_20260720.md</code> and <code>CAS_HARNESS_JSPACE_OHM_300B_CAPABILITY_ANALYSIS_20260720.md</code> | Current fleet control plane; no real Gate 5 distributed model backend | <code>PORT AND REPAIR</code> | The historical design has the right owning-rank and reconstruction obligations but no implemented backend. The historical worker contradicts the design by loading the full model per worker. | Add a fail-closed unavailable backend first, then a separately authorized real backend. Bind exact topology, rank, owned parameter ranges, owned probes, model shard hashes, fragment object version/hash/length, checkpoint, merge order, and independent reconstruction. Test no full copy, rank failure, OOM, stale/duplicate/conflicting fragment, resume without replacement, retry prohibition, exact reconstruction, and merge disagreement. | Can advance only the exact model/revision/backend capability after a future authorized measured run. It does not establish 100B/300B support now. |
| C5 | Exact historical definition-anchor run and off-pod local recovery | <code>02_RESEARCH_EVIDENCE/full_recovery/RESULT_SUMMARY.md</code>, <code>OFF_POD_VERIFICATION.json</code>, and <code>artifacts/full/tks_definition_anchor_raw_diagnostic_vectors.npz</code> | No current Stage C result; current evidence infrastructure is in C7 | <code>HISTORICAL EVIDENCE ONLY</code> | The old recovery rehashed 33 entries and safely reopened a 109,414,103-byte NPZ with exact shapes and token identities, but recovery is local/off-pod rather than independent WORM/object-store durability. The scientific delta is inconclusive and the run is <code>NOT_LICENSED_DIAGNOSTIC_ONLY</code>. | Preserve hashes, lengths, shapes, token-ID digests, exact Pythia revision, and original claim status during archive import. Test truncation, bit flip, pickle rejection, shape drift, token reordering, model relabeling, and attempted current-result promotion. | No current Stage C evidence, no durability closure, and no Gate 5 claim change. |
| C6 | Historical evidence import and verification | Historical recovery verifier and bundle structure under <code>02_RESEARCH_EVIDENCE/full_recovery/</code> | Current Gate 5 artifact/evidence schemas; no dedicated non-promoting historical importer | <code>PORT AND REPAIR</code> | The historical verifier is useful for hash/reopen/shape checks but is tied to one local layout and does not enforce a current historical-only namespace, immutable original status, or separation from current Evidence Packet inputs. | Add a read-only importer with an explicit <code>HISTORICAL_EVIDENCE_ONLY</code> namespace, original-path and original-status binding, stable byte snapshot, manifest-coverage report, no schema coercion, and no current-result output type. Test all C5 corruptions plus path traversal, symlink/reparse input, duplicate identity, mixed bundle, current-slot injection, and manifest drift. | Improves audit access only. Imported evidence remains ineligible for current criteria or authorization. |
| C7 | Object-store, WORM, readback, and evidence reconstruction controls | Historical recovery design and local bundle | <code>noetic-compass-scaffold/noetic-compass/api/services/cas_harness_evidence_object_store.py</code>, <code>api/services/production/worm_writes.py</code>, <code>api/services/cas_harness_fleet_executor.py</code>, and <code>tests/test_production_worm_writes.py</code> | <code>CURRENT ALREADY SUPERIOR</code> | The historical run proves local recovery, not independent object versioning, retention, trusted time, out-of-band readback, or authenticated WORM authority. | Keep the current stricter contracts. Before any live claim, require a real allowlisted backend, exact bucket/account/region/object version, checksum, content length, retention, trusted time, independent readback, reconstruction, and conflict receipt. Test unavailable backend, expired/wrong subject, caller-authored trust, version drift, readback mismatch, deletion/overwrite attempt, and reconstruction disagreement. | Current code is stronger, but the live trusted backend remains unavailable. No present durability or execution claim is added. |

## D. Prompt-injection detector and open-versus-closed comparison

| ID | Feature | Historical source or evidence | Current equivalent | Classification | Historical defect or risk | Required change and tests | Gate 5 effect |
|---|---|---|---|---|---|---|---|
| D1 | Three-layer prompt-injection detector | Historical W0 evidence under <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/</code> and historical TKS controls | Current detection-only design in <code>docs/working/project_coherence/gate5/stagec_qwen_prompt_injection_v0.1/README.md</code> and <code>STAGEC_IMPLEMENTATION_OBLIGATIONS_AND_EVIDENCE_PLAN_v0.1.json</code>; current runtime authorization controls | <code>PORT AND REPAIR</code> | Historical work measured a narrow hidden-state question and did not implement one detector with separately reported text/context, hidden-state, and runtime-policy layers. Surface encodings, indirect sources, multilingual fragments, exfiltration, tool misuse, and disagreement can be hidden by one aggregate verdict. | Define three independent result types: universal text/context detection by source and authority; open-model hidden-state detection at target and controls; universal runtime policy enforcement. Never collapse disagreement into one PASS. Test user/system/tool/retrieval/external separation, priority override, encoded/indirect/multilingual/fragmented attacks, exfiltration, tool misuse, null/clean/wrong-layer/shuffled-label/known-fault hidden controls, detector disagreement, and runtime denial when both detectors miss. Use replay fixtures only until separately authorized. | Adds software/design evidence only. Stage C C-Cal remains unrun and cannot claim detector performance or prevention. |
| D2 | Corrected historical Pythia W0 cross-model attempts | <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/GATE2_W0_FAIR_COMPARISON/STATUS.md</code>, <code>expert_panel/PANEL_FINAL_REPORT.md</code>, and the four reports plus attempts registry under <code>evidence/</code> | Current controlling correction in <code>docs/working/project_coherence/gate5/stagec_qwen_prompt_injection_v0.1/HISTORICAL_W0_CORRECTION.md</code> and current grouped Stage C design | <code>HISTORICAL EVIDENCE ONLY</code> | All four attempts failed. Eight repeats of 80 prompts inflated row count; the declared encoded surface was not decoded; row-level permutation broke group dependence; 1B/2.8B reports carried a hard-coded 160M field; injection was in the wrong gate scope; no closed-model shared lane existed. The strongest surface control beat hidden readout in the controlling Qwen correction. | Retain failures and exact identities as negative methodological priors. Any new study must use independent matched groups, decode-aware surfaces, group-respecting bootstrap/permutation, exact identity, distinct injection states, and separately reported detector layers. Test that repeats do not increase effective N and wrong model fields fail admission. | No positive detector prior, expected effect, power claim, or current evidence. No fifth retry of the same W0 family is authorized. |
| D3 | Superseded Qwen hidden W0 <code>14/14 PASS</code> and scoped license | Historical source referenced by current <code>HISTORICAL_W0_CORRECTION.md</code> | The current correction binds commit <code>25336f2c2b46c8b59a0fca6f06bb84ea0e190918</code> and records <code>FAIL / OPEN / NOT LICENSED</code> | <code>REJECT</code> | A missing character-level baseline allowed a withdrawn PASS. The corrected character balanced accuracy <code>0.925</code> exceeds hidden balanced accuracy <code>0.896875</code>; hidden-minus-character is <code>-0.028125</code>. | Do not use the old PASS, layer, direction, threshold, power assumption, or license. Add a regression test that any hidden detector failing the strongest frozen surface margin cannot be promoted. | The scoped license remains withdrawn. Gate 5 and Stage C remain open and not licensed. |
| D4 | Shared open-weight versus closed-weight behavioral lane | No complete historical lane; Gate 2 W0 is open-model-only | Current output-only closed API surface in <code>noetic-compass-scaffold/noetic-compass/api/services/cas_harness_api_endpoint_runner.py</code>, current exact open-model controls, and no provider-neutral shared runner | <code>PORT AND REPAIR</code> | Historical comparisons conflate mechanistic and behavioral evidence and provide no fair closed-model lane. Closed APIs do not expose hidden states, immutable weights, or activation steering. Provider policy can also make system-role formatting non-identical. | Add provider-neutral model, request, observation, and identity contracts; replay/mock closed adapter first; unavailable live adapters by default. Freeze matched prompt groups, semantic task, injection variant, clean/null controls, tools, authorization boundary, equivalent instructions, deterministic setting, output schema, token limit, model/revision/provider/config/time, and raw per-case outputs. Compare observable behavior only in the shared lane. Test provider/model substitution, source-role drift, result mixing, missing/duplicate cases, nondeterministic configuration, forged identity, hidden-state fields on closed models, and any live call from replay mode. | Creates no provider authority and no comparison result. Hidden-state absence is <code>unavailable</code>, not a closed-model failure. |
| D5 | Paired departure metrics | No complete historical implementation; historical W0 statistics supply failure examples | No current model-pair departure module | <code>PORT AND REPAIR</code> | Row-level inference, repeated prompts, one composite score, unsigned deltas, and unbound evaluators can hide direction, dependence, and disagreement. | Implement the full per-pair vector with signed <code>closed - open</code> differences: verdict disagreement, TPR, FPR, FNR, attack success, unauthorized tool-call rate, clean-task accuracy, refusal, schema failure, Brier, ECE, Cohen kappa, McNemar, Jensen-Shannon divergence, and median semantic-response distance from one frozen independent evaluator. Give each difference a 95% matched-group bootstrap interval and plain-English sign meaning. Preserve raw rows. Test hand-computed fixtures, all-equal models, complete disagreement, zero cells, evaluator substitution, group duplication, seed/order determinism, and independent recomputation. | Metrics remain design/software output until a future authorized run. No composite index may hide components or alter Gate 5 status. |
| D6 | Fair comparison of activation steering versus black-box policy controls | Historical steering ideas and no closed-model causal equivalent | No current shared effect-comparison module; Stage C forbids steering | <code>PORT AND REPAIR</code> | Treating stronger prompts, filtering, context isolation, permission limits, or output validation as activation steering would make a false shared-mechanism claim. | Label closed controls <code>BLACK_BOX_POLICY_CONTROL</code>. Report open activation effect, closed policy effect, and <code>closed_effect - open_effect</code> with matched confidence intervals, target benefit, clean-task damage, refusal, schema failure, and unauthorized actions. Test label separation, baseline pairing, intervention leakage into Stage C, missing zero dose, collateral-damage omission, and false mechanism-equivalence wording. | Future evidence can compare observable effect sizes only. It cannot show the same internal causal mechanism or authorize steering. |
| D7 | Canonical comparison artifacts and recomputation boundary | Historical per-attempt JSON/NPZ reports and current Gate 5 artifact controls | <code>docs/working/project_coherence/gate5/GATE5_ARTIFACT_MANIFEST_v0.1.json</code>, <code>GATE5_REVIEW_MATRIX_v0.1.json</code>, and worker protocol/preregistration specs | <code>PORT AND REPAIR</code> | Historical reports include hard-coded identity errors, duplicated effective samples, local-only arrays, and result files that are not a complete provider-neutral comparison packet. | Add versioned artifacts for exact model identity/revision, shared protocol, frozen roster, per-model observation, detector-layer result, disabled steering/control result, pairwise comparison, departure report, statistical receipt, runtime authorization, and spend. Preserve raw per-case rows and exact dependency closure. Test recomputation, missing artifact, hash/length drift, row reassignment, cross-model mixing, forged spend/authorization, and hidden evidence in a summary-only file. | Artifact structure alone is <code>NON_AUTHORITY</code>. A future packet still needs every current Gate 5 prerequisite and claim gate. |

## E. Provider state, superseded attempts, and disclosure

| ID | Feature | Historical source or evidence | Current equivalent | Classification | Historical defect or risk | Required change and tests | Gate 5 effect |
|---|---|---|---|---|---|---|---|
| E1 | Historical RunPod pod, price, balance, and stopped-state observation | <code>05_RUNPOD_STATE/RUNPOD_STATE_AT_HANDOFF.md</code> and historical provider observations under <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/</code> | Current Stage C activation controls and current canonical tracker state: no provider/model/GPU/RunPod/spend action for the present tranche | <code>HISTORICAL EVIDENCE ONLY</code> | Pod ID, stopped state, price, balance, storage charge, endpoint, GPU availability, and account state are time-sensitive observations from July 2026. They are not current provider authority, capacity, identity, or spend permission. | Preserve only as dated history. Any future RunPod use must re-authenticate provider/account/project, exact pod/GPU/image/model/revision, current cost, spend cap, UTC window, nonce, WORM/readback, and final verifier immediately before the model call. Test stale receipt, wrong subject, expired window, consumed nonce, price drift, model substitution, and zero-call failure paths. | No RunPod preparation or execution is authorized by this row. Current spend remains <code>$0.00</code>. |
| E2 | Amazon internal draft as a distribution or product basis | <code>04_AMAZON_INTERNAL_DRAFT_DO_NOT_SEND/README_DO_NOT_SEND.md</code>, <code>CAS_HARNESS_AMAZON_TECHNICAL_EVALUATION_SPEC_20260721.md</code>, and <code>CAS_HARNESS_AMAZON_CLAIM_EVIDENCE_MANIFEST_20260721.json</code> | Current disclosure status <code>NOT LICENSED / HELD / NOT FROZEN</code> | <code>REJECT</code> | The folder explicitly says internal draft and do not send. Historical technical or diagnostic material is not customer-production acceptance and cannot support current disclosure. | Do not publish, send, quote as current proof, or route into product/disclosure artifacts. A future external document needs separate evidence review, source authority, disclosure authorization, current claim ledger, and explicit human/legal approvals where required. Test that internal-only sources cannot enter public/export manifests. | Amazon distribution remains paused/held. No product, public, or license effect. |
| E3 | Superseded RunPod/Jacobian attempts and mixed execution layouts | <code>11_JACOBIAN_LIVE_MODEL_CANARY_V1_2026-07-22/04_PROTOCOL_AND_ANCHOR/ATTEMPT_05_PRE_ANCHOR_DD55BC73/superseded_eeec3ec7/STATUS.md</code> and <code>ATTEMPT_06_PRE_ANCHOR_F3E3ADAD/control/superseded_first_capture/runpod_provider_observation_raw.txt</code> | Current no-retry, exact-layout, activation, and reconciliation controls | <code>HISTORICAL EVIDENCE ONLY</code> | Superseded captures, failed attempts, mixed source trees, dependency layouts, and unauthenticated raw provider observations cannot be selected as a successful current attempt or used to replace a failed row. | Retain as failure taxonomy and known-fault fixtures only. Test superseded-attempt selection, layout mixing, retry/replacement, raw-observation trust, attempt-number rollback, and terminal-row resurrection. | No execution credit or current authority. The current one-attempt/no-replacement rule remains controlling. |

## Recovery order and stop boundary

The first seven recovery steps are now implemented only at their safe
structural ceilings:

1. A2/A5 have provider-neutral capability and universal-probe replay contracts.
2. D4/D5/D7 have shared behavioral protocol/runner, deterministic departure,
   artifact, blocked-execution, and zero-spend contracts.
3. D1 has three separately reported prompt-injection layers with no aggregate
   verdict.
4. B1 has per-cell Surface Gate and Meaning Preservation receipts.
5. C6 has a non-promoting read-only historical importer.
6. C4 has owning-rank/distributed reconstruction structure with no real backend.
7. B2/B4/B9/D6 have disabled J-Space/JVP/VJP and unavailable steering/control
   contracts.

The remaining safe order is package/verifier binding, current full-suite
execution, final unchanged-tree verifier, real exact 4+12 prerequisite intake,
external authentication, and only then a separately authorized bounded model
execution. No recovery step authorizes the next one automatically.

Stop before every provider call, target-model load, GPU, RunPod action, model
generation, intervention, or spend unless all current Stage C prerequisites
pass exactly, the exact model/revision and frozen corpus are bound, trusted
storage/readback/retention/time are authenticated, the authoritative one-use
authorization and nonce are valid and unused, the exact spend cap and UTC
window contain no placeholders, and the final clean Gate 5 verifier passes.

Those stop conditions currently fail: the real 4+12 bundle is absent and the
requested exact model/revision, maximum spend, start UTC, and expiry UTC remain
placeholders. Model/provider/GPU/RunPod calls are 0 and spend is
<code>$0.00</code>.

This matrix changes no gate or claim status. Gate 5 remains
<code>OPEN / KEEP_OPEN</code>; Stage C remains
<code>DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED</code>; execution and
disclosure remain <code>NOT LICENSED / HELD / NOT FROZEN</code>.
