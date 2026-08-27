"""Deterministic CJT simulator — Stage 1 of the CCB-R1 test program.

Semantics are taken from the source documents, not invented here:

  I     = V / R_total                     Quantification Guide p.12
  E*    = β · I                           Quantification Guide p.12
  ΔI    = I_obs − I_pred                  Quantification Guide p.12
  R_eq  = Σ R_k            (series)       Quantification Guide p.14
  1/R_eq= Σ 1/R_k          (parallel)     Quantification Guide p.14
  β_eq  = Π β_k            (cascade)      Quantification Guide pp.13-14

Operating regions, from CAS PCBA Engineer:
  cutoff      "faint signals fall under the cutoff floor and produce no effect"
  active      "amplifying its cause→effect transition predictably"
  saturation  "saturation only latches a stage that has already fired"
  breakdown   "its output flips to its involution pair, a ^2 Positive
               collapsing into ^3 Negative under overload"

SCALE IS DELIBERATELY EXPLICIT. The handbook constrains
`sat ∈ (0,1] and cutoff ∈ [0,1) — both live on the open simplex`, while the
guide's worked example on p.12 runs sat=8.5 with I=4.0. Those are different
normalizations. That is Preserved Conflict 3.1 (scale and saturation) in
`CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json`, and this module refuses to
silently pick a side: every spec declares its Scale and is validated against it.

This simulator produces BOUNDED SOFTWARE EVIDENCE only. Per the research paper,
synthetic boards "validate software behavior only; they are not experiments on a
live model and cannot establish causal or empirical validity." Nothing here is a
research packet and nothing here is authenticated evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Scale(str, Enum):
    """Which normalization a spec's thresholds live on (Preserved Conflict 3.1)."""

    UNIT = "unit"      # handbook: sat ∈ (0,1], cutoff ∈ [0,1), open simplex
    DESIGN = "design"  # guide p.12 worked example: design-scale quantities


class Region(str, Enum):
    CUTOFF = "cutoff"
    ACTIVE = "active"
    SATURATION = "saturation"
    BREAKDOWN = "breakdown"


class CjtError(ValueError):
    """A CJT that cannot be constructed. Carries the source's diagnostic code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class CjtSpec:
    """One Cognitive Junction Transistor stage.

    `bias` is mandatory — there is no bias-free CJT (E-CJT-001 MissingBias).
    `bias_domain` and `target_domain` are single letters from PCEO when given;
    a bias lower in precedence than its target is E-CJT-008 CjtCrossDomainBias.
    """

    label: str
    beta: float
    cutoff: float
    sat: float
    bias: str | None = None
    scale: Scale = Scale.UNIT
    bias_domain: str | None = None
    target_domain: str | None = None

    _PRECEDENCE = {"P": 0, "C": 1, "E": 2, "O": 3}

    def __post_init__(self) -> None:
        if self.bias is None or not str(self.bias).strip():
            raise CjtError("E-CJT-001", f"{self.label}: a CJT requires a bias")

        if not math.isfinite(self.beta) or self.beta < 0:
            raise CjtError("E-CJT-005", f"{self.label}: beta must be finite and >= 0")

        if self.sat <= self.cutoff:
            # "sat>cutoff so the active region is non-empty"
            raise CjtError(
                "E-CJT-003",
                f"{self.label}: sat={self.sat} <= cutoff={self.cutoff}; "
                "the active region would be empty and the stage can never fire",
            )

        if self.scale is Scale.UNIT:
            # Handbook: "sat ∈ (0,1] and cutoff ∈ [0,1) ... sat=0 or cutoff=1 is rejected"
            if not (0 < self.sat <= 1):
                raise CjtError(
                    "E-CJT-004", f"{self.label}: sat={self.sat} outside (0,1] on the unit scale"
                )
            if not (0 <= self.cutoff < 1):
                raise CjtError(
                    "E-CJT-004", f"{self.label}: cutoff={self.cutoff} outside [0,1) on the unit scale"
                )

        if self.bias_domain and self.target_domain:
            bd = self._PRECEDENCE.get(self.bias_domain)
            td = self._PRECEDENCE.get(self.target_domain)
            if bd is None or td is None:
                raise CjtError("E-CJT-002", f"{self.label}: bias/target domain must be one of PCEO")
            if bd > td:
                raise CjtError(
                    "E-CJT-008",
                    f"{self.label}: bias in {self.bias_domain} governs a "
                    f"{self.target_domain}-domain target, against P>C>E>O descent",
                )


@dataclass(frozen=True)
class Reading:
    """What a probe at this stage's test point reports."""

    label: str
    v: float
    r_total: float
    i_pred: float
    e_star: float
    region: Region
    i_obs: float | None = None
    delta_i: float | None = None
    aligned: bool | None = None
    warnings: tuple[str, ...] = ()


