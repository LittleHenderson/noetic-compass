# CAS-HH-RDE-01 / A — Claude first return (2026-09-28)

Original HELM session `session_011hJxopymaeoPQ67KvchtwW`, PR #245, branch `claude/focused-mccarthy-uj45ul`.
Package received at `62bb7f714810db5047eb07ef616c6ddfe470fca9`; receipt ACK: PR #245 comment 5876863361.

## Claim states, first

| Item | State |
|---|---|
| Vendored Harness source read and hash-checked (`543666e5…`) | real (computed here) |
| Learner anchors at `c45f775f` (`_rounds` observe 1197-1198, `core_block` call 1199, `pointer_key` 1313, `node_head` 1347, `_node_options` 1417, `_reach_options` 1512, `world_head` 1566) | real (read from the exact retained copy, sha256 `0f424d86…`) |
| Bridge modules and 41 test cases | written |
| Any test executed | NOT_RUN (packet forbids local pytest/torch; torch absent here) |
| Any HELM capture, checkpoint, witness, intervention on HELM | not done |
| Acceptance rows HH01-HH21 | obligations, none passed |
| Spec-sheet status | `ENGINEERED-NOT-VALIDATED` |

## Reused Harness code (HH01/HH07)

| Vendored name | Relationship | Where |
|---|---|---|
| `CaptureState`, `_top_k_neurons` | EXACT_SHARED_IMPLEMENTATION (called unchanged; `layer` -> round index, `index` -> coordinate; "neuron" meaning not transferred) | `diagnostic_configuration.detect_top_k` |
| `_softmax_margin` | VERSIONED_ADAPTATION (`MARGIN_SAT=6.0` is Pythia-160M empirical; labeled not HELM-calibrated) | `diagnostic_configuration.readout_margin` |
| `EraserIntervention` / `_apply_eraser` factor | SEMANTIC_CORRESPONDENCE (`max(0, 1 - max(0, gain))` reused; `[0, -1, idx]` last-token indexing not applicable to 2-D node rows) | `diagnostic_intervention.suppression_factor` |
| `capture_probes` | SEMANTIC_CORRESPONDENCE (register / yield / always remove) | `diagnostic_intervention.apply` |
| `resolve_probes`, `summarise`, `_mode7_edges_from_attentions` | NOT_REUSED (token/attention semantics absent) | — |

## Implemented functions

`diagnostic_configuration.py`: `check_contract`, `coverage`, `require_complete`, `raw_capture`, `row_values`,
`probe_compatibility`, `probe_validity`, `cas_mapping`, `build_configuration`, `detect_top_k`, `support`,
`freeze_configuration`, `require_frozen`, `assign_claim`, `configuration_to_json` / `configuration_from_json`,
`readout_margin`, `reuse_manifest`.

`diagnostic_intervention.py`: `suppression_factor`, `donor`, `declare`, `matched_control`, `verify_matched`,
`bind_sites`, `state_digest`, `apply` (context manager), `finalize`, `require_applied`, `receipt_to_json` /
`verify_receipt`, `witness_protocol`, `evidence_record` / `verify_evidence` / `rpa_projection` (read-only atlas view;
harvest ingestion `DISABLED_NOT_ADMITTED`).

Hookable sites without a learner change: `graph.round_input` (pre-hook `core_block`), `graph.round_update`
(post-hook `core_block`), `graph.pointer_query` (`pointer_key`), `head.node` (`node_head`), `head.reach`
(`reach_option_head`). Recorded NOT_HOOKABLE: `head.node_pointer` (tensor op at line 1417) and the eight
non-module sites. No Parts/Reach dependence on `world_head` is inferred (line 1566 feeds neither head).

## Distinctions kept

raw activity (raw capture record) -> detected configuration (`PROJECTED_COORDINATE_SET`, claim
`OBSERVED_CONFIGURATION`) -> validated CAS interpretation (`CAS_READOUT_SUPPORTED`, mapping `PROPOSED` ->
`ADAPTED` only through evidence; `EXACT` refused) -> causal effect (`TASK_CAUSAL_CONTRIBUTION_SUPPORTED`, needs
intervention + matched-control receipts and a task metric, never a probe score) -> useful improvement (outside the
pilot; `CLAIM_LEVEL_OUTSIDE_PILOT`).

## Tests written, NOT RUN

