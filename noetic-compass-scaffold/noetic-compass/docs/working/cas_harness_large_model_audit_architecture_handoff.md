# CAS Harness — How It Audits Large, Multi-Layered LLMs (Architecture Handoff)

**Audience:** the engineering agent building/maintaining the CAS Harness product.
**Purpose:** the single source of truth for *how a big model with many layers gets
audited with many probes*, what is already built, and what is still TODO. Read this
before you touch the distributed-audit, fleet, probe, evidence, or verdict code.

**The one rule that governs everything below:** the Harness never invents proof. Every
stage is allowed to say "I don't have that yet" and route the audit to human review.
A bigger model just means *more workers and more probes*, never *a looser standard*.

---

## 1. The core idea (why "many probes due to model size")

A large language model is a stack of transformer layers. You cannot meaningfully audit
a 70B / 300B / 1T model on one box, and you cannot read its "thinking" from the output
text alone. So the Harness does two things:

1. **Splits the model across workers by contiguous layer ranges and tensor shards.**
   The wrong mental model is "one harness per 1B parameters." The right unit is
   *layers, blocks, tensor shards, devices, and worker jobs*. Each worker owns a slice
   of the layer stack.

2. **Runs the model once and fans a *bank of probes* over the captured activations.**
   For each scenario prompt, a worker does one real forward pass over its assigned
   layers, captures the hidden-state activations at those layers, and then applies
   probes (CAS-axis linear probes, blindspot/inversion overlays, controls) to that
   captured signal. Capture-once, probe-many. The model is expensive; the probes are
   cheap once you have the activations.

This is why model size translates directly into **probe count and worker count**: more
layers → more slices → more probe applications → one merged Evidence Packet → one
verdict.

---

## 2. End-to-end lifecycle of a large-model audit

Each arrow is a real module/endpoint in this repo. Status tags: **[BUILT]** exists and
is exercised by tests, **[PARTIAL]** exists but with a named gap, **[TODO]** not built.

```
1. Plan the deployment            -> api/services/cas_harness_scale_planner.py        [BUILT]
   (size -> layers/shards/workers,    POST /scale-plan
    memory, validation rung)

2. Create the audit control plane -> api/services/cas_harness_distributed_audits.py   [BUILT]
   (one run, worker assignments,      POST /distributed/session
    state machine)                    POST /distributed/session/{audit_id}/dispatch

3. Stand up the worker fleet       -> api/services/cas_harness_fleet_executor.py       [BUILT]
   (register, heartbeat, lease jobs,  POST /distributed/fleet/worker/register
    fragment refs, gates)             POST /distributed/fleet/worker/{worker_id}/heartbeat
                                      POST /distributed/session/{audit_id}/fleet/prepare
                                      POST /distributed/session/{audit_id}/fleet/job/lease

4. Each worker runs its slice      -> live-trace-worker/scripts/run_open_weight_probe_shard.py [BUILT]
   (real HF forward, capture          live-trace-worker/app/runtime/probe_runner.py
    activations, apply probes,        POST /distributed/session/{audit_id}/fleet/job/{job_id}/receipt
    emit a fragment receipt)

5. Merge worker fragments          -> api/services/cas_harness_merged_evidence_packets.py [BUILT]
   (one Evidence Packet,              POST /distributed/session/{audit_id}/fleet/merge
    append-only hash log)

6. Verifier decision gate          -> api/services/cas_harness_fleet_verifier.py        [BUILT]
   (ACCEPT/SUPPRESS only with a       POST /distributed/session/{audit_id}/fleet/verifier
    real proof chain; else FLAG)

7. WORM-anchor the packet          -> api/services/cas_harness_static_evidence_anchor.py [BUILT service / PARTIAL prod]
   (tamper-evidence; required for     POST /evidence/{trace_id}/anchor?require_object_lock=true
    a true green ACCEPT)
```

Everything from step 2 onward is conservative: if any worker is missing, any output is
missing, or the proof chain is incomplete, the run gate and the verifier both return
**FLAG_FOR_HUMAN_REVIEW**, never ACCEPT.

