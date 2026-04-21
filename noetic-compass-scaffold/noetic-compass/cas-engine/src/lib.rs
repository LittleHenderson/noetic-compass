//! CAS Scoring Engine for Noetic Compass
//!
//! Implements the Cognitive Architecture System v7.4 (Corrected Edition)
//! scoring algorithms for AI psychological assessment, extended with the
//! CAS v7.5 Phenomenological Register axis per
//! `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8.
//!
//! CRITICAL: This crate implements four corrections from the v7.4 review:
//! 1. Admissibility Relations for operators (Dk ⊆ I × I)
//! 2. RPM as section-retraction, NOT adjunction
//! 3. Noetic Coverage uses COUNIT εI, not unit ηI
//! 4. State space is open probability simplex Δ39°
//!
//! CAS v7.5 adds an optional [`ontology::Register`] axis orthogonal to the
//! 40 Cognitive States and 7 Core Drives. v7.4 expressions (register-neutral)
//! remain fully valid; register-aware scoring is future work.
//!
//! CAS v7.6 adds Stoichiometric Production Semantics per
//! `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9. Production
//! semantics types live in [`ontology::recipe`] (Recipe, ProductionTarget,
//! StateVector, Leakage, Conditions, Catalyst, Inhibitor, PrimitiveId) and
//! yield-calculation algorithms live in [`scoring::yield_calc`]
//! (theoretical_yield, limiting_reagent, excess_capacity, efficiency). The
//! v7.6 layer is additive: no v7.4/v7.5 type, axiom, or signature is
//! modified.

pub mod algebra;
pub mod fractals;
pub mod inversions;
pub mod language;
pub mod metric;
pub mod ontology;
pub mod rpm;
pub mod scoring;
pub mod validation;

pub use ontology::Register;

// CAS v7.6 Stoichiometric Production Semantics re-exports (Clarification 9).
pub use ontology::{
    Catalyst, Conditions, Inhibitor, Leakage, PrimitiveId, ProductionTarget, Recipe, StateVector,
};

// CAS v7.7 Register Multiplicity re-exports (Clarification 10).
pub use ontology::{
    NamedEmergentRegister, NamedEmergentRegisterError, RegisterSet, RegisterSetError,
};
pub use validation::{
    validate_same_noetic_cross_product, CognitiveStateCore, CognitiveStateWithRegister,
    RuleFourResult,
};
pub use scoring::{
    efficiency, excess_capacity, limiting_reagent, theoretical_yield, LimitingReagent, Yield,
};

pub use casc_ir as compiler_ir;
pub use casc_syntax as compiler_syntax;
pub use casc_types as compiler_types;

#[cfg(feature = "python")]
pub mod python_bindings;

#[cfg(feature = "python")]
pub use python_bindings::cas_engine;
