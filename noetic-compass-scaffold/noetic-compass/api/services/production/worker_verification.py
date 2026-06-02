"""Worker-side verification seam — design-stage scaffold (workstream 01).

Import-isolated. NOTHING here is wired into the live FastAPI app, the fleet executor, the
live worker runner, or ``live-trace-worker/scripts/run_open_weight_probe_shard.py``. It
exists so the blueprint in ``docs/working/production_readiness/01_worker_side_verification.md``
has a concrete ``WorkerVerifier`` seam — the surface on which a ``*_DECLARED`` worker claim
becomes ``*_VERIFIED`` — that the team (and workstreams 02/07) can build against.

What "verified" honestly requires (blueprint §4), and the discipline this module encodes:
a worker proof chip may rise from ``"present"`` to ``"verified"`` ONLY when every one of
these is true at once —

* a reproducibility manifest is present (seed + explicit non-"auto" dtype + deterministic
  kernels) — so a content hash is *meaningful*;
* the model weights AND probe artifact hashes were recomputed and verified on the worker
  (``probe_weights_hash_verified`` — the field that already exists, hardcoded ``False``, at
  ``api/services/cas_harness_probe_compatibility.py:121``);
* the content hash of the activations/readout re-checks against the bytes actually stored;
* the worker's signed manifest verifies (tamper-evidence end to end);
* ``is_real_model is True`` — generalizing the invariant already enforced in
  ``api/services/cas_harness_live_worker_runner.py`` (``_ablation_block_from_events`` /
  ``_control_block_from_events`` gate "present" on ``is_real_model``).

Honesty rule (mirrors ``api/services/production/__init__.py``): a stub is a stub. The
in-memory ``InMemoryWorkerVerifier`` below does NOT pin determinism, does NOT load real
weights, and does NOT hold a signing key — so its ``attest`` NEVER returns
``WORKER_EVIDENCE_VERIFIED``; it returns ``WORKER_EVIDENCE_DECLARED`` (or
``WORKER_EVIDENCE_UNVERIFIED``) and records honestly *why* it cannot verify. The promotion
*logic* (``reverify`` / ``promote_chip``) is real and exercisable on a caller-supplied
receipt: that is how the team can test the gate without a GPU. ``promote_chip`` is the only
sanctioned path to the ``"verified"`` that the production gate
(``api/services/cas_harness_verifier_decision_adapter.py::_stage9_proof_chips_pass_ready``,
which requires the strict chips == ``"verified"``) demands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Literal, Mapping, Protocol, runtime_checkable


WORKER_EVIDENCE_RECEIPT_SCHEMA_VERSION = "cas_harness_worker_evidence_receipt.v1"

WorkerVerificationStatus = Literal[
    "WORKER_EVIDENCE_VERIFIED",  # determinism + weights/probe hash + content hash + signature + is_real_model
    "WORKER_EVIDENCE_DECLARED",  # evidence present, not yet independently re-checked
    "READOUT_REPRODUCIBLE_WITHIN_TOL",  # determinism kill-gate fallback (published tolerance)
    "WORKER_EVIDENCE_UNVERIFIED",  # a required real input is missing/failed -> cannot promote
]

# The four strict proof chips the production verifier requires at exactly "verified"
# (api/services/cas_harness_verifier_decision_adapter.py:146-151). model_proof/packet_proof
# may pass at "present"; these four must be "verified".
STRICT_VERIFIED_CHIPS: frozenset[str] = frozenset(
    {"cas_readout", "causal_proof", "control_proof", "output_proof"}
)


class WorkerVerificationError(ValueError):
    """Base error for the worker-verification seam."""


@dataclass(frozen=True)
class ReproducibilityManifest:
    """What makes a downstream content hash *meaningful* (blueprint §3 Phase A).

    Without a seed, an explicit (non-"auto") dtype, and deterministic kernels, two runs of
    the same shard can produce different activation bytes — so hashing them proves nothing.
    """

    seed: int | None = None
    torch_dtype: str | None = None  # explicit; "auto" is NOT verifiable
    deterministic_algorithms: bool = False
    torch_version: str | None = None
    transformers_version: str | None = None
    accelerator: str | None = None
    cuda_version: str | None = None
    worker_commit_sha: str | None = None  # _code_commit_sha()-style; None/"unknown" if unresolved

    @property
    def is_pinned(self) -> bool:
        """True only when determinism is genuinely pinned (the §4 hash precondition)."""
        return (
            self.seed is not None
            and bool(self.torch_dtype)
            and self.torch_dtype != "auto"
            and self.deterministic_algorithms is True
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "torch_dtype": self.torch_dtype,
            "deterministic_algorithms": self.deterministic_algorithms,
            "torch_version": self.torch_version,
            "transformers_version": self.transformers_version,
            "accelerator": self.accelerator,
            "cuda_version": self.cuda_version,
            "worker_commit_sha": self.worker_commit_sha,
            "is_pinned": self.is_pinned,
        }


@dataclass(frozen=True)
class WeightsAttestation:
    """Which bytes actually loaded, and whether the probe artifact matched (blueprint §3 Phase B).

    ``probe_weights_hash_verified`` is the honest worker-side counterpart of
    ``ProbeCompatibilitySummary.weights_hash_verified`` (always ``False`` at the API tier,
    ``cas_harness_probe_compatibility.py:121``): it may be ``True`` only once the worker has
    recomputed the probe file ``sha256`` and matched it.
    """

    model_id: str | None = None
    resolved_revision_commit: str | None = None
    model_weights_sha256: str | None = None
    probe_weights_sha256: str | None = None
    probe_weights_hash_verified: bool = False

    @property
    def has_weights_identity(self) -> bool:
        """True when the loaded weights are nameable (commit and/or weights digest)."""
        return bool(self.resolved_revision_commit) or bool(self.model_weights_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "model_id": self.model_id,
            "resolved_revision_commit": self.resolved_revision_commit,
            "model_weights_sha256": self.model_weights_sha256,
            "probe_weights_sha256": self.probe_weights_sha256,
            "probe_weights_hash_verified": self.probe_weights_hash_verified,
            "has_weights_identity": self.has_weights_identity,
        }


@dataclass(frozen=True)
class WorkerAttestation:
    """Which physical worker did the work (blueprint §3 Phase D).

    Replaces the hardcoded ``worker_evidence_manifest = True``
    (``run_open_weight_probe_shard.py:362``) with something a consumer can *fail*.
    ``hardware_attestation`` is ``None`` when no hardware root of trust is available — stated
    plainly as "unattested", never fabricated.
    """

    worker_id: str | None = None
    instance_id: str | None = None
    image_digest: str | None = None
    hardware_attestation: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "instance_id": self.instance_id,
            "image_digest": self.image_digest,
            "hardware_attestation": self.hardware_attestation,
        }


@dataclass(frozen=True)
class WorkerEvidenceReceipt:
    """The honest, self-verifying receipt a worker emits for one shard's evidence.

    ``content_sha256`` is computed once over the serialized evidence bytes — and is intended
    to *be* the ``ArtifactDescriptor.sha256`` workstream 02 stores (blueprint §6: no
    double-hashing). ``fragment_ref`` mirrors the fleet executor's
    ``build_evidence_fragment_ref`` shape.
    """

    status: WorkerVerificationStatus
    content_sha256: str
    is_real_model: bool
    reproducibility: ReproducibilityManifest
    weights: WeightsAttestation
    worker: WorkerAttestation
    fragment_ref: str | None = None
    signature: str | None = None  # over the canonicalized receipt; None == unsigned
    schema_version: str = WORKER_EVIDENCE_RECEIPT_SCHEMA_VERSION
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_verified(self) -> bool:
        return self.status == "WORKER_EVIDENCE_VERIFIED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "content_sha256": self.content_sha256,
            "is_real_model": self.is_real_model,
            "reproducibility": self.reproducibility.to_dict(),
            "weights": self.weights.to_dict(),
            "worker": self.worker.to_dict(),
            "fragment_ref": self.fragment_ref,
            "signature": self.signature,
            "schema_version": self.schema_version,
            "reasons": list(self.reasons),
        }


def _canonical_json(value: Any) -> str:
    """Canonical JSON, matching the anchor's discipline (cas_harness_evidence_anchor.py:454-459)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_sha256_over_evidence(evidence_payload: Mapping[str, Any]) -> str:
    """sha256 over the canonical-JSON serialization of the worker's evidence payload.

    Hash provenance is over the bytes a consumer would re-serialize — so the digit the
    verifier recomputes is the digit the worker committed (blueprint §4). For the large
    tensor case the real worker hashes the serialized tensor bytes in workstream 02's frozen
    format; this scaffold hashes the JSON evidence (already deterministic).
    """
    return hashlib.sha256(_canonical_json(evidence_payload).encode("utf-8")).hexdigest()