| File | Cases | Needs |
|---|---:|---|
| `test_diagnostic_configuration.py` | 24 | Python only (imports Codex's `observation` module) |
| `test_diagnostic_intervention.py` | 17 | torch; CUDA by default (`HELM_DIAG_TEST_DEVICE`), labeled fixture `FIXTURE_NOT_HELM` |

Exact acceptance command (inside an admitted job; the namespace `conftest.py` refuses otherwise):

```sh
HELM_SI_EXECUTION_VENUE=ADMITTED_AWS python -B -m pytest -q -p no:cacheprovider --basetemp=<out>/pytest-temp --junitxml=<out>/hh-rde-01-claude-junit.xml -rA research/helm_self_improvement/test_diagnostic_configuration.py research/helm_self_improvement/test_diagnostic_intervention.py
```

Expected `41 / 0 / 0 / 0` if collection matches. Any other count is the result; do not lower the expectation.

## Witness protocol

`diagnostic_intervention.witness_protocol()`: one preserved checkpoint (identity from Codex's admission), 4 synthetic
Parts/Reach fixtures split by structure family (2 discovery, 2 confirmation), six conditions (C0 baseline, C1
OBSERVE_ONLY neutrality, C2 NO_OP_CONTROL, C3 SUPPRESS frozen top-4 at `graph.round_input` round 3 gain 1.0, C4
MATCHED_CONTROL seed 2026, C5 INJECTED full-row suppression at round 0), two hypotheses (H0 injected plumbing check,
H1 natural within-checkpoint), 24 packet forwards of 768, zero optimizer updates, one job. A planning record, not an
admission.

## Smallest remaining dependency

Codex's `observation.py` emitter producing contract-shaped raw captures (identity + tensor + coverage fields) from the
learner's `observe` callback and the head calls, plus the admitted checkpoint identity. With those, the first witness
can run in one admitted job on the existing runner. Claude launches nothing.

## Binding to Codex's real emitter (second packet, same allocation)

Received by Git object: Codex `fd4215728209ef90948323d1268f2db664bc88ed` (`observation.py`, `observation_sites.py`,
`test_observation.py`, `diagnostic_worker.py`, `cas_hh_rde_01/IMPLEMENTED_SOURCE_MAP.md`, `aws_runner.py`,
`aws_worker.py`, `diagnostic_admission.py`, vendored evidence/definition-lock files) and DeepSeek's relay at
`8e0ec2592` (`DELIVERY.json` sha256 `d9f26d5b…`; five deliverables verified 5/5 against declared bytes and sha256;
the four earlier files are the same blobs at `fd421572` and `8e0ec259`).

| Binding | Function | Real / written |
|---|---|---|
| Emitter meanings, modes, expected-call rule, canonical form equal the module's | `EMITTER_MEANINGS`, `OBSERVATION_MODES`, `expected_hits_for`, `_emitter_canonical` | real (import-checked here against `observation.py`; also a written test) |
| Receipt digest recomputed; external anchor optional | `verify_observation(receipt, retained_receipt_sha256=)` | written |
| One site's events to validated captures + coverage | `captures_from_observation` | written |
| Configuration only from a COMPLETE receipt | `detect_from_observation` | written |
| Parts packet expects 0 `head.reach` hits in `apply` | `apply(..., expected_hits=expected_hits_for(site, kind))` | written |
| External anchors on every verifier; atlas view refuses without one | `verify_receipt`, `verify_evidence`, `rpa_projection`, `configuration_from_json` | written |

Interplay recorded in `apply`'s docstring: the emitter's `graph.round_input` emit fires before `core_block`, so a
passive capture there records the unmodified input; the intervention receipt is the record of the change and the
`graph.round_update` capture shows its effect. The emitter binds `learner._graph` for one forward and disables
`stage_batch`; the hooks touch neither.

DeepSeek findings as they touch this lease: D-RDE-02 (no silent eraser) and D-RDE-03 (no transferred probe) are
consistent with `suppression_factor` scoping and `probe_validity`; F4 (self-carried digest is not tamper evidence)
adopted as above; D-RDE-04 (files missing) is now falsified by `d0d2e14f` and `fd421572` on the branches.

## Third packet, same allocation: Codex's parity report and two lease asks

**Parity attempt (Codex's report, comment 5877140015; reported-by-Codex-not-verified, no junit hash yet).** 18 collected,
17 passed, 0 failures, 1 setup error. The error is in `test_host_retains_incomplete_and_detects_tampering`: the native
baseline fixture raised `PCBA_STATIC_CHECK_FAILED`; Codex's source/log diagnosis is a missing pinned `pydantic` in the
diagnostic venv. Consequence: zero real-parent forwards and zero optimizer updates, so passive neutrality, 14-site
coverage and fresh reload are NOT_RUN. It is a failed attempt, not partial acceptance. Paid attempt 1 is consumed.

**Exact callables added (written, NOT RUN).**
- `diagnostic_configuration.convert_observation(receipt, *, retained_receipt_sha256)` -> versioned record
  `helm.harness.converted-observation/0.1`. Anchor mandatory; refuses `OBSERVATION_INCOMPLETE`, `SITE_UNKNOWN`,
  `CAPTURE_DTYPE_UNKNOWN`, and (through `raw_capture`, unchanged) `COORDINATE_MEANING_MISMATCH`; maps only
  `torch.<dtype>` -> `<dtype>`; preserves the emitter's raw meaning, identity and `binding`; tensor sites carry
  validated captures + coverage, non-tensor sites carry event counts and public-value digests, zero-expected sites
  are marked `expected_zero`; `conversion_digest` sealed.
- `diagnostic_intervention.caller_binding(model, torch, *, checkpoint_sha256, source_sha256, restored_by)` and
  `apply(..., binding=)`: the guarded caller builds the binding after its restore; `apply` verifies the module's
  parameter digest and the declaration's checkpoint/source against it; receipts carry `model_binding`
  (`CALLER_VERIFIED` or `UNVERIFIED_SELF_REPORTED`); `require_applied` and `evidence_record` refuse anything but
  `CALLER_VERIFIED`. Declaration strings alone never authenticate the module or confer success.

## Codex integration source `788aa5f7` (receipt, verified here)

- My four leased files at `788aa5f7` are byte-identical to my `5ec7d5e9` bytes (4/4 blob sha256). Codex's
  `observation.reload_configuration_inputs` calls `captures_from_observation(receipt, site, retained_receipt_sha256=anchor)`
  after `reload_observation` and its own identity/count/order checks; the names it imports keep their signatures at
  `ae940c44`, which additionally offers `convert_observation` (anchor mandatory) and the caller-verified binding.
- `cas_hh_rde_01/CLOSEOUT_RECOVERY.json` sha256 `e7eb7d491453491d788e51985537eb84f0a98f70ff4015119c4a961f28f4703b`:
  `FAILED_HH_RDE_PARITY_CLEANUP_VERIFIED`, 18 / 17 / 0 / 1, zero forwards, neutrality/coverage/reload `NOT_RUN`,
  dependency correction `f1e3c479` with remote correction `NOT_RUN`. Codex's report; AWS state not verified here.
- ACK posted on PR #245 after comment 5877327531.
