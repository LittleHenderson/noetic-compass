# Diagnostic numeric policy 0.2.0 — 2026-09-22

`NUMERIC_POLICY_VERSION = "cas-ohm-diagnostic-numeric/0.2.0"` identifies the
validation and threshold behavior. This is a bounded numeric repair of the
standalone diagnostic prototype, not validation of the instrument or a shared
compiler core. The unchanged residual method identity still means that a signed
residual cannot identify its cause.

Claude's finite-input guards from `86ba3d75` and `a4b2e0d7` are retained and
extended. All public call signatures and existing result field names/types stay
available. The 39 original test bodies and Claude's 12 added test bodies remain
unchanged. No compiler helper, old dataset, source snapshot or receipt is updated.

Behavior changes in 0.2.0:

- Float APIs reject non-finite inputs, conversion overflow and a nonzero declared
  Decimal that becomes zero on float conversion. Arithmetic overflow is refused
  before a numeric prediction or residual is emitted.
- Tolerances and minimum effects must be finite and nonnegative. Negative values
  are no longer silently made positive. A threshold that cannot be represented
  in the public float metadata is refused rather than displayed as zero/infinity.
  Maturity/trend results append an optional `minimum_effect_exact` string so
  the unrounded threshold survives alongside the legacy float display field.
  Existing positional fields retain their order and types.
- Invalid caller quantities raise `ValueError` with a reason; malformed trend
  evidence raises the existing `InadmissibleTrendError`. Existing `KindError`
  score/resistance checks and active-region/eligibility checks remain in place.
- Unusable observations return the existing `CensoredResult` type. New markers
  distinguish invalid intervals, points outside the interval and unrepresentable
  results. Existing zero-compatible observations retain
  `OBSERVED_INTERVAL_INCLUDES_ZERO`. No ratio of an observed zero is emitted.
- Intervals for `r_hidden` must have exactly two finite, ordered bounds and must
  contain the point before they can admit a ratio. A valid tight positive
  interval still overrides the simplified point-epsilon censoring rule.
- `maturity_q4` accepts finite nonnegative levels, including overload above ten.
  It preserves every decimal digit in `i_q_exact`; fixed-point formatting may
  retain trailing zeros. It no longer rounds a saved value into a different band.
- Maturity/trend decisions use exact Decimal values and rational differences,
  independent of the caller's Decimal precision/rounding. Import no longer
  changes global Decimal precision. Float inputs still enter through their
  shortest decimal string; this does not recover missing measurement precision.
- `admissible_trend` requires an actual nonblank axis, ordered finite intervals,
  and its implemented `interval-non-overlap` rule. Unsupported rule labels no
  longer claim an implemented method.

Signed differences remain signed. The diagnostic source permits signed
activation projections, so this repair does not import the compiler's separate
nonnegative Drive/attention/constraint contract into this API. In particular,
zero observed flow can produce a valid negative residual while its inverse ratio
is censored. Resistance stays strictly positive where the old contract required
it; the extra-chapter `r_total` contract continues to check its total rather than
invent a new per-component domain rule.

Limits retained: this module is an arithmetic prototype. The convenience
functions do not manufacture observations, calibrations, profile identity or
authorization. The separately callable eligibility gate is not a newly enforced
pipeline. `CjtQRecord` remains a caller-supplied trace container, not a validating
acceptance record. No actual model is imported or measured by these tests.
Trend intervals are checked for ordering and finiteness; this bounded repair
does not add a point-containment precondition to that separate convenience API.
The shared-core proposal must settle such adapter-specific validation explicitly.
