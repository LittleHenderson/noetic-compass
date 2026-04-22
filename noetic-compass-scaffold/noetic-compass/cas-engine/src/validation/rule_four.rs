//! Rule 4 — Same-Noetic Cross-Register `×` Admissibility Validator.
//!
//! Per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10 Section 4,
//! same-Noetic, multi-register expressions using `×` are **invalid by
//! default**. Such expressions are structurally ambiguous — they could denote
//! co-presence (`+`), architectural specification (`|⟨…⟩`), or true emergent
//! cross-register integration. The ambiguity is resolved only when the
//! author explicitly names the emergent integrated result (e.g.,
//! `(^2^P|T × ^2^P|f) = ^2^P|TF`).
//!
//! This validator inspects a list of cross-product operands (AST-level
//! data) and returns:
//!
//! - [`RuleFourResult::Valid`] when the expression is admissible, either
//!   because:
//!   - The operands differ in their core (Noetic, Domain, or Drive) — this
//!     is different-state integration, explicitly licensed under
//!     Clarification 10 Section 8 ("Valid different-state integration"); or
//!   - The operands share identical cores and differ only in register, AND
//!     an emergent result is explicitly supplied; or
//!   - Only one operand is supplied (no `×` to validate).
//!
//! - [`RuleFourResult::ViolationRequiresEmergentResult`] when operands
//!   share identical cores, at least two differ in register, and no emergent
//!   result is supplied. The variant carries the shared core and the
//!   distinct-register list so callers can produce framework-aware error
//!   messages citing Clarification 10 Section 4.
//!
//! # Design Note — Validator Input Type
//!
//! This validator inspects EXPRESSION-TREE DATA; it does NOT parse text.
//! Text parsing is the Python compiler's job (`api/notation/compiler.py`).
//! The Rust engine receives AST-level data via PyO3 or serde and validates
//! structural compliance. The [`CognitiveStateWithRegister`] type provided
//! here is a minimal AST view carrying exactly the fields Rule 4 needs.
//! It is intentionally a thin data-only struct; the compiler may produce
//! these directly, or wrap existing compound-state AST nodes.

use crate::ontology::register::Register;
use crate::ontology::register_set::NamedEmergentRegister;
use crate::ontology::{CognitiveOperator, CoreDrive, Domain};

// ---------------------------------------------------------------------------
// CognitiveStateWithRegister — AST-level operand view
// ---------------------------------------------------------------------------

/// A minimal AST-level view of a CAS state literal with its Register
/// annotation.
///
/// Rule 4 inspects exactly four fields per operand: Noetic, Domain (optional),
/// Drive (optional), and Register (optional). Everything else about the
/// operand (source span, probability vector, etc.) is irrelevant to Rule 4
/// and is deliberately excluded from this view. Callers on the Python side
/// typically construct this from their own AST node types when invoking the
/// validator via PyO3.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CognitiveStateWithRegister {
    /// The Noetic operator (CO-0..CO-9).
    pub noetic: CognitiveOperator,
    /// The Processing Domain (P, C, E, O), if specified. Pure-Noetic
    /// expressions (no domain) produce `None` here.
    pub domain: Option<Domain>,
    /// The Core Drive (F1..F7), if specified. Drive-less expressions produce
    /// `None` here.
    pub drive: Option<CoreDrive>,
    /// The Register annotation (|T, |A, |f, |E), if specified. Register-
    /// neutral (v7.4-compatible) operands produce `None` here.
    pub register: Option<Register>,
}

impl CognitiveStateWithRegister {
    /// Construct an operand view.
    pub fn new(
        noetic: CognitiveOperator,
        domain: Option<Domain>,
        drive: Option<CoreDrive>,
        register: Option<Register>,
    ) -> Self {
        Self {
            noetic,
            domain,
            drive,
            register,
        }
    }

    /// Extract the register-independent core for Rule 4 core-equality
    /// comparison.
    pub fn core(&self) -> CognitiveStateCore {
        CognitiveStateCore {
            noetic: self.noetic,
            domain: self.domain,
            drive: self.drive,
        }
    }
}

// ---------------------------------------------------------------------------
// CognitiveStateCore — the register-independent part of an operand
// ---------------------------------------------------------------------------

/// The register-INDEPENDENT part of a cognitive-state operand: the Noetic,
/// Domain, and Drive fields. Rule 4 compares cores across cross-product
/// operands to decide whether the expression is same-state (all cores equal)
/// or different-state (any core differs).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CognitiveStateCore {
    pub noetic: CognitiveOperator,
    pub domain: Option<Domain>,
    pub drive: Option<CoreDrive>,
}

// ---------------------------------------------------------------------------
// RuleFourResult
// ---------------------------------------------------------------------------

