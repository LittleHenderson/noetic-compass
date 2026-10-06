# Typed TKS v8 core prototype: formal specification and proof obligations v0.1

Status: `GATE 1 PROTOTYPE / IN REVIEW / NOT FROZEN`

Admission: `Ring 4`

License status: `NOT LICENSED`

This document specifies the deliberately small executable kernel in
`src/tks_v8_core`. It is an independent reference model. It does not modify,
replace, or certify the active CAS notation compiler, and it does not make a
canonical TKS v8 or empirical CAS claim.

## 1. Scope and inherited-artifact boundary

The current production compiler has value kinds such as state, drive, relation,
and program. Those kinds do not by themselves enforce categorical source and
target objects. This prototype therefore supplies a separate semantic layer
for the Gate 1 questions audited in the Project Coherence mathematical red-team
report.

Included:

- named finite objects;
- total finite-function arrows with explicit source and target;
- partial, type-checked categorical composition;
- one-carrier endomaps and their monoid powers;
- nonempty semigroupoid paths across different carriers;
- deterministic standard-basis lifts; and
- canonical representatives defined by a declared generator order and
  denotational shortlex minimization.

Excluded and still `OPEN`:

- parsing or evaluating TKS v7.4/v8 surface syntax;
- mapping the ten canonical Noetics or any CAS construct to kernel arrows;
- RPM monad data or laws;
- a rewrite system for inherited TKS equations;
- Noetic Topos 2.0 coverage/modalities;
- stochastic kernels, quantum channels, or empirical dynamics; and
- any transfer from the Ten Advances manuscript.

All such research transfers remain `Ring 4 / NOT LICENSED`.

## 2. Typed finite-function category

### 2.1 Objects and arrows

An object is a pair `X=(name_X, carrier_X)` where `carrier_X` is a finite,
explicitly ordered sequence of distinct, hashable elements. Object identity includes the declared name as
well as the carrier. This prevents accidental coercion between semantically
distinct objects that happen to have equal cardinality or equal Python
elements.

Carrier elements, arrow mappings, path arrows, word labels, catalog objects,
catalog generators, and lift coordinate vectors reject sets, mappings, and
one-shot iterables. Their order changes basis indices, typed denotations, or
shortlex rank, so silently accepting hash-order iteration would make results
depend on `PYTHONHASHSEED`. Callers must provide a replayable ordered sequence.

An arrow judgment

```text
f : X -> Y
```

contains a total map from every standard source index in `X` to one standard
target index in `Y`. Two finite arrows are extensionally equal when source,
target, and the full mapping tuple agree; their presentation names do not
affect equality.

### 2.2 Identity and composition

For each object `X`, `id_X(i)=i`. Given `f:X->Y` and `g:Y->Z`, composition is

```text
(g o f)(i) = g(f(i)) : X -> Z.
```

The implementation rejects `g o f` unless the declared target of `f` equals
the declared source of `g`. No cardinality-only or carrier-only coercion is
performed.

For total finite functions, left identity, right identity, and associativity
follow pointwise. The executable tests exercise these laws and exhaustively
check a bounded family; this is not proof-assistant verification.

### 2.3 Endomaps versus semigroupoid paths

`Endomap(f)` is constructible only when `f:X->X`. Its `power(n)` is the monoid
power of that one fixed endomap, including `f^0=id_X`. The safe finite result
`f^(|X|!)` is idempotent is tested exhaustively for carriers through size four.
For `|X|>=2`, after `|X|!` iterations every point has entered its functional-
graph cycle, and every possible cycle length at most `|X|` divides `|X|!`;
another `|X|!` iterations therefore leaves the value unchanged. The empty and
one-point cases are immediate.

A `SemigroupoidPath` is a nonempty sequence

```text
X0 -f1-> X1 -f2-> ... -fn-> Xn
```

whose adjacent object types match. The path may cross carriers. It has a typed
composite, but it intentionally has no `power` operation. This blocks the
invalid inference from arbitrary typed or time-varying generator sequences to
one finite semigroup element.

Exponentiation by squaring uses bounded internal presentation names and emits
one compact final name. Large exponents use bit length plus a short SHA-256
label rather than Python decimal conversion. Presentation-name construction is
therefore bounded by the exponent's bit length and cannot hit Python's decimal
digit conversion limit; regression tests cover `2^30` and `10^5000`.

## 3. Deterministic standard-basis lift

For `f:X->Y`, let `H_X` and `H_Y` have the orthonormal bases indexed by `X` and
`Y`. Define

```text
A_f : H_X -> H_Y,       A_f e_x = e_{f(x)}.
```

### 3.1 Correct norm theorem

For nonempty `X`, and with the empty-domain value defined as zero,

```text
||A_f||^2 = max_{y in Y} |f^{-1}(y)|,
||A_f||   = sqrt(max_{y in Y} |f^{-1}(y)|).
```

Proof argument: the `(x,x')` entry of `A_f* A_f` is one exactly when
`f(x)=f(x')`. After grouping the input basis by fibers, this Gram matrix is a
direct sum of all-ones blocks `J_m`, one per nonempty fiber. The eigenvalues of
`J_m` are `m` once and zero with multiplicity `m-1`. Therefore the largest
eigenvalue of `A_f* A_f` is the maximum fiber size, which is `||A_f||^2`.

Consequences implemented by the prototype:

```text
tr(A_f* A_f) = |X|,
rank(A_f) = |im(f)|,
A_f is an isometry iff f is injective.
```

