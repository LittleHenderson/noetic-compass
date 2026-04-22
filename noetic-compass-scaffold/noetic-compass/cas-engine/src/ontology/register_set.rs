//! Register Set and Named Emergent Register (CAS v7.7 Extension).
//!
//! Per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10, CAS v7.7
//! introduces the `|⟨…⟩` register-set notation to denote register occupancy
//! or architectural specification without making any operational claim about
//! dynamics between the register-specific instances.
//!
//! This module adds two types:
//!
//! 1. [`RegisterSet`] — an ordered, deduplicated, non-empty set of
//!    [`Register`] values. Canonical notation: `|⟨R1,R2,...⟩`.
//! 2. [`NamedEmergentRegister`] — an identifier (e.g., `Ω`, `TF`) denoting
//!    an explicitly-named emergent result produced by same-Noetic
//!    cross-register `×` integration (Clarification 10 Section 2C).
//!
//! Both types are ADDITIVE over v7.5/v7.6. No existing type, axiom, or
//! signature is modified. CAS v7.4/v7.5/v7.6 expressions remain valid under
//! v7.7 semantics.
//!
//! Scope of this module: data-only. Rule 4 admissibility validation lives
//! in [`crate::validation::rule_four`].

use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use std::fmt;

use super::register::Register;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Error returned by [`RegisterSet`] constructors.
///
/// NOTE: Duplicates in input register lists are SILENTLY deduplicated by the
/// underlying `BTreeSet`. There is no `Duplicate` variant — this is a design
/// choice consistent with mathematical set semantics (a set `{T, A, T}` is
/// equal to the set `{T, A}`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegisterSetError {
    /// An empty register list was supplied. A `RegisterSet` must contain at
    /// least one register per Clarification 10 Section 2A: `|⟨⟩` is not a
    /// meaningful specification.
    Empty,
}

impl fmt::Display for RegisterSetError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str(
                "RegisterSet must contain at least one Register; empty sets are not admissible",
            ),
        }
    }
}

impl std::error::Error for RegisterSetError {}

/// Error returned by [`NamedEmergentRegister::from_str`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NamedEmergentRegisterError {
    /// The supplied name was empty.
    Empty,
    /// The first character was not a letter (ASCII alphabetic) or a Greek
    /// uppercase letter.
    InvalidStart(char),
    /// A subsequent character was not letter, digit, or underscore.
    InvalidChar(char),
}

impl fmt::Display for NamedEmergentRegisterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Empty => f.write_str("NamedEmergentRegister name must be non-empty"),
            Self::InvalidStart(c) => write!(
                f,
                "NamedEmergentRegister name must start with a letter or Greek uppercase, got {c:?}"
            ),
            Self::InvalidChar(c) => write!(
                f,
                "NamedEmergentRegister name may only contain letter/digit/underscore, got {c:?}"
            ),
        }
    }
}

impl std::error::Error for NamedEmergentRegisterError {}

// ---------------------------------------------------------------------------
// OrderedRegister — private ordering wrapper
// ---------------------------------------------------------------------------

/// Internal ordering wrapper for [`Register`].
///
/// Canonical order is the Clarification 8 Section 3 enumeration:
/// `T, A, f, E`. This wrapper exists because the public v7.5 `Register` enum
/// does not derive `Ord`, and modifying the v7.5 type is out of scope for
/// the v7.7 extension. The wrapper is private to this module — the public
/// [`RegisterSet`] API is in terms of `Register` and converts at the
/// boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
struct OrderedRegister(Register);

impl OrderedRegister {
    fn canonical_rank(self) -> u8 {
        match self.0 {
            Register::Transcendent => 0,
            Register::Analytical => 1,
            Register::Affective => 2,
            Register::Embodied => 3,
        }
    }
}

impl PartialOrd for OrderedRegister {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for OrderedRegister {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.canonical_rank().cmp(&other.canonical_rank())
    }
}

// ---------------------------------------------------------------------------
// RegisterSet
// ---------------------------------------------------------------------------