---

## 3. Component reference (grounded in the real code)

### 3.1 Scale Planner — `cas_harness_scale_planner.py` **[BUILT]** (frontier lane **[PARTIAL]** at HTTP)

Turns a declared open-weight model size into a deployment plan. It is *not* a verdict
runner — it only plans.

- `build_scale_plan(ScalePlanRequest)` → `ScalePlan` with: `num_layers`, `scale_tier`,
  `recommended_worker_count`, `worker_assignments` (each worker gets `layer_start`,
  `layer_end`, `shard_id`, `assigned_methods`, `expected_outputs`), a `memory_estimate`,
  `expected_capability`, `evidence_requirements`, and `limitations`.
- Worker count floors scale with the tier: single → small (`ceil(layers/20)`) →
  distributed (`ceil(layers/14)`) → enterprise (`ceil(layers/10)`) → frontier
  (`ceil(layers/8)`), capped at 512 workers. When workers > layers, it shards a single
  layer into tensor shards (`layer-NNN-tensor-shard-MM`).
- **Open-weight only.** There is deliberately no black-box / output-only audit mode in
  this product lane. The plan requires open weights or customer-hosted activation hooks.

**The validation/claim ladder (single source of truth — do not bypass):**
`scale_validation_status(parameter_count_b)` returns one of three honest rungs, and the
matching `scale_validation_notice(...)` text rides along on every plan:

| Rung | Size band | What it means |
|---|---|---|
| `EMPIRICALLY_VALIDATED` | ≤ 20B | Actually executed open-weight (Pythia-160M reproduced on CPU). Proven lane. |
| `ENGINEERED_NOT_VALIDATED` | 20B–300B | Architecture is engineered for it, but no run of that size has executed. Architecture-validated, not size-validated. |
| `EXPERIMENTAL_NOT_VALIDATED` | 300B–4T | Frontier lane. Unproven. Plan is produced **only** when the caller sets `accept_experimental_frontier=True`, and carries the frontier waiver. |

- Hard ceiling: > 4000B (4T) is refused outright.
- 300B–4T is refused **unless** `accept_experimental_frontier=True`; the refusal text *is*
  the `frontier_scale_disclaimer()` (experimental, customer risk, no warranty, results
  marked `EXPERIMENTAL_NOT_VALIDATED`, requires compute/license/risk approval).

**[PARTIAL] gap to close:** the service layer supports the 4T frontier lane, but the HTTP
request model in `api/routes/cas_harness_audit.py` still caps `parameter_count_b` at 300
and does **not** forward `accept_experimental_frontier`, nor surface `validation_status` /
`validation_notice`, nor convert the planner's `ValueError` into a 422. So today the
frontier lane is reachable only by calling `build_scale_plan(...)` directly. Wiring the
route is the remaining task (see §9).

### 3.2 Distributed Audit Control Plane — `cas_harness_distributed_audits.py` **[BUILT]**

The state machine that owns one audit run: `create → dispatch → worker-running →
record-evidence → merge`. It holds the plan, the per-worker assignments, and the merge
status. Its merge is conservative: it only produces a completed merge when **all** workers
finished **with** an `evidence_packet_ref` and **no** missing outputs; otherwise the run is
flagged. It never fabricates ACCEPT. The merged packet trace id is
`f"{audit_id}-distributed-merge"`.

There are two evidence paths on the control plane:
- The **legacy direct path** (`POST .../worker/{worker_id}/evidence`) for non-fleet runs.
  It returns **409** if a fleet run exists for that audit (fleet-backed audits must use
  leased fleet receipts, not direct posts).
- The **fleet path** (§3.3), which is the one you use for large models.

### 3.3 Fleet Executor — `cas_harness_fleet_executor.py` **[BUILT]** (the heart of large-model audits)

This is the distributed worker layer *below* the control plane. **Do not forget this
component** — it is what makes "many probes due to model size" actually run safely.

- **Worker registry + heartbeat:** `register_worker`, `heartbeat_worker`, `list_workers`,
  `mark_stale_workers`. A worker whose heartbeat is older than the cutoff (default **120s**)
  is marked stale so its jobs can be re-leased.
