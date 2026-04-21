//! Stoichiometric Production Semantics — Recipe and Production Target types
//! (CAS v7.6 Extension)
//!
//! Per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9, CAS v7.6
//! introduces production semantics as a higher-order analytical layer over the
//! v7.5 state space. Every outcome is treated as a **Production Target (Ω)**
//! requiring a **Recipe (Θ)** of prerequisite activations in specific
//! proportional weightings:
//!
//! ```text
//! Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω
//! ```
//!
//! where each `Xᵢ` is a v7.5 CAS primitive (Noetic, Domain, Drive, Register,
//! or compound state) and each `aᵢ` is the required proportional coefficient.
//!
//! Production semantics does NOT add new primitives to the topos. The 40
//! Cognitive States, 7 Core Drives, and 4 Registers named in USPTO
//! #64/037,173 and Clarifications 1-8 remain unchanged. v7.6 adds recipe
//! notation, yield measurement, leakage detection, catalyst/inhibitor
//! formalism, and limiting reagent analysis — all analytical capacities OVER
//! existing primitives.
//!
//! Backward compatibility: these types are additive. All existing v7.4/v7.5
//! types (Register, CognitiveStateVector, CoreDrive, ...) are unmodified.
//!
//! Scope of this module: data-only. Recipe arithmetic (the v7.6
//! higher-order recipe operations in Clarification 9 Section 6) is
//! follow-on research work and deliberately out of scope here.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::domains::Domain;
use super::drives::CoreDrive;
use super::operators::CognitiveOperator;
use super::register::Register;
use super::states::CognitiveStateId;

// ---------------------------------------------------------------------------
// PrimitiveId — tagged union identifying any v7.5 primitive
// ---------------------------------------------------------------------------

/// A canonical identifier for any CAS v7.5 primitive that may appear as a
/// recipe prerequisite.
///
/// Per Clarification 9 Section 4, recipe prerequisites `Xᵢ` are always drawn
/// from the v7.5 state space: Noetics (^0-^9), Domains (P, C, E, O), Drives
/// (F1-F7), Registers (|T, |A, |f, |E), or compound states (^n^D_{Fk}|R).
///
/// This enum is a **structured tagged union** over the four pure-axis cases
/// plus a compound-state case, with each variant carrying an optional
/// Register annotation (CAS v7.5 orthogonal axis per Clarification 8).
///
/// Serde serialization is the `untagged` form so that JSON round-trips
/// naturally reflect which axis is addressed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PrimitiveId {
    /// A pure Noetic operator (^0 through ^9), optionally with a Register.
    /// Canonical notation: `^n` or `^n|R`.
    Noetic {
        operator: CognitiveOperator,
        register: Option<Register>,
    },
    /// A pure Processing Domain (P, C, E, O), optionally with a Register.
    /// Canonical notation: `^D` or `^D|R` (where D is the domain letter).
    Domain {
        domain: Domain,
        register: Option<Register>,
    },
    /// A pure Core Drive (F1 through F7), optionally with a Register.
    /// Canonical notation: `F_k` or `F_k|R`.
    Drive {
        drive: CoreDrive,
        register: Option<Register>,
    },
    /// A Register alone (used only when the axis is the specification target).
    /// Canonical notation: `|R`.
    Register {
        register: Register,
    },
    /// A compound state combining a Noetic × Domain × Drive, optionally with
    /// a Register. Canonical notation: `^n^D_{F_k}` or `^n^D_{F_k}|R`.
    Compound {
        operator: CognitiveOperator,
        domain: Domain,
        drive: CoreDrive,
        register: Option<Register>,
    },
}

impl PrimitiveId {
    /// Constructor for a pure Noetic primitive (register-neutral).
    pub fn noetic(operator: CognitiveOperator) -> Self {
        Self::Noetic {
            operator,
            register: None,
        }
    }