`A_f* A_f` is the input-collision Gram matrix. `A_f A_f*` is diagonal with
fiber sizes. The codomain support projector is instead the diagonal zero-one
matrix marking nonempty fibers. These are kept as distinct operations.

For the constant map on two points,

```text
A_f = [1 1]
      [0 0],
```

the lift is idempotent but has norm `sqrt(2)`, trace-Gram `2`, rank `1`, and is
neither a partial isometry nor an orthogonal projector. This is a permanent
regression fixture.

The implementation also satisfies the finite standard-basis functor laws

```text
A_(id_X) = I_(H_X),
A_(g o f) = A_g A_f.
```

These identities are checked by exact matrix equality for every valid typed-map
pair on carriers through size three (1,678 composition pairs), including empty
carriers. Lean additionally kernel-checks identity entrywise and on basis
vectors, typed composition on basis vectors, and relational-product support
composition. Finite-sum numerical matrix multiplication and arbitrary-vector
linearity remain `OPEN`.

## 4. Stable denotational normal forms

Let `G=(g_0,...,g_{k-1})` be a finite, explicitly ordered set of typed
generators. A typed word carries a start object, and its labels must compose in
sequence. Shortlex compares word length first and then the declared generator
rank sequence. For a reachable finite-function denotation `a`, define

```text
NF_G(a) = the shortlex-least well-typed word w with [[w]]=a.
```

The empty word at each object denotes its identity. The algorithm explores
words in shortlex order and expands only the first representative of each
extensional denotation. This pruning is sound: if two prefixes have the same
typed denotation, appending the same well-typed suffix preserves both equality
of denotation and the shortlex advantage of the earlier prefix.

The closure is finite because for finite objects `X,Y` there are at most
`|Y|^|X|` total maps `X->Y`, and the object set is finite. The implementation
returns only after closure completion. It deduplicates queued candidates by
typed denotation and separately caps accepted denotations and the pending
frontier. Either resource guard raises `ClosureLimitExceeded`; it never returns
a partial table as canonical.

This definition does **not** claim termination or confluence of an inherited
rewrite system. Changing the declared generator order may change the selected
representative without changing its denotation.

## 5. Proof and integration ledger

| ID | Obligation | Current evidence | Status |
|---|---|---|---|
| PO-TKS8-CORE-01 | Identity and associativity for finite-function composition | Pointwise argument; unit and bounded exhaustive tests; exact Lean `TypedCategory` lemmas | `PARTIAL FORMAL VERIFICATION PRESENT` |
| PO-TKS8-CORE-02 | Reject every source/target mismatch | Constructor and negative tests | `EXECUTABLE_VALIDATION` |
| PO-TKS8-CORE-03 | Keep one-carrier powers distinct from heterogeneous paths | Separate runtime types and negative tests | `EXECUTABLE_VALIDATION` |
| PO-TKS8-CORE-04 | `f^(|X|!)` is idempotent for finite endomaps | Standard finite-semigroup result; bounded exhaustive test | `STANDARD_RESULT / FORMALIZATION OPEN` |
| PO-TKS8-CORE-05 | Exact deterministic-lift norm formula | Block-Gram proof above; bounded exhaustive structural tests; Lean checks only the exact two-state expansion, not the universal norm or generic matrix/trace/rank bridge | `INFORMAL_PROOF_PRESENT / UNIVERSAL FORMALIZATION OPEN` |
| PO-TKS8-CORE-06 | Soundness and leastness of shortlex catalog | Finiteness/pruning argument above; regression tests | `INFORMAL_CORRECTNESS_ARGUMENT / FORMALIZATION OPEN` |
| PO-TKS8-CORE-07 | Independent theorem-prover formalization | Pinned Lean 4.32.1 seed and axiom audit at `formal/lean`; exact scope in `LEAN_PROOF_MANIFEST_v0.1.json` | `PARTIAL / PRESENT` |
| PO-TKS8-CORE-08 | Reconcile kernel object/arrow types with corrected v7.4 theorem records | No semantic mapping admitted in this prototype | `OPEN / NOT LICENSED` |
| PO-TKS8-CORE-09 | Integrate with the active notation compiler | Explicitly outside this lane; requires compatibility design and review | `OPEN` |
| PO-TKS8-CORE-10 | Independent specialist review | No external review receipt | `OPEN` |
| PO-TKS8-CORE-11 | Standard-basis lift preserves identities and composition | 1,678 exact bounded matrix-composition cases; Lean entry/basis/support proofs | `PARTIAL FORMAL VERIFICATION PRESENT / FINITE-SUM MATRIX BRIDGE OPEN` |

## 6. Reproduction

From the repository root with `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH=(Resolve-Path src)
python -m unittest discover -s tests/tks_v8_core -v
```

The tests include bounded exhaustive enumeration. Passing them establishes
only the behavior covered by this finite executable model; it does not close
the open formalization, integration, semantic-transfer, or specialist-review
obligations.

The separate formal seed is reproduced with the pinned isolated Lean toolchain
by running `python scripts/verify_psr8_lean_gate1.py`. That verifier hardcodes
the sole allowed standard axiom dependency (`propext`), rejects project axiom
declarations and `sorry`, checks source hashes, builds through Lake, and audits
the exact theorem dependency reports. It does not formalize the universal lift
norm, finite-sum numerical matrix multiplication, generic Gram/trace/rank
bridge, arbitrary-vector linearity, factorial idempotence, shortlex leastness,
or the full Noetic site.
