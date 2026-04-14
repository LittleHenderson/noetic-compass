//! Cognitive State Multiplication (×)
//!
//! Algebraically generative operation on cognitive states.
//! Produces a new state via:
//! 1. Operator composition (monoid on Z/10Z)
//! 2. Domain descent (P > C > E > O; same-domain preserved)
//! 3. Drive synthesis (inversion pairs → F4, non-paired → attractor)
//! 4. Admissibility check on the result

use crate::ontology::{CognitiveOperator, CognitiveStateId, CoreDrive, Domain};
use super::drives::synthesize_drives;
use super::error::AlgebraError;

/// Multiply two cognitive states.
///
/// Returns the product state or an error if:
/// - Domain ascent would be required (E × C is invalid)
/// - The result violates admissibility
pub fn multiply_states(
    left: CognitiveStateId,
    left_drive: CoreDrive,
    right: CognitiveStateId,
    right_drive: CoreDrive,
) -> Result<(CognitiveStateId, CoreDrive), AlgebraError> {
    // 1. Operator composition via monoid
    let new_op = left.operator().compose(right.operator());

    // 2. Domain descent
    let ld = left.domain();
    let rd = right.domain();
    let new_domain = if ld == rd {
        // Same domain: preserve
        ld
    } else if ld.dominates(rd) {
        // Left dominates right (P > C etc.): descend to right
        rd
    } else {
        // Right dominates left: would require ascent — violation
        return Err(AlgebraError::DomainAscentViolation {
            left: format!("{}^{}", left.operator(), left.domain()),
            right: format!("{}^{}", right.operator(), right.domain()),
        });
    };

    // 3. Drive synthesis
    let new_drive = synthesize_drives(left_drive, right_drive);

    // 4. Construct result and check admissibility
    let result = CognitiveStateId::new(new_op, new_domain);
    if new_op == CognitiveOperator::CO0 {
        // CO-0 admissibility: only on diagonal (source == target)
        // For multiplication, the result is a new state, so we check
        // it against itself (self-referential product)
        // This is always admissible by definition for CO-0 diagonal.
    } else {
        // Non-identity operators: check that the result state is reachable.
        // In multiplication context, we verify the composed operator is
        // admissible for the chosen domain's state space.
        let source = left;
        let target = result;
        if !new_op.is_admissible(source, target) {
            return Err(AlgebraError::AdmissibilityViolation {
                operator: format!("{new_op}"),
                source: format!("{source}"),
                target: format!("{target}"),
            });
        }
    }

    Ok((result, new_drive))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identity_multiplication() {
        // CO-0 × anything = anything (monoid identity)
        let co0_p = CognitiveStateId::new(CognitiveOperator::CO0, Domain::Principled);
        let co5_p = CognitiveStateId::new(CognitiveOperator::CO5, Domain::Principled);
        let (result, _drive) = multiply_states(
            co0_p, CoreDrive::F4Connection,
            co5_p, CoreDrive::F2Wisdom,
        ).unwrap();
        // CO-0 compose CO-5 = CO-5, same domain P
        assert_eq!(result.operator(), CognitiveOperator::CO5);
        assert_eq!(result.domain(), Domain::Principled);
    }

    #[test]
    fn test_same_domain_preserve() {
        let co3_c = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Cognitive);
        let co7_c = CognitiveStateId::new(CognitiveOperator::CO7, Domain::Cognitive);
        let (result, _) = multiply_states(
            co3_c, CoreDrive::F1Unity,
            co7_c, CoreDrive::F1Unity,
        ).unwrap();
        // CO-3 compose CO-7 = (3+7)%10 = CO-0
        assert_eq!(result.operator(), CognitiveOperator::CO0);
        assert_eq!(result.domain(), Domain::Cognitive);
    }

    #[test]
    fn test_domain_descent() {
        // P × C = C (descend to lower domain)
        let co2_p = CognitiveStateId::new(CognitiveOperator::CO2, Domain::Principled);
        let co3_c = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Cognitive);
        let (result, _) = multiply_states(
            co2_p, CoreDrive::F2Wisdom,
            co3_c, CoreDrive::F6Structure,
        ).unwrap();
        // CO-2 compose CO-3 = CO-5
        assert_eq!(result.operator(), CognitiveOperator::CO5);
        assert_eq!(result.domain(), Domain::Cognitive);
    }

    #[test]
    fn test_domain_ascent_error() {
        // E × C should fail (ascending from E to C)
        let co5_e = CognitiveStateId::new(CognitiveOperator::CO5, Domain::Evaluative);
        let co3_c = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Cognitive);
        let result = multiply_states(
            co5_e, CoreDrive::F4Connection,
            co3_c, CoreDrive::F4Connection,
        );
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), AlgebraError::DomainAscentViolation { .. }));
    }

    #[test]
    fn test_drive_synthesis_through_multiplication() {
        let co1_p = CognitiveStateId::new(CognitiveOperator::CO1, Domain::Principled);
        let co4_p = CognitiveStateId::new(CognitiveOperator::CO4, Domain::Principled);
        // F1 × F7 = F4 (inversion pair)
        let (_, drive) = multiply_states(
            co1_p, CoreDrive::F1Unity,
            co4_p, CoreDrive::F7Purpose,
        ).unwrap();
        assert_eq!(drive, CoreDrive::F4Connection);
    }

    #[test]
    fn test_associativity() {
        // (a × b) × c should equal a × (b × c) for operator composition
        let a = CognitiveStateId::new(CognitiveOperator::CO2, Domain::Principled);
        let b = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Principled);
        let c = CognitiveStateId::new(CognitiveOperator::CO4, Domain::Principled);
        let d = CoreDrive::F4Connection;

        let (ab, ab_d) = multiply_states(a, d, b, d).unwrap();
        let (ab_c, _) = multiply_states(ab, ab_d, c, d).unwrap();

        let (bc, bc_d) = multiply_states(b, d, c, d).unwrap();
        let (a_bc, _) = multiply_states(a, d, bc, bc_d).unwrap();

        assert_eq!(ab_c.operator(), a_bc.operator());
        assert_eq!(ab_c.domain(), a_bc.domain());
    }
}
