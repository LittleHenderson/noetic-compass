//! CAS Validation — structural admissibility checks (CAS v7.7).
//!
//! This module hosts validators that enforce CAS-level admissibility rules
//! over expression-tree data (AST-level structures, not text). The first
//! inhabitant is Rule 4 from `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
//! Clarification 10 Section 4 — admissibility for same-Noetic, multi-register
//! `×` usage.
//!
//! Validation is separate from parsing and separate from scoring. The
//! compiler / parser (Python side, in `api/notation/compiler.py`) is
//! responsible for textual parsing and producing AST data. The Rust engine
//! receives AST-level data via PyO3 or serde, validates structural
//! compliance, and reports violations to the caller.

pub mod rule_four;

pub use rule_four::{
    validate_same_noetic_cross_product, CognitiveStateCore, CognitiveStateWithRegister,
    RuleFourResult,
};
