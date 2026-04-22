//! Integration tests for the Rule 4 validator per
//! `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10 Section 4.
//!
//! Rule 4: same-Noetic, multi-register `×` expressions are invalid by default
//! unless an emergent integrated result is explicitly named.

use cas_engine::ontology::{
    CognitiveOperator, CoreDrive, Domain, NamedEmergentRegister, Register,
};
use cas_engine::validation::{
    rule_four_distance, rule_four_distance_batch, validate_same_noetic_cross_product,
    CognitiveStateWithRegister, RuleFourBatchInput, RuleFourResult,
};

fn state(
    noetic: CognitiveOperator,
    domain: Option<Domain>,
    drive: Option<CoreDrive>,
    register: Option<Register>,
) -> CognitiveStateWithRegister {
    CognitiveStateWithRegister::new(noetic, domain, drive, register)
}

// ---------------------------------------------------------------------------
// 1. Same-Noetic × bare (no emergent result) → violation
// ---------------------------------------------------------------------------

#[test]
fn same_noetic_cross_bare_without_named_result_is_violation() {
    // ^3^P|A × ^3^P|f × ^3^P|T — Clarification 10 Section 8's invalid example.
    let operands = vec![
        state(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        state(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
        state(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Transcendent),
        ),
    ];
    let result = validate_same_noetic_cross_product(&operands, None);
    match result {
        RuleFourResult::ViolationRequiresEmergentResult { core, registers } => {
            assert_eq!(core.noetic, CognitiveOperator::CO3);
            assert_eq!(core.domain, Some(Domain::Principled));
            assert_eq!(core.drive, None);
            // Distinct registers reported (the three named ones).
            assert_eq!(registers.len(), 3);
        }
        other => panic!(
            "expected ViolationRequiresEmergentResult, got {other:?} \
             (same-Noetic × without emergent result should trigger violation \
              per Clarification 10 Section 4)"
        ),
    }
}

// ---------------------------------------------------------------------------
// 2. Different-Noetic × passes
// ---------------------------------------------------------------------------

#[test]
fn different_noetic_cross_is_valid() {
    // ^5^C × ^6^C — Clarification 10 Section 8 worked example.
    let operands = vec![
        state(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
        state(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
    ];
    assert_eq!(
        validate_same_noetic_cross_product(&operands, None),
        RuleFourResult::Valid
    );
}

// ---------------------------------------------------------------------------
// 3. Different-Domain × passes
// ---------------------------------------------------------------------------

#[test]
fn different_domain_cross_is_valid() {
    // ^2^P × ^2^O — same Noetic but different Domain; different-state.
    let operands = vec![
        state(CognitiveOperator::CO2, Some(Domain::Principled), None, None),
        state(CognitiveOperator::CO2, Some(Domain::Operational), None, None),
    ];
    assert_eq!(
        validate_same_noetic_cross_product(&operands, None),
        RuleFourResult::Valid
    );
}

// ---------------------------------------------------------------------------
// 4. Different-Drive × passes
// ---------------------------------------------------------------------------

#[test]
fn different_drive_cross_is_valid() {
    // ^5^C_{F2} × ^5^C_{F4}
    let operands = vec![
        state(
            CognitiveOperator::CO5,
            Some(Domain::Cognitive),
            Some(CoreDrive::F2Wisdom),
            None,
        ),
        state(
            CognitiveOperator::CO5,
            Some(Domain::Cognitive),
            Some(CoreDrive::F4Connection),
            None,
        ),
    ];
    assert_eq!(
        validate_same_noetic_cross_product(&operands, None),
        RuleFourResult::Valid
    );
}

// ---------------------------------------------------------------------------
// 5. Same-Noetic × with explicit named result passes
// ---------------------------------------------------------------------------

#[test]
fn same_noetic_cross_with_named_emergent_result_is_valid() {
    // (^2^P|T × ^2^P|f) = ^2^P|TF — Clarification 10 Section 8's
    // "conditionally valid" example.
    let operands = vec![
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Transcendent),
        ),
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let named = NamedEmergentRegister::from_str("TF").unwrap();
    assert_eq!(
        validate_same_noetic_cross_product(&operands, Some(&named)),
        RuleFourResult::Valid
    );

    // Also with Greek Omega.
    let omega = NamedEmergentRegister::from_str("Ω").unwrap();
    assert_eq!(
        validate_same_noetic_cross_product(&operands, Some(&omega)),
        RuleFourResult::Valid
    );
}

// ---------------------------------------------------------------------------
// 6. Violation variant carries core and register list
// ---------------------------------------------------------------------------

#[test]
fn violation_result_carries_core_and_register_list() {
    // Construct a minimal 2-operand same-core different-register case.
    let operands = vec![
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            Some(CoreDrive::F2Wisdom),
            Some(Register::Transcendent),
        ),
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            Some(CoreDrive::F2Wisdom),
            Some(Register::Affective),
        ),
    ];
    let result = validate_same_noetic_cross_product(&operands, None);
    match result {
        RuleFourResult::ViolationRequiresEmergentResult { core, registers } => {
            // Full core preserved.
            assert_eq!(core.noetic, CognitiveOperator::CO2);
            assert_eq!(core.domain, Some(Domain::Principled));
            assert_eq!(core.drive, Some(CoreDrive::F2Wisdom));
            // Registers list contains both T and f (in first-appearance
            // order: T then f).
            assert_eq!(registers, vec![Register::Transcendent, Register::Affective]);
        }
        other => panic!("expected violation, got {other:?}"),
    }
}

