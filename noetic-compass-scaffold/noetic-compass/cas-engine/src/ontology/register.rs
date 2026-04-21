//! Phenomenological Register Axis (CAS v7.5 Extension)
//!
//! Per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8, CAS v7.5
//! introduces a second orthogonal axis to the Noetic Topos: the
//! **Phenomenological Register**. Register specifies the *operational
//! character* of a cognitive operation without changing what the operation IS
//! or which Cognitive State / Core Drive primitive is being expressed.
//!
//! Register is an optional specification. CAS v7.4 expressions
//! (register-unspecified) remain valid under v7.5 and are interpreted as
//! register-neutral. This preserves full backward compatibility with v7.4.
//!
//! The four Register values (verbatim per Clarification 8 Section 2):
//!
//! - `T` — Transcendent: high-abstraction, purpose-orienting,
//!   integrative-across-particulars.
//! - `A` — Analytical: explicit, sequential, logical, reason-based.
//! - `f` — Affective (LOWERCASE is authoritative per Clarification 8
//!   Section 3): value-laden, feeling-toned.
//! - `E` — Embodied: sensorimotor, concrete, direct engagement with
//!   material/physical substrate.
//!
//! Register does not modify axioms A1-A7, the 40 Cognitive States, or the
//! 7 Core Drives. It is a characterization layer analogous to coordinate
//! system choice in differential geometry: it enriches description without
//! modifying the underlying manifold structure.
//!
//! Scoring-engine integration (register-aware scoring) is deliberately out of
//! scope for this module; Register is exposed here as data only.

use serde::{Deserialize, Serialize};
use std::fmt;

/// Phenomenological Register — operational-character axis introduced in
/// CAS v7.5.
///
/// Serialization uses the canonical short notation from Clarification 8
/// Section 3: `"T"`, `"A"`, `"f"` (LOWERCASE — authoritative), `"E"`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Register {
    /// `T` — Transcendent Register: high-abstraction, purpose-orienting,
    /// integrative-across-particulars.
    #[serde(rename = "T")]
    Transcendent,
    /// `A` — Analytical Register: explicit, sequential, logical,
    /// reason-based.
    #[serde(rename = "A")]
    Analytical,
    /// `f` — Affective Register (LOWERCASE per Clarification 8 Section 3):
    /// value-laden, feeling-toned.
    #[serde(rename = "f")]
    Affective,
    /// `E` — Embodied Register: sensorimotor, concrete, direct engagement
    /// with material/physical substrate.
    #[serde(rename = "E")]
    Embodied,
}

impl Register {
    /// All four Register values in canonical order (T, A, f, E).
    pub const ALL: [Register; 4] = [
        Register::Transcendent,
        Register::Analytical,
        Register::Affective,
        Register::Embodied,
    ];

    /// The canonical short-form symbol for this Register
    /// (Clarification 8 Section 3 notation).
    ///
    /// Note: `"f"` is LOWERCASE — this is authoritative and not a typo.
    pub fn symbol(self) -> &'static str {
        match self {
            Register::Transcendent => "T",
            Register::Analytical => "A",
            Register::Affective => "f",
            Register::Embodied => "E",
        }
    }

    /// The long-form name for this Register.
    pub fn name(self) -> &'static str {
        match self {
            Register::Transcendent => "Transcendent",
            Register::Analytical => "Analytical",
            Register::Affective => "Affective",
            Register::Embodied => "Embodied",
        }
    }

    /// Parse a Register from its canonical short-form symbol.
    /// Accepts only the authoritative forms; `"f"` is lowercase.
    pub fn from_symbol(symbol: &str) -> Option<Register> {
        match symbol {
            "T" => Some(Register::Transcendent),
            "A" => Some(Register::Analytical),
            "f" => Some(Register::Affective),
            "E" => Some(Register::Embodied),
            _ => None,
        }
    }
}

impl fmt::Display for Register {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.symbol())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::hash_map::DefaultHasher;
    use std::collections::HashSet;
    use std::hash::{Hash, Hasher};

    #[test]
    fn test_register_symbol_roundtrip() {
        for r in Register::ALL {
            assert_eq!(Register::from_symbol(r.symbol()), Some(r));
        }
    }

    #[test]
    fn test_affective_symbol_is_lowercase_f() {
        assert_eq!(Register::Affective.symbol(), "f");
        // Uppercase "F" must NOT deserialize to Affective.
        assert_eq!(Register::from_symbol("F"), None);
    }

    #[test]
    fn test_register_serde_roundtrip_all_variants() {
        let values = [
            (Register::Transcendent, "\"T\""),
            (Register::Analytical, "\"A\""),
            (Register::Affective, "\"f\""),
            (Register::Embodied, "\"E\""),
        ];
        for (variant, expected_json) in values {
            let json = serde_json::to_string(&variant).unwrap();
            assert_eq!(json, expected_json);
            let back: Register = serde_json::from_str(&json).unwrap();
            assert_eq!(back, variant);
        }
    }

    #[test]
    fn test_register_equality_and_hash() {
        let a = Register::Affective;
        let b = Register::Affective;
        assert_eq!(a, b);

        let mut ha = DefaultHasher::new();
        a.hash(&mut ha);
        let mut hb = DefaultHasher::new();
        b.hash(&mut hb);
        assert_eq!(ha.finish(), hb.finish());

        let mut set: HashSet<Register> = HashSet::new();
        for r in Register::ALL {
            assert!(set.insert(r));
        }
        assert_eq!(set.len(), 4);
    }

    #[test]
    fn test_register_display_matches_symbol() {
        for r in Register::ALL {
            assert_eq!(format!("{r}"), r.symbol());
        }
    }

    #[test]
    fn test_register_is_copy() {
        let r = Register::Transcendent;
        let r2 = r; // Copy, not move.
        assert_eq!(r, r2);
    }
}
