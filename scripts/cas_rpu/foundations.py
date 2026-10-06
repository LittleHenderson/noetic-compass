"""The Foundation Engine Bank — seven engines, twenty-eight channels.

This is the ambition half of the processor. It decides *what is worth
pursuing* and *in which register that pursuit is expressed*. It does not decide
what is true; see `LAW_2` and the firewall in `runtime.py`.

Notation, and why it is not `TF5b`
-----------------------------------
An earlier sketch of this bank proposed a `TF1..TF7` / `DF1..DF7` split with
worlds `a,b,c,d`, on the reading that the TKS Foundations and the CAS Drive
rails are different objects that must not be blended. The observation behind it
is factually right -- canonical TKS F6 is *Wealth* while CAS F6 is *Structure*,
and TKS F7 is *Continuation* while CAS F7 is *Purpose*. The conclusion is
wrong, because the repository already resolves the divergence by position:

    "CAS Drive names are authoritative. Where TKS labels use different
     nomenclature, the mapping is by position in the 7-Foundation sequence,
     not by label. TKS-specific labels ... are never carried into the CAS v7.5
     expression."
                    -- docs/reference/tks_28_foundations_translation_key.md:41

And the four Worlds are the four **Registers**, not four Domains:

    |T Transcendent = 1st World,  |A Analytical = 2nd,
    |f Affective    = 3rd World,  |E Embodied   = 4th
                    -- the same file, "Register-to-World correspondence"

confirmed by the shipped compiler's `VALID_REGISTERS = ("T","A","f","E")`
(`noetic-compass-scaffold/noetic-compass/api/notation/compiler.py:73`) and its
`SubFoundations` meta-set of 28 members spelled `F5|A`.

So a `TF5b` production would have been a *third* spelling -- `F5b` (TKS),
`F5|A` (compiler), `TF5b` (sketch) -- for one position, in a design whose own
first rule warns against symbolic soup. This module uses `F5|A`.

(One in-repo inconsistency is left standing rather than silently picked: the
offline terminal's glossary calls the 28 "7 x 4 Domains". The translation key
and CLAUDE.md's v7.5 section both say Registers, and Registers is what is
implemented here.)

Measurement kind
----------------
Every number in this module is a DESIGN VALUE in the sense of the research
paper's section 2.2 -- "declared by a board or profile, not measured". A
`Recipe`'s coefficients in particular are declared, and carry no empirical
claim about any real system.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

# The load-bearing constitutional rule, quoted where it is enforced.
LAW_2 = (
    "The Foundations generate ambition, route attention, and define what "
    "outcomes matter. They must not manufacture the truth used to justify "
    "those outcomes."
)


class FoundationError(ValueError):
    """A profile, recipe, or reference that cannot be constructed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class Drive(str, Enum):
    """The seven Drives. `Foundation` is a synonym for `Drive` in CAS."""

    F1 = "F1"  # Unity
    F2 = "F2"  # Wisdom
    F3 = "F3"  # Vitality
    F4 = "F4"  # Connection  (self-dual centre)
    F5 = "F5"  # Agency
    F6 = "F6"  # Structure
    F7 = "F7"  # Purpose


class Register(str, Enum):
    """The four Registers. These are the four Worlds, secularised."""

    T = "T"  # Transcendent -- 1st World, high abstraction, purpose-orienting
    A = "A"  # Analytical   -- 2nd World, explicit, sequential, reason-based
    f = "f"  # Affective    -- 3rd World, value-laden, feeling-toned
    E = "E"  # Embodied     -- 4th World, sensorimotor, concrete


DRIVE_NAMES: dict[Drive, str] = {
    Drive.F1: "Unity",
    Drive.F2: "Wisdom",
    Drive.F3: "Vitality",
    Drive.F4: "Connection",
    Drive.F5: "Agency",
    Drive.F6: "Structure",
    Drive.F7: "Purpose",
}

REGISTER_NAMES: dict[Register, str] = {
    Register.T: "Transcendent",
    Register.A: "Analytical",
    Register.f: "Affective",
    Register.E: "Embodied",
}