def r_series(*resistances: float) -> float:
    """Sequential constraints add. Guide p.14."""
    if not resistances:
        raise ValueError("r_series requires at least one resistance")
    return math.fsum(resistances)


def r_parallel(*resistances: float) -> float:
    """Parallel conductances add. Guide p.14."""
    if not resistances:
        raise ValueError("r_parallel requires at least one resistance")
    if any(r <= 0 for r in resistances):
        raise ValueError("parallel branch resistances must be > 0")
    return 1.0 / math.fsum(1.0 / r for r in resistances)


def beta_cascade(*betas: float) -> float:
    """Amplification along an active series path multiplies. Guide pp.13-14."""
    if not betas:
        raise ValueError("beta_cascade requires at least one beta")
    return math.prod(betas)


def measure(
    spec: CjtSpec,
    v: float,
    r_total: float,
    *,
    i_obs: float | None = None,
    tolerance: float = 0.5,
    breakdown_at: float | None = None,
) -> Reading:
    """Forward measurement of one stage. Guide p.12.

    `tolerance` defaults to the +/-0.5 band used in the guide's worked example.
    `breakdown_at`, when given, is the overload point past which the effect flips
    to its involution pair rather than merely clamping.
    """
    if r_total <= 0:
        raise CjtError("E-CJT-006", f"{spec.label}: R_total must be > 0")

    i_pred = v / r_total
    e_star = spec.beta * i_pred
    warnings: list[str] = []

    if breakdown_at is not None and e_star >= breakdown_at:
        region = Region.BREAKDOWN
        warnings.append("W-CJT-006 CjtBreakdown: effect flips to its involution pair")
    elif i_pred <= spec.cutoff:
        region = Region.CUTOFF
        warnings.append("E-CJT-003 CjtCutoff: stage is silent; faint causes produce no effect")
    elif e_star >= spec.sat:
        region = Region.SATURATION
        e_star = spec.sat  # "stronger causes do nothing"
        warnings.append("W-CJT-004 CjtSaturation: stage is latched at sat")
    else:
        region = Region.ACTIVE

    delta_i = aligned = None
    if i_obs is not None:
        delta_i = i_obs - i_pred
        aligned = abs(delta_i) <= tolerance
        if not aligned:
            warnings.append(
                f"W-CJT-005 ResidualOutOfBand: dI={delta_i:+.3f} exceeds +/-{tolerance}"
            )

    return Reading(
        label=spec.label,
        v=v,
        r_total=r_total,
        i_pred=i_pred,
        e_star=e_star,
        region=region,
        i_obs=i_obs,
        delta_i=delta_i,
        aligned=aligned,
        warnings=tuple(warnings),
    )


def cascade(stages: list[tuple[CjtSpec, float, float]]) -> list[Reading]:
    """Run a multi-stage cascade. Guide p.13.

    Each stage is (spec, V, R_total). The guide is explicit that a cascade is
    NOT a wire carrying one conserved current: "activation can be amplified,
    attenuated, saturated, or reshaped at each stage. Therefore read I locally
    at TP1, TP2, TP3." Each stage is therefore measured against its own V and R,
    and every stage returns its own reading. A stage in cutoff yields no effect,
    so the cascade stops there.
    """
    readings: list[Reading] = []
    for spec, v, r_total in stages:
        reading = measure(spec, v, r_total)
        readings.append(reading)
        if reading.region is Region.CUTOFF:
            break
    return readings