// ---------------------------------------------------------------------------
// 7. Single-operand (degenerate) case — no `×` to validate
// ---------------------------------------------------------------------------

#[test]
fn single_operand_never_triggers_violation() {
    // A single operand, even with a register annotation, has no `×`
    // expression to validate. Must return Valid.
    let operands = vec![state(
        CognitiveOperator::CO3,
        Some(Domain::Principled),
        None,
        Some(Register::Analytical),
    )];
    assert_eq!(
        validate_same_noetic_cross_product(&operands, None),
        RuleFourResult::Valid
    );

    // Same with a named result provided — still valid, nothing to enforce.
    let named = NamedEmergentRegister::from_str("TF").unwrap();
    assert_eq!(
        validate_same_noetic_cross_product(&operands, Some(&named)),
        RuleFourResult::Valid
    );
}

// ===========================================================================
// Continuous distance-to-valid signal (ADR-06)
// ===========================================================================
//
// `rule_four_distance` / `rule_four_distance_batch` return 0.0 for admissible
// expressions and a positive severity-weighted scalar for violations. The
// metric MUST satisfy:
//   (a) `distance == 0.0` iff binary validator returns `Valid`
//   (b) strictly non-negative everywhere
//   (c) monotone non-decreasing in the distinct-register count for violations
// Tests below exercise each invariant plus the batch surface.

// ---------------------------------------------------------------------------
// 8. Distance on a trivially-valid single-operand expression is 0.0
// ---------------------------------------------------------------------------

#[test]
fn distance_single_operand_is_zero() {
    let operands = vec![state(
        CognitiveOperator::CO3,
        Some(Domain::Principled),
        None,
        Some(Register::Analytical),
    )];
    assert_eq!(rule_four_distance(&operands, None), 0.0);
}

// ---------------------------------------------------------------------------
// 9. Distance on a licensed different-Noetic × expression is 0.0
// ---------------------------------------------------------------------------

