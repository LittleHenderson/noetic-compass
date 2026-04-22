//! Integration tests for the CAS-Native v2 ADR-06 Rust-engine batch APIs.
//!
//! Batch APIs under test:
//! - `validate_same_noetic_cross_product_batch` — Rule 4 admissibility over a
//!   list of `×`-cross-product expressions (Clarification 10 Section 4).
//! - `verify_named_emergent_register_batch` — per-sample verification of
//!   `(RegisterSet, NamedEmergentRegister)` pairs.
//! - `compute_yield_batch` — per-sample stoichiometric yield bundles
//!   (Clarification 9 Section 2).
//!
//! Each batch wrapper MUST delegate to its per-sample function, preserve
//! ordering, handle empty input, and produce per-sample results matching
//! the existing per-sample APIs exactly. These tests exercise each property
//! explicitly.

use cas_engine::ontology::{
    verify_named_emergent_register, verify_named_emergent_register_batch, CognitiveOperator,
    CoreDrive, Domain, NamedEmergentRegister, PrimitiveId, ProductionTarget, Recipe, Register,
    RegisterSet, StateVector, ValidationResult,
};
use cas_engine::scoring::yield_calc::{
    compute_yield_batch, efficiency, excess_capacity, limiting_reagent, theoretical_yield,
    LimitingReagent, YieldBatchInput, YieldResult,
};
use cas_engine::validation::{
    validate_same_noetic_cross_product, validate_same_noetic_cross_product_batch,
    CognitiveStateWithRegister, RuleFourBatchInput, RuleFourResult,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn op(
    n: CognitiveOperator,
    d: Option<Domain>,
    dr: Option<CoreDrive>,
    r: Option<Register>,
) -> CognitiveStateWithRegister {
    CognitiveStateWithRegister::new(n, d, dr, r)
}

fn state_from(pairs: &[(PrimitiveId, f64)]) -> StateVector {
    let mut s = StateVector::empty();
    for (p, q) in pairs {
        s.set(*p, *q);
    }
    s
}

// ---------------------------------------------------------------------------
// 1. Rule 4 batch — empty input
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_empty_input_returns_empty_vec() {
    let inputs: Vec<RuleFourBatchInput> = Vec::new();
    let results = validate_same_noetic_cross_product_batch(&inputs);
    assert!(
        results.is_empty(),
        "empty batch must return empty Vec, got {} entries",
        results.len()
    );
}

// ---------------------------------------------------------------------------
// 2. Rule 4 batch — single element matches per-sample
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_single_element_matches_per_sample() {
    let operands = vec![
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let expected = validate_same_noetic_cross_product(&operands, None);

    let batch_input: Vec<RuleFourBatchInput> = vec![(operands.clone(), None)];
    let results = validate_same_noetic_cross_product_batch(&batch_input);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0], expected);
}

