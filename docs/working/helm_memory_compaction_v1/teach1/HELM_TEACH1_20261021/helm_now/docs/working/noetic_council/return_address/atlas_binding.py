"""atlas_binding.py -- the read-only bridge to the real atlas model, for the two things this build needs.

WHAT THIS MODULE DOES
---------------------
  * It re-hashes the six real-model files copied into ``real_atlas/`` beside this file and
    refuses if any byte moved (``verify_real_model()``). The copy is a read-only input.
  * ``snapshot_digest_of(snapshot)`` reads the REAL ``AtlasSnapshot.snapshot_digest`` -- the
    sha256 the atlas model computes over its own canonical form -- so the ``snapshot_digest``
    in a return address is a number somebody computed over a saved snapshot, not a string a
    caller typed.
  * ``require_snapshot(address, snapshot)`` checks that an address names the saved snapshot it
    is being used against, and refuses ``SNAPSHOT_MISMATCH`` when it names another one.
  * ``glue_back(nodes, witness_id=None)`` answers one question and only one: what the real
    model's own ``compatibility()`` and ``certify_overlap()`` said about these nodes gluing
    back together. ``GlueBack.ok`` is those two verdicts joined with ``and`` -- the only thing
    this module adds -- so there is no second glue rule to disagree with the real one.

WHAT THIS MODULE DOES NOT DO
----------------------------
  * It does NOT build, extend or re-implement an atlas. There is no node class, link class,
    kind vocabulary or digest scheme in this file; every one of those is the real model's.
  * It does NOT decide glue-back. No field comparison, no overlap test, no witness choice. If
    the real model refuses, the refusal is surfaced as ``REAL_MODEL_REFUSAL`` carrying its own
    words.
  * It does NOT promote a node's status, rename a status word, or write anything back into a
    snapshot.
  * It does NOT read the clock, the network, or any file except the six real-model files it
    hashes.

THE COPY
--------
The six files were copied byte for byte from
``C:\\Users\\wakil\\Documents\\Codex\\2026-10-16\\continuity_build_v3\\real_atlas\\``, which is
itself a byte-for-byte copy of branch ``codex/helm-rpa-recorded-run-20260922`` at commit
``eb9985566bd11a89f485d627186ef0efa7177f02``. ``real_atlas/PROVENANCE.md`` is carried
unchanged and records that first hop; ``ATLAS_COPY.md`` beside this file records the second.
Nothing in either source folder was modified to make this copy.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NO CIRCUIT USES THIS YET.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from real_atlas.model import ContractError
from real_atlas.rpa_model import (
    AtlasSnapshot,
    certify_overlap,
    compatibility,
)

from address import NOT_A_RETURN_PATH, ReturnAddress, ReturnRefusal

__all__ = [
    "GlueBack",
    "glue_back",
    "glue_back_ok",
    "snapshot_digest_of",
    "require_snapshot",
    "real_model_files",
    "verify_real_model",
    "REAL_MODEL_SHA256",
    "REAL_MODEL_BRANCH",
    "REAL_MODEL_COMMIT",
    "REAL_MODEL_DIR",
    "REAL_MODEL_VERIFIED",
    "REAL_MODEL_FILES_CHANGED",
    "REAL_MODEL_REFUSAL",
    "BAD_SNAPSHOT",
    "SNAPSHOT_MISMATCH",
    "CANON_VERIFY_ON_COMPLETION",
]

CANON_VERIFY_ON_COMPLETION = (
    '"On completion, verify the child\'s result and its episode, branch, occurrence and '
    'expected parent. Commit the accepted result/update and consume its return token through '
    'the existing coordinator."  [CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md, line 29]'
)

#: The branch and commit the real model came from. Recorded so a reader can re-extract it.
REAL_MODEL_BRANCH = "codex/helm-rpa-recorded-run-20260922"
REAL_MODEL_COMMIT = "eb9985566bd11a89f485d627186ef0efa7177f02"

#: The sha256 of every file copied out of that commit, measured on the bytes now on disk.
REAL_MODEL_SHA256 = {
    "rpa_model.py": "323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01",
    "canonical.py": "424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a",
    "model.py": "aafa82f0267d0e741a90ba095d939da47401be577b5682832608a6845be54766",
    "rpa_ohm_atlas.py": "6aa030651278f217965a788427d55d3f475bb666b366a8095d6a5fb05be9694f",
    "CAS_RPA_OHM_ATLAS_20260922.md": "516aa180212643c97da6241dfe618548d71be422e3d966d747cad812c95acc34",
    "VERIFICATION.md": "5eec0108af1408d91c44063fb4950723c52e3170856b6947bfad77bef69602d0",
}

#: The folder the real model sits in, beside this file.
REAL_MODEL_DIR = Path(__file__).resolve().parent / "real_atlas"

REAL_MODEL_FILES_CHANGED = "REAL_MODEL_FILES_CHANGED"
REAL_MODEL_REFUSAL = "REAL_MODEL_REFUSAL"
BAD_SNAPSHOT = "BAD_SNAPSHOT"
SNAPSHOT_MISMATCH = "SNAPSHOT_MISMATCH"


def real_model_files() -> dict:
    """The sha256 of every copied real-model file, hashed now. ``{name: hex}``."""
    hashes = {}
    for name in sorted(REAL_MODEL_SHA256):
        path = REAL_MODEL_DIR / name
        if not path.is_file():
            raise ReturnRefusal(
                REAL_MODEL_FILES_CHANGED,
                f"real-model file {name!r} is missing from {REAL_MODEL_DIR}",
            )
        hashes[name] = sha256(path.read_bytes()).hexdigest()
    return hashes


def verify_real_model() -> dict:
    """Re-hash the copies and refuse if any byte moved. Returns ``{name: hex}``."""
    now = real_model_files()
    changed = [name for name in sorted(now) if now[name] != REAL_MODEL_SHA256[name]]
    if changed:
        raise ReturnRefusal(
            REAL_MODEL_FILES_CHANGED,
            f"{len(changed)} real-model file(s) no longer hash to the recorded value: "
            f"{changed}; the copies are read-only inputs and must not be edited",
        )
    return now


#: The hashes of the copies, checked once at import, so no later caller can proceed on a
#: changed file by forgetting to ask.
REAL_MODEL_VERIFIED = verify_real_model()


def _real(call, label: str):
    """Run one call on the real model, turning its refusal into this build's typed one."""
    try:
        return call()
    except ContractError as refusal:
        raise ReturnRefusal(
            REAL_MODEL_REFUSAL, f"the real atlas model refused {label}: {refusal}"
        ) from refusal