def build_worker_fragment_ref(
    *, audit_id: str, job_id: str, worker_id: str, shard_id: str, digest: str
) -> str:
    """Worker-evidence fragment ref, mirroring build_evidence_fragment_ref's shape."""
    return f"cas-fragment://{audit_id}/{job_id}/{worker_id}/{shard_id}/sha256:{digest}"


def _promotion_blockers(receipt: WorkerEvidenceReceipt) -> list[str]:
    """Every reason this receipt may NOT promote a strict chip to "verified".

    The single source of truth for the honesty gate. An empty list means — and only means —
    that all of determinism, weights+probe hash, content identity, signature, and
    is_real_model are satisfied.
    """
    blockers: list[str] = []
    if receipt.is_real_model is not True:
        blockers.append("is_real_model is not True (demo/failed/absent measurement)")
    if not receipt.reproducibility.is_pinned:
        blockers.append("reproducibility not pinned (seed/explicit-dtype/deterministic kernels)")
    if not receipt.weights.probe_weights_hash_verified:
        blockers.append("probe weights hash not verified on the worker")
    if not receipt.weights.has_weights_identity:
        blockers.append("loaded weights have no identity (no resolved commit or weights digest)")
    if not receipt.content_sha256:
        blockers.append("no content hash over the evidence")
    if not receipt.signature:
        blockers.append("worker evidence manifest is unsigned (not tamper-evident)")
    return blockers