    /// Constructor for a Noetic primitive with an explicit Register.
    pub fn noetic_with_register(operator: CognitiveOperator, register: Register) -> Self {
        Self::Noetic {
            operator,
            register: Some(register),
        }
    }

    /// Constructor for a pure Domain primitive (register-neutral).
    pub fn domain(domain: Domain) -> Self {
        Self::Domain {
            domain,
            register: None,
        }
    }

    /// Constructor for a Domain primitive with an explicit Register.
    pub fn domain_with_register(domain: Domain, register: Register) -> Self {
        Self::Domain {
            domain,
            register: Some(register),
        }
    }

    /// Constructor for a pure Drive primitive (register-neutral).
    pub fn drive(drive: CoreDrive) -> Self {
        Self::Drive {
            drive,
            register: None,
        }
    }

    /// Constructor for a Drive primitive with an explicit Register.
    pub fn drive_with_register(drive: CoreDrive, register: Register) -> Self {
        Self::Drive {
            drive,
            register: Some(register),
        }
    }

    /// Constructor for a Register-only primitive.
    pub fn register(register: Register) -> Self {
        Self::Register { register }
    }

    /// Constructor for a compound state primitive (register-neutral).
    pub fn compound(
        operator: CognitiveOperator,
        domain: Domain,
        drive: CoreDrive,
    ) -> Self {
        Self::Compound {
            operator,
            domain,
            drive,
            register: None,
        }
    }

    /// Constructor for a compound state primitive with an explicit Register.
    pub fn compound_with_register(
        operator: CognitiveOperator,
        domain: Domain,
        drive: CoreDrive,
        register: Register,
    ) -> Self {
        Self::Compound {
            operator,
            domain,
            drive,
            register: Some(register),
        }
    }

    /// Construct from a Noetic × Domain CognitiveStateId (register-neutral).
    /// The resulting variant is `Compound` only if a drive is supplied;
    /// otherwise the caller wanted a pure Noetic, which they should use
    /// [`PrimitiveId::noetic`] for. To represent a Noetic × Domain state
    /// without a drive, use the `Compound` variant via `compound` with a
    /// placeholder drive — but that is semantically compound. This helper
    /// exists specifically for the compound-state path.
    pub fn from_state_with_drive(state: CognitiveStateId, drive: CoreDrive) -> Self {
        Self::Compound {
            operator: state.operator(),
            domain: state.domain(),
            drive,
            register: None,
        }
    }

    /// The Register annotation, if any.
    pub fn register_annotation(&self) -> Option<Register> {
        match self {
            Self::Noetic { register, .. } => *register,
            Self::Domain { register, .. } => *register,
            Self::Drive { register, .. } => *register,
            Self::Register { register } => Some(*register),
            Self::Compound { register, .. } => *register,
        }
    }

    /// Canonical CAS notation string for this primitive, e.g. `"^2"`,
    /// `"^C|A"`, `"F_2|A"`, `"^2^C_{F_2}|A"`, `"|E"`.
    pub fn canonical_notation(&self) -> String {
        let register_suffix = |r: Option<Register>| -> String {
            match r {
                Some(reg) => format!("|{}", reg.symbol()),
                None => String::new(),
            }
        };
        match self {
            Self::Noetic { operator, register } => {
                format!("^{}{}", operator.index(), register_suffix(*register))
            }
            Self::Domain { domain, register } => {
                format!("^{}{}", domain.abbreviation(), register_suffix(*register))
            }
            Self::Drive { drive, register } => {
                format!("F_{}{}", drive.number(), register_suffix(*register))
            }
            Self::Register { register } => {
                format!("|{}", register.symbol())
            }
            Self::Compound {
                operator,
                domain,
                drive,
                register,
            } => format!(
                "^{}^{}_{{F_{}}}{}",
                operator.index(),
                domain.abbreviation(),
                drive.number(),
                register_suffix(*register),
            ),
        }
    }
}

// ---------------------------------------------------------------------------
// ProductionTarget — Ω
// ---------------------------------------------------------------------------