#[test]
fn distance_different_noetic_cross_is_zero() {
    // ^5^C × ^6^C — different-state integration, explicitly licensed.
    let operands = vec![
        state(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
        state(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
    ];
    assert_eq!(rule_four_distance(&operands, None), 0.0);
}

// ---------------------------------------------------------------------------
// 10. Distance on same-core × WITH explicit named emergent result is 0.0
// ---------------------------------------------------------------------------

#[test]
fn distance_same_noetic_with_named_emergent_result_is_zero() {
    // (^2^P|T × ^2^P|f) = ^2^P|TF — conditionally valid, named result
    // resolves the ambiguity.
    let operands = vec![
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Transcendent),
        ),
        state(
            CognitiveOperator::CO2,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let named = NamedEmergentRegister::from_str("TF").unwrap();
    assert_eq!(rule_four_distance(&operands, Some(&named)), 0.0);
}

// ---------------------------------------------------------------------------
// 11. Distance on a 2-register violation is exactly 1.0
// ---------------------------------------------------------------------------

#[test]
fn distance_violation_two_registers_is_one() {
    // ^3^P|A × ^3^P|f — minimum-ambiguity violation.
    let operands = vec![
        state(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Analytical),
        ),
        state(
            CognitiveOperator::CO3,
            Some(Domain::Principled),
            None,
            Some(Register::Affective),
        ),
    ];
    let d = rule_four_distance(&operands, None);
    assert_eq!(d, 1.0, "2-register violation must have distance 1.0, got {d}");
}

// ---------------------------------------------------------------------------
// 12. Distance monotonically increases as register count grows (2 → 3 → 4)
// ---------------------------------------------------------------------------

#[test]
fn distance_monotone_increases_with_register_count() {
    // 2 registers: ^3^P|A × ^3^P|f
    let d2 = rule_four_distance(
        &[
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Analytical),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
        ],
        None,
    );

    // 3 registers: ^3^P|A × ^3^P|f × ^3^P|T
    let d3 = rule_four_distance(
        &[
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Analytical),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Transcendent),
            ),
        ],
        None,
    );

    // 4 registers: ^3^P|A × ^3^P|f × ^3^P|T × ^3^P|E
    let d4 = rule_four_distance(
        &[
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Analytical),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Transcendent),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Embodied),
            ),
        ],
        None,
    );

    // Expected metric values per option-(b) severity weighting:
    //   2 regs → 1.0, 3 regs → 1.5, 4 regs → 2.0.
    assert_eq!(d2, 1.0);
    assert_eq!(d3, 1.5);
    assert_eq!(d4, 2.0);

    // Strict monotonicity (the behavioral invariant required by the task).
    assert!(d3 > d2, "d3={d3} must be strictly greater than d2={d2}");
    assert!(d4 > d3, "d4={d4} must be strictly greater than d3={d3}");
}

// ---------------------------------------------------------------------------
// 13. Consistency: distance == 0.0 iff binary validator returns Valid
// ---------------------------------------------------------------------------

#[test]
fn distance_zero_iff_binary_valid_consistency() {
    // A mix of inputs covering Valid paths, Violation paths, and
    // degenerate cases. For each, distance == 0.0 ⇔ binary == Valid.
    let test_inputs: Vec<(Vec<CognitiveStateWithRegister>, Option<NamedEmergentRegister>)> = vec![
        // Valid: empty
        (vec![], None),
        // Valid: single operand
        (
            vec![state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Transcendent),
            )],
            None,
        ),
        // Valid: different-Noetic
        (
            vec![
                state(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
                state(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
            ],
            None,
        ),
        // Valid: different-Domain
        (
            vec![
                state(CognitiveOperator::CO2, Some(Domain::Principled), None, None),
                state(CognitiveOperator::CO2, Some(Domain::Operational), None, None),
            ],
            None,
        ),
        // Valid: same-Noetic × with named emergent result
        (
            vec![
                state(
                    CognitiveOperator::CO2,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Transcendent),
                ),
                state(
                    CognitiveOperator::CO2,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Affective),
                ),
            ],
            Some(NamedEmergentRegister::from_str("TF").unwrap()),
        ),
        // Violation: same-Noetic × without named result (2 regs)
        (
            vec![
                state(
                    CognitiveOperator::CO3,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Analytical),
                ),
                state(
                    CognitiveOperator::CO3,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Affective),
                ),
            ],
            None,
        ),
        // Violation: 3 registers, bare
        (
            vec![
                state(
                    CognitiveOperator::CO3,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Analytical),
                ),
                state(
                    CognitiveOperator::CO3,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Affective),
                ),
                state(
                    CognitiveOperator::CO3,
                    Some(Domain::Principled),
                    None,
                    Some(Register::Transcendent),
                ),
            ],
            None,
        ),
    ];

    for (i, (operands, named)) in test_inputs.iter().enumerate() {
        let binary = validate_same_noetic_cross_product(operands, named.as_ref());
        let distance = rule_four_distance(operands, named.as_ref());
        let is_binary_valid = matches!(binary, RuleFourResult::Valid);
        let is_distance_zero = distance == 0.0;
        assert_eq!(
            is_binary_valid, is_distance_zero,
            "consistency violated at index {i}: binary={binary:?}, distance={distance}"
        );
        // Distance is always non-negative.
        assert!(
            distance >= 0.0,
            "distance must be non-negative at index {i}, got {distance}"
        );
    }
}