def snapshot_digest_of(snapshot) -> str:
    """The real ``AtlasSnapshot.snapshot_digest`` of a saved snapshot, or a typed refusal."""
    if type(snapshot) is not AtlasSnapshot:
        raise ReturnRefusal(
            BAD_SNAPSHOT,
            f"a saved snapshot is the real model's AtlasSnapshot, got "
            f"{type(snapshot).__name__}; an object that merely carries digest-shaped fields is "
            f"not the real snapshot",
        )
    return snapshot.snapshot_digest


def require_snapshot(address, snapshot) -> str:
    """True-ish: the address names THIS saved snapshot, or ``SNAPSHOT_MISMATCH``.

    This is what makes "which saved snapshot" checkable rather than decorative: the digest in
    the address has to be the digest the real model computes for the snapshot in hand.
    """
    if type(address) is not ReturnAddress:
        raise ReturnRefusal(
            NOT_A_RETURN_PATH,
            f"require_snapshot() takes a ReturnAddress, got {type(address).__name__}",
        )
    digest = snapshot_digest_of(snapshot)
    if address.snapshot_digest != digest:
        raise ReturnRefusal(
            SNAPSHOT_MISMATCH,
            f"the address names snapshot {address.snapshot_digest[:12]}... and the snapshot in "
            f"hand is {digest[:12]}.... A return bound to one saved snapshot is not delivered "
            f"against another",
        )
    return digest


@dataclass(frozen=True)
class GlueBack:
    """What the REAL model said about a child gluing back onto its parent.

    Every decision field is the real model's output, copied: ``compatible``,
    ``same_context``, ``shared_fields`` and ``conflicting_fields`` come from
    ``compatibility()``; ``certificate_id`` and ``witness_id`` come from
    ``certify_overlap()``. ``ok`` joins those two verdicts with ``and`` and is the only thing
    this build adds.
    """

    node_ids: tuple
    region_digests: tuple
    same_context: bool
    shared_fields: tuple
    conflicting_fields: tuple
    compatible: bool
    witness_id: str | None
    certificate_id: str | None

    @property
    def ok(self) -> bool:
        """True only when the real model both reports compatibility and certifies overlap."""
        return bool(self.compatible and self.certificate_id is not None)

    def as_dict(self) -> dict:
        return {
            "node_ids": self.node_ids,
            "region_digests": self.region_digests,
            "same_context": self.same_context,
            "shared_fields": self.shared_fields,
            "conflicting_fields": self.conflicting_fields,
            "compatible": self.compatible,
            "witness_id": self.witness_id,
            "certificate_id": self.certificate_id,
            "ok": self.ok,
            "boundary": "the real model's shared-field consistency and common-witness "
            "certificate only; not a sheaf gluing proof",
        }

    def __str__(self) -> str:
        return (
            f"GlueBack(node_ids={self.node_ids}, compatible={self.compatible}, "
            f"certificate={self.certificate_id!r}, ok={self.ok})"
        )


# UNDECIDED IN SOURCES: may this build's caller choose the glue-back witness instead of taking the real model's own default -- the real certify_overlap picks the minimum common member when no witness is named and the addendum says nothing about who chooses (CAS_RPA_RETURN_ADDRESS_ADDENDUM_v1.md:29-30), so a witness is passed through when the caller names one and the real model's default is used when it does not.
def glue_back(nodes, witness_id=None) -> GlueBack:
    """Ask the REAL model whether these nodes glue back, and report both of its answers.

    Both real calls are made and nothing is short-circuited. If the real model refuses -- two
    regions with no common member, fewer than two typed views, an object that is not a real
    ``AtlasNode`` -- the refusal comes out as ``REAL_MODEL_REFUSAL`` carrying its own words.
    """
    nodes = nodes if isinstance(nodes, tuple) else tuple(nodes)
    report = _real(lambda: compatibility(nodes), "compatibility")
    certificate = _real(lambda: certify_overlap(nodes, witness_id), "certify_overlap")
    return GlueBack(
        node_ids=report.node_ids,
        region_digests=tuple((node.node_id, node.region_digest) for node in nodes),
        same_context=report.same_context,
        shared_fields=report.shared_fields,
        conflicting_fields=report.conflicting_fields,
        compatible=report.compatible,
        witness_id=certificate.witness_id,
        certificate_id=certificate.certificate_id,
    )


def glue_back_ok(nodes, witness_id=None) -> bool:
    """True only when the real ``compatibility()`` and ``certify_overlap()`` both pass."""
    return glue_back(nodes, witness_id).ok