// ---------------------------------------------------------------------------
// 3. Rule 4 batch — ordering preservation, element-wise correctness
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_preserves_ordering_and_matches_per_sample_elementwise() {
    // Mix three independent expressions — (violation, valid-different-noetic,
    // valid-with-named-result) — and confirm batch outputs match per-sample.
    let expr_a_ops = vec![
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let expr_a_named: Option<NamedEmergentRegister> = None;

    let expr_b_ops = vec![
        op(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
        op(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
    ];
    let expr_b_named: Option<NamedEmergentRegister> = None;

    let expr_c_ops = vec![
        op(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Transcendent),
        ),
        op(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let expr_c_named = Some(NamedEmergentRegister::from_str("TF").unwrap());

    let per_sample_a =
        validate_same_noetic_cross_product(&expr_a_ops, expr_a_named.as_ref());
    let per_sample_b =
        validate_same_noetic_cross_product(&expr_b_ops, expr_b_named.as_ref());
    let per_sample_c =
        validate_same_noetic_cross_product(&expr_c_ops, expr_c_named.as_ref());

    let batch: Vec<RuleFourBatchInput> = vec![
        (expr_a_ops.clone(), expr_a_named.clone()),
        (expr_b_ops.clone(), expr_b_named.clone()),
        (expr_c_ops.clone(), expr_c_named.clone()),
    ];
    let results = validate_same_noetic_cross_product_batch(&batch);

    assert_eq!(results.len(), 3, "ordering requires 3 results for 3 inputs");
    assert_eq!(results[0], per_sample_a, "element 0 mismatch");
    assert_eq!(results[1], per_sample_b, "element 1 mismatch");
    assert_eq!(results[2], per_sample_c, "element 2 mismatch");

    // Spot-check semantic expectations to guard against the per-sample
    // function regressing in lockstep with a broken batch implementation.
    assert!(matches!(
        results[0],
        RuleFourResult::ViolationRequiresEmergentResult { .. }
    ));
    assert_eq!(results[1], RuleFourResult::Valid);
    assert_eq!(results[2], RuleFourResult::Valid);
}

// ---------------------------------------------------------------------------
// 4. Rule 4 batch — mix of valid and invalid with per-element correctness
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_mix_of_valid_and_invalid_per_element_correct() {
    // Ten expressions alternating between violation and valid; check that
    // batch preserves the alternation.
    let mut batch: Vec<RuleFourBatchInput> = Vec::new();
    for i in 0..10 {
        if i % 2 == 0 {
            // Same-core, multi-register, no named result → violation.
            batch.push((
                vec![
                    op(
                        CognitiveOperator::CO3,
                        Some(Domain::Principled),
                        None,
                        Some(Register::Analytical),
                    ),
                    op(
                        CognitiveOperator::CO3,
                        Some(Domain::Principled),
                        None,
                        Some(Register::Affective),
                    ),
                ],
                None,
            ));
        } else {
            // Different Noetic — licensed different-state integration.
            batch.push((
                vec![
                    op(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
                    op(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
                ],
                None,
            ));
        }
    }
    let results = validate_same_noetic_cross_product_batch(&batch);
    assert_eq!(results.len(), 10);
    for (i, r) in results.iter().enumerate() {
        if i % 2 == 0 {
            assert!(
                matches!(r, RuleFourResult::ViolationRequiresEmergentResult { .. }),
                "even index {i} expected violation, got {r:?}"
            );
        } else {
            assert_eq!(*r, RuleFourResult::Valid, "odd index {i} expected Valid");
        }
    }
}

// ---------------------------------------------------------------------------
// 5. Rule 4 batch — degenerate per-sample inputs pass through correctly
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_handles_degenerate_per_sample_inputs() {
    // Zero-operand and single-operand expressions are Valid per the
    // per-sample semantics. Batch must pass them through unchanged.
    let batch: Vec<RuleFourBatchInput> = vec![
        (Vec::new(), None),
        (
            vec![op(
                CognitiveOperator::CO1,
                Some(Domain::Operational),
                None,
                None,
            )],
            None,
        ),
    ];
    let results = validate_same_noetic_cross_product_batch(&batch);
    assert_eq!(results.len(), 2);
    assert_eq!(results[0], RuleFourResult::Valid);
    assert_eq!(results[1], RuleFourResult::Valid);
}

// ---------------------------------------------------------------------------
// 6. NamedEmergentRegister batch — per-sample correctness
// ---------------------------------------------------------------------------

#[test]
fn named_emergent_register_batch_matches_per_sample() {
    let set_te =
        RegisterSet::from_registers(&[Register::Transcendent, Register::Embodied]).unwrap();
    let set_af =
        RegisterSet::from_registers(&[Register::Analytical, Register::Affective]).unwrap();
    let set_solo = RegisterSet::from_registers(&[Register::Transcendent]).unwrap();

    let omega = NamedEmergentRegister::from_str("Ω").unwrap();
    let tf = NamedEmergentRegister::from_str("TF").unwrap();

    let inputs = vec![
        (set_te.clone(), omega.clone()),
        (set_af.clone(), tf.clone()),
        (set_solo.clone(), omega.clone()), // singleton set → invalid
    ];
    let batch = verify_named_emergent_register_batch(&inputs);
    assert_eq!(batch.len(), 3);

    // Element-wise equality with per-sample verifier.
    for (i, (rs, named)) in inputs.iter().enumerate() {
        let expected = verify_named_emergent_register(rs, named);
        assert_eq!(batch[i], expected, "mismatch at index {i}");
    }

    // Semantic spot-check.
    assert_eq!(batch[0], ValidationResult::Valid);
    assert_eq!(batch[1], ValidationResult::Valid);
    assert!(
        !batch[2].is_valid(),
        "singleton RegisterSet paired with a NamedEmergentRegister should be invalid"
    );
    if let ValidationResult::Invalid { reason, .. } = &batch[2] {
        assert_eq!(
            reason, "singleton_register_set",
            "reason tag must be the documented machine-readable string"
        );
    }
}

// ---------------------------------------------------------------------------
// 7. NamedEmergentRegister batch — empty input
// ---------------------------------------------------------------------------

#[test]
fn named_emergent_register_batch_empty_input_returns_empty_vec() {
    let results = verify_named_emergent_register_batch(&[]);
    assert!(results.is_empty());
}

// ---------------------------------------------------------------------------
// 8. NamedEmergentRegister batch — flags invalid name via new_unchecked
// ---------------------------------------------------------------------------

#[test]
fn named_emergent_register_batch_catches_invalid_name_from_new_unchecked() {
    // Constructing via `new_unchecked` bypasses validation, so the batch
    // verifier must re-check defensively.
    let set =
        RegisterSet::from_registers(&[Register::Transcendent, Register::Embodied]).unwrap();
    let bad = NamedEmergentRegister::new_unchecked("1BadStart");
    let results = verify_named_emergent_register_batch(&[(set, bad)]);
    assert_eq!(results.len(), 1);
    match &results[0] {
        ValidationResult::Invalid { reason, .. } => {
            assert_eq!(reason, "invalid_name_start");
        }
        _ => panic!("expected Invalid for a name starting with a digit"),
    }
}

// ---------------------------------------------------------------------------
// 9. Yield batch — empty input
// ---------------------------------------------------------------------------

#[test]
fn yield_batch_empty_input_returns_empty_vec() {
    let inputs: Vec<YieldBatchInput> = Vec::new();
    let results = compute_yield_batch(&inputs);
    assert!(results.is_empty());
}

// ---------------------------------------------------------------------------
// 10. Yield batch — single sample matches per-sample functions
// ---------------------------------------------------------------------------

#[test]
fn yield_batch_single_sample_matches_per_sample_with_actual() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 4.0)],
    );
    // Ratios: 10, 3, 5 → Y_T = 3 via f2.
    let state = state_from(&[(f1, 10.0), (f2, 6.0), (f3, 20.0)]);

    let expected_yt = theoretical_yield(&recipe, &state).theoretical;
    let expected_lr = limiting_reagent(&recipe, &state);
    let expected_eps = excess_capacity(&recipe, &state);
    let expected_actual = 2.4_f64; // η should be 0.8
    let expected_eta = efficiency(expected_yt, expected_actual);

    let inputs = vec![(recipe.clone(), state.clone(), Some(expected_actual))];
    let results = compute_yield_batch(&inputs);
    assert_eq!(results.len(), 1);
    let r = &results[0];
    assert_eq!(r.theoretical_yield, expected_yt);
    assert_eq!(r.limiting_reagent, expected_lr);
    assert_eq!(r.actual_yield, Some(expected_actual));
    assert_eq!(r.efficiency, Some(expected_eta));
    assert!((r.efficiency.unwrap() - 0.8).abs() < 1e-12);
    // Excess capacity map equality.
    assert_eq!(r.excess_capacity.len(), expected_eps.len());
    for (p, eps) in &expected_eps {
        assert_eq!(r.excess_capacity.get(p).copied(), Some(*eps));
    }
}

// ---------------------------------------------------------------------------
// 11. Yield batch — observed=None yields None efficiency
// ---------------------------------------------------------------------------

#[test]
fn yield_batch_none_observed_yields_none_efficiency() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 2.0)]);
    let state = state_from(&[(f1, 10.0)]);
    let inputs = vec![(recipe, state, None)];
    let results = compute_yield_batch(&inputs);
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].theoretical_yield, 5.0);
    assert_eq!(results[0].actual_yield, None);
    assert_eq!(results[0].efficiency, None);
}