/// A non-empty, ordered, deduplicated set of [`Register`] values.
///
/// Canonical CAS notation: `|⟨R1,R2,...⟩` where registers are printed in
/// canonical order `T, A, f, E` (matching Clarification 8 Section 3 enum
/// ordering).
///
/// Semantic: per Clarification 10 Section 2A, `X|⟨R1,R2,...⟩` denotes that
/// the state `X` is present in registers `R1,R2,...` — an *architectural
/// specification* without any claim about interaction dynamics. Uses of this
/// notation are neither co-presence (`+`) nor integration (`×`).
///
/// # Representation
///
/// Internally a `BTreeSet` over a private ordering wrapper for:
///
/// - Canonical ordered iteration (T, A, f, E).
/// - O(log n) membership and subset/superset checks.
/// - Automatic deduplication at insertion time.
///
/// # Copy / Clone
///
/// `BTreeSet` is `Clone` but NOT `Copy`; therefore `RegisterSet` is `Clone`
/// and NOT `Copy`. This is a deliberate trade-off: the set representation
/// supports up to 4 registers (the full inventory) but heap-allocation
/// semantics preclude `Copy`. For high-throughput contexts consider passing
/// a `RegisterSet` by reference rather than cloning.
///
/// # Serde
///
/// Serializes as a JSON array of register short-form symbols, leveraging the
/// existing [`Register`] `#[serde(rename)]` attributes (e.g., `["T","A","f"]`
/// for `{T, A, f}`). This matches the v7.5 Register serde pattern and is
/// broad-tooling-compatible. The canonical short-form notation string
/// (`"⟨T,A,f⟩"`) is available via [`Self::canonical_notation`] and the
/// `Display` impl.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct RegisterSet {
    registers: BTreeSet<OrderedRegister>,
}

impl RegisterSet {
    /// Construct an empty `RegisterSet`. Internal use only — external
    /// callers should use [`Self::from_registers`], which rejects the empty
    /// case per Clarification 10 Section 2A. This function is `pub` for
    /// API completeness but returns a value that
    /// [`Self::is_empty`] identifies as empty.
    pub fn new() -> Self {
        Self {
            registers: BTreeSet::new(),
        }
    }

    /// Construct a `RegisterSet` from a slice of registers.
    ///
    /// Duplicates in the input are silently deduplicated (mathematical set
    /// semantics). An empty input is rejected with
    /// [`RegisterSetError::Empty`].
    pub fn from_registers(registers: &[Register]) -> Result<Self, RegisterSetError> {
        if registers.is_empty() {
            return Err(RegisterSetError::Empty);
        }
        let set: BTreeSet<OrderedRegister> =
            registers.iter().copied().map(OrderedRegister).collect();
        Ok(Self { registers: set })
    }

    /// Membership test.
    pub fn contains(&self, register: &Register) -> bool {
        self.registers.contains(&OrderedRegister(*register))
    }

    /// Subset test: `self ⊆ other`.
    pub fn is_subset_of(&self, other: &RegisterSet) -> bool {
        self.registers.is_subset(&other.registers)
    }

    /// Superset test: `self ⊇ other`.
    pub fn is_superset_of(&self, other: &RegisterSet) -> bool {
        self.registers.is_superset(&other.registers)
    }

    /// Returns `true` if this set contains a Register involution pair:
    /// either `{|T, |E}` or `{|A, |f}` (both registers of the pair
    /// simultaneously present).
    ///
    /// Per Clarification 8 Section 3, the register involution pairs are
    /// `|T ↔ |E` (Transcendent / Embodied) and `|A ↔ |f` (Analytical /
    /// Affective). The presence of both members of a pair is an
    /// architecturally significant structural signal.
    pub fn involution_pair_present(&self) -> bool {
        let t = self.contains(&Register::Transcendent);
        let e = self.contains(&Register::Embodied);
        let a = self.contains(&Register::Analytical);
        let f = self.contains(&Register::Affective);
        (t && e) || (a && f)
    }