- **Job preparation:** `prepare_fleet_for_audit(audit_id)` turns the dispatched plan's
  worker assignments into leasable fleet **jobs** (one per layer-range/shard).
- **Leasing with anti-double-work tokens:** `lease_next_job(...)` hands a queued job to a
  registered worker and returns a **SHA256 lease token**. A receipt is only accepted if it
  presents the matching lease token, so two workers can't both "win" the same job.
- **Content-addressed Evidence Packet fragments:** each worker returns a fragment whose ref
  is `cas-fragment://<audit_id>/<job_id>/<worker_id>/<shard_id>/sha256:<digest>`. On
  `submit_job_receipt(...)` the executor **recomputes the SHA256 over the fragment payload
  and rejects the receipt if it doesn't match the ref** (tamper/transmission check), and
  dedups identical fragments via `_FRAGMENT_REFS`.
- **Run gate (`_refresh_run_gate`)** moves through:
  `waiting_for_workers` → `blocked_failed_worker` → `waiting_for_receipts` →
  `blocked_missing_outputs` → `ready_for_verifier`. Only the last status lets the run
  proceed to merge/verifier.
- **Merge defers the verdict:** `merge_fleet_evidence(...)` assembles the merged packet but
  **never** promotes fleet completion into ACCEPT — it hands the decision to the verifier
  (§3.6). It calls `record_worker_evidence` (control plane) and
  `write_merged_fleet_evidence_packet` (§3.5).

### 3.4 Probe Worker — `run_open_weight_probe_shard.py` + `app/runtime/probe_runner.py` **[BUILT]**

This is the program that runs behind each leased job and does the *real* model work. It
reads `CAS_FLEET_*` env vars set by the fleet daemon and writes a result JSON to
`CAS_FLEET_RESULT_PATH`.

What it actually does (capture-once-fan-out-many-probes, made concrete):
1. **Loads the declared open-weight model** through Hugging Face Transformers
   (`AutoModelForCausalLM`, `device_map`, dtype from `CAS_FLEET_TORCH_DTYPE`,
   `low_cpu_mem_usage=True`). Records real `model_info` (architecture, hidden size,
   layer/head counts, **counted** parameters).
2. **Locates the transformer layer stack** across architecture families it knows:
   `gpt_neox.layers`, `model.layers`, `transformer.h`, `transformer.blocks`. (Adding more
   families is a known extension point — see §7.)
3. **Selects only its assigned layer range** (`CAS_FLEET_LAYER_START..END`) and registers
   forward hooks to **capture the last-token activation** at each assigned layer for each
   scenario prompt. One forward pass per prompt; `use_cache=False`; inference mode.
4. **Summarizes each captured layer** (mean/max abs activation, top-k neurons) and the
   output **confidence margin** (softmax top-1 minus top-2).
5. **Applies the probe bank over the captured activations:**
   - `cas_axis_readout` — a linear CAS probe (`schema_version=cas_probe_linear_v1`, with
     `axes`/`weights`/`bias`) projected over the pooled activation vector. **Only produced
     when a model-matched probe-weights file is supplied** (`CAS_FLEET_PROBE_WEIGHTS_PATH`).
   - `blindspot_overlay` — **only produced when a model-matched cover-map file is supplied**
     (`CAS_FLEET_COVER_MAP_PATH`), and only if its `model_id` matches the audited model.
6. **Classifies produced vs missing outputs.** `layer_activation_summary` and
   `worker_evidence_manifest` are always produced after a real forward; `cas_axis_readout`
   and `blindspot_overlay` are reported as **missing** when their proof inputs aren't
   present. Missing proof is reported honestly so the merge/verifier cannot overclaim.

The four canonical per-worker `expected_outputs` are:
`layer_activation_summary`, `cas_axis_readout`, `blindspot_overlay`, `worker_evidence_manifest`.
The planner's `assigned_methods` are `foundation_probe`, `inversion_scan`,
`blindspot_detection`, `verification_stack`, plus `targeted_ablation` and
`matched_controls` in `FULL_INTERNAL` depth.