#: Drive inversion pairs. F4 is self-dual.
INVERSION_PAIRS: tuple[tuple[Drive, Drive], ...] = (
    (Drive.F1, Drive.F7),
    (Drive.F2, Drive.F6),
    (Drive.F3, Drive.F5),
)


def subfoundation(drive: Drive, register: Register) -> str:
    """`F5|A`. The canonical spelling of one of the 28 sub-Foundations."""
    return f"{drive.value}|{register.value}"


def parse_subfoundation(ref: str) -> tuple[Drive, Register]:
    """Inverse of `subfoundation`. `F5|A` -> (F5, Register.A)."""
    text = ref.strip()
    if "|" not in text:
        raise FoundationError("E-FDN-001", f"{ref!r} is not an F<k>|<R> reference")
    left, _, right = text.partition("|")
    try:
        drive = Drive(left.upper())
        register = Register(right)  # case-sensitive: |f and |E are distinct
    except ValueError as exc:
        raise FoundationError("E-FDN-001", f"{ref!r} is not an F<k>|<R> reference") from exc
    return drive, register


#: All 28, in canonical order.
SUBFOUNDATIONS: tuple[str, ...] = tuple(
    subfoundation(d, r) for d in Drive for r in Register
)
assert len(SUBFOUNDATIONS) == 28


# ---- the state vector ------------------------------------------------------

@dataclass(frozen=True)
class FoundationProfile:
    """The State Vector S: current activation of each of the 28 primitives.

    Two different normalisations, deliberately:

      `g[k]`     in [0,1], INDEPENDENT across Drives. All seven may run hot at
                 once -- they are not competing for one finite pool, and
                 forcing them to sum to 1 would assert a scarcity the sources
                 never claim and make "ambitious across the board"
                 unrepresentable.

      `q[k][R]`  sums to 1 WITHIN each Drive. The four Registers are how one
                 engine's output is distributed, so here the constraint is
                 real: a Drive cannot spend more than itself.

    `activation(k, R) = g[k] * q[k][R]`.
    """

    g: dict[Drive, float]
    q: dict[Drive, dict[Register, float]]
    tolerance: float = 1e-9

    def __post_init__(self) -> None:
        for drive in Drive:
            if drive not in self.g:
                raise FoundationError("E-FDN-002", f"{drive.value} missing from g")
            level = self.g[drive]
            if not (0.0 <= level <= 1.0):
                raise FoundationError("E-FDN-003", f"g[{drive.value}]={level} outside [0,1]")
            if drive not in self.q:
                raise FoundationError("E-FDN-004", f"{drive.value} missing from q")
            share = self.q[drive]
            for register in Register:
                if register not in share:
                    raise FoundationError(
                        "E-FDN-004", f"q[{drive.value}] missing register |{register.value}"
                    )
                if share[register] < 0:
                    raise FoundationError(
                        "E-FDN-005", f"q[{drive.value}][|{register.value}] is negative"
                    )
            total = math.fsum(share[r] for r in Register)
            if abs(total - 1.0) > self.tolerance:
                raise FoundationError(
                    "E-FDN-006",
                    f"q[{drive.value}] sums to {total}, not 1; the four Registers "
                    "distribute one Drive's activation",
                )

    def activation(self, drive: Drive, register: Register) -> float:
        return self.g[drive] * self.q[drive][register]

    def channels(self) -> dict[str, float]:
        """All 28 activations, keyed `F1|T` .. `F7|E`."""
        return {
            subfoundation(d, r): self.activation(d, r) for d in Drive for r in Register
        }

    def dominant(self) -> str:
        lanes = self.channels()
        return max(sorted(lanes), key=lambda ref: lanes[ref])

    def drive_totals(self) -> dict[Drive, float]:
        """Activation summed over Registers -- the seven rail levels."""
        return {d: math.fsum(self.q[d][r] for r in Register) * self.g[d] for d in Drive}

    def inversion_imbalance(self) -> dict[str, float]:
        """|a - b| for each Drive inversion pair. F4 is self-dual and omitted.

        Reported, not enforced. A large imbalance is an inversion-axis signal
        the caller may act on; this bank does not gate on it.
        """
        totals = self.drive_totals()
        return {
            f"{a.value}<->{b.value}": abs(totals[a] - totals[b])
            for a, b in INVERSION_PAIRS
        }