/// The result of [`validate_same_noetic_cross_product`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuleFourResult {
    /// The cross-product expression is admissible under Clarification 10
    /// Section 4.
    Valid,
    /// The cross-product expression is a same-Noetic, multi-register `×`
    /// without an emergent result — Rule 4 requires the author to specify
    /// the integrated fused state or rewrite to `+` / `|⟨…⟩`.
    ///
    /// The shared core and the distinct-register list are carried so error
    /// formatters can produce framework-aware messages (e.g., cite
    /// Clarification 10 Section 4 and name the specific registers).
    ViolationRequiresEmergentResult {
        /// The shared Noetic/Domain/Drive core of all operands.
        core: CognitiveStateCore,
        /// The distinct registers observed across operands (in the order
        /// they first appear in the operand list).
        registers: Vec<Register>,
    },
}

// ---------------------------------------------------------------------------
// validate_same_noetic_cross_product
// ---------------------------------------------------------------------------

/// Validate a list of `×`-cross-product operands against Rule 4 from
/// Clarification 10 Section 4.
///
/// # Semantics
///
/// 1. Extract the [`CognitiveStateCore`] (Noetic + Domain + Drive, ignoring
///    Register) from each operand.
/// 2. If the cores are pairwise equal AND at least two operands differ in
///    Register:
///    - If `named_emergent_result` is `Some(_)`: return
///      [`RuleFourResult::Valid`].
///    - Else: return
///      [`RuleFourResult::ViolationRequiresEmergentResult`] with the shared
///      core and the list of distinct registers.
/// 3. If the cores differ in any field (Noetic, Domain, or Drive): return
///    [`RuleFourResult::Valid`]. This is different-state integration, which
///    Clarification 10 Section 8 explicitly lists as valid.
/// 4. Degenerate cases:
///    - Zero operands: `Valid` (no `×` expression exists).
///    - One operand: `Valid` (no `×` to validate).
///    - All operands same register: `Valid` (not a multi-register
///      expression — this is the pathological repeat case, not what Rule 4
///      guards against; it reduces to a single term).
///
/// # Note on "at least two operands differ in register"
///
/// Per Clarification 10 Section 2C, Rule 4 targets the structural pattern
/// `X|R1 × X|R2 × ...` with R1 ≠ R2. An expression like `X|T × X|T` would
/// not instantiate the ambiguity Rule 4 guards against (same register on
/// both sides means no "cross-register integration" claim is being made),
/// so we treat it as valid. The spec focuses on DISTINCT registers because
/// that is where the three-way ambiguity (co-presence / specification /
/// integration) arises.
pub fn validate_same_noetic_cross_product(
    operands: &[CognitiveStateWithRegister],
    named_emergent_result: Option<&NamedEmergentRegister>,
) -> RuleFourResult {
    // Degenerate: 0 or 1 operand — no `×` to validate.
    if operands.len() < 2 {
        return RuleFourResult::Valid;
    }

    // Extract cores and check pairwise equality.
    let first_core = operands[0].core();
    let all_cores_equal = operands.iter().all(|op| op.core() == first_core);

    if !all_cores_equal {
        // Different-state integration — Clarification 10 Section 8 licenses
        // `×` for operands whose cores differ.
        return RuleFourResult::Valid;
    }

    // All cores equal — now check whether registers differ. "Different
    // register flavors" counts each distinct Some(register) AND the
    // presence of any None as separate flavors. An unannotated operand
    // paired with an annotated operand still represents multiple distinct
    // register states (one being unspecified).
    let (distinct_registers, saw_register_neutral) = collect_distinct_registers(operands);
    let flavor_count = distinct_registers.len() + if saw_register_neutral { 1 } else { 0 };

    // If fewer than 2 distinct flavors, no multi-register integration is
    // being claimed (all operands share the same register annotation).
    // Not the structural pattern Rule 4 guards against.
    if flavor_count < 2 {
        return RuleFourResult::Valid;
    }

    // Same core, multiple distinct register flavors — this IS the Rule 4
    // pattern.
    if named_emergent_result.is_some() {
        // Author has specified the emergent integrated result: admissible
        // per Clarification 10 Section 2C.
        RuleFourResult::Valid
    } else {
        // No emergent result specified: rewrite required.
        RuleFourResult::ViolationRequiresEmergentResult {
            core: first_core,
            registers: distinct_registers,
        }
    }
}

// ---------------------------------------------------------------------------
// validate_same_noetic_cross_product_batch — ADR-06 Rust engine batch API
// ---------------------------------------------------------------------------

