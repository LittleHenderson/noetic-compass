//! Integration tests for the Rule 4 validator per
//! `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10 Section 4.
//!
//! Rule 4: same-Noetic, multi-register `×` expressions are invalid by default
//! unless an emergent integrated result is explicitly named.

use cas_engine::ontology::{
    CognitiveOperator, CoreDrive, Domain, NamedEmergentRegister, Register,
};
use cas_engine::validation::{
    validate_same_noetic_cross_product, CognitiveStateWithRegister, RuleFourResult,
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
