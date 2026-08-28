"""The CJT engine: Cause | Bias => Effect with controlled gain.

A Cognitive Junction Transition (CJT) is the primitive transformation of
the CAS reasoning machine. A cause strikes a bias substrate; the junction
transforms it into an effect at a controlled gain, with a cutoff region
(no firing below threshold), an active region (linear amplification), and
a saturation region (bounded output).

Two laws are enforced here structurally (CAS-RR spec Ch. 9):

1. There is no bias-free CJT. Every config must reference a typed bias.
2. Gain is not truth. Decomposition and inference stages run at unity gain
   (beta = 1.0); constructing an evaluation CJT with any other gain is a
   constitution error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ontology import GAIN_CANDIDATE, GAIN_COMMIT, GAIN_EVAL, GAIN_LEARN


class ConstitutionError(Exception):
    """Raised when a configuration violates a load-bearing law."""


@dataclass(frozen=True)
class BiasRef:
    """Typed reference to a bias cell in the constitution's bias bank."""
    label: str          # e.g. memory_bias, charter_bias, goal_bias
    noetic: str         # e.g. ^5
    domain: str         # P / C / E / O
    drive: str          # F1..F7
    register: str       # T / A / f / E


@dataclass(frozen=True)
class CJTConfig:
    label: str
    noetic: str         # ^8 candidate | ^6 decompose | ^9 infer | ^4 commit | ^7 learn
    domain: str
    drive: str
    register: str
    role: str           # generate | decompose | infer | commit | learn
    beta: float
    cutoff: float
    sat: float
    breakdown: float    # input drive at which the junction enters breakdown
    bias: BiasRef

    def __post_init__(self) -> None:
        # The gain laws are enforced at construction, not at call time.
        validate_config(self)


@dataclass
class CJTProbe:
    """A test point on the junction. Parent totals never replace child probes."""
    tick: int
    cjt_label: str
    role: str
    cause: float
    bias: float
    beta: float
    output: float
    region: str
    parent_probe_id: Optional[str] = None

    def to_dict(self):
        return {
            "tick": self.tick,
            "cjt": self.cjt_label,
            "role": self.role,
            "cause": round(self.cause, 4),
            "bias": round(self.bias, 4),
            "beta": self.beta,
            "output": round(self.output, 4),
            "region": self.region,
            "parent_probe_id": self.parent_probe_id,
        }


@dataclass
class CJTResult:
    value: float
    region: str   # cutoff | active | saturation
    probe: CJTProbe


GAIN_BY_ROLE = {
    "generate": GAIN_CANDIDATE,
    "decompose": GAIN_EVAL,
    "infer": GAIN_EVAL,
    "commit": GAIN_COMMIT,
    "learn": GAIN_LEARN,
}


def make_config(
    label: str,
    noetic: str,
    domain: str,
    drive: str,
    register: str,
    role: str,
    bias: BiasRef,
    cutoff: float = 0.2,
    sat: float = 0.95,
    beta: Optional[float] = None,
) -> CJTConfig:
    if beta is None:
        beta = GAIN_BY_ROLE[role]
    cfg = CJTConfig(label=label, noetic=noetic, domain=domain, drive=drive,
                    register=register, role=role, beta=beta, cutoff=cutoff,
                    sat=sat, breakdown=sat + 0.25, bias=bias)
    validate_config(cfg)
    return cfg


def validate_config(cfg: CJTConfig) -> None:
    if cfg.beta <= 0.0:
        raise ConstitutionError(f"CJT {cfg.label}: gain must be positive, got {cfg.beta}")
    if not (0.0 <= cfg.cutoff < cfg.sat <= 1.0):
        raise ConstitutionError(f"CJT {cfg.label}: need 0 <= cutoff < sat <= 1")
    if not (cfg.sat < cfg.breakdown):
        raise ConstitutionError(f"CJT {cfg.label}: need sat < breakdown")
    if cfg.role in ("decompose", "infer") and cfg.beta != GAIN_EVAL:
        raise ConstitutionError(
            f"CJT {cfg.label}: evaluation stage ({cfg.role}) must run at unity gain "
            f"beta={GAIN_EVAL}; got {cfg.beta}. Gain is not truth."
        )


def transfer(
    cause: float,
    bias: float,
    cfg: CJTConfig,
    tick: int = 0,
    parent_probe_id: Optional[str] = None,
) -> CJTResult:
    """Transform a cause against a bias substrate at the config's gain."""
    if bias < 0.0:
        raise ConstitutionError(f"CJT {cfg.label}: negative bias is not a valid substrate")
    input_level = cause * bias
    if input_level < cfg.cutoff:
        region, output = "cutoff", 0.0
    else:
        raw = cfg.beta * input_level
        if raw >= cfg.breakdown:
            # Fourth operating region: overdriven beyond the safe area.
            region, output = "breakdown", cfg.sat
        elif raw > cfg.sat:
            region, output = "saturation", cfg.sat
        else:
            region, output = "active", raw
    probe = CJTProbe(tick=tick, cjt_label=cfg.label, role=cfg.role, cause=cause,
                     bias=bias, beta=cfg.beta, output=output, region=region,
                     parent_probe_id=parent_probe_id)
    return CJTResult(value=output, region=region, probe=probe)