    /// Cardinality of the set.
    pub fn len(&self) -> usize {
        self.registers.len()
    }

    /// Whether the set is empty. Constructed `RegisterSet` values via
    /// [`Self::from_registers`] are never empty; this method exists for API
    /// completeness and reports `true` only for a value created via
    /// [`Self::new`].
    pub fn is_empty(&self) -> bool {
        self.registers.is_empty()
    }

    /// Iterator over the contained registers in canonical order
    /// (T, A, f, E).
    pub fn iter(&self) -> impl Iterator<Item = Register> + '_ {
        self.registers.iter().map(|or| or.0)
    }

    /// Canonical CAS notation, WITHOUT the leading `|` prefix.
    /// Example: `{T, A, f}` → `"⟨T,A,f⟩"`.
    ///
    /// The leading `|` prefix (yielding `"|⟨T,A,f⟩"`) is the caller's
    /// responsibility — typically added by the enclosing state-literal
    /// serializer (e.g., `^3^P` + `|⟨…⟩`).
    pub fn canonical_notation(&self) -> String {
        let inner = self
            .iter()
            .map(|r| r.symbol())
            .collect::<Vec<_>>()
            .join(",");
        format!("⟨{inner}⟩")
    }
}

impl Default for RegisterSet {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for RegisterSet {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.canonical_notation())
    }
}

// Serde — serialize as an array of register short-form symbols.
// Example: {T, A, f} -> ["T","A","f"]. Matches the v7.5 Register pattern.
impl Serialize for RegisterSet {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeSeq;
        let mut seq = serializer.serialize_seq(Some(self.registers.len()))?;
        for or in &self.registers {
            seq.serialize_element(&or.0)?;
        }
        seq.end()
    }
}

impl<'de> Deserialize<'de> for RegisterSet {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let vec: Vec<Register> = Vec::deserialize(deserializer)?;
        if vec.is_empty() {
            return Err(serde::de::Error::custom(
                "RegisterSet deserialization: empty array; RegisterSet must be non-empty",
            ));
        }
        let set: BTreeSet<OrderedRegister> =
            vec.into_iter().map(OrderedRegister).collect();
        Ok(Self { registers: set })
    }
}

// ---------------------------------------------------------------------------
// NamedEmergentRegister
// ---------------------------------------------------------------------------

/// A **named emergent register** — an identifier for the unified result of
/// a same-Noetic, multi-register `×` integration per Clarification 10
/// Section 2C.
///
/// Example usage in CAS notation:
///
/// ```text
/// (^2^P|T × ^2^P|f) = ^2^P|TF
///                            ↑
///            NamedEmergentRegister { name: "TF" }
/// ```
///
/// The name `TF` denotes a specific fused cross-register state (here, unified
/// transcendent-affective principled affinity). The name is not constrained
/// to come from the base `|T|A|f|E` alphabet; common conventions include
/// `Ω`, `TF`, `AE`, etc., with semantics specified by the author of the
/// expression.
///
/// # Validation
///
/// - Name must be non-empty.
/// - First character: ASCII letter OR Greek uppercase letter
///   (U+0391..=U+03A9 excluding the reserved U+03A2 slot).
/// - Subsequent characters: ASCII letter, ASCII digit, or underscore.
///
/// The restricted alphabet for subsequent characters is deliberate: it keeps
/// emergent-register identifiers parseable in downstream tooling
/// (compiler / parser / LaTeX renderer) without requiring Greek-letter
/// handling beyond the leading position.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct NamedEmergentRegister {
    /// The emergent register's identifier, e.g., `"Omega"`, `"TF"`, `"Ω"`.
    pub name: String,
}