// ---------------------------------------------------------------------------
// 14. Batch empty input returns empty Vec
// ---------------------------------------------------------------------------

#[test]
fn distance_batch_empty_input_returns_empty_vec() {
    let inputs: Vec<RuleFourBatchInput> = Vec::new();
    let results = rule_four_distance_batch(&inputs);
    assert!(results.is_empty(), "empty batch must yield empty Vec");
}

// ---------------------------------------------------------------------------
// 15. Batch results match per-sample results index-by-index
// ---------------------------------------------------------------------------

#[test]
fn distance_batch_matches_per_sample_elementwise() {
    // Mix: violation (2-reg), valid different-Noetic, violation (3-reg),
    // valid with named emergent result.
    let expr_a: RuleFourBatchInput = (
        vec![
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Analytical),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
        ],
        None,
    );
    let expr_b: RuleFourBatchInput = (
        vec![
            state(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
            state(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
        ],
        None,
    );
    let expr_c: RuleFourBatchInput = (
        vec![
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Analytical),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
            state(
                CognitiveOperator::CO3,
                Some(Domain::Principled),
                None,
                Some(Register::Transcendent),
            ),
        ],
        None,
    );
    let expr_d: RuleFourBatchInput = (
        vec![
            state(
                CognitiveOperator::CO2,
                Some(Domain::Principled),
                None,
                Some(Register::Transcendent),
            ),
            state(
                CognitiveOperator::CO2,
                Some(Domain::Principled),
                None,
                Some(Register::Affective),
            ),
        ],
        Some(NamedEmergentRegister::from_str("TF").unwrap()),
    );

    let batch = vec![expr_a.clone(), expr_b.clone(), expr_c.clone(), expr_d.clone()];
    let results = rule_four_distance_batch(&batch);

    assert_eq!(results.len(), 4);
    for (i, (operands, named)) in batch.iter().enumerate() {
        let per_sample = rule_four_distance(operands, named.as_ref());
        assert_eq!(
            results[i], per_sample,
            "batch result at index {i} ({val}) did not match per-sample ({ps})",
            val = results[i],
            ps = per_sample
        );
    }

    // Semantic spot-checks: ordering preserved, expected metric values.
    assert_eq!(results[0], 1.0, "expr_a is 2-reg violation");
    assert_eq!(results[1], 0.0, "expr_b is different-Noetic valid");
    assert_eq!(results[2], 1.5, "expr_c is 3-reg violation");
    assert_eq!(results[3], 0.0, "expr_d is valid with named emergent");
}

// ---------------------------------------------------------------------------
// 16. Batch results non-negative for all inputs
// ---------------------------------------------------------------------------

#[test]
fn distance_batch_always_non_negative() {
    // Alternating valid / violation inputs.
    let mut batch: Vec<RuleFourBatchInput> = Vec::new();
    for i in 0..6 {
        if i % 2 == 0 {
            batch.push((
                vec![
                    state(
                        CognitiveOperator::CO3,
                        Some(Domain::Principled),
                        None,
                        Some(Register::Analytical),
                    ),
                    state(
                        CognitiveOperator::CO3,
                        Some(Domain::Principled),
                        None,
                        Some(Register::Affective),
                    ),
                ],
                None,
            ));
        } else {
            batch.push((
                vec![
                    state(CognitiveOperator::CO5, Some(Domain::Cognitive), None, None),
                    state(CognitiveOperator::CO6, Some(Domain::Cognitive), None, None),
                ],
                None,
            ));
        }
    }
    let results = rule_four_distance_batch(&batch);
    assert_eq!(results.len(), 6);
    for (i, d) in results.iter().enumerate() {
        assert!(*d >= 0.0, "result {i} has negative distance: {d}");
    }
    // Even indices are violations (distance 1.0), odd indices are valid (0.0).
    for (i, d) in results.iter().enumerate() {
        if i % 2 == 0 {
            assert_eq!(*d, 1.0, "even index {i} expected 1.0, got {d}");
        } else {
            assert_eq!(*d, 0.0, "odd index {i} expected 0.0, got {d}");
        }
    }
}