def uniform_profile(**levels: float) -> FoundationProfile:
    """Each named Drive spread evenly over its four Registers.

    `uniform_profile(F5=0.9, F7=0.95)` -- unnamed Drives sit at 0.0.
    """
    g: dict[Drive, float] = {d: 0.0 for d in Drive}
    for name, value in levels.items():
        try:
            g[Drive(name.upper())] = value
        except ValueError as exc:
            raise FoundationError("E-FDN-007", f"{name!r} is not a Drive") from exc
    q = {d: {r: 0.25 for r in Register} for d in Drive}
    return FoundationProfile(g=g, q=q)


def focused_profile(ref: str, level: float, *, spread: float = 0.1) -> FoundationProfile:
    """One sub-Foundation carries the goal; its siblings keep `spread` each.

    `focused_profile("F2|A", 0.9)` -- an analytical Wisdom ambition.
    """
    drive, register = parse_subfoundation(ref)
    if not (0.0 <= level <= 1.0):
        raise FoundationError("E-FDN-003", f"level={level} outside [0,1]")
    if not (0.0 <= spread < 1.0 / 3.0):
        raise FoundationError(
            "E-FDN-008",
            f"spread={spread} must be in [0, 1/3) so the target keeps the majority",
        )
    g = {d: 0.0 for d in Drive}
    g[drive] = level
    q = {d: {r: 0.25 for r in Register} for d in Drive}
    q[drive] = {r: (1.0 - 3.0 * spread if r is register else spread) for r in Register}
    return FoundationProfile(g=g, q=q)


def reasoning_profile(level: float = 0.9, *, register: Register = Register.A) -> FoundationProfile:
    """The default ambition of a processor built to reason.

    A profile spiked entirely on one lane cannot produce a deduction: the
    recipe also needs Structure to hold a chain together and Purpose to keep
    going, and a single-lane ambition supplies neither. So the default carries
    Wisdom at `level` with Structure and Purpose behind it, all leaning on the
    analytical register.

    The resulting limiting reagent is `F2|A` -- Wisdom itself -- which is the
    correct bottleneck for a reasoning task and a useful thing for the trace to
    say.
    """
    if not (0.0 <= level <= 1.0):
        raise FoundationError("E-FDN-003", f"level={level} outside [0,1]")
    support = 0.6 * level
    g = {d: 0.0 for d in Drive}
    g[Drive.F2] = level
    g[Drive.F6] = support
    g[Drive.F7] = support
    lean = {r: (0.7 if r is register else 0.1) for r in Register}
    q = {d: {r: 0.25 for r in Register} for d in Drive}
    for drive in (Drive.F2, Drive.F6, Drive.F7):
        q[drive] = dict(lean)
    return FoundationProfile(g=g, q=q)


# ---- recipes: what an outcome actually requires -----------------------------

