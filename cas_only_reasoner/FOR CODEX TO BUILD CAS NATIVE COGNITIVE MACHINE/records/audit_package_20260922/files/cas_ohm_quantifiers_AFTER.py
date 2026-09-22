"""CAS-Ohm quantifier module — the three headline quantifiers plus the
surrounding discipline that makes them usable and honest.

MONOGRAPH HONESTY RULE (read this first, in spirit verbatim)
------------------------------------------------------------
Every quantity produced here is a DESIGN SCORE, a CALIBRATION VALUE, or an
OBSERVED RATING recorded under a single calibration profile by tested
software.  NONE of it is a voltmeter reading from a brain or from a language
model.  The electrical vocabulary (current, resistance, breakdown, overload)
is a MODELLING ANALOGY: it names structural roles, it does not assert that any
deployed system was measured.  Units are MODEL units (ALPHA, ACTIVATION,
ALPHA_PER_ACTIVATION, Q10, ...); volt / ampere / ohm are forbidden aliases and
never appear.

STATUS: WORKING DRAFT.  This is a PROPOSED-NOT-VALIDATED instrument.  Its whole
content is RING 4 / NOT LICENSED / HELD — a data contract plus a registered
hypothesis with an implemented guard apparatus, NOT an established law.  No
live calibration exists; every worked number in the sources and in the tests is
FABRICATED for exposition.  Passing tests is evidence about code<->spec, never
about spec<->world (V&V separation, ch06:328-379).

Sources reconciled into this module (CAS-Ohm 1.0 monograph,
docs/whitepapers/monograph/cas_ohm1/chapters/):
  * ch05_calibration.tex   — calibration profile, I_FS methods, tolerances,
                             currency assertion, region enumeration.
  * ch06_response_model.tex — the response model y_hat = a / r_eff, the
                             admissibility rule, anti-circularity, resistance
                             role typing, the REJECTED legacy form I=V/R_total.
  * ch07_classification.tex — Region axis, Outcome axis, the derived-only ASOM
                             overlay, the fail-closed no-diagnosis gate, the 16
                             typed quantity kinds.
  * ch08_quantization.tex   — exact Q10 normalization, the half-open Q1..Q4
                             bands with cut points 2.5 / 5 / 7.5, overload.
  * ch10_residuals.tex      — the residual delta_y = y_obs - y_pred, censoring
                             at a zero-compatible observation, NON-IDENTIFICATION
                             (a residual sign ranks probes, never a mechanism).

CAVEATS on constructs the owner asked for that are NOT in the extracted
chapters (ch05/06/07/08/10) and had to be sourced from the broader design:
  * R_total = R_cap + R_policy + R_context + R_resource additive decomposition
    is NOT in ch05/06.  There R_total appears ONLY inside the REJECTED legacy
    form I_pred = V/R_total (ch06:48).  Implemented here per the owner's
    named contract; flagged as extra-chapter.
  * R_cap(P_cap) capability->resistance inversion with R_min/R_max bounds is
    NOT in ch05/06/07/08/10.  Implemented per the owner's named contract as a
    monotone-decreasing inversion; flagged as extra-chapter.
These two are provided because the owner named them as required callables; they
are marked in their docstrings as extra-chapter so no reader mistakes them for
reconciled monograph text.

NAMING-OVERRIDE DISCLOSURE (r_hidden / RHidden)
-----------------------------------------------
ch10 states the candidate "does NOT expose R_hidden = V/I_obs - R_known as a
diagnostic" and places hidden-resistance vocabulary on the forbidden-wording
list for EMITTED quantities.  The monograph's own neutral name for the same
arithmetic is the RESISTANCE_DELTA = a/y_obs - r_eff, emitted uncensored-only,
with r_apparent = a/y_obs tagged role APPARENT_SAME_SAMPLE.  The owner named a
HEADLINE quantifier ``r_hidden`` and DELIBERATELY overrides the ch10
forbidden-wording rule for that one caller-facing symbol.  The override is
disclosed here and in-code (WITHDRAWN_CAUSAL_IDENTITY_NOTE,
R_HIDDEN_NAME_OVERRIDE_NOTE) so no reader takes the name ``r_hidden`` as
monograph-reconciled: the SUBSTANCE is monograph-faithful (role
APPARENT_SAME_SAMPLE, identifies_mechanism=False, censored at zero-compatible
observation), only the caller-facing NAME departs from ch10, by owner decision.
The neutral monograph field name ``resistance_delta`` is exposed alongside
``magnitude`` on the result so downstream code can use the reconciled vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from enum import Enum
from typing import Optional, Sequence, Union

getcontext().prec = 50  # generous precision for pre-rounding band comparisons

Number = Union[int, float, Decimal]

# Method identity stamped on every residual (ch10:rule:nonident).
RESIDUAL_METHOD_IDENTITY = "CAS-OHM-V1-NONIDENTIFYING-RESIDUAL"

# Default tolerances (profile-bound in the real instrument; these are neutral
# module defaults for standalone use, NOT universal constants).
DEFAULT_ALIGN_TOL = 0.05          # delta_abs analogue for delta_current sign
DEFAULT_ZERO_COMPAT_EPS = 1e-9    # |i_obs| <= eps => zero-compatible => censor
DEFAULT_TREND_TOL = 0.0           # minimum effect for maturity_q4 trend tag


# ---------------------------------------------------------------------------
# Enumerations (ch05:504-517, ch07:def:region / ch07:def:outcome / ch07:def:asom)
# ---------------------------------------------------------------------------

class Region(Enum):
    """Axis 1 — SHAPE of the local dose-response curve (ch07:def:region).

    UNASSESSED is the honest default and does NOT imply ACTIVE-by-default.
    Only ACTIVE admits a diagnostic.
    """
    UNASSESSED = "UNASSESSED"
    CUTOFF = "CUTOFF"
    ACTIVE = "ACTIVE"
    SATURATION = "SATURATION"
    BREAKDOWN = "BREAKDOWN"
    NON_OHMIC = "NON_OHMIC"
    UNSTABLE = "UNSTABLE"


class Outcome(Enum):
    """Axis 2 — DIRECTION of the response (ch07:def:outcome).

    INTENDED binds to the REGISTERED direction only; it does NOT imply
    appropriate magnitude or endorsement.
    """
    UNASSESSED = "UNASSESSED"
    INTENDED = "INTENDED"
    OPPOSITE = "OPPOSITE"
    OFF_AXIS = "OFF_AXIS"


class AsomLabel(Enum):
    """Derived display overlay (ch07:def:asom).  NEVER a primitive."""
    STARVED = "STARVED"
    ALIGNED = "ALIGNED"
    OVERSATURATED = "OVERSATURATED"
    MISALIGNED = "MISALIGNED"


class ResistanceRole(Enum):
    """Resistance role typing (ch06:107-141)."""
    CALIBRATED_HELD_OUT = "CALIBRATED_HELD_OUT"   # only prediction-admissible role
    APPARENT_SAME_SAMPLE = "APPARENT_SAME_SAMPLE"  # a/y — barred from prediction
    NETWORK_EQUIVALENT = "NETWORK_EQUIVALENT"
    DESIGN_PROPOSAL = "DESIGN_PROPOSAL"            # declared value, never admissible


class SignReading(Enum):
    """Directional reading of the residual delta_I (ch10 non-identification).

    NEUTRAL DIRECTIONAL LABELS ONLY.  ch10:rule:nonident forbids mechanism
    vocabulary ("opposition", "amplification", "bypass", "hidden") in any
    EMITTED quantity: "the residual sign ranks probes, never a mechanism."  An
    earlier draft emitted HIDDEN_OPPOSITION / EXCESS_AMPLIFICATION on this field,
    which imported exactly the forbidden mechanism reading even though
    identifies_mechanism=False sat alongside.  These are renamed to purely
    directional terms — they describe WHICH WAY the observation missed the
    prediction, nothing about why.
    """
    WITHIN_TOLERANCE = "WITHIN_TOLERANCE"  # |delta_I| <= tolerance (zero-compatible)
    UNDERSHOOT = "UNDERSHOOT"              # delta_I < -tolerance (observed below prediction)
    OVERSHOOT = "OVERSHOOT"               # delta_I >  tolerance (observed above prediction)


class Band(Enum):
    """Q4 maturity bands (ch08:def:bands)."""
    Q1 = "Q1"  # [0, 2.5)
    Q2 = "Q2"  # [2.5, 5)
    Q3 = "Q3"  # [5, 7.5)
    Q4 = "Q4"  # [7.5, inf)


class Trend(Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    WANING = "WANING"


# ---------------------------------------------------------------------------
# Typed-kind discipline (ch07 appA:sec:quantity) — light enforcement.
#
# A Score (Q10/Q100 scale) must NEVER occupy the resistance position in a
# prediction.  We give Score a distinct wrapper type so a resistance argument
# can reject it structurally, encoding the audit's conflict that no score kind
# may sit where an EFFECTIVE_RESISTANCE belongs.
# ---------------------------------------------------------------------------

class KindError(TypeError):
    """Raised when a score is passed where a resistance (or vice-versa) belongs."""


@dataclass(frozen=True)
class Score:
    """A scored level (DRIVE_SCORE / CAPABILITY_SCORE / CONSTRAINT_SCORE ...),
    unit Q10 or Q100.  A Score is NOT a resistance and NOT a dose; it carries a
    distinct type precisely so it cannot silently occupy a resistance slot.
    """
    value: float
    unit: str = "Q10"

    def __post_init__(self) -> None:
        hi = 10.0 if self.unit == "Q10" else (100.0 if self.unit == "Q100" else None)
        if hi is None:
            raise KindError(f"Score unit must be Q10 or Q100, got {self.unit!r}")
        if not (0.0 <= float(self.value) <= hi):
            raise ValueError(f"{self.unit} score out of range [0,{hi}]: {self.value}")


def _is_finite(x: float) -> bool:
    import math
    return math.isfinite(x)


def _as_resistance(name: str, r: Number) -> float:
    """Coerce a resistance argument, rejecting Score wrappers and non-positive
    values (EFFECTIVE_RESISTANCE is strictly positive — ch06:54-60)."""
    if isinstance(r, Score):
        raise KindError(
            f"{name}: a {r.unit} Score cannot occupy the resistance position "
            f"(ALPHA_PER_ACTIVATION); a constraint SCORE in the denominator is a "
            f"type error, not a smaller numeric error (ch06:47-52)."
        )
    rf = float(r)
    if not _is_finite(rf):
        raise ValueError(
            f"{name}: effective resistance must be a finite number; got {rf!r}. "
            f"An undefined quantity is refused with a reason, never carried into "
            f"arithmetic as NaN or infinity (ch10:def:censoring). NaN in particular "
            f"would pass a strictly-positive test, because NaN compares False "
            f"against every operator."
        )
    if rf <= 0.0:
        raise ValueError(
            f"{name}: effective resistance must be strictly positive "
            f"(non-positive rejected before arithmetic, ch06:54-60): {rf}"
        )
    return rf


# ---------------------------------------------------------------------------
# Constraint decomposition and the response model.
# ---------------------------------------------------------------------------

def r_total(r_cap: Number, r_policy: Number,
            r_context: Number, r_resource: Number) -> float:
    """R_total = R_cap + R_policy + R_context + R_resource.

    EXTRA-CHAPTER: this additive decomposition is NOT present in ch05/ch06.
    There R_total occurs ONLY inside the REJECTED legacy form I_pred=V/R_total
    (ch06:48).  Implemented here per the owner's named contract.  Each component
    is a resistance term (ALPHA_PER_ACTIVATION); Score wrappers are rejected and
    the sum must be strictly positive.
    """
    parts = {
        "r_cap": r_cap, "r_policy": r_policy,
        "r_context": r_context, "r_resource": r_resource,
    }
    total = 0.0
    for name, val in parts.items():
        if isinstance(val, Score):
            raise KindError(
                f"r_total: component {name} is a {val.unit} Score; a score cannot "
                f"be summed into a resistance total (ch07 quantity-kind rule)."
            )
        component = float(val)
        if not _is_finite(component):
            raise ValueError(
                f"r_total: component {name} must be a finite number; got "
                f"{component!r} (ch10:def:censoring)."
            )
        total += component
    if not _is_finite(total):
        raise ValueError(
            f"r_total: the sum of the four constraint terms overflowed to "
            f"{total!r}; a non-finite total is refused rather than carried "
            f"into a prediction (ch10:def:censoring)."
        )
    if total <= 0.0:
        raise ValueError(f"r_total must be strictly positive, got {total}")
    return total


def r_cap(p_cap: Number, r_min: float, r_max: float) -> float:
    """Capability -> resistance inversion:  R_cap(P_cap).

    EXTRA-CHAPTER: the P_cap symbol, the R_cap(.) inversion, and the R_min/R_max
    bounds are NOT in ch05/06/07/08/10.  Implemented per the owner's named
    contract as a MONOTONE-DECREASING linear inversion of a capability score:

        R_cap = R_max - (P_cap / 10) * (R_max - R_min)

    so a null capability (P_cap=0) yields the maximal resistance R_max and a
    maxed capability (P_cap=10, Q10 top) yields the minimal resistance R_min.
    More capability -> less resistance.  P_cap is a Q10 CAPABILITY_SCORE; a
    Score wrapper is accepted here (this is the one place a score is the input),
    but the OUTPUT is a resistance and is clamped to [R_min, R_max].
    """
    if isinstance(p_cap, Score):
        if p_cap.unit != "Q10":
            raise KindError("r_cap expects a Q10 CAPABILITY_SCORE")
        p = float(p_cap.value)
    else:
        p = float(p_cap)
    if not (0.0 < r_min <= r_max):
        raise ValueError(
            f"r_cap bounds require 0 < r_min <= r_max, got r_min={r_min}, r_max={r_max}")
    if not (0.0 <= p <= 10.0):
        raise ValueError(f"p_cap must be a Q10 score in [0,10], got {p}")
    r = r_max - (p / 10.0) * (r_max - r_min)
    # numerical clamp into the declared bounds
    return max(r_min, min(r_max, r))


def i_pred(v: Number, r_total_value: Number) -> float:
    """Predicted response  i_pred = v / r_total  — the candidate's repair of the
    legacy form I=V/R_total (ch06:47-52).  Mapped into candidate types this is
    y_hat = a / r_eff with r_eff the calibrated bridge quantity (and NOTHING
    else).  v is the ALPHA dose; r_total_value is ALPHA_PER_ACTIVATION and must
    be strictly positive.  A Score in the denominator is refused as a type error.
    """
    r = _as_resistance("i_pred", r_total_value)
    vf = float(v)
    if not _is_finite(vf):
        raise ValueError(
            f"i_pred: drive must be a finite number; got {vf!r}. An undefined "
            f"quantity is refused with a reason, never emitted (ch10:def:censoring)."
        )
    return vf / r


# Alias with the monograph's own symbol names for the response model.
def y_hat(a: Number, r_eff: Number) -> float:
    """y_hat = a / r_eff  (THE response model, ch06:5-7, ch06:36).

    Asserted, AS A HYPOTHESIS not a fact, to approximate the observed response
    within the profile's declared tolerances.  r_eff strictly positive.
    """
    return i_pred(a, r_eff)


# ---------------------------------------------------------------------------
# HEADLINE QUANTIFIER 1 — delta_current (the residual delta_I).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeltaCurrent:
    """Result of delta_current.  delta_i = i_obs - i_pred, in ACTIVATION units,
    quantity kind FLOW_RESIDUAL (ch10)."""
    value: float
    sign: SignReading
    tolerance: float
    region: Region
    # NON-IDENTIFICATION contract (ch10:rule:nonident): this is False, always.
    identifies_mechanism: bool = False
    method_identity: str = RESIDUAL_METHOD_IDENTITY
    note: str = (
        "The SIGN of this residual ranks which follow-up PROBE to spend the next "
        "measurement budget on.  It NEVER identifies a hidden cause, policy, or "
        "bypass: at least seven mechanisms (hidden facilitation, constraint "
        "bypass, opposition elsewhere, measurement error, model misspecification, "
        "calibration-transfer failure, sampling fluctuation) reproduce any given "
        "sign and are observationally equivalent."
    )


def delta_current(i_obs: Number, i_pred_value: Number,
                  tolerance: float = DEFAULT_ALIGN_TOL,
                  region: Region = Region.ACTIVE) -> DeltaCurrent:
    """delta_I = I_obs - I_pred — the residual, with a directional sign reading.

    Sign readings (NEUTRAL DIRECTION ONLY — no mechanism vocabulary):
        WITHIN_TOLERANCE  |delta_I| <= tolerance    (residual is zero-compatible)
        UNDERSHOOT        delta_I < -tolerance       (observed below prediction)
        OVERSHOOT         delta_I >  tolerance        (observed above prediction)

    NON-IDENTIFICATION DISCIPLINE (ch10:rule:nonident, ch10:sec:goodfor):
    the returned sign is ordinal evidence for ALLOCATING further measurement —
    it ranks follow-up PROBES only.  It does NOT, and the record explicitly
    refuses to, identify a generating mechanism.  The labels name a DIRECTION of
    discrepancy (below vs above prediction), never a cause — mechanism words
    ("opposition", "amplification", "bypass") are barred from the emitted label
    by ch10:rule:nonident.  The dataclass field ``identifies_mechanism`` is fixed
    False for exactly this reason.

    ACTIVE-REGION-ONLY precondition (ch06:63-68, ch10 active-region gate): a
    residual is only computable when the dose-response region is ACTIVE.  A
    non-ACTIVE region raises EligibilityError — saturated / flat / unassessed
    residuals are UNCOMPUTABLE, not merely inadvisable.
    """
    if region is not Region.ACTIVE:
        raise EligibilityError(
            f"delta_current refuses to run in region {region.value}: a residual is "
            f"admissible ONLY in the ACTIVE region (ch06:63-68). Silence is the "
            f"default; a missing precondition is a typed rejection, not a degraded "
            f"diagnostic."
        )
    tol = abs(float(tolerance))
    delta = float(i_obs) - float(i_pred_value)
    if delta < -tol:
        sign = SignReading.UNDERSHOOT
    elif delta > tol:
        sign = SignReading.OVERSHOOT
    else:
        sign = SignReading.WITHIN_TOLERANCE
    return DeltaCurrent(value=delta, sign=sign, tolerance=tol, region=region)


# ---------------------------------------------------------------------------
# HEADLINE QUANTIFIER 2 — r_hidden (with censoring).
# ---------------------------------------------------------------------------

# The probe shortlist an r_hidden magnitude can direct a budget toward.  This is
# a list of THINGS TO PROBE, not a list of identified causes.
R_HIDDEN_PROBE_SHORTLIST = (
    "capability",
    "policy",
    "context",
    "resource",
    "miswired-branch",
)

WITHDRAWN_CAUSAL_IDENTITY_NOTE = (
    "The candidate does NOT expose R_hidden as a proof of a hidden constraint. "
    "r_apparent = v / i_obs carries role APPARENT_SAME_SAMPLE — the very role the "
    "prediction gate REFUSES as input. A positive value is NOT read as a 'bypass' "
    "or 'hidden resistance proven'; that reading is on the forbidden-wording list "
    "regardless of any future outcome (ch10:rule:nonident, ch10:tab:tensions). "
    "The magnitude only ranks which of the shortlisted probes to run next."
)

# The caller-facing name ``r_hidden`` overrides ch10's forbidden-wording rule by
# OWNER DECISION for the headline quantifier only; the emitted substance stays
# monograph-faithful.  The monograph's neutral name for this quantity is
# RESISTANCE_DELTA (= a/y_obs - r_eff), also exposed on the result.
R_HIDDEN_NAME_OVERRIDE_NOTE = (
    "NAME OVERRIDE: the symbol 'r_hidden' / 'RHidden' is an owner-chosen headline "
    "name that deliberately departs from ch10, which bans hidden-resistance "
    "vocabulary in emitted quantities. It is NOT monograph-reconciled wording. The "
    "reconciled neutral name for this exact arithmetic is RESISTANCE_DELTA = "
    "a/y_obs - r_eff (role APPARENT_SAME_SAMPLE, uncensored-only); use the "
    "'resistance_delta' field for the monograph vocabulary."
)


@dataclass(frozen=True)
class RHidden:
    """Uncensored r_hidden result.  magnitude = V/I_obs - R_known, unit
    ALPHA_PER_ACTIVATION, role APPARENT_SAME_SAMPLE (quarantined).

    ``magnitude`` and ``resistance_delta`` are the SAME number; the second is the
    monograph's neutral name (RESISTANCE_DELTA = a/y_obs - r_eff).  The type name
    'RHidden' is an owner-chosen headline override of ch10 (see
    ``name_override_note``); the substance is monograph-faithful.
    """
    magnitude: float
    r_apparent: float          # v / i_obs
    r_known: float
    role: ResistanceRole = ResistanceRole.APPARENT_SAME_SAMPLE
    probe_shortlist: Sequence[str] = R_HIDDEN_PROBE_SHORTLIST
    identifies_mechanism: bool = False
    causal_identity_note: str = WITHDRAWN_CAUSAL_IDENTITY_NOTE
    name_override_note: str = R_HIDDEN_NAME_OVERRIDE_NOTE

    @property
    def resistance_delta(self) -> float:
        """Monograph-neutral name for ``magnitude`` (= a/y_obs - r_eff)."""
        return self.magnitude


@dataclass(frozen=True)
class CensoredResult:
    """Typed censored result (ch10:def:censoring).  Structurally cannot carry a
    resistance estimate; carries an explicit reason instead of an empty slot."""
    marker: str
    reason: str
    censored: bool = True
    identifies_mechanism: bool = False


def r_hidden(v: Number, i_obs: Number, r_known: Number,
             zero_compat_eps: float = DEFAULT_ZERO_COMPAT_EPS,
             i_obs_interval: Optional[Sequence[Number]] = None
             ) -> Union[RHidden, CensoredResult]:
    """R_hidden = V / I_obs - R_known — the 'hidden resistance' quantity, kept
    quarantined.  (Caller-facing name is an owner override of ch10; the emitted
    substance is monograph-faithful — see R_HIDDEN_NAME_OVERRIDE_NOTE.)

    CENSORING (ch10:def:censoring, ch10:ex:censored).  The MONOGRAPH rule censors
    on the OBSERVATION UNCERTAINTY INTERVAL: refuse the ratio quantities iff the
    interval's lower bound <= 0 (it includes or touches zero).  This module has
    no first-class interval arithmetic, so it supports censoring two ways:

      * INTERVAL mode (monograph-faithful) — pass ``i_obs_interval=(lo, hi)`` and
        the ratio is CENSORED iff lo <= 0 (interval includes/touches zero),
        exactly as ch10:def:censoring specifies, independent of the point value.
      * POINT mode (simplified fallback, used when no interval is given) — the
        ratio is censored iff |I_obs| <= eps (a point-and-epsilon proxy for the
        interval rule).  This is correct in spirit but cannot honor a tight
        interval that excludes zero at a tiny point value, nor an interval that
        touches zero at a point far from zero.  The gap is disclosed here.

    When censored, r_hidden returns a typed CensoredResult carrying the marker
    OBSERVED_INTERVAL_INCLUDES_ZERO and an explicit reason string.  Rationale: a
    ratio V/I_obs with a zero-compatible denominator has no finite moments and no
    usable interval (0.1 -> 40, 0.01 -> 400 from data the instrument cannot
    distinguish from silence).  Absence-by-censoring is never an empty slot.

    On an admissible I_obs it returns an RHidden carrying:
      * magnitude = V/I_obs - R_known (also exposed as ``resistance_delta``),
      * r_apparent = V/I_obs tagged role APPARENT_SAME_SAMPLE (the role the
        prediction gate refuses as input),
      * the probe shortlist {capability, policy, context, resource,
        miswired-branch} — things to PROBE, not causes identified,
      * the withdrawn-causal-identity note and identifies_mechanism = False.

    Worked check (fabricated, ch10 spirit): V=8, R_known=2, I_obs=2 ->
    R_hidden = 8/2 - 2 = 2.
    """
    r_known = _as_resistance("r_hidden(r_known)", r_known)
    vf = float(v)
    if not _is_finite(vf):
        raise ValueError(
            f"r_hidden: drive must be a finite number; got {vf!r}. An undefined "
            f"quantity is refused with a reason, never emitted (ch10:def:censoring). "
            f"The drive is the value the caller applied, so a non-finite drive is a "
            f"caller error rather than an observation too uncertain to support a "
            f"conclusion, and it raises rather than censoring."
        )

    # INTERVAL mode — monograph-faithful censoring on lower_bound <= 0.
    if i_obs_interval is not None:
        try:
            lo = float(i_obs_interval[0])
            hi = float(i_obs_interval[1])
        except (TypeError, ValueError, IndexError):
            return CensoredResult(
                marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
                reason="i_obs_interval is malformed / non-numeric; ratio v/i_obs "
                       "unrepresentable, resistance estimate censored.",
            )
        if not (_is_finite(lo) and _is_finite(hi)):
            return CensoredResult(
                marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
                reason=f"i_obs_interval=({lo},{hi}) is non-finite; ratio censored.",
            )
        if lo <= 0.0:
            return CensoredResult(
                marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
                reason=(
                    f"observation interval [{lo}, {hi}] includes or touches zero "
                    f"(lower bound <= 0); the ratio v/i_obs has no finite moments "
                    f"and no usable interval, so apparent resistance and resistance "
                    f"delta are CENSORED (ch10:def:censoring). The residual itself "
                    f"remains computable; only the ratio quantity is refused."
                ),
            )

    try:
        i = float(i_obs)
    except (TypeError, ValueError):
        return CensoredResult(
            marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
            reason="i_obs is undefined / not a finite number; ratio v/i_obs "
                   "unrepresentable, resistance estimate censored.",
        )
    # POINT mode fallback (only when no admissible interval was supplied).
    if i_obs_interval is None and (not _is_finite(i) or abs(i) <= abs(float(zero_compat_eps))):
        return CensoredResult(
            marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
            reason=(
                f"i_obs={i} is zero-compatible (|i_obs| <= {zero_compat_eps}); the "
                f"ratio v/i_obs has no finite moments and no usable interval, so the "
                f"apparent resistance and any resistance delta are CENSORED "
                f"(ch10:def:censoring). The residual itself remains computable "
                f"elsewhere; only the ratio quantity is refused."
            ),
        )
    if not _is_finite(i):
        return CensoredResult(
            marker="OBSERVED_INTERVAL_INCLUDES_ZERO",
            reason=f"i_obs={i} is non-finite; ratio v/i_obs censored.",
        )
    r_apparent = float(v) / i
    return RHidden(
        magnitude=r_apparent - r_known,
        r_apparent=r_apparent,
        r_known=r_known,
    )


# ---------------------------------------------------------------------------
# HEADLINE QUANTIFIER 3 — maturity_q4 (half-open banding + trend).
# ---------------------------------------------------------------------------

# Exact cut points as rationals (ch08:def:bands): 5/2, 5, 15/2.
_CUT_1 = Decimal(5) / Decimal(2)    # 2.5
_CUT_2 = Decimal(5)                 # 5
_CUT_3 = Decimal(15) / Decimal(2)   # 7.5


@dataclass(frozen=True)
class MaturityQ4:
    """Result of maturity_q4.  band from the PRE-ROUNDING exact value; trend
    from prev_i_q when supplied."""
    band: Band
    i_q_exact: str            # decimal string of the pre-rounding value
    trend: Optional[Trend] = None
    minimum_effect: float = DEFAULT_TREND_TOL


def _to_decimal(x: Number) -> Decimal:
    if isinstance(x, Decimal):
        return x
    # str() route preserves the human-entered pre-rounding value exactly.
    return Decimal(str(x))


def _band_of(exact: Decimal) -> Band:
    """Guarded cascade in exact arithmetic, first STRICT-inequality wins; cut
    points assigned UPWARD (equality fails '<' and falls to the upper band).
    Top band [7.5, inf) has NO upper test — overloaded values band Q4."""
    if exact < _CUT_1:      # [0, 2.5)
        return Band.Q1
    if exact < _CUT_2:      # [2.5, 5)
        return Band.Q2
    if exact < _CUT_3:      # [5, 7.5)
        return Band.Q3
    return Band.Q4          # [7.5, inf)


def maturity_q4(i_q: Number, prev_i_q: Optional[Number] = None,
                minimum_effect: float = DEFAULT_TREND_TOL) -> MaturityQ4:
    """I_Q maturity band Q1..Q4 on the HALF-OPEN cut points 2.5 / 5 / 7.5, read
    off the PRE-ROUNDING decimal value (ch08:def:bands), plus a trend tag.

    Bands (left-closed, cut points assigned upward):
        [0, 2.5)  -> Q1     [2.5, 5)  -> Q2
        [5, 7.5)  -> Q3     [7.5, inf) -> Q4

    Classification reads the exact (pre-rounding) value, never a rounded
    display: 7.499 is Q3, 7.5 is Q4; every value in [2.495, 2.5) is Q1 even
    though a 2-decimal display renders 2.50.  Banding divides by nothing from
    the observation side, so a zero i_q bands Q1 without censoring.

    Trend tag (from prev_i_q, computed on exact values):
        RISING   i_q - prev > minimum_effect
        WANING   prev - i_q > minimum_effect
        STABLE   |i_q - prev| <= minimum_effect
    prev_i_q=None -> trend is None (no comparison declared).

    IMPORTANT — this convenience trend is NOT the ADMISSIBLE ch08 trend.  It
    enforces ONLY the minimum-effect component and (with the default
    minimum_effect=0.0) treats any nonzero delta as a trend.  ch08:rule:trend
    requires an ADMISSIBLE tag to declare all four of axis + interval +
    minimum-effect + uncertainty rule and to use interval NON-OVERLAP; a tag
    missing any component is INADMISSIBLE, not degraded.  For that discipline use
    ``admissible_trend(...)`` below, which fails closed when any component is
    absent.  This point trend is a display mnemonic only.
    """
    exact = _to_decimal(i_q)
    band = _band_of(exact)
    trend: Optional[Trend] = None
    if prev_i_q is not None:
        prev = _to_decimal(prev_i_q)
        diff = exact - prev
        me = _to_decimal(abs(float(minimum_effect)))
        if diff > me:
            trend = Trend.RISING
        elif -diff > me:
            trend = Trend.WANING
        else:
            trend = Trend.STABLE
    return MaturityQ4(
        band=band,
        i_q_exact=format(exact.normalize(), "f"),
        trend=trend,
        minimum_effect=abs(float(minimum_effect)),
    )


# ---------------------------------------------------------------------------
# Admissible trend tag (ch08:rule:trend) — all-or-nothing declaration.
# ---------------------------------------------------------------------------

class TrendVerdict(Enum):
    """ch08:rule:trend verdict vocabulary (distinct from the maturity display
    Trend).  NO_TREND is the honest default when the evidence does not clear
    both the interval-non-overlap AND minimum-effect bars."""
    RISING = "RISING"
    FALLING = "FALLING"
    NO_TREND = "NO_TREND"


class InadmissibleTrendError(ValueError):
    """Raised when a trend tag omits any required component (axis, interval,
    minimum-effect, uncertainty rule).  A missing component makes the tag
    INADMISSIBLE, not degraded (ch08:rule:trend)."""


@dataclass(frozen=True)
class TrendTag:
    verdict: TrendVerdict
    axis: str
    minimum_effect: float
    uncertainty_rule: str


def admissible_trend(earlier_point: Number, later_point: Number, *,
                     axis: Optional[str] = None,
                     earlier_interval: Optional[Sequence[Number]] = None,
                     later_interval: Optional[Sequence[Number]] = None,
                     minimum_effect: Optional[Number] = None,
                     uncertainty_rule: str = "interval-non-overlap") -> TrendTag:
    """ADMISSIBLE trend tag per ch08:rule:trend — all-or-nothing.

    A trend tag is admissible ONLY if it declares all four:
      (i)   axis        — the typed quantity / test point / profile identity,
      (ii)  interval    — ordered replay frames, one uncertainty interval each,
      (iii) minimum_effect — a threshold fixed BEFORE comparison,
      (iv)  uncertainty_rule — how uncertainties enter (here: interval NON-OVERLAP).
    Omit ANY one and this raises InadmissibleTrendError (never a degraded tag).

    Verdict (computed on EXACT point values + intervals, never a rounded display):
        RISING   iff lower(later) > upper(earlier)  AND  (later - earlier) > minimum_effect
        FALLING  iff upper(later) < lower(earlier)  AND  (earlier - later) > minimum_effect
        NO_TREND otherwise (overlapping intervals OR sub-threshold difference).

    NOTE: no trend tag over live-model data is asserted anywhere in the monograph;
    every value here is fabricated for exposition (RING 4 / NOT LICENSED / HELD).
    """
    missing = []
    if axis is None:
        missing.append("axis")
    if earlier_interval is None or later_interval is None:
        missing.append("interval")
    if minimum_effect is None:
        missing.append("minimum-effect")
    if not uncertainty_rule:
        missing.append("uncertainty-rule")
    if missing:
        raise InadmissibleTrendError(
            "inadmissible trend tag: missing " + ", ".join(missing)
            + " (ch08:rule:trend requires axis + interval + minimum-effect + "
              "uncertainty rule; a missing component is inadmissible, not degraded)."
        )
    e_lo, e_hi = float(earlier_interval[0]), float(earlier_interval[1])
    l_lo, l_hi = float(later_interval[0]), float(later_interval[1])
    me = abs(float(minimum_effect))
    ep = float(earlier_point)
    lp = float(later_point)
    if l_lo > e_hi and (lp - ep) > me:
        verdict = TrendVerdict.RISING
    elif l_hi < e_lo and (ep - lp) > me:
        verdict = TrendVerdict.FALLING
    else:
        verdict = TrendVerdict.NO_TREND
    return TrendTag(verdict=verdict, axis=axis, minimum_effect=me,
                    uncertainty_rule=uncertainty_rule)


# ---------------------------------------------------------------------------
# ASOM derived overlay (ch07:def:asom, ch07:rule:asom-no-identity).
# ---------------------------------------------------------------------------

def asom(region: Region, outcome: Outcome) -> Optional[AsomLabel]:
    """Derived display overlay.  Partial function of the two STORED axes;
    computed on demand, stored nowhere, never writable, never consumed by any
    gate / diagnostic / claim, and NEVER a stand-in for the two axes.

    Map (ch07:def:asom):
        outcome in {OPPOSITE, OFF_AXIS}      -> MISALIGNED   (region discarded)
        outcome == INTENDED, region CUTOFF   -> STARVED
        outcome == INTENDED, region ACTIVE   -> ALIGNED
        outcome == INTENDED, region SATURATION -> OVERSATURATED
        every other pair                     -> None
    Over the 7x4 product it names 3 cells distinctly, merges 14 into MISALIGNED
    (lossy, non-invertible), and leaves 11 with no label.
    """
    if outcome in (Outcome.OPPOSITE, Outcome.OFF_AXIS):
        return AsomLabel.MISALIGNED
    if outcome is Outcome.INTENDED:
        if region is Region.CUTOFF:
            return AsomLabel.STARVED
        if region is Region.ACTIVE:
            return AsomLabel.ALIGNED
        if region is Region.SATURATION:
            return AsomLabel.OVERSATURATED
        return None
    # outcome == UNASSESSED
    return None


# ---------------------------------------------------------------------------
# Eligibility / no-diagnosis gate (ch07:rule:nodiag) — fail-closed.
# ---------------------------------------------------------------------------

class EligibilityError(RuntimeError):
    """Raised when a diagnostic is requested but a precondition fails.  Silence
    is the default; there is NO override / force / bypass path."""


@dataclass(frozen=True)
class Eligibility:
    admitted: bool
    reason: str


def check_eligibility(region: Region,
                      calibrated: bool,
                      right_model: bool,
                      stale: bool,
                      outcome: Outcome = Outcome.INTENDED) -> Eligibility:
    """Fail-closed conjunction (ch07:rule:nodiag): NO diagnostic is emitted
    unless ALL hold — region == ACTIVE, profile calibrated AND reviewed,
    right model / right profile, and NOT stale (currency assertion).  A
    semantic outcome of UNASSESSED is itself a hard no-diagnosis condition.

    Returns an Eligibility(admitted, reason).  Silence is the default: a missing
    precondition yields a typed rejection, never a degraded/warned diagnostic.
    """
    if region is not Region.ACTIVE:
        return Eligibility(False, f"region {region.value} != ACTIVE")
    if outcome is Outcome.UNASSESSED:
        return Eligibility(False, "semantic outcome UNASSESSED")
    if not calibrated:
        return Eligibility(False, "profile uncalibrated / not REVIEWED")
    if not right_model:
        return Eligibility(False, "wrong-model / wrong-profile (digest mismatch)")
    if stale:
        return Eligibility(False, "profile drift / replay-time stale (not CURRENT)")
    return Eligibility(True, "all preconditions satisfied")


def require_eligible(region: Region, calibrated: bool, right_model: bool,
                     stale: bool, outcome: Outcome = Outcome.INTENDED) -> None:
    """Raise EligibilityError unless check_eligibility admits."""
    e = check_eligibility(region, calibrated, right_model, stale, outcome)
    if not e.admitted:
        raise EligibilityError(f"no diagnostic emitted: {e.reason}")


# ---------------------------------------------------------------------------
# CjtQ trace record (object-traceability + full quantifier trace).
# ---------------------------------------------------------------------------

@dataclass
class CjtQRecord:
    """Cause->Bias->Effect quantified-trace record.

    Logs the full trace of a single CAS-Ohm assessment: the cause/bias/effect
    triple, the dose v, the constraint components and total, the prediction and
    observation, the residual, the amplification beta, the saturation reading,
    and the two classification axes at a test point.

    Object-traceability fields (id / created_at / version / source / trace_id)
    are caller-supplied.  This module NEVER calls datetime.now / uuid at import
    or construction; timestamp and id default to None so the caller controls
    provenance (project rule: object traceability + no import-time clocks).
    """
    # Cause / Bias / Effect triple
    cause: Optional[str] = None
    bias: Optional[str] = None
    effect: Optional[str] = None
    # Dose + constraint decomposition
    v: Optional[float] = None
    r_cap: Optional[float] = None
    r_policy: Optional[float] = None
    r_context: Optional[float] = None
    r_resource: Optional[float] = None
    r_total: Optional[float] = None
    # Prediction / observation / residual
    i_pred: Optional[float] = None
    i_obs: Optional[float] = None
    delta_i: Optional[float] = None
    beta: Optional[float] = None
    saturation: Optional[float] = None
    # Classification axes
    region: Optional[Region] = None
    outcome: Optional[Outcome] = None
    test_point: Optional[str] = None
    timestamp: Optional[str] = None
    # Object-traceability (caller-supplied; never generated at import)
    id: Optional[str] = None
    created_at: Optional[str] = None
    version: str = "cas-ohm-quantifiers-0.1.0-DRAFT"
    source: Optional[str] = None
    trace_id: Optional[str] = None

    @property
    def asom_label(self) -> Optional[AsomLabel]:
        """Derived-only overlay; None when either axis is missing.  Never stored,
        never a stand-in for the two axes."""
        if self.region is None or self.outcome is None:
            return None
        return asom(self.region, self.outcome)


__all__ = [
    # headline quantifiers
    "delta_current", "r_hidden", "maturity_q4",
    # response model + constraint discipline
    "i_pred", "y_hat", "r_total", "r_cap",
    # classification + overlay
    "Region", "Outcome", "AsomLabel", "asom",
    # admissible trend (ch08:rule:trend)
    "admissible_trend", "TrendTag", "TrendVerdict", "InadmissibleTrendError",
    # eligibility gate
    "check_eligibility", "require_eligible", "Eligibility", "EligibilityError",
    # result / trace dataclasses
    "DeltaCurrent", "RHidden", "CensoredResult", "MaturityQ4", "CjtQRecord",
    # typed-kind discipline
    "Score", "ResistanceRole", "SignReading", "Band", "Trend", "KindError",
    # constants
    "RESIDUAL_METHOD_IDENTITY", "R_HIDDEN_PROBE_SHORTLIST",
    "R_HIDDEN_NAME_OVERRIDE_NOTE", "WITHDRAWN_CAUSAL_IDENTITY_NOTE",
]
