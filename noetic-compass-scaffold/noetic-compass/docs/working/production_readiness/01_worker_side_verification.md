# 01 — Worker-Side Verification Upgrades

**Workstream:** 01 of 9 · **Status:** design + gap blueprint (not implemented) · **Date:** Jun 1, 2026
**Owner seam:** the probe worker — the only place a `*_DECLARED` status may honestly become `*_VERIFIED`.

> Scope boundary up front: this workstream makes the worker's claims *checkable*. It does not
> decide where the bytes physically land (that is **02**), nor whether they are held immutably
> (that is **07**). 01 produces a deterministic, attested, self-verifying evidence artifact; 02
> stores it; 07 retains it. The whole program's honesty ethos lives or dies here: every
> `MODEL_ACCESS_VERIFIED` / `PROBE_COMPATIBILITY_VERIFIED` / `COMPUTE_FEASIBILITY_VERIFIED` the
> fleet ever emits is only honest if the worker actually did — and can prove it did — the thing
> the status names.

---

## 1. Current state (what already exists)

The worker already runs a **real** model and captures **real** activations. The honest-status
*vocabulary* and the declared/verified *split* are already designed into the gates. What is
missing is the bridge: the worker does not yet emit anything a downstream consumer can
independently re-check, so no `*_DECLARED` status can be honestly promoted to `*_VERIFIED` today.

### 1.1 The worker does real work (not a stub)

`live-trace-worker/scripts/run_open_weight_probe_shard.py` is a genuine open-weight probe:

- **Real weight load.** `load_open_weight_model` (`:179-217`) calls
  `AutoModelForCausalLM.from_pretrained(model_id, revision=…, torch_dtype=…, device_map=…,
  low_cpu_mem_usage=True, trust_remote_code=…)`, then `model.eval()`. It records `model_info`
  (`:206-216`): architectures, `model_type`, `hidden_size`, `num_hidden_layers`, `vocab_size`,
  resolved dtype, device_map, `parameter_count`.
- **Real layer location + hook.** `locate_transformer_layers` (`:265-279`) walks four decoder-stack
  paths (`("gpt_neox","layers")`, `("model","layers")`, `("transformer","h")`,
  `("transformer","blocks")`). `run_activation_capture` (`:220-254`) registers a
  `register_forward_hook` on `getattr(layer, "mlp", layer)` and `_capture_last_token` (`:257-262`)
  pulls `value[0, -1].detach().float().cpu()`. The forward runs under
  `torch.inference_mode()` (`inference_context` `:431-434`, `use_cache=False`).
- **Real CAS readout.** `compute_cas_axis_readout` (`:313-336`) requires
  `schema_version == "cas_probe_linear_v1"`, dots each per-axis weight vector against the pooled
  activation vector (`pooled_activation_vector` `:339-346`), and emits `scores` per axis with
  `score_source = "linear_probe_over_assigned_layer_activation_summary"`.
- **Honest missing-output discipline already exists.** `classify_outputs` (`:358-367`) reports
  `cas_axis_readout` / `blindspot_overlay` as *missing* when their inputs are absent, so a degraded
  shard cannot overclaim. On any exception, `main` (`:91-116`) writes
  `status: "failed_before_or_during_model_forward"` with empty `produced_outputs`.

### 1.2 The honest-status vocabulary already names the verified end-state

Three gates already define the exact `*_VERIFIED` token the worker must earn, and each docstring
already says it is **worker-side only, never produced at the API tier**:

- **Probe (gate 7)** — `api/services/cas_harness_probe_compatibility.py`. `ProbeCompatibilitySummary`
  carries two fields hardcoded `False` at the API tier:
  `weights_hash_verified: bool` (`:121`) and `probe_loadable: bool` (`:122`). Both
  `_unsupported` (`:182-183`) and the success path (`:312-313`) set them `False`.
  `PROBE_COMPATIBILITY_VERIFIED` is "the worker actually loaded the probe and computed the readout
  with matching dimensions. Worker-side only; never produced at the API tier" (`:37-39`). The spec
  even declares an *optional* `weights_sha256` "(declared here, recomputed worker-side)" (`:87`,
  `ProbeReadoutSpecification.weights_sha256` `:94`).
