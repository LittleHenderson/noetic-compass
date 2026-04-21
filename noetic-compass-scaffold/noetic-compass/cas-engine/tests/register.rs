//! Integration tests for the CAS v7.5 Phenomenological Register extension.
//!
//! Covers Clarification 8 conformance requirements:
//! - Register enum serde round-trip with canonical short-form symbols
//!   ("T", "A", "f", "E"), confirming the LOWERCASE "f" is authoritative.
//! - Backward compatibility: default-constructed state vectors have no
//!   Register (register-neutral / v7.4-compatible semantics).
//! - The `with_register` builder annotates without altering the
//!   probability geometry, and the serialized form exposes the
//!   authoritative `"register": "f"` spelling.
//! - Register equality and Hash behavior.

use std::collections::hash_map::DefaultHasher;
use std::collections::{HashMap, HashSet};
use std::hash::{Hash, Hasher};

use cas_engine::ontology::{CognitiveStateVector, Register};

// ---------------------------------------------------------------------------
// (a) Register enum serde round-trip through JSON, verifying LOWERCASE "f"
// ---------------------------------------------------------------------------

#[test]
fn register_serializes_to_canonical_short_form() {
    assert_eq!(
        serde_json::to_string(&Register::Transcendent).unwrap(),
        "\"T\""
    );
    assert_eq!(
        serde_json::to_string(&Register::Analytical).unwrap(),
        "\"A\""
    );
    // Affective MUST serialize to lowercase "f" per Clarification 8 Section 3.
    assert_eq!(
        serde_json::to_string(&Register::Affective).unwrap(),
        "\"f\""
    );
    assert_eq!(
        serde_json::to_string(&Register::Embodied).unwrap(),
        "\"E\""
    );
}

#[test]
fn register_deserializes_from_canonical_short_form() {
    let t: Register = serde_json::from_str("\"T\"").unwrap();
    let a: Register = serde_json::from_str("\"A\"").unwrap();
    let f: Register = serde_json::from_str("\"f\"").unwrap();
    let e: Register = serde_json::from_str("\"E\"").unwrap();
    assert_eq!(t, Register::Transcendent);
    assert_eq!(a, Register::Analytical);
    assert_eq!(f, Register::Affective);
    assert_eq!(e, Register::Embodied);
}

#[test]
fn register_uppercase_f_rejected_during_deserialization() {
    // Uppercase "F" is NOT a valid Register symbol; only lowercase "f" is
    // authoritative per Clarification 8.
    let result: Result<Register, _> = serde_json::from_str("\"F\"");
    assert!(
        result.is_err(),
        "uppercase \"F\" must not deserialize as Affective; lowercase is authoritative"
    );
}

#[test]
fn register_roundtrips_all_variants_through_json() {
    for r in Register::ALL {
        let json = serde_json::to_string(&r).unwrap();
        let back: Register = serde_json::from_str(&json).unwrap();
        assert_eq!(back, r);
    }
}

// ---------------------------------------------------------------------------
// (b) CognitiveStateVector default construction has register: None
// ---------------------------------------------------------------------------

#[test]
fn uniform_state_vector_is_register_neutral_by_default() {
    let v = CognitiveStateVector::uniform();
    assert_eq!(v.register(), None);
}

#[test]
fn new_state_vector_is_register_neutral_by_default() {
    let probs = [1.0 / 40.0; 40];
    let v = CognitiveStateVector::new(probs).unwrap();
    assert_eq!(v.register(), None);
}

#[test]
fn register_neutral_state_vector_omits_register_key_on_serialize() {
    // Backward-compat: v7.4 consumers must see no "register" key for
    // register-neutral vectors (skip_serializing_if = Option::is_none).
    let v = CognitiveStateVector::uniform();
    let json = serde_json::to_string(&v).unwrap();
    assert!(
        !json.contains("\"register\""),
        "register-neutral state vector must not serialize a register field; got {json}"
    );
}