### 3.5 Merged Evidence Packet writer — `cas_harness_merged_evidence_packets.py` **[BUILT]**

Turns validated worker receipts into one retrievable Evidence Packet and makes it
tamper-evident:
- Copies Stage 19/20 verifier fields **only** from a worker fragment that explicitly
  carries them; otherwise writes a `_pending_verification_block()` whose proof chips are
  honestly `unavailable`.
- Writes the packet to a content store and appends an entry to an **append-only hash log**
  (`hash-log.jsonl`), each row chaining to the previous via `previous_entry_sha256`. Then
  calls the external anchor (`anchor_hash_log_entry`) and re-writes the packet with the
  anchor receipt.
- `verify_merged_fleet_evidence_packet_payload(...)` re-checks: packet-without-hashes
  SHA256, the hash-log entry pointer, and the full chain integrity.

**The Evidence Packet is a manifest, not a warehouse.** It stores hashes / URIs /
locations / sizes / summaries — never terabytes of raw activations inline. (Wiring the
object store those URIs point at, for >20B activations, is **[TODO]** — see §7.)

### 3.6 Fleet Verifier — `cas_harness_fleet_verifier.py` **[BUILT]**

The decision gate over the merged packet. It is the only place a fleet run can become
ACCEPT/SUPPRESS, and it is deliberately hard to satisfy:
- With **no** explicit packet-level verifier decision → `FLAG_FOR_HUMAN_REVIEW`,
  `confidence=None`, with the blockers spelled out.
- With an explicit ACCEPT/SUPPRESS decision **but** the merged packet is **not WORM-retained**
  (`packet_proof_is_worm_retained(...)` is false) → it **blocks** the ACCEPT and routes to
  human review, telling the operator to anchor to S3 Object Lock and re-verify.
- Only an explicit verifier decision **with** a WORM-retained packet passes through.

### 3.7 WORM anchor — `cas_harness_static_evidence_anchor.py` + `POST /evidence/{trace_id}/anchor` **[BUILT service / PARTIAL prod]**

Tamper-evidence + retention. `summarize_static_anchor_worm_status(anchored, verify)` is the
**shared honesty gate** used by both the CLI (`scripts/anchor_stage9_40e_packet.py`) and the
HTTP endpoint, so they can never disagree on what "WORM-retained" means.
- Anchor mode `disabled` (default) or `local` → anchored but **NOT** WORM; console honestly
  stays at human review.
- Anchor mode `s3` + Object Lock → a real `boto3 put_object` with `ObjectLockMode` +
  retain-until, **re-read and confirmed** → this is the only thing that flips a packet to a
  true green ACCEPT.
- `POST /evidence/{trace_id}/anchor?require_object_lock=true` returns **409** unless a real
  S3 Object-Lock WORM write re-reads clean. The actual production S3 write is operational
  and **human-gated** (the remaining prod step).

---

## 4. The proof model (what each verdict actually requires)

A merged packet carries six proof chips. **Do not mark any of these `present` unless the
real thing ran:**

| Chip | `present` means |
|---|---|
| `model_proof` | The audited open-weight model identity (+ weight/tokenizer hashes) is recorded. |
| `cas_readout` | A real Stage 19/20 hidden-state CAS readout was produced and merged. |
| `causal_proof` | A real intervention/ablation actually ran. **Not** present just because the field exists. |
| `control_proof` | Matched random/wrong-drive **controls actually ran**. **Not** present unless they did. |
| `output_proof` | A real output-effect measurement (e.g. the η→ε bridge) ran. |
| `packet_proof` | The packet is content-addressed **and** WORM-retained (S3 re-read with active Object Lock). |

Verdict vocabulary is exactly: `ACCEPT` / `SUPPRESS` / `FLAG_FOR_HUMAN_REVIEW`.

**η→ε output bridge** (`cas_harness_evidence_bridge.py`): read the hidden-state CAS class
(η), realize it as a readable English prefix (ε), run a second forward pass, and measure the
likelihood shift. Raw CAS symbols alone are **not** load-bearing proof — the output-effect
measurement is what makes the readout count.

