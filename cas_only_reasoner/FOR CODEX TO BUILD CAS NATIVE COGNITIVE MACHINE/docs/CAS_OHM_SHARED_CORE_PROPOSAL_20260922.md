# Proposed shared CAS-Ohm arithmetic core — 2026-09-22

Status: **PROPOSAL ONLY** after the bounded diagnostic numeric repair.
The compiler, compiler distribution, atlas, frozen engines and historical
datasets keep their existing identities. This proposal does not replace either
public interface and grants no resource permission.

## One core, two contracts

Put a small standard-library-only arithmetic package beside the existing
standalone compiler, with no imports of the application, trading code, Torch,
measurement collectors or atlas. The exact package path and distribution
migration must be committed together when implemented. Both interfaces would
delegate only agreed arithmetic primitives to it.

The core would accept bounded exact rational operands and perform multiplication,
division and signed subtraction. It would refuse zero denominators and excessive
numeric size with neutral internal errors. It would not infer scales, calibration,
observations, circuit topology, eligibility or causation. Domain-specific wrappers
would retain their current public errors and result contracts.

| Interface | Preserve |
| --- | --- |
| `api/notation/cas_ohm.py` | `OhmScale`, `OhmQuantity`, `make_scale`, `make_quantity`, `attention_flow`, `required_drive`, `effective_constraint`, named `CasOhmError` refusals, exact fractions, rounded display distinction, full scale equality, provenance and bounded lineage. |
| `api/cas_ohm/quantifiers.py` | Existing callable names and result fields, calibration/region eligibility, independent observations, censoring, signed residuals and non-identifying interpretation. The legacy `r_hidden` name remains the disclosed owner override; arithmetic does not establish a hidden mechanism. |

The compiler's admitted nonnegative quantities are not the type of a signed
residual. Zero observed flow may allow a finite difference but cannot support
an inverse ratio. A positive denominator policy belongs to the appropriate
interface. No epsilon substitution, clipping, invented infinity or uniform
profile is implicit.

## Numeric and evidence policies must remain explicit

- Compiler decimal text remains exact decimal text. Its existing float rule,
  `binary_float_via_shortest_decimal`, must not silently change to
  `Fraction.from_float`. The compiler does not currently admit arbitrary
  Decimal objects; sharing a core must not broaden that API accidentally.
- Diagnostic original int/float/Decimal values and uncertainty retain their
  representation and source. Exact representation of a supplied number does
  not increase the accuracy of a measurement.
- Keep existing float return types at legacy diagnostic entry points. A future
  exact diagnostic result API needs a separate versioned policy and explicit
  conversion/rounding metadata. It must not reinterpret old saved records.
- Exact band comparisons and serialization must agree. Any changed threshold,
  rounding or serialization policy gets a new version and before/after boundary
  tests; historical policy identifiers remain replayable.
- Observation values come from independent source records. Do not calculate an
  observation from the prediction being checked. Residual agreement does not
  authenticate the observation or validate the instrument scientifically.
- Calibration profiles, independent observation provenance and eligibility
  remain diagnostic requirements. Compiler design declarations are never
  promoted to calibrated observations merely because a formula is shared.

## Bounded migration and acceptance plan

1. Complete and retain the current invalid-number repair at the diagnostic
   entry points, with new before/after receipts. This is the present code change.
2. Freeze a contract matrix for both interfaces: accepted representations,
   signs, zero behavior, finite conversion/result checks, limits, error types,
   return types, source tags and rounding. Inventory caller locations using
   tracked Git objects, not only files materialized by sparse checkout.
3. Introduce the pure exact primitives. Differential tests compare each facade
   with its own frozen contract. Test input values around zero, exact band
   boundaries, tiny positive observations, large finite values and size limits.
   A formula identity alone is not a compatibility test.
4. Move one facade at a time. Demonstrate the public compiler/CLI and public
   diagnostic callables separately. The compiler's source folder and offline
   ZIP/folder must carry the same dependency bytes. An explicit new distribution
   manifest is required; old hashes remain historical, never repointed.
5. Verify the existing PCBA-to-calculation-to-atlas path and retained Helm
   display without changing their profiles, addresses or saved-present meaning.
   The 12/4/3 example remains a design record. Real Helm tasks keep missing
   profiles and measurements missing.
6. Publish test functions, parameterized cases, added and existing cases,
   repeated executions, excluded/unloaded files and requirement mapping
   separately. Selected-case proportion is not source coverage.

Historical datasets, acceptance records and engine snapshots are read-only
inputs to this migration. New runs always get new paths and fingerprints.
Compatibility or scientific claims cannot be inferred from one green subset.

## Current coordination

`CAS_SHARED_MODULE_INVENTORY_20260922.json` records explicit branch/source
identities, public entry points, editing responsibilities, dependency scopes,
recent changes and tracked source discovery outside sparse checkouts. It is
generated by `tools/inventory_cas_shared_modules.py`.

Separate editing branches are `codex/ohm-invalid-numbers-20260922` for diagnostic
code and `codex/evidence-reconcile-20260922` for the audit addendum. Integration
uses `codex/cas-reconcile-20260922` based on the completed atlas/recorded-view
commit `eb9985566bd11a89f485d627186ef0efa7177f02`. No parallel branch is overwritten.