#[test]
fn state_vector_json_without_register_deserializes_via_default() {
    // A JSON payload that predates v7.5 (no "register" field) must still
    // deserialize cleanly via the serde default.
    let legacy_probs: Vec<f64> = vec![1.0 / 40.0; 40];
    let legacy_json =
        serde_json::to_string(&serde_json::json!({ "probabilities": legacy_probs })).unwrap();
    let v: CognitiveStateVector = serde_json::from_str(&legacy_json).unwrap();
    assert_eq!(v.register(), None);
}

// ---------------------------------------------------------------------------
// (c) with_register(Register::Affective) => serializes with "register": "f"
// ---------------------------------------------------------------------------

#[test]
fn with_register_affective_serializes_lowercase_f() {
    let v = CognitiveStateVector::uniform().with_register(Register::Affective);
    let json = serde_json::to_string(&v).unwrap();
    assert!(
        json.contains("\"register\":\"f\""),
        "expected serialized form to contain lowercase \"register\":\"f\"; got {json}"
    );
    assert!(
        !json.contains("\"register\":\"F\""),
        "serialized form must never contain uppercase F for Affective; got {json}"
    );
}

#[test]
fn with_register_sets_all_four_registers_correctly() {
    for r in Register::ALL {
        let v = CognitiveStateVector::uniform().with_register(r);
        assert_eq!(v.register(), Some(r));
        let json = serde_json::to_string(&v).unwrap();
        let expected = format!("\"register\":\"{}\"", r.symbol());
        assert!(
            json.contains(&expected),
            "expected {expected} in serialized form; got {json}"
        );
    }
}

#[test]
fn with_register_preserves_probability_distribution() {
    // Clarification 8 Section 1: Register does not change what the operation
    // IS — only its operational character. The probability geometry must be
    // untouched by register annotation.
    let base = CognitiveStateVector::uniform();
    let base_probs = base.as_slice().to_vec();
    let annotated = base.clone().with_register(Register::Analytical);
    assert_eq!(annotated.as_slice().to_vec(), base_probs);
}

#[test]
fn without_register_clears_annotation() {
    let v = CognitiveStateVector::uniform()
        .with_register(Register::Transcendent)
        .without_register();
    assert_eq!(v.register(), None);
    let json = serde_json::to_string(&v).unwrap();
    assert!(
        !json.contains("\"register\""),
        "without_register must remove the register field from serialization; got {json}"
    );
}

#[test]
fn state_vector_with_register_roundtrips_through_json() {
    let original = CognitiveStateVector::uniform().with_register(Register::Affective);
    let json = serde_json::to_string(&original).unwrap();
    let back: CognitiveStateVector = serde_json::from_str(&json).unwrap();
    assert_eq!(back.register(), Some(Register::Affective));
    assert_eq!(back.as_slice(), original.as_slice());
}

// ---------------------------------------------------------------------------
// (d) Register equality and Hash
// ---------------------------------------------------------------------------

#[test]
fn register_equality_is_reflexive_and_symmetric() {
    for r in Register::ALL {
        assert_eq!(r, r);
    }
    assert_eq!(Register::Affective, Register::Affective);
    assert_ne!(Register::Affective, Register::Analytical);
    assert_ne!(Register::Transcendent, Register::Embodied);
}

#[test]
fn register_hash_is_consistent_with_equality() {
    for r in Register::ALL {
        let mut h1 = DefaultHasher::new();
        r.hash(&mut h1);
        let r_copy = r; // Copy semantics.
        let mut h2 = DefaultHasher::new();
        r_copy.hash(&mut h2);
        assert_eq!(h1.finish(), h2.finish());
    }
}

#[test]
fn register_usable_as_hashset_and_hashmap_key() {
    let mut set: HashSet<Register> = HashSet::new();
    for r in Register::ALL {
        assert!(set.insert(r));
    }
    assert_eq!(set.len(), 4);
    // Re-inserting is a no-op.
    assert!(!set.insert(Register::Affective));

    let mut map: HashMap<Register, &'static str> = HashMap::new();
    for r in Register::ALL {
        map.insert(r, r.name());
    }
    assert_eq!(map.get(&Register::Affective), Some(&"Affective"));
    assert_eq!(map.get(&Register::Transcendent), Some(&"Transcendent"));
}