- **Model access (gate 2)** — `MODEL_ACCESS_VERIFIED` is the fleet-side promise that a real model
  was loaded (the worker proves it by attesting *which* weights revision actually loaded).
- **Compute (gate 3)** — `COMPUTE_FEASIBILITY_VERIFIED` is the fleet-side promise that the assigned
  shard actually fit and ran on the worker's real hardware.

### 1.3 The honest gate *pattern* to generalize already exists in the live path

`api/services/cas_harness_live_worker_runner.py` already encodes the discipline 01 must extend
fleet-wide — a status flips to "real" **only** when `is_real_model is True`:

- `_ablation_block_from_events` (`:364-410`): `packet["ablation"]["status"] == "present"` ⟺ an
  `ablation_effect` event exists **and** `event.get("is_real_model") is True` (`:384`); a
  demo-flagged event is forced to `"unavailable"` (`:391-401`).
- `_control_block_from_events` (`:526-566`): same invariant for `matched_controls` (`:548`),
  explicitly scoped to single-unit selectivity, "not the 40-element subspace matched control"
  (`:558-565`).
- `_proof_chips_for_live_fields` (`:637-709`): `causal_proof` / `control_proof` flip to `"present"`
  *only* off those `is_real_model`-gated flags (`:666-693`).
- `_code_commit_sha` (`:751-766`) resolves git HEAD so every packet is reproducible, falling back to
  `"unknown"` honestly rather than claiming a sha it cannot resolve.

### 1.4 The bar the worker's evidence must clear (the consumer)

`api/services/cas_harness_verifier_decision_adapter.py::_stage9_proof_chips_pass_ready` (`:135-164`)
is the production gate. It requires all six chips present **and**
`strict_verified = {cas_readout, causal_proof, control_proof, output_proof}` each equal to exactly
`"verified"` (`:146-151`, `:164`). **This is the crux of the gap:** the live path's
`_proof_chips_for_live_fields` only ever emits `"present"` or `"unavailable"` — *never*
`"verified"` (`:646-709`). So **nothing the worker produces today can satisfy the production
verifier.** The `"present" → "verified"` promotion is precisely this workstream.

### 1.5 What is verified vs only declared, today

| Claim | Today | Honest status now | Where it becomes `*_VERIFIED` |
|---|---|---|---|
| A real model loaded | real load happens | declared (`is_real_model` flag, no weights identity) | 01 §3 Phase B (weights attestation) |
| Activations were captured | real hook + capture | computed, but **not hashed** → not re-checkable | 01 §3 Phase C (content-hash) |
| The CAS readout is this exact readout | real dot-product | computed, **not hashed**, **not deterministic** | 01 §3 Phase A+C |
| The probe artifact is the declared one | `weights_sha256` **declared only** | `weights_hash_verified=False` (`probe_compat:121`) | 01 §3 Phase B (recompute on worker) |
| This specific worker did the work | nothing | unattested | 01 §3 Phase D (worker identity) |
| The evidence is tamper-evident | packet hash-log exists | partial (no signature over worker evidence) | 01 §3 Phase E (signing) |

---

## 2. Gap to production

1. **No determinism pinning → a hash would be meaningless.** The worker sets **no seed**, **no
   kernel-determinism flags** (`torch.use_deterministic_algorithms`, cuBLAS workspace), and dtype
   defaults to `"auto"` (`ProbeShardConfig.torch_dtype = "auto"` `:49`; `resolve_torch_dtype`
   returns `None` for auto `:396-399`). Two runs of the same shard can produce different
   activation bytes, so content-hashing them first (Phase C) is pointless. **Determinism is a
   prerequisite for every other verification**, not an optional nicety.