/// A **Production Target (Ω)** — a specified outcome whose generation is
/// under analysis.
///
/// May be any discrete achievement: completing a project, producing a
/// reliable refusal, reaching an insight, forming a relationship, building a
/// capability. Canonical notation: `Ω_{name}`.
///
/// Clarification 9 Section 2.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct ProductionTarget {
    /// Human-readable name identifying this production target.
    pub name: String,
}

impl ProductionTarget {
    /// Construct a production target from a name.
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

// ---------------------------------------------------------------------------
// Leakage — Λ
// ---------------------------------------------------------------------------

/// **Leakage / Side-Reaction (Λ)** — input prerequisite consumed by
/// unintended products rather than the target Ω.
///
/// Distinct from **lacunarity** (prerequisite ABSENT) and **inversion**
/// (prerequisite in shadow form) — leakage is a PRESENT prerequisite
/// producing a WRONG product. Clarification 9 Section 5.
///
/// Canonical notation: `Λᵢ(Ω_side)` — leakage of prerequisite `Xᵢ` into
/// unintended product `Ω_side`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Leakage {
    /// The prerequisite primitive being leaked.
    pub prerequisite: PrimitiveId,
    /// The unintended side product `Ω_side` receiving the leaked prerequisite.
    pub side_product: String,
    /// Magnitude of the leakage (units of prerequisite diverted per unit of
    /// side product). Non-negative by convention; validation is the caller's
    /// responsibility at this scope.
    pub magnitude: f64,
}

impl Leakage {
    pub fn new(
        prerequisite: PrimitiveId,
        side_product: impl Into<String>,
        magnitude: f64,
    ) -> Self {
        Self {
            prerequisite,
            side_product: side_product.into(),
            magnitude,
        }
    }
}

// ---------------------------------------------------------------------------
// Catalyst κ and Inhibitor ι
// ---------------------------------------------------------------------------

/// **Catalyst (κ)** — a contextual or environmental factor that enhances
/// conversion efficiency WITHOUT being consumed as a prerequisite.
///
/// Raises η (efficiency) without appearing in the recipe prerequisites.
/// Clarification 9 Section 2.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Catalyst {
    /// Human-readable name for this catalyst.
    pub name: String,
}

impl Catalyst {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

/// **Inhibitor (ι)** — a contextual or environmental factor that reduces
/// conversion efficiency WITHOUT removing prerequisites.
///
/// Lowers η (efficiency) without appearing in the recipe prerequisites.
/// Clarification 9 Section 2.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Inhibitor {
    /// Human-readable name for this inhibitor.
    pub name: String,
}

impl Inhibitor {
    pub fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

// ---------------------------------------------------------------------------
// Conditions — κ / ι bundle
// ---------------------------------------------------------------------------

/// Environmental / contextual modifiers on a recipe: catalysts (enhance η)
/// and inhibitors (reduce η).
///
/// Canonical notation: `Θ(Ω) | κ₁, κ₂, ..., ι₁, ι₂, ... → Ω`.
/// Clarification 9 Section 3.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct Conditions {
    /// Environmental factors that raise conversion efficiency.
    pub catalysts: Vec<Catalyst>,
    /// Environmental factors that lower conversion efficiency.
    pub inhibitors: Vec<Inhibitor>,
}

impl Conditions {
    /// Construct empty conditions (no catalysts, no inhibitors).
    pub fn empty() -> Self {
        Self::default()
    }

    /// Construct from explicit catalyst and inhibitor lists.
    pub fn new(catalysts: Vec<Catalyst>, inhibitors: Vec<Inhibitor>) -> Self {
        Self {
            catalysts,
            inhibitors,
        }
    }
}

// ---------------------------------------------------------------------------
// Recipe — Θ(Ω)
// ---------------------------------------------------------------------------

