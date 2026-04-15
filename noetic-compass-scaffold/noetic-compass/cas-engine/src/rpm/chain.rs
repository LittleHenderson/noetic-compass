//! RPM Chain Evaluation with D/W/P Stage Classification
//!
//! Based on v6.1 Definition 7.10 (evalChain) adapted for v7.4 section-retraction:
//!   evalChain_m = check(A0) >> check(D_m) >> check(W_m) >> check(P_m) >> return(Outcome_m)
//!
//! CRITICAL: This uses SECTION-RETRACTION semantics (v7.4), NOT monadic bind (v6.1).
//!   - Forward evaluation (check prerequisites in order) works
//!   - Backward reconstruction does NOT recover original state
//!   - εI ∘ ηI = idI, but ηI ∘ εI ≠ idR(I)

use serde::{Deserialize, Serialize};
use std::fmt;

/// D/W/P developmental stage classification.
///
/// Based on CAS Cognitive Framework §2.4 chain completion levels:
/// Level 0 = no satisfaction, Level 3 = complete chain.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum DwpStage {
    // Desire stages
    Dormant,   // score < 0.2 — no motivation detected
    Awakening, // 0.2 ≤ score < 0.5 — motivation acknowledged but weak
    Peak,      // 0.5 ≤ score < 0.7 — strong clear motivation
    Fading,    // score ≥ 0.7 — present but potentially declining

    // Wisdom stages
    Unaware,   // score < 0.2 — doesn't know what it doesn't know
    Learning,  // 0.2 ≤ score < 0.5 — actively acquiring, gaps remain
    Knowing,   // 0.5 ≤ score < 0.8 — sufficient knowledge to act
    Mastering, // score ≥ 0.8 — deep expertise evident

    // Power stages
    Nascent,    // score < 0.2 — no resources identified
    Developing, // 0.2 ≤ score < 0.5 — some resources, gaps remain
    Capable,    // 0.5 ≤ score < 0.8 — all resources available
    Mastery,    // score ≥ 0.8 — surplus resources
}

impl DwpStage {
    /// Classify a Desire score into its stage.
    pub fn classify_desire(score: f64) -> Self {
        if score < 0.2 {
            Self::Dormant
        } else if score < 0.5 {
            Self::Awakening
        } else if score < 0.7 {
            Self::Peak
        } else {
            Self::Fading
        }
    }

    /// Classify a Wisdom score into its stage.
    pub fn classify_wisdom(score: f64) -> Self {
        if score < 0.2 {
            Self::Unaware
        } else if score < 0.5 {
            Self::Learning
        } else if score < 0.8 {
            Self::Knowing
        } else {
            Self::Mastering
        }
    }

    /// Classify a Power score into its stage.
    pub fn classify_power(score: f64) -> Self {
        if score < 0.2 {
            Self::Nascent
        } else if score < 0.5 {
            Self::Developing
        } else if score < 0.8 {
            Self::Capable
        } else {
            Self::Mastery
        }
    }

    /// Level 0-3 for chain completion (Definition 2.10 from Cognitive Framework).
    pub fn level(&self) -> u8 {
        match self {
            Self::Dormant | Self::Unaware | Self::Nascent => 0,
            Self::Awakening | Self::Learning | Self::Developing => 1,
            Self::Peak | Self::Knowing | Self::Capable => 2,
            Self::Fading | Self::Mastering | Self::Mastery => 3,
        }
    }
}

impl fmt::Display for DwpStage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Dormant => write!(f, "Dormant"),
            Self::Awakening => write!(f, "Awakening"),
            Self::Peak => write!(f, "Peak"),
            Self::Fading => write!(f, "Fading"),
            Self::Unaware => write!(f, "Unaware"),
            Self::Learning => write!(f, "Learning"),
            Self::Knowing => write!(f, "Knowing"),
            Self::Mastering => write!(f, "Mastering"),
            Self::Nascent => write!(f, "Nascent"),
            Self::Developing => write!(f, "Developing"),
            Self::Capable => write!(f, "Capable"),
            Self::Mastery => write!(f, "Mastery"),
        }
    }
}

/// Result of evaluating an RPM chain for a single drive.
///
/// Per v7.4 Correction #2: forward evaluation works but backward
/// reconstruction does NOT recover original state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RpmChainResult {
    pub drive_index: usize,
    pub a0_satisfied: bool,
    pub desire_satisfied: bool,
    pub desire_stage: DwpStage,
    pub desire_score: f64,
    pub wisdom_satisfied: bool,
    pub wisdom_stage: DwpStage,
    pub wisdom_score: f64,
    pub power_satisfied: bool,
    pub power_stage: DwpStage,
    pub power_score: f64,
    pub first_failure: Option<String>,
    pub completeness: f64,
}

/// Satisfaction threshold for prerequisite checking.
const SATISFACTION_THRESHOLD: f64 = 0.5;