---

## 5. HTTP API surface (real endpoints, lifecycle order)

All under the CAS Harness audit router (confirm the mount prefix in `api/main.py`).

```
POST /scale-plan                                                  plan size -> workers/shards
POST /distributed/session                                         create control-plane run
POST /distributed/session/{audit_id}/dispatch                     mark assignments dispatched
POST /distributed/fleet/worker/register                           register a Probe Worker
POST /distributed/fleet/worker/{worker_id}/heartbeat              keep a worker alive (120s cutoff)
POST /distributed/fleet/workers/stale-scan                        retire stale workers
GET  /distributed/fleet/workers                                   list workers
POST /distributed/session/{audit_id}/fleet/prepare               build leasable jobs
POST /distributed/session/{audit_id}/fleet/job/lease             lease next job (SHA256 token)
POST /distributed/session/{audit_id}/fleet/job/{job_id}/receipt  submit fragment receipt
POST /distributed/session/{audit_id}/fleet/merge                 merge fragments (no ACCEPT here)
POST /distributed/session/{audit_id}/fleet/verifier             verifier decision gate
GET  /distributed/session/{audit_id}/fleet                       fleet run state
GET  /distributed/fleet/runs                                     list fleet runs
GET  /distributed/session/{audit_id}                             control-plane run state
GET  /distributed/sessions                                       list control-plane runs
POST /evidence/{trace_id}/anchor[?require_object_lock=true]      WORM anchor (409 if not WORM)
POST /target/verify                                              validate a model target (no verdict)
```

(The legacy `POST /distributed/session/{audit_id}/worker/{worker_id}/{running,evidence}` and
`/merge` endpoints exist for non-fleet runs; fleet-backed audits must use the fleet path and
will 409 on the direct evidence post.)

---

## 6. The scale & frontier claim ladder (say this out loud to customers)

- **≤ 20B — `EMPIRICALLY_VALIDATED`:** proven lane.
- **20B–300B — `ENGINEERED_NOT_VALIDATED`:** the architecture is built for it; we have not
  executed a run of that size. Architecture-validated, not size-validated.
- **300B–4T — `EXPERIMENTAL_NOT_VALIDATED` (the frontier lane):** *ARCHITECTED / EXPERIMENTAL /
  NOT VALIDATED.* Offered only as an experimental run, at customer risk, with no warranty of
  correctness or completeness. Every result is stamped `EXPERIMENTAL_NOT_VALIDATED`. Requires
  the customer to approve compute cost, model license/provenance, and experimental-risk terms,
  and to set `accept_experimental_frontier=True`. **> 4T is refused.**

Never use the words `SUPPORTED` / `VALIDATED` / `PRODUCTION-READY` for anything above 20B
without a real run behind it. The honest framing is: *"1T–4T has not been run on our system;
in theory the infrastructure should support it, but you use it at your own risk and we hold no
responsibility for ill-gotten results."*

---

## 7. Support systems (the full list — don't drop any of these)

These surround the audit path. Status is honest.

1. **Scale planning** — `cas_harness_scale_planner.py`. **[BUILT]** (HTTP frontier wiring [PARTIAL].)
2. **Checkpoint / shard manifest** — which layers live in which shard/file, with hashes. The
   probe runner counts params and records `model_info`; a first-class shard manifest that maps
   layer ranges → checkpoint shards is **[TODO]**.
3. **Architecture adapters** — the layer-locator handles `gpt_neox / model.layers /
   transformer.h / transformer.blocks`. Anything else raises. Adding families (MoE experts,
   non-standard blocks) is **[TODO]** and is the most likely first failure on a new model.
4. **Probe-bank registry** — probe weights (`cas_probe_linear_v1`) and blindspot cover-maps are
   passed per-shard as file paths today. A managed, versioned registry of probes per axis/model
   is **[TODO]**.
5. **Artifact / object store for activations** — the Evidence Packet stores URIs + hashes; the
   store those URIs point at (S3/GCS) for large hidden-state tensors is **[TODO]**. Today the
   probe summarizes activations inline (top-k), which is fine for small models but won't hold
   for >20B full capture.
