"""Byte-attested, local-only open-weight runtime primitives.

This package is deliberately separate from the milestone-one fake LIVE path.
It provides a shared, executable engineering core for local model capture.  A
successful run proves only that the bound model bytes executed and that the
declared tensors were captured.  It is not a scientific result, detector
validation, product licence, or Evidence Packet.
"""

from .identity import LocalModelSnapshot, SnapshotAttestation, attest_local_snapshot

__all__ = [
    "LocalModelSnapshot",
    "SnapshotAttestation",
    "attest_local_snapshot",
]
