"""Authenticated eligibility: the axis self-generated evidence can never satisfy.

The live-readiness checklist aggregates checks whose evidence the app itself
computes - ledger files it wrote, movement streams it recorded, demo receipts
it collected. Those roll up into STRUCTURAL COMPLETENESS: "the packet is
locally whole." No volume of that evidence establishes AUTHENTICATED
ELIGIBILITY: "an external authority attests this system may trade real money."
An operator who triples the minimum self-generated evidence is exactly as
ineligible as one with none, because the two axes read disjoint evidence
classes.

This module is the second axis. Its design rules, in order of importance:

1. NO WRITE PATH. ``authenticated_eligibility()`` reads no config, no
   environment, no runtime file, no override store. Its result changes only
   when a human edits ``REQUIRED_ATTESTATIONS`` in this file to wire a real
   external verifier - a reviewed code diff, not a data write. This is
   deliberate: any data-driven path here would let accumulation (or a
   persuadable process) drift the axis.

2. FAIL CLOSED, PER ATTESTATION. Every required attestation must positively
   verify; anything else - unwired, erroring, ambiguous - counts as not
   attested.

3. DISJOINT FROM THE STRUCTURAL AXIS. Nothing in this module may consult the
   structural checklist, and the checklist may consume this module's verdict
   only as an opaque boolean+reasons. No summing across the axes.

The three attestations named here are the external authorities the live
eligibility checklist already lists as open: a live (non-demo) broker account
attested by the broker's own API, an external counsel review record, and an
independent timestamp/WORM anchor for the evidence chain. Each is currently
NOT WIRED and therefore False.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ELIGIBILITY_CLAIM_BOUNDARY = (
    "Authenticated eligibility reports whether EXTERNAL authorities attest that "
    "live trading may be enabled. It is not satisfiable by any quantity of "
    "self-generated evidence, cannot be set by config, environment, or runtime "
    "state, and does not itself place orders or move money."
)

NOT_WIRED = "NOT_WIRED"
ATTESTED = "ATTESTED"
REFUSED = "REFUSED"


def _not_wired(reason: str) -> Callable[[], bool]:
    def verify() -> bool:
        return False

    verify.__doc__ = reason
    return verify


@dataclass(frozen=True)
class Attestation:
    """One externally-attested requirement.

    ``verify`` must return True only on positive confirmation from the named
    external authority. Wiring a real verifier is a code change to this file.
    """

    attestation_id: str
    authority: str
    requirement: str
    verify: Callable[[], bool]

    def evaluate(self) -> dict[str, object]:
        try:
            attested = bool(self.verify())
        except Exception as exc:  # any verifier failure is a refusal, not a pass
            attested = False
            status = REFUSED
            detail = f"verifier raised {type(exc).__name__}: {exc}"
        else:
            if attested:
                status = ATTESTED
            elif (
                self.attestation_id in _NOT_WIRED_DOCS
                and self.verify.__doc__ == _NOT_WIRED_DOCS[self.attestation_id]
            ):
                status = NOT_WIRED
            else:
                # A wired verifier that returns False is a refusal - including
                # custom attestations with no docstring (None == None must not
                # read as "not wired").
                status = REFUSED
            detail = self.verify.__doc__ or ""
        return {
            "attestation_id": self.attestation_id,
            "authority": self.authority,
            "requirement": self.requirement,
            "status": status,
            "attested": attested,
            "detail": detail,
        }


_NOT_WIRED_DOCS = {
    "broker_live_account": (
        "No broker-API verifier is wired. Requires the broker's own API "
        "attesting a funded, live (non-demo) account bound to the configured "
        "login/server."
    ),
    "external_counsel_review": (
        "No counsel-record verifier is wired. Requires a counsel review record "
        "whose artifact hash is confirmed against the external reviewer's copy, "
        "not only the local file."
    ),
    "independent_evidence_anchor": (
        "No independent anchor verifier is wired. Requires the evidence chain "
        "head to be anchored with an external timestamp authority or WORM "
        "store; the local hash chain cannot attest itself."
    ),
}

REQUIRED_ATTESTATIONS: tuple[Attestation, ...] = (
    Attestation(
        attestation_id="broker_live_account",
        authority="broker API",
        requirement="Funded live (non-demo) broker account bound to the configured login/server.",
        verify=_not_wired(_NOT_WIRED_DOCS["broker_live_account"]),
    ),
    Attestation(
        attestation_id="external_counsel_review",
        authority="external counsel",
        requirement="Counsel review record confirmed against the reviewer's own copy.",
        verify=_not_wired(_NOT_WIRED_DOCS["external_counsel_review"]),
    ),
    Attestation(
        attestation_id="independent_evidence_anchor",
        authority="timestamp authority / WORM store",
        requirement="Evidence chain head anchored outside this machine.",
        verify=_not_wired(_NOT_WIRED_DOCS["independent_evidence_anchor"]),
    ),
)


def evaluate_authenticated_eligibility() -> dict[str, object]:
    """Evaluate the authenticated axis. Pure: no config, env, or runtime reads.

    Returns ``eligible`` (the AND across all required attestations - False
    whenever any is unwired, refused, or failing) plus the per-attestation
    records and the reasons the axis is not satisfied.
    """
    records = [attestation.evaluate() for attestation in REQUIRED_ATTESTATIONS]
    reasons = tuple(
        f"{r['attestation_id']}: {r['status']} - {r['detail']}"
        for r in records
        if not r["attested"]
    )
    return {
        "report_kind": "cas_forex_authenticated_eligibility",
        "eligible": not reasons and bool(records),
        "attestations": records,
        "reasons_not_eligible": reasons,
        "no_drift_invariant": (
            "No quantity of self-generated evidence can change this verdict; "
            "it changes only when an external verifier is wired by code change "
            "and positively attests."
        ),
        "claim_boundary": ELIGIBILITY_CLAIM_BOUNDARY,
    }