/// A **Recipe (Θ)** — the proportional weighting of prerequisite primitives
/// required for a unit of production target Ω.
///
/// ```text
/// Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω
/// ```
///
/// `prerequisites` is a list of `(PrimitiveId, coefficient)` pairs where
/// `coefficient = aᵢ` and `PrimitiveId = Xᵢ`. Recipes are always relative
/// to a specific target — different outcomes require different recipes.
/// Clarification 9 Section 2.
///
/// Coefficient semantics: the authoritative specification gives recipe
/// coefficients as proportional requirements per unit production. This
/// module does not reject any finite coefficient at construction time; the
/// yield calculation in [`crate::scoring::yield_calc`] treats `aᵢ = 0` by
/// skipping that prerequisite (no constraint on yield), and treats negative
/// coefficients as uninterpreted (callers should validate upstream if they
/// wish to forbid them). See [`crate::scoring::yield_calc`] for the full
/// handling convention.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Recipe {
    /// The production target Ω this recipe produces.
    pub target: ProductionTarget,
    /// Ordered list of `(Xᵢ, aᵢ)` prerequisite/coefficient pairs.
    pub prerequisites: Vec<(PrimitiveId, f64)>,
    /// Optional leakage specifications — prerequisites diverted to side
    /// products. Empty for an ideal recipe with no side reactions.
    pub leakages: Vec<Leakage>,
    /// Environmental conditions (catalysts, inhibitors) modifying conversion
    /// efficiency but not appearing as recipe prerequisites.
    pub conditions: Conditions,
}

impl Recipe {
    /// Construct a minimal recipe with no leakages and no conditions.
    pub fn new(target: ProductionTarget, prerequisites: Vec<(PrimitiveId, f64)>) -> Self {
        Self {
            target,
            prerequisites,
            leakages: Vec::new(),
            conditions: Conditions::empty(),
        }
    }

    /// Construct a full recipe with explicit leakages and conditions.
    pub fn with_leakages_and_conditions(
        target: ProductionTarget,
        prerequisites: Vec<(PrimitiveId, f64)>,
        leakages: Vec<Leakage>,
        conditions: Conditions,
    ) -> Self {
        Self {
            target,
            prerequisites,
            leakages,
            conditions,
        }
    }

    /// The number of prerequisite primitives in this recipe.
    pub fn arity(&self) -> usize {
        self.prerequisites.len()
    }

    /// Whether this recipe has no prerequisites (the empty-recipe edge case).
    pub fn is_empty(&self) -> bool {
        self.prerequisites.is_empty()
    }
}

// ---------------------------------------------------------------------------
// StateVector — S
// ---------------------------------------------------------------------------

/// A v7.6 **State Vector (S)** — the current activation profile of a Mind,
/// specified as the available quantities of each primitive.
///
/// ```text
/// S = ⟨x₁, x₂, ..., xₙ⟩ = {X₁: x₁, X₂: x₂, ..., Xₙ: xₙ}
/// ```
///
/// NOTE: This is a **different type** from the v7.5
/// [`crate::ontology::CognitiveStateVector`], which represents a point on the
/// open probability simplex Δ°₃₉. The v7.6 `StateVector` here represents
/// available quantities of specified primitives (no normalization
/// constraint) for recipe yield analysis. Both types coexist —
/// `CognitiveStateVector` is untouched by v7.6.
///
/// Serde: because `PrimitiveId` is a non-string structured key, JSON
/// serialization uses a manual implementation that emits a list of
/// `{"primitive": ..., "quantity": ...}` entries rather than a JSON object
/// with struct keys. Round-trip through `serde_json` is preserved by the
/// implementation below.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct StateVector {
    /// Per-primitive available quantities. Missing keys are interpreted as
    /// quantity = 0 by the yield calculation (per Clarification 9 Section 2:
    /// an absent prerequisite contributes 0/aᵢ = 0 to `min_i(xᵢ/aᵢ)`).
    pub activations: HashMap<PrimitiveId, f64>,
}

/// Internal serde shape for a single activation entry.
#[derive(Serialize, Deserialize)]
struct StateVectorEntry {
    primitive: PrimitiveId,
    quantity: f64,
}