impl NamedEmergentRegister {
    /// Construct a `NamedEmergentRegister` from a string, validating the
    /// name per the rules documented on this type.
    pub fn from_str(name: &str) -> Result<Self, NamedEmergentRegisterError> {
        if name.is_empty() {
            return Err(NamedEmergentRegisterError::Empty);
        }
        let mut chars = name.chars();
        let first = chars.next().expect("non-empty guarded above");
        if !is_valid_start(first) {
            return Err(NamedEmergentRegisterError::InvalidStart(first));
        }
        for c in chars {
            if !is_valid_subsequent(c) {
                return Err(NamedEmergentRegisterError::InvalidChar(c));
            }
        }
        Ok(Self {
            name: name.to_string(),
        })
    }

    /// Construct without validation. Intended for internal / trusted callers
    /// only. External code should prefer [`Self::from_str`].
    pub fn new_unchecked(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

impl fmt::Display for NamedEmergentRegister {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.name)
    }
}

// ---------------------------------------------------------------------------
// ValidationResult — batch verification outcome (ADR-06)
// ---------------------------------------------------------------------------

/// Outcome of a single batched verification check.
///
/// Used by [`verify_named_emergent_register_batch`] to report per-sample
/// results without aborting the whole batch on a single failure. The variants
/// carry a structured reason for the failure so downstream Python code can
/// surface diagnostics without re-parsing textual error messages.
///
/// See `docs/architecture/cas_native_v2_adrs.md` ADR-06 for motivation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValidationResult {
    /// The sample passed all checks.
    Valid,
    /// The sample failed validation. `reason` is a short machine-readable
    /// tag (e.g., `"empty_register_set"`, `"invalid_name_start"`) suitable
    /// for dispatching, plus a human-readable `detail` string.
    Invalid { reason: String, detail: String },
}

impl ValidationResult {
    /// Whether this result is valid.
    pub fn is_valid(&self) -> bool {
        matches!(self, Self::Valid)
    }

    /// Construct an Invalid result with a short tag and a long-form message.
    pub fn invalid(reason: impl Into<String>, detail: impl Into<String>) -> Self {
        Self::Invalid {
            reason: reason.into(),
            detail: detail.into(),
        }
    }
}

/// Per-sample input for [`verify_named_emergent_register_batch`]: a
/// `RegisterSet` (architectural specification) paired with a
/// `NamedEmergentRegister` (the emergent fused result claimed for that
/// specification).
pub type NamedEmergentBatchInput = (RegisterSet, NamedEmergentRegister);

/// Verify a single `(RegisterSet, NamedEmergentRegister)` pair.
///
/// Checks performed:
///
/// 1. `RegisterSet` is non-empty (enforced at construction; defensive check
///    here covers any future relaxation).
/// 2. `NamedEmergentRegister.name` is well-formed per
///    [`NamedEmergentRegister::from_str`] rules (re-validated defensively so
///    stale/unchecked values via `new_unchecked` are still caught).
/// 3. The `RegisterSet` has at least 2 registers — a same-Noetic emergent
///    fusion requires at least two register-instantiations per Clarification
///    10 Section 2C. A singleton register set does not instantiate the
///    ambiguity pattern Rule 4 guards against and therefore does not require
///    a `NamedEmergentRegister`. When a named result is nevertheless supplied
///    for a singleton set, we report this as invalid to surface the likely
///    modeling error.
///
/// Returns [`ValidationResult::Valid`] when all checks pass, else
/// [`ValidationResult::Invalid`] with a structured reason tag.
pub fn verify_named_emergent_register(
    register_set: &RegisterSet,
    named: &NamedEmergentRegister,
) -> ValidationResult {
    if register_set.is_empty() {
        return ValidationResult::invalid(
            "empty_register_set",
            "RegisterSet must contain at least one Register per Clarification 10 Section 2A",
        );
    }
    if register_set.len() < 2 {
        return ValidationResult::invalid(
            "singleton_register_set",
            "NamedEmergentRegister is only meaningful when the RegisterSet \
             contains ≥2 distinct registers (fusion requires ≥2 source \
             instantiations per Clarification 10 Section 2C)",
        );
    }
    // Re-validate the name defensively; callers may have constructed via
    // `new_unchecked`.
    if let Err(err) = NamedEmergentRegister::from_str(&named.name) {
        let reason = match &err {
            NamedEmergentRegisterError::Empty => "empty_name",
            NamedEmergentRegisterError::InvalidStart(_) => "invalid_name_start",
            NamedEmergentRegisterError::InvalidChar(_) => "invalid_name_char",
        };
        return ValidationResult::invalid(reason, format!("{err}"));
    }
    ValidationResult::Valid
}