2. **No weights identity.** `model_info` (`:206-216`) records architecture/param-count but **no hash
   of the loaded weights** and does not pin the *resolved* revision commit (a moving tag like
   `main` is recorded as-passed, `model_revision` `:144`). `MODEL_ACCESS_VERIFIED` cannot be honest
   without naming *which bytes* loaded.
3. **No activation / readout content-hash.** Neither `activation_summary` nor `cas_axis_readout` is
   hashed at the worker. There is no `cas-fragment://…/sha256:<digest>` for the worker's own
   evidence (that ref currently exists only at the fleet-executor receipt layer —
   `cas_harness_fleet_executor.py::build_evidence_fragment_ref`). A consumer cannot re-derive and
   compare.
4. **Probe weights hash is declared but never recomputed.** `compute_cas_axis_readout` (`:313-336`)
   reads the probe JSON and uses it, but never `sha256`s the file to confirm it matches the
   `weights_sha256` the gate accepted. So `weights_hash_verified` stays `False` with no path to
   `True` — the field exists but nothing fills it.
5. **No worker identity / attestation.** `worker_evidence_manifest` is hardcoded `True` in
   `classify_outputs` (`:362`). Nothing records *which physical worker*, *which probe weights-hash*,
   *which torch/transformers/CUDA versions* produced the evidence. "This worker ran it" is
   currently an unfalsifiable assertion.
6. **No signature / tamper-evidence over the worker's evidence.** The packet hash-log
   (`cas_harness_merged_evidence_packets.py`) chains *packets*, but the worker's `evidence_payload`
   itself is unsigned: a result JSON written to `CAS_FLEET_RESULT_PATH` can be edited in flight
   between worker and fleet with no detectable break.
7. **The `"present" → "verified"` promotion does not exist.** Per §1.4, the live path never emits
   `"verified"`; the production verifier requires it. There is no function that, given attested +
   hashed + determinism-pinned worker evidence, upgrades a chip to `"verified"`.

---

## 3. Phased plan (each phase has an explicit kill/validate gate)

> Ordering rationale: **A → B → C** is forced. A determinism harness (A) must exist before any hash
> (C) is meaningful, and weights identity (B) is the cheapest independent win and a prerequisite for
> honest `MODEL_ACCESS_VERIFIED`. D (attestation) and E (signing) layer on top. Only after A–E can
> the `"present" → "verified"` promotion (the §2.7 gap) be honest — it is the *exit* of Phase E, not
> a separate phase.

### Phase A — Determinism harness (seed, dtype pin, kernel flags, reproducibility manifest)
Add to the shard config/run: an explicit integer **seed** (seed `random`, `numpy`, `torch`,
`torch.cuda`); a **required** dtype (reject `"auto"` for any run that will be verified —
non-determinism by omission); `torch.use_deterministic_algorithms(True)` + cuBLAS workspace env;
and a `reproducibility_manifest` recording seed, resolved dtype, torch/transformers/CUDA/cuDNN
versions, device, and `_code_commit_sha()`-style worker commit.
- **Validate:** the same shard run twice on the same hardware produces **byte-identical**
  `activation_summary` and `cas_axis_readout`. (Test: two in-process runs, assert equal serialized
  bytes.)
- **Kill:** if byte-level determinism is unattainable on the target accelerator (e.g. an
  irreducibly non-deterministic kernel), **downgrade the honest claim** — define a
  `READOUT_REPRODUCIBLE_WITHIN_TOL` status with a published numerical tolerance instead of claiming
  a byte-exact hash. Never ship a content-hash whose inputs aren't deterministic.