impl Serialize for StateVector {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let entries: Vec<StateVectorEntry> = self
            .activations
            .iter()
            .map(|(primitive, quantity)| StateVectorEntry {
                primitive: *primitive,
                quantity: *quantity,
            })
            .collect();
        let mut state = serializer.serialize_struct("StateVector", 1)?;
        state.serialize_field("activations", &entries)?;
        state.end()
    }
}

impl<'de> Deserialize<'de> for StateVector {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        #[derive(Deserialize)]
        struct Shim {
            activations: Vec<StateVectorEntry>,
        }
        let shim = Shim::deserialize(deserializer)?;
        let mut map = HashMap::with_capacity(shim.activations.len());
        for entry in shim.activations {
            map.insert(entry.primitive, entry.quantity);
        }
        Ok(Self { activations: map })
    }
}

impl StateVector {
    /// Construct an empty state vector (no activations recorded; every
    /// primitive is treated as quantity 0).
    pub fn empty() -> Self {
        Self::default()
    }

    /// Construct from an explicit activation map.
    pub fn new(activations: HashMap<PrimitiveId, f64>) -> Self {
        Self { activations }
    }

    /// Record or overwrite the activation for a single primitive.
    pub fn set(&mut self, primitive: PrimitiveId, quantity: f64) {
        self.activations.insert(primitive, quantity);
    }

    /// Look up the available quantity of a primitive. Missing entries
    /// return 0 per the Clarification 9 Section 2 convention.
    pub fn quantity(&self, primitive: &PrimitiveId) -> f64 {
        self.activations.get(primitive).copied().unwrap_or(0.0)
    }

    /// Number of primitives with an explicitly recorded activation.
    pub fn len(&self) -> usize {
        self.activations.len()
    }

    /// Whether no activations are recorded.
    pub fn is_empty(&self) -> bool {
        self.activations.is_empty()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn primitive_id_noetic_constructor() {
        let p = PrimitiveId::noetic(CognitiveOperator::CO2);
        assert_eq!(p.register_annotation(), None);
        assert_eq!(p.canonical_notation(), "^2");
    }

    #[test]
    fn primitive_id_noetic_with_register() {
        let p = PrimitiveId::noetic_with_register(CognitiveOperator::CO2, Register::Analytical);
        assert_eq!(p.register_annotation(), Some(Register::Analytical));
        assert_eq!(p.canonical_notation(), "^2|A");
    }

    #[test]
    fn primitive_id_compound_with_register() {
        let p = PrimitiveId::compound_with_register(
            CognitiveOperator::CO2,
            Domain::Cognitive,
            CoreDrive::F2Wisdom,
            Register::Analytical,
        );
        assert_eq!(p.canonical_notation(), "^2^C_{F_2}|A");
    }

    #[test]
    fn primitive_id_affective_register_uses_lowercase_f() {
        let p = PrimitiveId::drive_with_register(CoreDrive::F2Wisdom, Register::Affective);
        assert_eq!(p.canonical_notation(), "F_2|f");
    }

    #[test]
    fn production_target_new() {
        let t = ProductionTarget::new("paper");
        assert_eq!(t.name, "paper");
    }

    #[test]
    fn recipe_new_has_no_leakages_no_conditions() {
        let r = Recipe::new(
            ProductionTarget::new("refusal"),
            vec![(PrimitiveId::drive(CoreDrive::F2Wisdom), 2.0)],
        );
        assert!(r.leakages.is_empty());
        assert!(r.conditions.catalysts.is_empty());
        assert!(r.conditions.inhibitors.is_empty());
        assert_eq!(r.arity(), 1);
        assert!(!r.is_empty());
    }

    #[test]
    fn state_vector_missing_primitive_is_zero() {
        let s = StateVector::empty();
        let p = PrimitiveId::drive(CoreDrive::F2Wisdom);
        assert_eq!(s.quantity(&p), 0.0);
    }
}