// ---------------------------------------------------------------------------
// 12. Yield batch — ordering preservation, element-wise correctness
// ---------------------------------------------------------------------------

#[test]
fn yield_batch_preserves_ordering_and_matches_per_sample_elementwise() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);

    // Sample A: single-prerequisite recipe.
    let recipe_a = Recipe::new(ProductionTarget::new("Ω_A"), vec![(f1, 1.0)]);
    let state_a = state_from(&[(f1, 7.0)]);

    // Sample B: tied limiting reagents.
    let recipe_b = Recipe::new(
        ProductionTarget::new("Ω_B"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 1.0)],
    );
    let state_b = state_from(&[(f1, 4.0), (f2, 8.0), (f3, 10.0)]);

    // Sample C: zero-stock prerequisite bottleneck.
    let recipe_c = Recipe::new(
        ProductionTarget::new("Ω_C"),
        vec![(f1, 1.0), (f2, 1.0)],
    );
    let state_c = state_from(&[(f1, 10.0)]); // f2 missing → 0

    let inputs = vec![
        (recipe_a.clone(), state_a.clone(), None),
        (recipe_b.clone(), state_b.clone(), Some(3.5)),
        (recipe_c.clone(), state_c.clone(), Some(0.0)),
    ];
    let results = compute_yield_batch(&inputs);
    assert_eq!(results.len(), 3);

    // Per-element equality with per-sample functions.
    for (i, (r, s, o)) in inputs.iter().enumerate() {
        let per_sample_yt = theoretical_yield(r, s).theoretical;
        let per_sample_lr = limiting_reagent(r, s);
        let per_sample_eps = excess_capacity(r, s);
        assert_eq!(
            results[i].theoretical_yield, per_sample_yt,
            "Y_T mismatch at index {i}"
        );
        assert_eq!(
            results[i].limiting_reagent, per_sample_lr,
            "limiting reagent mismatch at index {i}"
        );
        assert_eq!(
            results[i].actual_yield, *o,
            "actual_yield mismatch at index {i}"
        );
        assert_eq!(
            results[i].excess_capacity.len(),
            per_sample_eps.len(),
            "excess_capacity cardinality mismatch at index {i}"
        );
    }

    // Semantic spot-checks for the edge cases.
    assert_eq!(results[0].theoretical_yield, 7.0);
    assert_eq!(results[1].theoretical_yield, 4.0);
    assert!(matches!(
        results[1].limiting_reagent,
        LimitingReagent::Multiple(_)
    ));
    // Sample C: bottlenecked to Y_T=0 by missing f2; actual=0 → efficiency NaN.
    assert_eq!(results[2].theoretical_yield, 0.0);
    assert!(results[2].efficiency.unwrap().is_nan());
}

