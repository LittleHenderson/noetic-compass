# Engineering Adversarial Checks

**Status:** DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD

**Public disclosure authorized:** No

**Canon effect:** None

**Product-claim effect:** None

## 1. Mathematical checks

### 1.1 Projector Gram-kernel normalization

For orthogonal projectors with common rank d, the proposed kernel is
K(i,j) = tr(P_i P_j) / d. The positive-rank hypothesis is necessary.

Counterexample to the engineering wording as written:

- choose any Hilbert space and P_i = 0;
- then the common finite rank is d = 0;
- tr(P_i P_j) / d = 0 / 0, which is undefined.

Disposition: the theorem remains sound for common rank d > 0, as stated in
Formal Mathematics Paper 3. Add d > 0 to the integrated engineering
dependency statement.

### 1.2 Capacity-transfer hypothesis

Formal Mathematics Paper 3 requires an isometry B: V -> W tensor V and the
adjoint intertwining identity
B*(ell_x tensor u) = sqrt(Lambda) u.

Counterexample when the intertwining condition is dropped:

- take D = d = 1;
- take two orthogonal code vectors in W;
- take both projectors equal to the identity on V;
- their projector separation is zero;
- assigning unsupported Lambda = 1 would yield the false conclusion
  2 <= 1.

Disposition: THM-PROJECTOR-CAPACITY-CAS-TRANSFER remains a proof gap for CAS.
No CAS-specific B, code family, or verified intertwining certificate is
present.

### 1.3 Same-sample resistance circularity

If apparent resistance is defined on one sample by
r_app = alpha / activation, substituting it into
activation_hat = alpha / r_app reproduces the observed activation by
construction. That is an identity, not held-out prediction.

Disposition: the draft correctly bars same-sample apparent resistance from the
predictor. Only independently calibrated, split-separated, profile-matched
parameters may enter a predictive claim.

### 1.4 Residual non-identification

The sign or magnitude of a model residual can be compatible with multiple
unobserved mechanisms. Without an explicit causal graph, intervention, and
identification argument, a residual cannot identify a hidden cause.

Disposition: residual localization remains a diagnostic hypothesis, not a
causal conclusion.

## 2. Type and unit checks

### 2.1 CAS-Ohm units

The implemented CAS-Ohm unit kinds are:

- ALPHA
- ACTIVATION
- Q10
- Q100
- ALPHA_PER_ACTIVATION
- DIMENSIONLESS
- FRACTION

Physical SI quantities are not members of this ontology. The paper sentence
that says the ontology includes “any separately declared physical SI quantity”
must be corrected. A future physical profile would need separate types,
instrumentation, calibration, authority, and review.

### 2.2 PCBA generic VOLT vocabulary

The PCBA Unit enumeration includes VOLT, and a DRC test uses it. This does
not contradict the nonphysical CAS-Ohm ontology. It does mean that the
publication must distinguish:

- “the generic PCBA modeling vocabulary can represent a value tagged VOLT”;
  from
- “a CAS quantity is demonstrated physical voltage.”

Only the first is supported. The second remains prohibited and not licensed.

### 2.3 Quantity-direction and provenance separation

CAS-Ohm keeps intervention, response, effective parameter, scale, uncertainty,
sample size, split, calibration profile, lineage, raw evidence, controls, and
missingness type-distinct. The engineering claim is supported by the bound
implementation and tests only. It does not establish empirical validity or
metrological traceability.

## 3. Interface checks

### 3.1 PCBA / CAS-Ohm separation

No audited interface automatically converts a PCBA component parameter,
signal, or test-point value into a CAS-Ohm calibrated measurement. The two
packages have distinct data models and evidence requirements.

Disposition: keep PCBA as the circuit-model grammar and CAS-Ohm as a
nonphysical response/calibration profile. Any future bridge must declare
coordinate, unit, direction, calibration, provenance, uncertainty, and
authority contracts.