### Phase B — Weights + probe attestation (recompute hashes on the worker)
Record a **weights identity**: resolved revision commit (pin the tag→commit at load time) and a
hash over the loaded weights (parameter-tensor digest, or the model's resolved file `sha256`s).
Recompute the **probe artifact `sha256`** inside `compute_cas_axis_readout` and compare it to the
declared `weights_sha256`; on match, set the worker-side `weights_hash_verified = True` (the field
already exists at `probe_compat:121`).
- **Validate:** worker emits `model_weights_sha256` + `resolved_revision_commit`; re-loading the
  same pinned commit reproduces the same weights hash; a probe file edited by one byte flips
  `weights_hash_verified` to `False` and the shard refuses to emit `PROBE_COMPATIBILITY_VERIFIED`.
- **Kill:** if hashing full frontier weights is too expensive per run, fall back to attesting the
  **resolved revision commit + HF file-level `sha256`s from the snapshot** (cheap, already on disk)
  rather than a full parameter digest — and say so in the manifest. Do not silently skip identity.

### Phase C — Deterministic content-hash of activations + readout
With A guaranteeing determinism, compute a `sha256` over the **serialized bytes** of the pooled
activations and the `cas_axis_readout`, using the repo's canonical-JSON discipline for the small
JSON parts (`json.dumps(…, sort_keys=True, separators=(",",":"))`, matching
`cas_harness_evidence_anchor.py:454-459`) and the **02 serialization format** for the large tensor
bytes. Emit a worker-side `cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:<digest>`
for its own evidence, mirroring `build_evidence_fragment_ref`. **Compute the hash once**, over the
exact bytes 02 will store (§6: 01's hash *is* `ArtifactDescriptor.sha256`).
- **Validate:** a consumer re-serializes the worker evidence and recomputes the same digest; a
  one-bit edit to any activation value changes the digest; the worker digest equals the
  `ArtifactDescriptor.sha256` 02 records for the same bytes (no double-hashing).
- **Kill:** if the large-tensor serialization (02 §7 open question) is not yet frozen, hash **only**
  the small canonical-JSON readout + activation *summary* now (already deterministic), and defer the
  full-tensor content-hash until 02 freezes safetensors/npy. Ship the half that is honest.

### Phase D — Worker identity / attestation
Replace the hardcoded `worker_evidence_manifest = True` (`:362`) with a real manifest binding the
evidence to *this* worker: worker id, host/instance identity (and a hardware-attestation token where
available, e.g. Nitro/SEV/TPM), accelerator model, plus the Phase-A reproducibility manifest and the
Phase-B weights/probe hashes. This is what makes `MODEL_ACCESS_VERIFIED` / `COMPUTE_FEASIBILITY_VERIFIED`
nameable to a specific machine.
- **Validate:** the manifest names worker id + accelerator + weights-hash + probe-hash + repro
  manifest, and a packet missing any required field cannot reach a `*_VERIFIED` status.
- **Kill:** if cloud hardware attestation (Nitro/SEV/TPM) is unavailable in the target environment,
  attest only **software identity** (worker id, instance id, image digest, library versions) and
  mark hardware attestation `unattested` honestly — do not fabricate a hardware root of trust.

### Phase E — Signing + tamper-evidence + the `present → verified` promotion
Sign the worker evidence manifest (worker holds a key; fleet verifies the signature) so the
`evidence_payload` is tamper-evident end-to-end, not just chained at the packet layer. **Then**, and
only then, define the single honest promotion: a `promote_chip` that upgrades `cas_readout` /
`causal_proof` / `control_proof` / `output_proof` from `"present"` to `"verified"` **iff**
(determinism manifest present) ∧ (weights+probe hashes verified) ∧ (content-hash re-checks) ∧
(signature valid) ∧ (`is_real_model is True`). This is the function that lets the fleet emit what
`_stage9_proof_chips_pass_ready` (`:164`) demands.
- **Validate:** a fully-attested, signed, determinism-pinned packet promotes all four strict chips
  to `"verified"` and passes `_stage9_proof_chips_pass_ready`; breaking the signature, the hash, the
  determinism manifest, or flipping `is_real_model` to `False` each independently blocks promotion.
- **Kill:** if any single input cannot be made real (e.g. signing infra slips), the promotion **must
  not fire** — the chip stays `"present"` and the run flags for human review. A partial promotion is
  the exact dishonesty this program forbids; ship `"present"` honestly rather than `"verified"`
  prematurely.

---

## 4. Honesty constraints (non-negotiable)

- **`*_VERIFIED` is worker-only and earns its name.** `MODEL_ACCESS_VERIFIED`,
  `PROBE_COMPATIBILITY_VERIFIED`, `COMPUTE_FEASIBILITY_VERIFIED`, and a verified proof chip may be
  produced **only** by the worker, **only** after the corresponding real check passed *and is
  re-checkable*. The API tier keeps `weights_hash_verified=False` / `probe_loadable=False`
  (`probe_compat:121-122`) — never flip those at the control plane.
- **A hash is honest only if its inputs are deterministic.** Never emit a content-hash (Phase C) for
  bytes produced without the Phase-A determinism manifest. An irreproducible "hash" is a fabricated
  proof. If determinism fails, downgrade to `READOUT_REPRODUCIBLE_WITHIN_TOL` with a published
  tolerance (§3 Phase A kill).
- **Generalize the `is_real_model` invariant, never weaken it.** Demo/failed/absent measurements
  carry **no** deltas and stay `"unavailable"`, exactly as `_ablation_block_from_events` /
  `_control_block_from_events` already enforce (`live_worker_runner:384,548`). The promotion in
  Phase E is *additive* gating on top of `is_real_model`, never a bypass.
- **`"present" → "verified"` requires the full evidence set.** The promotion fires only with
  determinism ∧ weights/probe hash ∧ content-hash ∧ signature ∧ `is_real_model`. Any missing input
  ⇒ stays `"present"` ⇒ run flags for human review (mirrors the merge that "never fabricates ACCEPT
  — always FLAG_FOR_HUMAN_REVIEW pending verifier").
- **Attestation must be falsifiable.** Replace `worker_evidence_manifest = True` (`:362`) with a
  manifest a consumer can *fail*. "This worker ran it" must be checkable, or it is not claimed.
- **Stub honesty (if a scaffold ships).** Per `api/services/production/__init__.py:9-12`, no module
  in `production/` may emit a `*_VERIFIED` / `*_METERED` / `*_WORM_COMMITTED` status from a stub
  backend. A scaffold may define the seam and *prove content integrity over bytes it holds in
  memory* (honest), but must never imply determinism, durability, or attestation it does not
  perform.
- **Hash provenance over bytes actually stored.** The worker's content-hash is computed over the
  exact serialized bytes 02 persists — so the digit a verifier recomputes is the digit the worker
  committed (one hash, computed once; §6).

---

## 5. Interfaces / seams

Concrete Protocol/dataclass shapes for the import-isolated scaffold
(`api/services/production/worker_verification.py`). These describe the worker's *verification*
surface; they do not import the live worker or any route.

```python
WorkerVerificationStatus = Literal[
    "WORKER_EVIDENCE_VERIFIED",          # determinism + hashes + signature + is_real_model all real
    "WORKER_EVIDENCE_DECLARED",          # evidence present but not yet re-checked
    "READOUT_REPRODUCIBLE_WITHIN_TOL",   # determinism kill-gate fallback (published tolerance)
    "WORKER_EVIDENCE_UNVERIFIED",        # missing/failed input → cannot promote
]

@dataclass(frozen=True)
class ReproducibilityManifest:
    seed: int
    torch_dtype: str                 # explicit — never "auto" for a verified run
    deterministic_algorithms: bool
    torch_version: str
    transformers_version: str
    accelerator: str                 # e.g. "NVIDIA A100-80GB" / "cpu"
    cuda_version: str | None
    worker_commit_sha: str           # _code_commit_sha()-style; "unknown" if unresolved

@dataclass(frozen=True)
class WeightsAttestation:
    model_id: str
    resolved_revision_commit: str | None    # tag pinned to a commit at load time
    model_weights_sha256: str | None        # full digest, or HF file-level sha256s (§3 Phase B kill)
    probe_weights_sha256: str | None        # recomputed on the worker
    probe_weights_hash_verified: bool        # ↔ ProbeCompatibilitySummary.weights_hash_verified

@dataclass(frozen=True)
class WorkerAttestation:
    worker_id: str
    instance_id: str | None
    image_digest: str | None
    hardware_attestation: str | None         # Nitro/SEV/TPM token, or None == "unattested"

@dataclass(frozen=True)
class WorkerEvidenceReceipt:
    status: WorkerVerificationStatus
    fragment_ref: str                        # cas-fragment://{audit}/{job}/{worker}/{shard}/sha256:<digest>
    content_sha256: str                      # == ArtifactDescriptor.sha256 (02 §6) — computed once
    is_real_model: bool
    reproducibility: ReproducibilityManifest
    weights: WeightsAttestation
    worker: WorkerAttestation
    signature: str | None                    # over the canonicalized receipt; None == unsigned
    reasons: tuple[str, ...] = ()

class WorkerVerifier(Protocol):
    def attest(self, evidence_payload: Mapping[str, Any]) -> WorkerEvidenceReceipt: ...
        # Worker-side: pin determinism, recompute weights/probe/content hashes, sign.

    def reverify(self, receipt: WorkerEvidenceReceipt, evidence_payload: Mapping[str, Any]) -> bool: ...
        # Consumer-side: re-serialize bytes, recompute content_sha256, verify signature + hashes.

    def promote_chip(self, chip_id: str, receipt: WorkerEvidenceReceipt) -> Literal["present", "verified"]: ...
        # Returns "verified" IFF determinism ∧ weights/probe hash verified ∧ content re-check ∧
        # signature valid ∧ is_real_model; else "present". Never raises a chip to "verified" partially.
```

**Seam to the worker script.** `run_open_weight_probe_shard.py` gains (behind the determinism
config) a call that wraps `evidence_payload` into a `WorkerEvidenceReceipt`: it recomputes the probe
`sha256` inside/after `compute_cas_axis_readout` (`:313-336`), hashes the serialized
activations/readout, and replaces the hardcoded `worker_evidence_manifest = True` (`:362`) with the
real receipt. No live route imports this; it executes only in the fleet worker process.

**Seam to the chip layer.** `promote_chip` is the missing inverse of
`_proof_chips_for_live_fields` (`live_worker_runner:646-709`): that function caps chips at
`"present"`; `promote_chip` is the *only* sanctioned path from `"present"` to the `"verified"` that
`_stage9_proof_chips_pass_ready` (`verifier_decision_adapter:164`) requires.

---

## 6. Cross-references

- **02 (large artifact object storage)** *stores what 01 produces.* 02 §6 already states "01's
  deterministic hash should **be** the `ArtifactDescriptor.sha256` … no double-hashing." Honored
  here: `WorkerEvidenceReceipt.content_sha256` is computed once, over the exact serialized bytes 02
  persists. 01's Phase-C kill gate explicitly defers the full-tensor hash until 02 freezes its
  serialization format (02 §7 Q1: safetensors), hashing the deterministic JSON readout/summary in
  the meantime. The worker `fragment_ref` mirrors `build_evidence_fragment_ref`
  (`cas_harness_fleet_executor.py`), which stays the *receipt* join key; 02's key is the
  durable-bytes pointer.
- **03 (fleet execution at scale)** *places the workers 01 attests.* `COMPUTE_FEASIBILITY_VERIFIED`
  is honest only with 01's `WorkerAttestation` naming the accelerator the shard actually ran on. As
  the fleet scales past the fan-out cap, 03 must carry 01's per-worker receipt through fan-in so the
  merge can promote chips per shard.
- **05 (observability)** *surfaces 01's verification timing + outcomes.* Per-stage timing of
  load/hook/readout/hash/sign, and a counter of `present` vs `verified` promotions, are 05's
  traceability surface. A run that never reaches `"verified"` should be visible, not silent.
- **07 (production WORM writes)** *commits 01's verified evidence.* 01 is the producer; 07 wraps 02's
  real S3 backend with Object-Lock/retention. The lock-verify chain already exists
  (`cas_harness_evidence_anchor.py::_verify_s3_anchor` `:248-376`: re-read + re-hash, then
  `head_object` checks `ObjectLockMode` + future `ObjectLockRetainUntilDate`), and
  `cas_harness_static_evidence_anchor.py::summarize_static_anchor_worm_status` gates `worm_retained`
  on all of `("object was re-read","object lock","retention is active")`. **The WORM commit is only
  honest over evidence 01 has verified** — committing unverified bytes immutably would permanently
  enshrine an unprovable claim. `DATA_CAPTURE_WORM_COMMITTED` (gate 8,
  `cas_harness_data_governance.py`) presupposes 01's content-hash identifies *what* was committed.
- **04 (queue/resume)** a resumed/retried shard must re-attest; a `WorkerEvidenceReceipt` from a
  prior attempt is not transferable to a new worker without re-verification (ties to Phase D).
- **08 / 09** the weights/probe/worker identity 01 attests is the provenance 09's audit trail needs;
  09's retention-vs-redaction tension applies to the verified evidence 07 retains.

---

## 7. Open questions (for a human)

1. **Weights-hash cost vs fidelity — the single most important decision.** Hashing full frontier
   (300B–4T) parameter tensors every run is expensive. Is the cheap fallback — attesting the
   **resolved revision commit + HF snapshot file-level `sha256`s** (already on disk) — sufficient
   for an honest `MODEL_ACCESS_VERIFIED`, or must we pay for a true parameter-tensor digest? This
   gates Phase B and directly shapes what `MODEL_ACCESS_VERIFIED` is *allowed to mean*.
2. **Byte-exact determinism vs published tolerance.** Some accelerator kernels are irreducibly
   non-deterministic. Do we (a) restrict verified runs to determinism-capable kernels/hardware, or
   (b) adopt `READOUT_REPRODUCIBLE_WITHIN_TOL` with a published numerical tolerance as a first-class
   honest status? Affects whether the headline claim is "byte-identical hash" or "reproducible
   within ε."
3. **Worker signing key custody + hardware root of trust.** Where do worker signing keys live (KMS,
   instance identity, enclave), and is cloud hardware attestation (Nitro/SEV/TPM) available in the
   target fleet? If not, is software-only attestation (image digest + library versions + worker id)
   an acceptable `MODEL_ACCESS_VERIFIED` basis, or is a hardware root of trust required for the
   verified tier? (Phase D/E.)
4. **Does `MODEL_ACCESS_VERIFIED` require activation-level proof, or is weights-load attestation
   enough?** Two honest readings: "verified" = "the declared weights demonstrably loaded" (Phase B
   alone), vs "verified" = "the declared weights loaded **and** produced this attested readout"
   (Phase B+C+D). The stricter reading is safer but couples model-access verification to a
   successful readout. Human call on where the line sits.
5. **Promotion authority — worker self-attestation vs independent re-verification.** Should the chip
   promotion to `"verified"` trust the worker's signed receipt, or must an **independent** fleet-side
   re-verifier recompute the content-hash and re-check the signature before
   `_stage9_proof_chips_pass_ready` sees `"verified"`? (Leaning independent re-verification — a
   self-attested "verified" is weaker than the program's ethos wants — but it costs a re-hash at
   fan-in. Confirm.)