/// Batch version of [`verify_named_emergent_register`] (ADR-06).
///
/// Applies the single-sample verifier to each `(RegisterSet,
/// NamedEmergentRegister)` pair in `inputs` and returns a `Vec<ValidationResult>`
/// preserving input order: `result[i]` corresponds to `inputs[i]`.
///
/// Determinism / parallelism / empty-batch semantics match
/// [`crate::validation::rule_four::validate_same_noetic_cross_product_batch`].
pub fn verify_named_emergent_register_batch(
    inputs: &[NamedEmergentBatchInput],
) -> Vec<ValidationResult> {
    inputs
        .iter()
        .map(|(rset, named)| verify_named_emergent_register(rset, named))
        .collect()
}

/// ASCII letter or Greek uppercase letter.
fn is_valid_start(c: char) -> bool {
    c.is_ascii_alphabetic() || is_greek_uppercase(c)
}

/// Greek uppercase letters (Unicode block Greek and Coptic,
/// `0x0391..=0x03A9`). `U+03A2` is unassigned and is excluded.
fn is_greek_uppercase(c: char) -> bool {
    let code = c as u32;
    (0x0391..=0x03A9).contains(&code) && code != 0x03A2
}

/// ASCII letter, ASCII digit, or underscore.
fn is_valid_subsequent(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '_'
}

// ---------------------------------------------------------------------------
// Tests (module-local smoke tests)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn register_set_empty_rejected() {
        let err = RegisterSet::from_registers(&[]).unwrap_err();
        assert_eq!(err, RegisterSetError::Empty);
    }

    #[test]
    fn register_set_deduplicates() {
        let set =
            RegisterSet::from_registers(&[Register::Transcendent, Register::Transcendent])
                .unwrap();
        assert_eq!(set.len(), 1);
        assert!(set.contains(&Register::Transcendent));
    }

    #[test]
    fn register_set_canonical_order() {
        // Input in non-canonical order; output must be T, A, f, E.
        let set = RegisterSet::from_registers(&[
            Register::Embodied,
            Register::Affective,
            Register::Transcendent,
            Register::Analytical,
        ])
        .unwrap();
        assert_eq!(set.canonical_notation(), "⟨T,A,f,E⟩");
    }

    #[test]
    fn involution_pair_present_t_e() {
        let set = RegisterSet::from_registers(&[Register::Transcendent, Register::Embodied])
            .unwrap();
        assert!(set.involution_pair_present());
    }

    #[test]
    fn involution_pair_absent_single_member() {
        let set = RegisterSet::from_registers(&[Register::Transcendent]).unwrap();
        assert!(!set.involution_pair_present());
    }

    #[test]
    fn named_emergent_register_accepts_simple_ascii() {
        let n = NamedEmergentRegister::from_str("TF").unwrap();
        assert_eq!(n.name, "TF");
    }

    #[test]
    fn named_emergent_register_accepts_greek_omega() {
        let n = NamedEmergentRegister::from_str("Ω").unwrap();
        assert_eq!(n.name, "Ω");
    }

    #[test]
    fn named_emergent_register_rejects_empty() {
        assert_eq!(
            NamedEmergentRegister::from_str(""),
            Err(NamedEmergentRegisterError::Empty)
        );
    }

    #[test]
    fn named_emergent_register_rejects_digit_start() {
        let err = NamedEmergentRegister::from_str("1TF").unwrap_err();
        assert!(matches!(err, NamedEmergentRegisterError::InvalidStart('1')));
    }
}