### 3.2 TKS adapter

The candidate adapter admits only certified, total, finite, deterministic,
stateless, non-stochastic transition tables and binds exact kernel and PCBA
identities.

Disposition: this is a narrow software interface result. It does not license
general TKS equivalence, stateful dynamics, cognitive validity, or canon
migration.

### 3.3 Projector profile

The projector profile is type-distinct from the canonical mixed-simplex
Fisher-Rao profile and carries matrix, rank, source/basis, tolerance, and
validation residuals.

Disposition: implementation of the type does not prove that any CAS object
satisfies the capacity-transfer hypotheses. The integrated package must point
to Formal Mathematics Paper 3 as the sole theorem authority.

### 3.4 Freshness and authentication

The calibration context evaluates validity relative to caller-supplied
replay_as_of. The implementation returns false for authenticated_current and
reports missing external authority/trusted current clock evidence.

Disposition: use “replay-time-current, not authenticated-current.” Do not
describe the candidate as proving live freshness.

## 4. Engineering and counterexample checks

### 4.1 Q4 overload domain

The exact score is 10 * numerator / denominator; it is not clipped. The
displayed Q10 value is clipped to 10, and overload is preserved separately.
The classifier evaluates the exact score:

- below 2.5: Q1;
- at least 2.5 and below 5: Q2;
- at least 5 and below 7.5: Q3;
- at least 7.5, with no finite upper bound: Q4.

Concrete overload case:

- raw/full-scale ratio = 1.2;
- exact score = 12;
- displayed Q10 = 10;
- overload ratio = 1.2;
- band = Q4.

Disposition: tested behavior is coherent, but the paper’s [7.5, 10] interval
conflates clipped display with exact classifier input.

### 4.2 CCDL grammar corpus

The bound Gate 4 inventory reconfirms four direct EBNF syntax counterexamples
across the five published boards. One bounded board listing had no direct
counterexample established by this audit.

Disposition: the grammar is not corpus-complete. Parser, round-trip,
ambiguity/conformance, and independent replay obligations remain open.

### 4.3 CSB unreachable threshold

Under the published source semantics:

- the red-stage output is clamped at 0.1;
- the downstream fuse threshold is 0.9;
- therefore that path cannot cross the threshold.

The same source retains non-finite gain and incomplete latch/fail-closed
semantics.

Disposition: preserve the known-fault finding and fixture. Do not present the
board as functionally validated.

### 4.4 Feedback and resource checks

The DRC uses graph-cycle analysis, conservative declared-gain checks, and
fail-closed resource-limit behavior for the supported profile. These are
bounded implementation properties. They do not establish stability of richer,
stateful, stochastic, adaptive, delayed, or nonlinear feedback systems.

### 4.5 Memristive implementation search

Search over the manifest-bound source and tests found no implementation terms
for memristor, hysteresis, charge state, or flux state. The only memristive
material is provisional paper-level motivation and a nonphysical candidate
state equation.

Disposition: no memristive implementation, device, material mapping,
calibrated history variable, or hysteresis evidence exists. MEM-OPEN-001
remains open, not implemented, not preregistered, and not licensed.

## 5. Citation-scope check

Fourteen of the fifteen external citations support the narrow uses assigned in
the ledger. E9, QuickCheck, supports property-oriented randomized testing but
must not be used as support for mutation testing. Either add a primary
mutation-testing source or leave mutation testing as an uncited open
obligation.

None of the fifteen references is evidence that CAS/TKS claims are true, that
the software is operationally valid, or that a physical, causal, safety,
clinical, regulatory, product, or canonical conclusion has been established.

## 6. Verification boundary

The unchanged Gate 4 runner passed 208 test methods and 272 parameterized
subtests, and all declared hashes matched. That verifies only the bound
software/evidence behavior. It does not close the 20 open Gate 4 criteria or
any Gate 5 requirement.

Final state: DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD.