/// A single Rule 4 expression in batch form: a list of cross-product operands
/// plus an optional [`NamedEmergentRegister`] declaring the emergent fused
/// result (when applicable).
///
/// Used by [`validate_same_noetic_cross_product_batch`] so one PyO3 crossing
/// can validate many expressions at once. Each batch element is independent;
/// ordering is preserved in the returned `Vec<RuleFourResult>`.
pub type RuleFourBatchInput = (Vec<CognitiveStateWithRegister>, Option<NamedEmergentRegister>);

/// Batch version of [`validate_same_noetic_cross_product`] (ADR-06).
///
/// Applies the existing per-sample validator to each `(operands, named_emergent)`
/// pair and collects results into a `Vec<RuleFourResult>` preserving input
/// order: `result[i]` is the validation outcome for `expressions[i]`.
///
/// # Determinism
///
/// This function performs NO parallelism and introduces no non-determinism.
/// It is a straight iterate-and-collect wrapper over the per-sample function,
/// specified by ADR-06 primarily to amortize PyO3 crossing cost for the
/// CAS-Native v2 training pipeline (see
/// `docs/architecture/cas_native_v2_adrs.md` ADR-06).
///
/// # Empty batch
///
/// Returns an empty `Vec` for an empty input slice. No allocations beyond the
/// result `Vec`'s zero-capacity initialization.
pub fn validate_same_noetic_cross_product_batch(
    expressions: &[RuleFourBatchInput],
) -> Vec<RuleFourResult> {
    expressions
        .iter()
        .map(|(operands, named)| {
            validate_same_noetic_cross_product(operands.as_slice(), named.as_ref())
        })
        .collect()
}

/// Collect the distinct explicit registers across operands in
/// first-appearance order, and separately report whether any operand was
/// register-neutral (`None`). The `None` sentinel is excluded from the
/// returned `Vec<Register>` because `Register` has no neutral variant; the
/// bool tracks its presence so the main validator can compute the true
/// flavor count as `returned_vec.len() + saw_none as usize`.
fn collect_distinct_registers(
    operands: &[CognitiveStateWithRegister],
) -> (Vec<Register>, bool) {
    let mut seen_some: Vec<Register> = Vec::new();
    let mut seen_none = false;
    for op in operands {
        match op.register {
            Some(r) => {
                if !seen_some.contains(&r) {
                    seen_some.push(r);
                }
            }
            None => seen_none = true,
        }
    }
    (seen_some, seen_none)
}

// ---------------------------------------------------------------------------
// Tests (module-local smoke tests)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ontology::{CognitiveOperator, CoreDrive, Domain};

    fn op_with(
        noetic: CognitiveOperator,
        domain: Domain,
        reg: Option<Register>,
    ) -> CognitiveStateWithRegister {
        CognitiveStateWithRegister::new(noetic, Some(domain), None, reg)
    }

    #[test]
    fn zero_operands_is_valid() {
        assert_eq!(
            validate_same_noetic_cross_product(&[], None),
            RuleFourResult::Valid
        );
    }

    #[test]
    fn one_operand_is_valid() {
        let ops = vec![op_with(
            CognitiveOperator::CO3,
            Domain::Principled,
            Some(Register::Transcendent),
        )];
        assert_eq!(
            validate_same_noetic_cross_product(&ops, None),
            RuleFourResult::Valid
        );
    }

    #[test]
    fn same_core_different_registers_no_named_result_is_violation() {
        let ops = vec![
            op_with(
                CognitiveOperator::CO3,
                Domain::Principled,
                Some(Register::Analytical),
            ),
            op_with(
                CognitiveOperator::CO3,
                Domain::Principled,
                Some(Register::Affective),
            ),
        ];
        match validate_same_noetic_cross_product(&ops, None) {
            RuleFourResult::ViolationRequiresEmergentResult { registers, .. } => {
                assert_eq!(registers.len(), 2);
            }
            other => panic!("expected violation, got {other:?}"),
        }
    }

    #[test]
    fn different_noetic_is_valid() {
        // ^5^C × ^6^C
        let ops = vec![
            op_with(CognitiveOperator::CO5, Domain::Cognitive, None),
            op_with(CognitiveOperator::CO6, Domain::Cognitive, None),
        ];
        assert_eq!(
            validate_same_noetic_cross_product(&ops, None),
            RuleFourResult::Valid
        );
    }

    #[test]
    fn same_core_with_named_emergent_result_is_valid() {
        let ops = vec![
            op_with(
                CognitiveOperator::CO2,
                Domain::Principled,
                Some(Register::Transcendent),
            ),
            op_with(
                CognitiveOperator::CO2,
                Domain::Principled,
                Some(Register::Affective),
            ),
        ];
        let named = NamedEmergentRegister::from_str("TF").unwrap();
        assert_eq!(
            validate_same_noetic_cross_product(&ops, Some(&named)),
            RuleFourResult::Valid
        );
    }
}