6. **Queue / resume / idempotency** — leasing + lease tokens + stale-worker re-leasing exist
   **[BUILT]**; a durable async job queue with crash-resume across the whole fleet is **[TODO]**.
7. **Observability** — structured run/job state is queryable via the GET endpoints **[BUILT]**;
   fleet-scale metrics/log aggregation is **[TODO]**.
8. **Cost authorization** — a compute-budget approval gate (mandatory for the frontier lane) is
   **[TODO]**; today the frontier waiver is text + the `accept_experimental_frontier` flag.
9. **Tenant isolation** — per-customer separation of evidence stores/namespaces. The store
   supports sub-namespaces (`evidence_store_namespace`) **[PARTIAL]**; full multi-tenant
   isolation is **[TODO]**.
10. **Failure taxonomy** — workers report `error_message` + `missing_outputs`; the run gate has
    explicit blocked states. A normalized failure taxonomy across the fleet is **[PARTIAL]**.
11. **Experimental-label propagation** — `validation_status` / `validation_notice` exist on the
    plan; propagating `EXPERIMENTAL_NOT_VALIDATED` into the console/report UI for 1T–4T is
    **[TODO]**.

---

## 8. Hard honesty rules (never break these)

- **Never fabricate a verdict.** Merge and fleet-merge never produce ACCEPT; only the verifier
  does, and only with a real proof chain + WORM retention.
- **Never mark a proof chip `present` unless the real thing ran** (especially `causal_proof`
  and `control_proof`).
- **Never call a scoped-validation ACCEPT a customer/production ACCEPT.** (Stage-9 40E is a
  scoped project-validation packet; WORM only proves it is tamper-evident, not that a customer
  model is certified.)
- **Never claim WORM retention for `disabled`/`local` anchor modes** — only a re-read S3
  Object-Lock write counts.
- **Never claim parameter-count support as validated runtime support.** Bucket/lane existence
  ≠ a real run at that size.
- **Never audit a model output-only and imply hidden-state proof.** This lane is open-weight /
  internal-access only by design.
- **Bigger model = more workers/probes, never a weaker gate.**

---

## 9. Current status snapshot & the next wiring task

**Built and tested:** scale planner (incl. validation ladder + frontier-lane logic at the
service layer), distributed control plane, fleet executor (registry/heartbeat/leasing/fragment
hash-validation/gates), probe-shard runner (real HF forward + capture + linear CAS probe +
blindspot overlay + honest missing-output classification), merged Evidence Packet writer
(append-only hash chain + anchor), fleet verifier (conservative WORM-gated decision), WORM
anchor service + `POST /evidence/{trace_id}/anchor`.

**The immediate open task** is to finish exposing the frontier lane through HTTP in
`api/routes/cas_harness_audit.py`:
1. Raise the request cap from `le=300` to `le=4000` and add an
   `accept_experimental_frontier: bool = False` field.
2. Add `"frontier_experimental_open_weight"` to the route's tier Literal and add
   `validation_status` + `validation_notice` to `ScalePlanResponse`.
3. Forward `accept_experimental_frontier` into both `build_scale_plan(...)` and
   `create_distributed_audit(...)`, and wrap them in `try/except ValueError →
   HTTPException(422)` (there is no global ValueError handler).
4. Update `tests/test_cas_harness_scale_planner.py`: the old
   `test_rejects_models_above_current_300b_boundary` must change (405B now needs the
   experimental ack), add a `>4T` hard-refuse test, and add positive frontier +
   validation-ladder tests; then `py_compile` + run tests, commit, push.

**Bigger TODOs** (in rough priority): object/artifact store for large activations →
architecture adapters beyond the 4 known families → probe-bank registry/versioning →
durable async queue + resume → cost-authorization gate → tenant isolation → fleet-scale
observability → `EXPERIMENTAL_NOT_VALIDATED` propagation into the console. And operationally:
the real S3 Object-Lock WORM write from production (human-gated) to flip a packet to a true
green ACCEPT.