@dataclass(frozen=True)
class Recipe:
    """A v7.6 production recipe over sub-Foundation primitives.

        Theta(Omega) = a1*X1 + a2*X2 + ... + an*Xn -> Omega

    An earlier sketch wrote this routing as a bare arrow -- "F5|A routes
    toward Wisdom + Agency + Structure" -- with the proportions left out.
    Without coefficients the bank cannot compute a bottleneck, which is the
    one thing it exists to do, so the coefficients are mandatory here.

    Coefficients are DESIGN VALUES. They say what a unit of this outcome is
    declared to require, not what any measured system consumes.
    """

    target: str
    coefficients: dict[str, float]

    def __post_init__(self) -> None:
        if not self.coefficients:
            raise FoundationError("E-FDN-009", f"{self.target}: a recipe needs prerequisites")
        for ref, weight in self.coefficients.items():
            parse_subfoundation(ref)
            if weight <= 0:
                raise FoundationError(
                    "E-FDN-010",
                    f"{self.target}: coefficient for {ref} is {weight}; a prerequisite "
                    "with non-positive weight is not a prerequisite",
                )

    def theoretical_yield(self, profile: FoundationProfile) -> float:
        """Y_T = min_i(x_i / a_i) over the recipe's prerequisites."""
        lanes = profile.channels()
        return min(lanes[ref] / weight for ref, weight in self.coefficients.items())

    def limiting_reagent(self, profile: FoundationProfile) -> str:
        """The prerequisite whose ratio bottlenecks the yield.

        Ties break by canonical order so the answer is deterministic. This is
        NOT lacunarity: it identifies what is *insufficient relative to the
        required ratio*, among prerequisites that are present.
        """
        lanes = profile.channels()
        return min(
            sorted(self.coefficients),
            key=lambda ref: lanes[ref] / self.coefficients[ref],
        )

    def excess_capacity(self, profile: FoundationProfile) -> dict[str, float]:
        """What each prerequisite has left over once the bottleneck binds."""
        lanes = profile.channels()
        yield_t = self.theoretical_yield(profile)
        return {
            ref: lanes[ref] - yield_t * weight
            for ref, weight in self.coefficients.items()
        }

    @staticmethod
    def efficiency(actual: float, theoretical: float) -> float:
        """eta = Y_A / Y_T, clamped into [0,1]."""
        if theoretical <= 0:
            return 0.0
        return max(0.0, min(1.0, actual / theoretical))

    def __str__(self) -> str:
        terms = " + ".join(
            f"{w:g}*{ref}" for ref, w in sorted(self.coefficients.items())
        )
        return f"Theta({self.target}) = {terms} -> {self.target}"


#: Declared recipes for the reasoning outcomes this processor produces.
#: Read as: a unit of this outcome requires these primitives in these
#: proportions. Design values, and deliberately few -- one per outcome the
#: runtime can actually reach.
REASONING_RECIPES: dict[str, Recipe] = {
    # Landing a deduction is analytical Wisdom, carried by enough Purpose to
    # keep going and enough Structure to hold the chain together.
    "deduction": Recipe("deduction", {"F2|A": 1.0, "F7|A": 0.3, "F6|A": 0.2}),
    # Admitting a gap costs Wisdom to notice it and Purpose to prefer the
    # admission over a guess.
    "honest_abstention": Recipe("honest_abstention", {"F2|A": 0.6, "F7|T": 0.4}),
    # Acting on a conclusion recruits Agency in the embodied register.
    "action": Recipe("action", {"F5|E": 1.0, "F6|E": 0.4, "F7|T": 0.2}),
}


# ---- the 28-lane consequence profile ---------------------------------------

@dataclass(frozen=True)
class Consequence:
    """What one candidate does to the 28 channels.

    Not a scalar utility. The point of carrying 28 lanes is that a plan can
    advance one Drive while damaging another, and collapsing that into a single
    reward number destroys exactly the information this bank exists to supply.
    """

    candidate: str
    effects: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for ref in self.effects:
            parse_subfoundation(ref)  # raises E-FDN-001 on a bad key

    def advanced(self, threshold: float = 0.0) -> tuple[str, ...]:
        return tuple(sorted(r for r, v in self.effects.items() if v > threshold))

    def damaged(self, threshold: float = 0.0) -> tuple[str, ...]:
        return tuple(sorted(r for r, v in self.effects.items() if v < -threshold))

    def weighted(self, profile: FoundationProfile) -> float:
        """Scalarise ONLY against a stated profile, and only at the very end.

        The weighting is the profile's own activations, so the number means
        "how much this candidate serves *these* ambitions", not "how good this
        candidate is". Two profiles rank the same candidates differently, which
        is the intended behaviour.
        """
        lanes = profile.channels()
        return math.fsum(lanes[ref] * value for ref, value in self.effects.items())
