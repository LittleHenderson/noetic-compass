//! Cognitive State Division (÷)
//!
//! Algebraically generative operation for same-domain ratio analysis.
//! Reveals causal structure between two cognitive states.
//!
//! Constraints:
//! - Both operands must share the same domain (cross-domain division is undefined)
//! - Result preserves domain
//! - Operator ratio uses midpoint for non-trivial cases

use crate::ontology::{CognitiveOperator, CognitiveStateId, CoreDrive, Domain};
use super::drives::drive_ratio;
use super::error::AlgebraError;

/// Check if two operators form an involution pair.
fn is_operator_involution_pair(a: CognitiveOperator, b: CognitiveOperator) -> bool {
    for &(x, y) in &CognitiveOperator::INVOLUTION_PAIRS {
        if (a == x && b == y) || (a == y && b == x) {
            return true;
        }
    }
    false
}

/// Divide two cognitive states (same-domain ratio analysis).
///
/// Returns the quotient state or an error if:
/// - Domains differ (cross-domain division undefined)
/// - The result violates admissibility
pub fn divide_states(
    left: CognitiveStateId,
    left_drive: CoreDrive,
    right: CognitiveStateId,
    right_drive: CoreDrive,
) -> Result<(CognitiveStateId, CoreDrive), AlgebraError> {
    // 1. Same domain required
    if left.domain() != right.domain() {
        return Err(AlgebraError::CrossDomainDivision {
            left: format!("{}^{}", left.operator(), left.domain()),
            right: format!("{}^{}", right.operator(), right.domain()),
        });
    }

    // 2. Operator ratio
    let lo = left.operator();
    let ro = right.operator();
    let new_op = if lo == ro {
        // Complete resolution: same operator divided by itself = identity
        CognitiveOperator::CO0
    } else if is_operator_involution_pair(lo, ro) {
        // Perfect opposition: involution pair quotient = identity
        CognitiveOperator::CO0
    } else {
        // Midpoint difference: captures the "distance" between two operators
        let idx = ((lo.index() + ro.index()) / 2) % 10;
        CognitiveOperator::from_index(idx).unwrap()
    };

    // 3. Domain preserved
    let new_domain = left.domain();

    // 4. Drive ratio
    let new_drive = drive_ratio(left_drive, right_drive);

    // 5. Admissibility check
    let result = CognitiveStateId::new(new_op, new_domain);
    if new_op != CognitiveOperator::CO0 {
        let source = left;
        if !new_op.is_admissible(source, result) {
            return Err(AlgebraError::AdmissibilityViolation {
                operator: format!("{new_op}"),
                source: format!("{source}"),
                target: format!("{result}"),
            });
        }
    }

    Ok((result, new_drive))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_same_operator_yields_identity() {
        let co5_o = CognitiveStateId::new(CognitiveOperator::CO5, Domain::Operational);
        let (result, _) = divide_states(
            co5_o, CoreDrive::F3Vitality,
            co5_o, CoreDrive::F3Vitality,
        ).unwrap();
        assert_eq!(result.operator(), CognitiveOperator::CO0);
        assert_eq!(result.domain(), Domain::Operational);
    }

    #[test]
    fn test_involution_pair_yields_identity() {
        let co8_o = CognitiveStateId::new(CognitiveOperator::CO8, Domain::Operational);
        let co9_o = CognitiveStateId::new(CognitiveOperator::CO9, Domain::Operational);
        let (result, _) = divide_states(
            co8_o, CoreDrive::F5Agency,
            co9_o, CoreDrive::F5Agency,
        ).unwrap();
        assert_eq!(result.operator(), CognitiveOperator::CO0);
    }

    #[test]
    fn test_cross_domain_error() {
        let co3_p = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Principled);
        let co5_e = CognitiveStateId::new(CognitiveOperator::CO5, Domain::Evaluative);
        let result = divide_states(
            co3_p, CoreDrive::F4Connection,
            co5_e, CoreDrive::F4Connection,
        );
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AlgebraError::CrossDomainDivision { .. }));
    }

    #[test]
    fn test_same_domain_valid() {
        let co8_o = CognitiveStateId::new(CognitiveOperator::CO8, Domain::Operational);
        let co2_o = CognitiveStateId::new(CognitiveOperator::CO2, Domain::Operational);
        let result = divide_states(
            co8_o, CoreDrive::F4Connection,
            co2_o, CoreDrive::F4Connection,
        );
        assert!(result.is_ok());
        let (state, _) = result.unwrap();
        assert_eq!(state.domain(), Domain::Operational);
        // Midpoint of 8 and 2 = 5
        assert_eq!(state.operator(), CognitiveOperator::CO5);
    }

    #[test]
    fn test_domain_preserved() {
        let co1_c = CognitiveStateId::new(CognitiveOperator::CO1, Domain::Cognitive);
        let co7_c = CognitiveStateId::new(CognitiveOperator::CO7, Domain::Cognitive);
        let (result, _) = divide_states(
            co1_c, CoreDrive::F2Wisdom,
            co7_c, CoreDrive::F2Wisdom,
        ).unwrap();
        assert_eq!(result.domain(), Domain::Cognitive);
    }
}