// ---------------------------------------------------------------------------
// 13. Yield batch — limiting reagent edge cases covered within batch
// ---------------------------------------------------------------------------

#[test]
fn yield_batch_limiting_reagent_edge_cases() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);

    // Empty recipe.
    let empty_recipe = Recipe::new(ProductionTarget::new("Ω_empty"), vec![]);
    let empty_state = StateVector::empty();

    // Single prerequisite.
    let single_recipe = Recipe::new(ProductionTarget::new("Ω_single"), vec![(f1, 2.0)]);
    let single_state = state_from(&[(f1, 10.0)]);

    // Zero-quantity prerequisite.
    let zero_state_recipe =
        Recipe::new(ProductionTarget::new("Ω_zero"), vec![(f1, 1.0), (f2, 1.0)]);
    let zero_state = state_from(&[(f1, 5.0), (f2, 0.0)]);

    let inputs = vec![
        (empty_recipe, empty_state, None),
        (single_recipe, single_state, None),
        (zero_state_recipe, zero_state, None),
    ];
    let results = compute_yield_batch(&inputs);
    assert_eq!(results.len(), 3);

    // Empty recipe → Y_T = 0, LimitingReagent::None.
    assert_eq!(results[0].theoretical_yield, 0.0);
    assert_eq!(results[0].limiting_reagent, LimitingReagent::None);
    assert!(results[0].excess_capacity.is_empty());

    // Single prerequisite → Y_T = 5, limiting reagent is that primitive.
    assert_eq!(results[1].theoretical_yield, 5.0);
    match &results[1].limiting_reagent {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(*p, f1);
            assert_eq!(*r, 5.0);
        }
        other => panic!("expected single Primitive limiting reagent, got {other:?}"),
    }

    // Zero-quantity prerequisite forces Y_T = 0.
    assert_eq!(results[2].theoretical_yield, 0.0);
    match &results[2].limiting_reagent {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(*p, f2);
            assert_eq!(*r, 0.0);
        }
        other => panic!("expected f2 limiting reagent at ratio 0.0, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// 14. Yield batch — performance (informational): batch >= single-sample × N
// ---------------------------------------------------------------------------
//
// This benchmark is flagged informational per task spec. We simply confirm
// the batch path completes for N > 10 samples and is not catastrophically
// slower than repeated per-sample calls; it must be no slower than 5× the
// per-sample loop (generous bound accommodating wall-clock noise on CI).

#[test]
fn yield_batch_informational_perf_batch_not_slower_than_5x_per_sample_loop() {
    use std::time::Instant;

    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0)],
    );
    let state = state_from(&[(f1, 10.0), (f2, 8.0)]);

    // Construct N = 100 identical samples.
    let n = 100usize;
    let inputs: Vec<YieldBatchInput> = (0..n)
        .map(|_| (recipe.clone(), state.clone(), Some(3.0)))
        .collect();

    // Per-sample loop.
    let t0 = Instant::now();
    let mut per_sample: Vec<YieldResult> = Vec::with_capacity(n);
    for (r, s, o) in &inputs {
        let yt = theoretical_yield(r, s).theoretical;
        let lr = limiting_reagent(r, s);
        let eps = excess_capacity(r, s);
        let (actual, eta) = match o {
            Some(a) => (Some(*a), Some(efficiency(yt, *a))),
            None => (None, None),
        };
        per_sample.push(YieldResult {
            theoretical_yield: yt,
            limiting_reagent: lr,
            actual_yield: actual,
            efficiency: eta,
            excess_capacity: eps,
        });
    }
    let per_sample_elapsed = t0.elapsed();

    // Batch path.
    let t1 = Instant::now();
    let batch = compute_yield_batch(&inputs);
    let batch_elapsed = t1.elapsed();

    assert_eq!(batch.len(), n);
    // Equivalence.
    for i in 0..n {
        assert_eq!(batch[i].theoretical_yield, per_sample[i].theoretical_yield);
        assert_eq!(batch[i].limiting_reagent, per_sample[i].limiting_reagent);
        assert_eq!(batch[i].actual_yield, per_sample[i].actual_yield);
        assert_eq!(batch[i].efficiency, per_sample[i].efficiency);
    }

    // Informational bound — batch must not be catastrophically slower. The
    // batch API exists for amortizing PyO3 crossings, not for pure-Rust
    // speedup; equality-within-constant-factor is sufficient.
    let ratio = batch_elapsed.as_nanos() as f64 / per_sample_elapsed.as_nanos().max(1) as f64;
    assert!(
        ratio < 5.0,
        "batch path took {batch_elapsed:?} vs per-sample loop {per_sample_elapsed:?} \
         (ratio {ratio:.2}× — expected <5× informational bound)"
    );
}

