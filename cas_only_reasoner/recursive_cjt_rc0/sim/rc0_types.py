"""rc0_types.py -- typed state objects for the RC-0 deterministic controller simulator.

PHASE RC-0: type, temporal, and authority repair. No neural network anywhere in this
package. CPU-only, deterministic, no randomness, no wall-clock in any state-bearing path.

The repairs this module enforces (owner directive RC-0):
  - Symbol collision fixed: the Bias tuple is (S, M, P_RPM, Z, Theta, G); RPMState is a
    distinct TYPE from Resistance, and the two cannot be confused in arithmetic or
    passed for one another (route_score type-checks).
  - ASOM typing fixed: region_posterior is Delta^3 over EXACTLY the four source-defined
    regions (cutoff/active/saturation/breakdown); response_model_status,
    stability_status, and semantic_outcome are separate enumerated fields. ASOM is a
    derived, readable dashboard -- never the authoritative stored state.
  - Actions are typed: ControlAction is an enum that RAISES on any attempt to enter
    scalar arithmetic. route_multiplier is a scalar in [0,1]. Never multiplied together
    by accident.
  - Authority fixed: BiasState is frozen (immutable). The ONLY path to a new BiasState
    is a BiasUpdateIntent committed by the TransactionCoordinator.
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------- enums / vocabularies
REGIONS = ("cutoff", "active", "saturation", "breakdown")  # source-defined, exactly four
RESPONSE_MODEL_STATUSES = ("ohmic", "non_ohmic", "unassessed")
STABILITY_STATUSES = ("stable", "unstable", "unassessed")
SEMANTIC_OUTCOMES = ("intended", "opposite", "off_axis", "unassessed")
FIRST_BLOCK_POLICY = ("DESIRE", "WISDOM", "POWER")  # frozen D -> W -> P check order

COMPUTE_UNIT = "CJT_EXPERT_EVALUATION"  # frozen single unit for the first experiment


_IMMUTABLE_LEAVES = (str, int, float, bool, bytes, type(None))


def _deeply_immutable(name, v):
    """RC-0.3 ALLOW-LIST: state-bearing values may contain ONLY canonical immutable
    leaves, tuples/frozensets of them, or enum members. Arbitrary custom objects are
    rejected even inside tuples (a frozen wrapper around a mutable object is still
    mutable through that object)."""
    if isinstance(v, tuple):
        for i, x in enumerate(v):
            _deeply_immutable(f"{name}[{i}]", x)
        return v
    if isinstance(v, frozenset):
        for x in v:
            _deeply_immutable(name + "{}", x)
        return v
    if isinstance(v, bool) or isinstance(v, _IMMUTABLE_LEAVES):
        return v
    if isinstance(v, enum.Enum):
        return v
    raise TypeError(f"{name} contains {type(v).__name__}, not on the canonical "
                    "immutable allow-list (str/int/float/bool/bytes/None/tuple/frozenset/enum)")


class ControlAction(enum.Enum):
    """Typed control action. NEVER a number. Any arithmetic use raises."""

    RUN = "RUN"
    CAP = "CAP"
    SPLIT = "SPLIT"
    REPAIR = "REPAIR"
    QUARANTINE = "QUARANTINE"
    HALT = "HALT"

    def _refuse(self, *_a, **_k):
        raise TypeError(
            f"ControlAction.{self.name} is an action, not a number: "
            "control actions cannot enter scalar route arithmetic")

    __mul__ = __rmul__ = __add__ = __radd__ = __sub__ = __rsub__ = _refuse
    __truediv__ = __rtruediv__ = __neg__ = __float__ = __int__ = _refuse


class NoReadyCJT(Exception):
    """Raised when every route score is zero. Code: NO_READY_CJT."""

    code = "NO_READY_CJT"


# ---------------------------------------------------------------- RPM state (P_RPM)
@dataclass(frozen=True)
class Subgoal:
    """A typed RPM subgoal. signature identifies it for cycle detection."""

    expert_id: str
    prereq: str  # one of FIRST_BLOCK_POLICY
    depth: int

    @property
    def signature(self) -> str:
        return f"{self.expert_id}::{self.prereq}"


@dataclass(frozen=True)
class RPMState:
    """P_RPM: the prerequisite state. NOT resistance; NOT a number.

    D/W/P are independently assessable raw values (never one simplex).
    """

    desire: float
    wisdom: float
    power: float
    open_subgoals: tuple = ()
    return_addresses: tuple = ()
    acquired: tuple = ()  # cached satisfied prerequisites (one-directional, Correction 2)

    def __post_init__(self):
        for name in ("desire", "wisdom", "power"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise TypeError(f"RPMState.{name} must be a raw number, got {type(v).__name__}")
            if math.isnan(v) or math.isinf(v):
                raise ValueError(f"RPMState.{name} must be finite, got {v!r}")
            if v < 0:
                raise ValueError(f"RPMState.{name} must be >= 0")
        for name in ("open_subgoals", "return_addresses", "acquired"):
            v = getattr(self, name)
            if not isinstance(v, tuple):
                raise TypeError(f"RPMState.{name} must be a tuple")
            _deeply_immutable(f"RPMState.{name}", v)

    def _refuse(self, *_a, **_k):
        raise TypeError("RPMState is a prerequisite record, not a resistance: "
                        "it cannot enter route arithmetic")

    __mul__ = __rmul__ = __add__ = __radd__ = __truediv__ = __rtruediv__ = __float__ = _refuse


# ---------------------------------------------------------------- resistance (r)
@dataclass(frozen=True)
class Resistance:
    """r: CAS-Ohm effective route resistance. Soft terms ONLY.

    Policy is NEVER a resistance component -- it is the hard mask in Governance.
    Wisdom is NEVER a resistance component -- it is a readiness threshold only
    (RC-0 non-duplication contract). Power acts as a hard threshold in readiness and
    may modulate r_cap ABOVE threshold (registered dual role).
    """

    r_cap: float
    r_context: float
    r_resource: float

    def __post_init__(self):
        for name in ("r_cap", "r_context", "r_resource"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise TypeError(f"Resistance.{name} must be a number, got {type(v).__name__}")
            if math.isnan(v) or math.isinf(v):
                raise ValueError(f"Resistance.{name} must be finite, got {v!r}")
            if v < 0:
                raise ValueError(f"Resistance.{name} must be >= 0")

    @property
    def total(self) -> float:
        return self.r_cap + self.r_context + self.r_resource


# ---------------------------------------------------------------- operating record (Z)
@dataclass(frozen=True)
class RegionRecord:
    """Z: the authoritative two-axis operating record (factorized RC-0 typing).

    region_posterior: POSTERIOR belief over EXACTLY the four source-defined regions
    (Delta^3 = 4 entries summing to 1). 'non_ohmic' and 'unstable' are NOT regions on
    the characteristic curve -- they live in their own status fields.
    semantic_outcome is written ONLY by the verifier, never by region arithmetic.
    """

    region_posterior: tuple  # length 4, sums to 1, aligned with REGIONS
    committed_region: str    # argmax at last COMMIT; one of REGIONS or "unassessed"
    response_model_status: str = "unassessed"
    stability_status: str = "unassessed"
    semantic_outcome: str = "unassessed"

    def __post_init__(self):
        rp = self.region_posterior
        if not isinstance(rp, tuple) or len(rp) != len(REGIONS):
            raise ValueError(
                f"region_posterior must have exactly {len(REGIONS)} entries "
                f"(the four source-defined regions {REGIONS}), got "
                f"{len(rp) if isinstance(rp, tuple) else type(rp).__name__}")
        for x in rp:
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise ValueError("region_posterior entries must be non-bool numbers")
            if math.isnan(x) or math.isinf(x):
                raise ValueError(f"region_posterior entries must be finite, got {x!r}")
            if x < 0:
                raise ValueError("region_posterior entries must be nonnegative")
        if not (abs(sum(rp) - 1.0) <= 1e-9):   # NaN-safe: NaN comparison is False -> reject
            raise ValueError(f"region_posterior must sum to 1, got {sum(rp)}")
        if self.committed_region not in REGIONS + ("unassessed",):
            raise ValueError(f"unknown committed_region {self.committed_region!r}")
        if self.response_model_status not in RESPONSE_MODEL_STATUSES:
            raise ValueError(f"unknown response_model_status {self.response_model_status!r}")
        if self.stability_status not in STABILITY_STATUSES:
            raise ValueError(f"unknown stability_status {self.stability_status!r}")
        if self.semantic_outcome not in SEMANTIC_OUTCOMES:
            raise ValueError(f"unknown semantic_outcome {self.semantic_outcome!r}")

    def asom_dashboard(self) -> str:
        """DERIVED human-readable ASOM letter. Never authoritative state."""
        letter = {"cutoff": "S", "active": "A", "saturation": "O", "breakdown": "M"}
        r = self.committed_region
        return letter.get(r, "?")


# ---------------------------------------------------------------- governance (G)
@dataclass(frozen=True)
class Governance:
    """G: hard typed permissions. The mask is absolute -- never a resistance."""

    hard_mask: int  # 1 = permitted, 0 = absolutely prohibited
    quarantined: bool = False
    max_depth: int = 4
    max_branches: int = 8

    def __post_init__(self):
        if isinstance(self.hard_mask, bool) or self.hard_mask not in (0, 1):
            raise ValueError("hard_mask must be exactly int 0 or 1 (bool and weights rejected)")
        if not isinstance(self.quarantined, bool):
            raise TypeError("quarantined must be a bool")
        for name in ("max_depth", "max_branches"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int):
                raise TypeError(f"Governance.{name} must be an int (bool rejected)")
            if v < 0:
                raise ValueError(f"Governance.{name} must be >= 0")

    @property
    def effective_mask(self) -> int:
        return 0 if self.quarantined else self.hard_mask


# ---------------------------------------------------------------- the Bias (B)
@dataclass(frozen=True)
class BiasState:
    """B_{j,t} = (S, M, P_RPM, Z, Theta, G). FROZEN: no direct mutation anywhere.

    The only path to B_{j,t+1} is a BiasUpdateIntent committed by the
    TransactionCoordinator (rc0_coordinator.py).
    """

    substrate: tuple            # S: stable substrate descriptors
    memory: tuple               # M: recent history entries (bounded)
    rpm: RPMState               # P_RPM: prerequisite state
    record: RegionRecord        # Z: two-axis operating record
    theta: tuple                # Theta: transformation parameters (declared)
    governance: Governance      # G: hard permissions and limits

    def __post_init__(self):
        if not isinstance(self.rpm, RPMState):
            raise TypeError("BiasState.rpm must be an RPMState (P_RPM), not "
                            + type(self.rpm).__name__)
        if not isinstance(self.record, RegionRecord):
            raise TypeError("BiasState.record must be a RegionRecord")
        if not isinstance(self.governance, Governance):
            raise TypeError("BiasState.governance must be a Governance")
        for name in ("substrate", "memory", "theta"):
            v = getattr(self, name)
            if not isinstance(v, tuple):
                raise TypeError(f"BiasState.{name} must be a tuple")
            _deeply_immutable(f"BiasState.{name}", v)


# ---------------------------------------------------------------- update intents
@dataclass(frozen=True)
class BiasUpdateIntent:
    """The ONLY instrument by which a CJT may request a Bias change.

    A CJT emits intents; the TransactionCoordinator validates and commits them
    atomically, or rejects the whole batch. CJTs never write BiasState directly.
    """

    expert_id: str
    fld: str          # which BiasState field ('rpm','record','memory','substrate')
    new_value: object
    reason: str
    tick: int