/// Evaluate the RPM chain for a drive using section-retraction semantics.
///
/// Per v6.1 Definition 7.10 (adapted for v7.4):
///   evalChain_m = check(A0) >> check(D_m) >> check(W_m) >> check(P_m) >> return(Outcome_m)
///
/// Short-circuits at the first failure. Forward evaluation only — no backward
/// reconstruction per v7.4 Correction #2.
pub fn evaluate_chain(
    drive_index: usize,
    a0_score: f64,
    desire_score: f64,
    wisdom_score: f64,
    power_score: f64,
) -> RpmChainResult {
    let a0_satisfied = a0_score >= SATISFACTION_THRESHOLD;
    let d_stage = DwpStage::classify_desire(desire_score);
    let w_stage = DwpStage::classify_wisdom(wisdom_score);
    let p_stage = DwpStage::classify_power(power_score);

    // Sequential prerequisite checking (short-circuit on failure)
    let (d_satisfied, w_satisfied, p_satisfied, first_failure);

    if !a0_satisfied {
        d_satisfied = false;
        w_satisfied = false;
        p_satisfied = false;
        first_failure = Some("A0 (Pure Desire)".to_string());
    } else if desire_score < SATISFACTION_THRESHOLD {
        d_satisfied = false;
        w_satisfied = false;
        p_satisfied = false;
        first_failure = Some(format!("D{} (Motivational Activation)", drive_index + 1));
    } else {
        d_satisfied = true;
        if wisdom_score < SATISFACTION_THRESHOLD {
            w_satisfied = false;
            p_satisfied = false;
            first_failure = Some(format!("W{} (Knowledge Integration)", drive_index + 1));
        } else {
            w_satisfied = true;
            if power_score < SATISFACTION_THRESHOLD {
                p_satisfied = false;
                first_failure = Some(format!("P{} (Execution Capability)", drive_index + 1));
            } else {
                p_satisfied = true;
                first_failure = None;
            }
        }
    }

    // Completeness: proportion of chain satisfied (0, 0.25, 0.5, 0.75, 1.0)
    let satisfied_count = [a0_satisfied, d_satisfied, w_satisfied, p_satisfied]
        .iter()
        .filter(|&&s| s)
        .count();
    let completeness = satisfied_count as f64 / 4.0;

    RpmChainResult {
        drive_index,
        a0_satisfied,
        desire_satisfied: d_satisfied,
        desire_stage: d_stage,
        desire_score,
        wisdom_satisfied: w_satisfied,
        wisdom_stage: w_stage,
        wisdom_score,
        power_satisfied: p_satisfied,
        power_stage: p_stage,
        power_score,
        first_failure,
        completeness,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_full_chain_satisfied() {
        let result = evaluate_chain(0, 0.8, 0.7, 0.6, 0.5);
        assert!(result.a0_satisfied);
        assert!(result.desire_satisfied);
        assert!(result.wisdom_satisfied);
        assert!(result.power_satisfied);
        assert!(result.first_failure.is_none());
        assert_eq!(result.completeness, 1.0);
    }

    #[test]
    fn test_failure_at_a0() {
        let result = evaluate_chain(0, 0.3, 0.9, 0.9, 0.9);
        assert!(!result.a0_satisfied);
        assert!(!result.desire_satisfied);
        assert!(result.first_failure.as_ref().unwrap().contains("A0"));
        assert_eq!(result.completeness, 0.0);
    }

    #[test]
    fn test_failure_at_wisdom() {
        let result = evaluate_chain(5, 0.8, 0.7, 0.3, 0.9);
        assert!(result.a0_satisfied);
        assert!(result.desire_satisfied);
        assert!(!result.wisdom_satisfied);
        assert!(!result.power_satisfied);
        assert!(result.first_failure.as_ref().unwrap().contains("W6"));
        assert_eq!(result.completeness, 0.5);
    }

    #[test]
    fn test_failure_at_power() {
        let result = evaluate_chain(2, 0.6, 0.6, 0.6, 0.3);
        assert!(result.a0_satisfied);
        assert!(result.desire_satisfied);
        assert!(result.wisdom_satisfied);
        assert!(!result.power_satisfied);
        assert!(result.first_failure.as_ref().unwrap().contains("P3"));
        assert_eq!(result.completeness, 0.75);
    }

    #[test]
    fn test_desire_stages() {
        assert_eq!(DwpStage::classify_desire(0.1), DwpStage::Dormant);
        assert_eq!(DwpStage::classify_desire(0.3), DwpStage::Awakening);
        assert_eq!(DwpStage::classify_desire(0.6), DwpStage::Peak);
        assert_eq!(DwpStage::classify_desire(0.8), DwpStage::Fading);
    }

    #[test]
    fn test_wisdom_stages() {
        assert_eq!(DwpStage::classify_wisdom(0.1), DwpStage::Unaware);
        assert_eq!(DwpStage::classify_wisdom(0.3), DwpStage::Learning);
        assert_eq!(DwpStage::classify_wisdom(0.6), DwpStage::Knowing);
        assert_eq!(DwpStage::classify_wisdom(0.9), DwpStage::Mastering);
    }

    #[test]
    fn test_power_stages() {
        assert_eq!(DwpStage::classify_power(0.1), DwpStage::Nascent);
        assert_eq!(DwpStage::classify_power(0.3), DwpStage::Developing);
        assert_eq!(DwpStage::classify_power(0.6), DwpStage::Capable);
        assert_eq!(DwpStage::classify_power(0.9), DwpStage::Mastery);
    }

    #[test]
    fn test_stage_levels() {
        assert_eq!(DwpStage::Dormant.level(), 0);
        assert_eq!(DwpStage::Awakening.level(), 1);
        assert_eq!(DwpStage::Peak.level(), 2);
        assert_eq!(DwpStage::Fading.level(), 3);
    }

    #[test]
    fn test_section_retraction_asymmetry() {
        // Forward check: if A0 passes and D passes, we proceed.
        // But we CANNOT infer the exact A0 score from downstream results.
        // This test verifies we don't store or expose backward inference.
        let result = evaluate_chain(0, 0.51, 0.51, 0.51, 0.51);
        assert!(result.a0_satisfied);
        assert!(result.desire_satisfied);
        assert!(result.wisdom_satisfied);
        assert!(result.power_satisfied);
        // The result only records boolean satisfaction, not back-inferred scores
    }
}