// ---------------------------------------------------------------------------
// 15. Rule 4 batch — performance (informational) for N > 10
// ---------------------------------------------------------------------------

#[test]
fn rule_four_batch_informational_perf_for_n_greater_than_ten() {
    use std::time::Instant;

    let n = 50usize;
    let operands_template = vec![
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let batch: Vec<RuleFourBatchInput> = (0..n)
        .map(|_| (operands_template.clone(), None))
        .collect();

    // Per-sample loop.
    let t0 = Instant::now();
    let mut per_sample: Vec<RuleFourResult> = Vec::with_capacity(n);
    for (ops, named) in &batch {
        per_sample.push(validate_same_noetic_cross_product(ops, named.as_ref()));
    }
    let per_sample_elapsed = t0.elapsed();

    // Batch path.
    let t1 = Instant::now();
    let results = validate_same_noetic_cross_product_batch(&batch);
    let batch_elapsed = t1.elapsed();

    assert_eq!(results.len(), n);
    for i in 0..n {
        assert_eq!(results[i], per_sample[i]);
    }
    let ratio = batch_elapsed.as_nanos() as f64 / per_sample_elapsed.as_nanos().max(1) as f64;
    assert!(
        ratio < 5.0,
        "rule-four batch ratio {ratio:.2}× — expected <5× informational bound"
    );
}

// ---------------------------------------------------------------------------
// 16. Backward compatibility — per-sample function untouched by batch API
// ---------------------------------------------------------------------------

#[test]
fn backward_compatibility_per_sample_rule_four_still_works_as_before() {
    // Violation path.
    let ops = vec![
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        op(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    match validate_same_noetic_cross_product(&ops, None) {
        RuleFourResult::ViolationRequiresEmergentResult { registers, .. } => {
            assert_eq!(registers.len(), 2);
        }
        other => panic!("per-sample violation path broken, got {other:?}"),
    }
    // Valid path with named emergent result.
    let named = NamedEmergentRegister::from_str("TF").unwrap();
    assert_eq!(
        validate_same_noetic_cross_product(&ops, Some(&named)),
        RuleFourResult::Valid
    );
}

#[test]
fn backward_compatibility_per_sample_yield_still_works_as_before() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0)],
    );
    let state = state_from(&[(f1, 5.0), (f2, 2.0)]);
    let y = theoretical_yield(&recipe, &state);
    assert_eq!(y.theoretical, 1.0); // f2 is bottleneck at ratio 1.0
    match limiting_reagent(&recipe, &state) {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(p, f2);
            assert_eq!(r, 1.0);
        }
        other => panic!("per-sample limiting reagent path broken, got {other:?}"),
    }
}

#[test]
fn backward_compatibility_per_sample_named_emergent_verify_still_works() {
    let set =
        RegisterSet::from_registers(&[Register::Transcendent, Register::Embodied]).unwrap();
    let named = NamedEmergentRegister::from_str("Ω").unwrap();
    let r = verify_named_emergent_register(&set, &named);
    assert!(r.is_valid());
}
