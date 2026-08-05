"""Non-bypassable research boundary for the isolated PCBA v8 candidate."""

from __future__ import annotations


class BoundaryError(ValueError):
    """Raised when an artifact attempts to claim authority it cannot have."""


RESEARCH_CLAIM = (
    "Typed research reference only; no runtime-safety, model-behavior, "
    "telemetry, certification, compliance, or production claim is licensed."
)


class ResearchBoundary:
    """Stateless fixed boundary whose fields cannot be overwritten.

    The class deliberately has no instance storage.  Even
    ``object.__setattr__`` therefore cannot mutate the exported singleton or an
    artifact boundary into an accepted, licensed, disclosed, or certified
    state.
    """

    __slots__ = ()

    def __init__(
        self,
        admission_ring: int = 4,
        status: str = "OPEN",
        license_status: str = "NOT LICENSED",
        disclosure_status: str = "HELD",
        safety_certified: bool = False,
        telemetry_authorized: bool = False,
        regulatory_authority: bool = False,
        claim: str = RESEARCH_CLAIM,
    ) -> None:
        valid = (
            type(admission_ring) is int
            and admission_ring == 4
            and type(status) is str
            and status == "OPEN"
            and type(license_status) is str
            and license_status == "NOT LICENSED"
            and type(disclosure_status) is str
            and disclosure_status == "HELD"
            and safety_certified is False
            and telemetry_authorized is False
            and regulatory_authority is False
            and type(claim) is str
            and claim == RESEARCH_CLAIM
        )
        if not valid:
            raise BoundaryError(
                "research artifacts are fixed at Ring 4 / OPEN / NOT LICENSED / "
                "HELD with no safety, telemetry, or regulatory authority"
            )

    @property
    def admission_ring(self) -> int:
        return 4

    @property
    def status(self) -> str:
        return "OPEN"

    @property
    def license_status(self) -> str:
        return "NOT LICENSED"

    @property
    def disclosure_status(self) -> str:
        return "HELD"

    @property
    def safety_certified(self) -> bool:
        return False

    @property
    def telemetry_authorized(self) -> bool:
        return False

    @property
    def regulatory_authority(self) -> bool:
        return False

    @property
    def claim(self) -> str:
        return RESEARCH_CLAIM

    def to_dict(self) -> dict[str, object]:
        require_research_boundary(self)
        return {
            "admission_ring": 4,
            "status": "OPEN",
            "license_status": "NOT LICENSED",
            "disclosure_status": "HELD",
            "safety_certified": False,
            "telemetry_authorized": False,
            "regulatory_authority": False,
            "claim": RESEARCH_CLAIM,
        }

    def __repr__(self) -> str:
        return "ResearchBoundary(Ring4, OPEN, NOT LICENSED, HELD)"

    def __eq__(self, other: object) -> bool:
        return type(other) is ResearchBoundary

    def __hash__(self) -> int:
        return hash((4, "OPEN", "NOT LICENSED", "HELD", RESEARCH_CLAIM))


def require_research_boundary(value: object) -> ResearchBoundary:
    if type(value) is not ResearchBoundary:
        raise BoundaryError("artifact boundary must be an exact ResearchBoundary")
    if (
        value.admission_ring != 4
        or value.status != "OPEN"
        or value.license_status != "NOT LICENSED"
        or value.disclosure_status != "HELD"
        or value.safety_certified is not False
        or value.telemetry_authorized is not False
        or value.regulatory_authority is not False
        or value.claim != RESEARCH_CLAIM
    ):
        raise BoundaryError("artifact boundary failed fixed research revalidation")
    return value


def fixed_research_boundary() -> ResearchBoundary:
    return ResearchBoundary()


RESEARCH_BOUNDARY = ResearchBoundary()