@runtime_checkable
class WorkerVerifier(Protocol):
    """The seam that turns a ``*_DECLARED`` worker claim into a ``*_VERIFIED`` one.

    A real implementation runs inside the fleet worker process: it pins determinism,
    recomputes the weights/probe/content hashes, and signs the manifest (``attest``); a
    fleet-side consumer independently re-checks it (``reverify``); and ``promote_chip`` is the
    only place a strict proof chip may become ``"verified"``.
    """

    def attest(self, evidence_payload: Mapping[str, Any], **provenance: Any) -> WorkerEvidenceReceipt: ...

    def reverify(self, receipt: WorkerEvidenceReceipt, evidence_payload: Mapping[str, Any]) -> bool: ...

    def promote_chip(
        self, chip_id: str, receipt: WorkerEvidenceReceipt
    ) -> Literal["present", "verified"]: ...


class InMemoryWorkerVerifier:
    """Labeled in-memory ``WorkerVerifier`` stub — exercises the honesty gate, fabricates nothing.

    For tests and design only. It is honest about exactly one thing: the *promotion logic*
    (``promote_chip`` / ``reverify``) really enforces the §4 gate on a caller-supplied
    receipt. It is honest about what it CANNOT do: ``attest`` never pins determinism, never
    loads weights, never signs — so it never returns ``WORKER_EVIDENCE_VERIFIED``. It returns
    ``WORKER_EVIDENCE_DECLARED`` and lists the blockers, exactly as the blueprint requires a
    stub to behave (``production/__init__.py``: no ``*_VERIFIED`` from a stub backend).
    """

    def attest(self, evidence_payload: Mapping[str, Any], **provenance: Any) -> WorkerEvidenceReceipt:
        if not isinstance(evidence_payload, Mapping):
            raise WorkerVerificationError("evidence_payload must be a mapping")

        digest = content_sha256_over_evidence(evidence_payload)
        is_real_model = bool(evidence_payload.get("is_real_model") is True)

        audit_id = str(provenance.get("audit_id") or evidence_payload.get("audit_id") or "")
        job_id = str(provenance.get("job_id") or evidence_payload.get("job_id") or "")
        worker_id = str(provenance.get("worker_id") or evidence_payload.get("worker_id") or "")
        shard_id = str(provenance.get("shard_id") or evidence_payload.get("shard_id") or "")
        fragment_ref = (
            build_worker_fragment_ref(
                audit_id=audit_id, job_id=job_id, worker_id=worker_id, shard_id=shard_id, digest=digest
            )
            if audit_id and job_id and worker_id and shard_id
            else None
        )

        # A stub did NOT pin determinism, load real weights, or sign. Surface those gaps as a
        # DECLARED receipt with honest blockers — never claim VERIFIED. The real worker fills
        # the manifests in and signs; only then can the status rise.
        receipt = WorkerEvidenceReceipt(
            status="WORKER_EVIDENCE_DECLARED",
            content_sha256=digest,
            is_real_model=is_real_model,
            reproducibility=ReproducibilityManifest(),
            weights=WeightsAttestation(model_id=str(evidence_payload.get("model_id") or "") or None),
            worker=WorkerAttestation(worker_id=worker_id or None),
            fragment_ref=fragment_ref,
            signature=None,
            reasons=(
                "in-memory stub: determinism not pinned, weights/probe hashes not recomputed, "
                "manifest unsigned -- cannot reach WORKER_EVIDENCE_VERIFIED (a stub is a stub)",
            ),
        )
        return receipt

    def reverify(self, receipt: WorkerEvidenceReceipt, evidence_payload: Mapping[str, Any]) -> bool:
        """Re-serialize the evidence, recompute the content hash, compare to the receipt.

        This half is genuinely honest even in the stub: it really does detect a content hash
        that no longer matches the bytes (tamper-evidence over the readout/activations).
        Signature verification is deferred to the real implementation (no key here).
        """
        recomputed = content_sha256_over_evidence(evidence_payload)
        return bool(receipt.content_sha256) and recomputed == receipt.content_sha256

    def promote_chip(
        self, chip_id: str, receipt: WorkerEvidenceReceipt
    ) -> Literal["present", "verified"]:
        """The ONLY sanctioned path from "present" to "verified".

        Returns ``"verified"`` iff ``chip_id`` is a strict chip AND the receipt clears every
        §4 blocker (determinism pinned, weights+probe hash verified, weights identity present,
        content hash present, signature valid, is_real_model). Otherwise ``"present"``. It
        never raises a chip partially — a single missing input keeps it at ``"present"`` and
        the run flags for human review (mirroring the merge that never fabricates ACCEPT).
        """
        if chip_id not in STRICT_VERIFIED_CHIPS:
            return "present"
        if _promotion_blockers(receipt):
            return "present"
        return "verified"
