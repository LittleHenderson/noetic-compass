//! Integration tests for the CAS v7.7 RegisterSet and NamedEmergentRegister
//! types per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10.

use cas_engine::ontology::{
    NamedEmergentRegister, NamedEmergentRegisterError, Register, RegisterSet, RegisterSetError,
};

// ---------------------------------------------------------------------------
// Construction and deduplication
// ---------------------------------------------------------------------------

#[test]
fn register_set_construction_deduplicates_inputs() {
    // Per Clarification 10 Section 2A, `|⟨T,A,T⟩` is the same specification
    // as `|⟨T,A⟩`. Mathematical set semantics — duplicates are silently
    // collapsed.
    let set = RegisterSet::from_registers(&[
        Register::Transcendent,
        Register::Analytical,
        Register::Transcendent,
    ])
    .unwrap();
    assert_eq!(set.len(), 2);
    assert!(set.contains(&Register::Transcendent));
    assert!(set.contains(&Register::Analytical));
    assert!(!set.contains(&Register::Affective));
    assert!(!set.contains(&Register::Embodied));
}

#[test]
fn register_set_empty_input_rejected() {
    let err = RegisterSet::from_registers(&[]).unwrap_err();
    assert_eq!(err, RegisterSetError::Empty);
    // Error message cites the structural reason.
    let msg = format!("{err}");
    assert!(msg.contains("empty") || msg.contains("non-empty") || msg.contains("at least"));
}

#[test]
fn register_set_canonical_serialization_order() {
    // Input in scrambled order — output must be T, A, f, E per
    // Clarification 8 Section 3 canonical order.
    let set = RegisterSet::from_registers(&[
        Register::Affective,
        Register::Transcendent,
        Register::Analytical,
    ])
    .unwrap();
    assert_eq!(set.canonical_notation(), "⟨T,A,f⟩");
    // Display trait matches.
    assert_eq!(format!("{set}"), "⟨T,A,f⟩");
}

#[test]
fn register_set_single_element_succeeds() {
    let set = RegisterSet::from_registers(&[Register::Analytical]).unwrap();
    assert_eq!(set.len(), 1);
    assert_eq!(set.canonical_notation(), "⟨A⟩");
    assert!(set.contains(&Register::Analytical));
}

// ---------------------------------------------------------------------------
// Membership and subset
// ---------------------------------------------------------------------------

#[test]
fn register_set_contains_is_correct() {
    let set = RegisterSet::from_registers(&[Register::Transcendent, Register::Analytical])
        .unwrap();
    assert!(set.contains(&Register::Transcendent));
    assert!(set.contains(&Register::Analytical));
    assert!(!set.contains(&Register::Affective));
    assert!(!set.contains(&Register::Embodied));
}

#[test]
fn register_set_subset_relation() {
    let smaller = RegisterSet::from_registers(&[Register::Transcendent]).unwrap();
    let larger =
        RegisterSet::from_registers(&[Register::Transcendent, Register::Analytical]).unwrap();
    assert!(smaller.is_subset_of(&larger));
    assert!(!larger.is_subset_of(&smaller));
    assert!(larger.is_superset_of(&smaller));
    // Reflexivity.
    assert!(smaller.is_subset_of(&smaller));
    assert!(smaller.is_superset_of(&smaller));
}

// ---------------------------------------------------------------------------
// Involution pair detection (Clarification 8 Section 3)
// ---------------------------------------------------------------------------

#[test]
fn register_set_involution_pair_detection() {
    // {T, E} is an involution pair.
    let te = RegisterSet::from_registers(&[Register::Transcendent, Register::Embodied])
        .unwrap();
    assert!(te.involution_pair_present());

    // {T, A} is NOT an involution pair (T↔E, A↔f are the pairs).
    let ta = RegisterSet::from_registers(&[Register::Transcendent, Register::Analytical])
        .unwrap();
    assert!(!ta.involution_pair_present());

    // {A, f} IS an involution pair.
    let af = RegisterSet::from_registers(&[Register::Analytical, Register::Affective]).unwrap();
    assert!(af.involution_pair_present());

    // The full set {T, A, f, E} contains BOTH involution pairs.
    let full = RegisterSet::from_registers(&[
        Register::Transcendent,
        Register::Analytical,
        Register::Affective,
        Register::Embodied,
    ])
    .unwrap();
    assert!(full.involution_pair_present());

    // A single register is not a pair.
    let solo = RegisterSet::from_registers(&[Register::Transcendent]).unwrap();
    assert!(!solo.involution_pair_present());
}

// ---------------------------------------------------------------------------
// Serde round-trip
// ---------------------------------------------------------------------------

#[test]
fn register_set_serde_json_round_trip_preserves_equality() {
    // Build a set in non-canonical order, serialize, deserialize, compare.
    let original = RegisterSet::from_registers(&[
        Register::Affective,
        Register::Transcendent,
        Register::Analytical,
    ])
    .unwrap();
    let json = serde_json::to_string(&original).unwrap();
    // Array-of-symbols form, in canonical T,A,f order.
    assert_eq!(json, "[\"T\",\"A\",\"f\"]");
    let restored: RegisterSet = serde_json::from_str(&json).unwrap();
    assert_eq!(restored, original);
    assert_eq!(restored.canonical_notation(), "⟨T,A,f⟩");
}

// ---------------------------------------------------------------------------
// NamedEmergentRegister validation
// ---------------------------------------------------------------------------

#[test]
fn named_emergent_register_accepts_canonical_names() {
    // ASCII "TF" — Clarification 10 Section 8 example (^2^P|TF).
    let tf = NamedEmergentRegister::from_str("TF").unwrap();
    assert_eq!(tf.name, "TF");

    // Greek uppercase Omega — the most natural choice for the generic
    // emergent integrated result.
    let omega = NamedEmergentRegister::from_str("Ω").unwrap();
    assert_eq!(omega.name, "Ω");

    // Mixed ASCII + digits + underscore after a letter.
    let n = NamedEmergentRegister::from_str("Fused_1").unwrap();
    assert_eq!(n.name, "Fused_1");
}

#[test]
fn named_emergent_register_rejects_invalid_names() {
    // Empty.
    assert_eq!(
        NamedEmergentRegister::from_str(""),
        Err(NamedEmergentRegisterError::Empty)
    );

    // Starts with digit.
    let err = NamedEmergentRegister::from_str("1TF").unwrap_err();
    assert!(matches!(err, NamedEmergentRegisterError::InvalidStart('1')));

    // Contains illegal punctuation.
    let err = NamedEmergentRegister::from_str("T-F").unwrap_err();
    assert!(matches!(err, NamedEmergentRegisterError::InvalidChar('-')));

    // Starts with underscore (not a letter, not Greek uppercase).
    let err = NamedEmergentRegister::from_str("_Omega").unwrap_err();
    assert!(matches!(err, NamedEmergentRegisterError::InvalidStart('_')));
}
