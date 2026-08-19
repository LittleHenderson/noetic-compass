"""CAS-Ohm quantifier package (CAS-Ohm 1.0 monograph reconciliation).

WORKING DRAFT / RING 4 / NOT LICENSED / HELD.  Every quantity is a design score,
calibration value, or observed rating under one calibration profile produced by
tested software — NOT a voltmeter reading from a brain or a language model.
Proposed-not-validated instrument.  See quantifiers.py module docstring for the
full honesty rule and chapter citations (ch05, ch06, ch07, ch08, ch10).
"""

from .quantifiers import (
    # headline quantifiers
    delta_current,
    r_hidden,
    maturity_q4,
    # response model + constraint discipline
    i_pred,
    y_hat,
    r_total,
    r_cap,
    # classification + overlay
    Region,
    Outcome,
    AsomLabel,
    asom,
    # admissible trend (ch08:rule:trend)
    admissible_trend,
    TrendTag,
    TrendVerdict,
    InadmissibleTrendError,
    # eligibility gate
    check_eligibility,
    require_eligible,
    Eligibility,
    EligibilityError,
    # result / trace dataclasses
    DeltaCurrent,
    RHidden,
    CensoredResult,
    MaturityQ4,
    CjtQRecord,
    # typed-kind discipline
    Score,
    ResistanceRole,
    SignReading,
    Band,
    Trend,
    KindError,
    # constants
    RESIDUAL_METHOD_IDENTITY,
    R_HIDDEN_PROBE_SHORTLIST,
    R_HIDDEN_NAME_OVERRIDE_NOTE,
    WITHDRAWN_CAUSAL_IDENTITY_NOTE,
)

__all__ = [
    "delta_current", "r_hidden", "maturity_q4",
    "i_pred", "y_hat", "r_total", "r_cap",
    "Region", "Outcome", "AsomLabel", "asom",
    "admissible_trend", "TrendTag", "TrendVerdict", "InadmissibleTrendError",
    "check_eligibility", "require_eligible", "Eligibility", "EligibilityError",
    "DeltaCurrent", "RHidden", "CensoredResult", "MaturityQ4", "CjtQRecord",
    "Score", "ResistanceRole", "SignReading", "Band", "Trend", "KindError",
    "RESIDUAL_METHOD_IDENTITY", "R_HIDDEN_PROBE_SHORTLIST",
    "R_HIDDEN_NAME_OVERRIDE_NOTE", "WITHDRAWN_CAUSAL_IDENTITY_NOTE",
]
