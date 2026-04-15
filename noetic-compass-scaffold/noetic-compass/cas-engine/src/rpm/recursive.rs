//! Recursive RPM Evaluation
//!
//! When a node in the D→W→P chain is blocked, specific Cognitive Operator
//! pairs activate to resolve the blockage:
//!
//! - POWER blocked → CO-8/CO-9 (Causal Reasoning / Consequential Grounding)
//!   Spawns a CHILD D/W/P chain to acquire the missing resource. RECURSIVE.
//!
//! - WISDOM blocked → CO-5 (Receptive Integration) or CO-6 (Projective Assertion)
//!   CO-5: find an external source that carries the knowledge. RECURSIVE (child chain).
//!   CO-6: decompose into smaller components, each with its own chain. RECURSIVE (parallel).
//!
//! - DESIRE blocked → CO-1/CO-4/CO-7 (Attention / Intensity / Entrainment)
//!   Exposure loop: observe → intensify → repeat. ITERATIVE, not recursive.
//!
//! Max recursion depth: 5. Section-retraction holds at every level.
//! Desire loops do NOT count toward recursion depth.

use serde::{Deserialize, Serialize};

use super::chain::DwpStage;

/// How a blocked node was resolved.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ResolutionMechanism {
    /// CO-8/CO-9: scan for causes, identify solution. Spawns child chain.
    CausalSearch,
    /// CO-5: find external knowledge source. Spawns child chain.
    KnowledgeReception,
    /// CO-6: decompose into components. Spawns parallel child chains.
    KnowledgeDecomposition,
    /// CO-1/CO-4/CO-7: observe → intensify → repeat loop. Iterative.
    ExposureLoop,
}

/// Result for a single D, W, or P node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeResult {
    pub stage: DwpStage,
    pub score: f64,
    pub blocked: bool,
    pub resolved: bool,
    pub resolved_via: Option<ResolutionMechanism>,
}

/// Full recursive RPM evaluation result for one drive.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecursiveRpmResult {
    pub drive_index: usize,
    pub depth: u8,
    pub desire: NodeResult,
    pub wisdom: NodeResult,
    pub power: NodeResult,
    pub completeness: f64,
    pub sub_chains: Vec<RecursiveRpmResult>,
    pub exposure_cycles: u8,
    pub max_depth_reached: bool,
}

const SATISFACTION_THRESHOLD: f64 = 0.5;
const RESOLUTION_THRESHOLD: f64 = 0.4;
const EXPOSURE_THRESHOLD: f64 = 0.3;
const RESOLVED_SCORE: f64 = 0.8;
const DEFAULT_MAX_DEPTH: u8 = 5;
const MAX_EXPOSURE_CYCLES: u8 = 10;
const MAX_DECOMPOSITION_COMPONENTS: usize = 4;

fn make_node(score: f64, classify: fn(f64) -> DwpStage) -> NodeResult {
    let stage = classify(score);
    let blocked = score < SATISFACTION_THRESHOLD;
    NodeResult { stage, score, blocked, resolved: false, resolved_via: None }
}

/// Evaluate a recursive RPM chain for one drive.
///
/// `operator_scores`: 10 floats in [0,1], indexed by CO-0 through CO-9.
/// `chain_scores`: [desire, wisdom, power] for this drive.
/// `a0_score`: the A0 (Pure Desire) gate score.
pub fn evaluate_recursive(
    drive_index: usize,
    operator_scores: &[f64; 10],
    chain_scores: &[f64; 3],
    a0_score: f64,
    depth: u8,
    max_depth: u8,
) -> RecursiveRpmResult {
    let mut sub_chains = Vec::new();
    let mut exposure_cycles: u8 = 0;

    // A0 gate — if A0 fails, entire chain is blocked (no recursion can help)
    if a0_score < SATISFACTION_THRESHOLD {
        return RecursiveRpmResult {
            drive_index, depth,
            desire: NodeResult { stage: DwpStage::Dormant, score: chain_scores[0], blocked: true, resolved: false, resolved_via: None },
            wisdom: NodeResult { stage: DwpStage::Unaware, score: chain_scores[1], blocked: true, resolved: false, resolved_via: None },
            power: NodeResult { stage: DwpStage::Nascent, score: chain_scores[2], blocked: true, resolved: false, resolved_via: None },
            completeness: 0.0,
            sub_chains: vec![],
            exposure_cycles: 0,
            max_depth_reached: false,
        };
    }

    // --- DESIRE ---
    let mut desire = make_node(chain_scores[0], DwpStage::classify_desire);
    if desire.blocked {
        // Exposure loop: CO-1/CO-4/CO-7
        let co1 = operator_scores[1];
        let co4 = operator_scores[4];
        let co7 = operator_scores[7];
        let exposure_strength = (co1 + co4 + co7) / 3.0;

        if exposure_strength > EXPOSURE_THRESHOLD {
            // Simulate exposure cycles
            let mut effective = desire.score;
            for cycle in 0..MAX_EXPOSURE_CYCLES {
                effective += exposure_strength * 0.1;
                exposure_cycles = cycle + 1;
                if effective >= SATISFACTION_THRESHOLD {
                    break;
                }
            }
            if effective >= SATISFACTION_THRESHOLD {
                desire.resolved = true;
                desire.resolved_via = Some(ResolutionMechanism::ExposureLoop);
                desire.blocked = false;
            }
        }
        // Exposure loop does NOT increment depth
    }

    // --- WISDOM (only if desire satisfied or resolved) ---
    let mut wisdom = make_node(chain_scores[1], DwpStage::classify_wisdom);
    if !(desire.blocked && !desire.resolved) && wisdom.blocked && depth < max_depth {
        let co5 = operator_scores[5];
        let co6 = operator_scores[6];

        if co5 > co6 && co5 > RESOLUTION_THRESHOLD {
            // Path A: CO-5 Knowledge Reception
            // Resolution succeeds based on CO-5 activation strength
            let resolution_strength = co5;
            // Spawn informational sub-chain with boosted wisdom score
            let boosted = [chain_scores[0], resolution_strength, chain_scores[2]];
            let sub = evaluate_recursive(
                drive_index, operator_scores, &boosted,
                a0_score, depth + 1, max_depth,
            );
            sub_chains.push(sub);
            if resolution_strength > SATISFACTION_THRESHOLD {
                wisdom.resolved = true;
                wisdom.resolved_via = Some(ResolutionMechanism::KnowledgeReception);
                wisdom.blocked = false;
            }
        } else if co6 > RESOLUTION_THRESHOLD {
            // Path B: CO-6 Knowledge Decomposition — parallel child chains
            let num_components = (co6 * MAX_DECOMPOSITION_COMPONENTS as f64).ceil() as usize;
            let num_components = num_components.clamp(2, MAX_DECOMPOSITION_COMPONENTS);
            let component_strength = co6;
            let boosted = [chain_scores[0], component_strength, chain_scores[2]];
            for _ in 0..num_components {
                let sub = evaluate_recursive(
                    drive_index, operator_scores, &boosted,
                    a0_score, depth + 1, max_depth,
                );
                sub_chains.push(sub);
            }
            if component_strength > SATISFACTION_THRESHOLD {
                wisdom.resolved = true;
                wisdom.resolved_via = Some(ResolutionMechanism::KnowledgeDecomposition);
                wisdom.blocked = false;
            }
        }
    }

    // --- POWER (only if wisdom satisfied or resolved) ---
    let mut power = make_node(chain_scores[2], DwpStage::classify_power);
    let wisdom_ok = !wisdom.blocked || wisdom.resolved;
    let desire_ok = !desire.blocked || desire.resolved;
    if desire_ok && wisdom_ok && power.blocked && depth < max_depth {
        let co8 = operator_scores[8];
        let co9 = operator_scores[9];

        if co8 > RESOLUTION_THRESHOLD && co9 > RESOLUTION_THRESHOLD {
            // CO-8/CO-9 Causal Search
            // Resolution succeeds based on CO-8 × CO-9 activation
            let resolution_strength = (co8 + co9) / 2.0;
            let boosted = [chain_scores[0], chain_scores[1], resolution_strength];
            let sub = evaluate_recursive(
                drive_index, operator_scores, &boosted,
                a0_score, depth + 1, max_depth,
            );
            sub_chains.push(sub);
            if resolution_strength > SATISFACTION_THRESHOLD {
                power.resolved = true;
                power.resolved_via = Some(ResolutionMechanism::CausalSearch);
                power.blocked = false;
            }
        }
    }

    // Compute completeness
    let eff_d = if desire.resolved { RESOLVED_SCORE } else if !desire.blocked { desire.score } else { 0.0 };
    let eff_w = if wisdom.resolved { RESOLVED_SCORE } else if !wisdom.blocked { wisdom.score } else { 0.0 };
    let eff_p = if power.resolved { RESOLVED_SCORE } else if !power.blocked { power.score } else { 0.0 };
    let completeness = (eff_d + eff_w + eff_p) / 3.0;

    RecursiveRpmResult {
        drive_index,
        depth,
        desire,
        wisdom,
        power,
        completeness,
        sub_chains,
        exposure_cycles,
        max_depth_reached: depth >= max_depth,
    }
}

/// Evaluate all 7 drives recursively.
pub fn evaluate_all_recursive(
    operator_scores: &[f64; 10],
    drive_chains: &[[f64; 3]; 7],
    a0_score: f64,
) -> Vec<RecursiveRpmResult> {
    (0..7)
        .map(|i| evaluate_recursive(
            i, operator_scores, &drive_chains[i], a0_score,
            0, DEFAULT_MAX_DEPTH,
        ))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn default_ops() -> [f64; 10] {
        [0.6; 10]
    }

    #[test]
    fn test_flat_chain_no_recursion() {
        // All scores above threshold — no recursion needed
        let result = evaluate_recursive(0, &default_ops(), &[0.8, 0.8, 0.8], 0.8, 0, 5);
        assert!(!result.desire.blocked);
        assert!(!result.wisdom.blocked);
        assert!(!result.power.blocked);
        assert!(result.sub_chains.is_empty());
        assert!(result.completeness > 0.7);
    }

    #[test]
    fn test_power_blocked_co8_co9_resolves() {
        let mut ops = default_ops();
        ops[8] = 0.8; // CO-8 strong
        ops[9] = 0.8; // CO-9 strong
        let result = evaluate_recursive(0, &ops, &[0.8, 0.8, 0.1], 0.8, 0, 5);
        assert!(result.power.resolved);
        assert_eq!(result.power.resolved_via, Some(ResolutionMechanism::CausalSearch));
        assert!(!result.sub_chains.is_empty());
    }

    #[test]
    fn test_power_blocked_co8_co9_inactive_stays_blocked() {
        let mut ops = default_ops();
        ops[8] = 0.1; // CO-8 weak
        ops[9] = 0.1; // CO-9 weak
        let result = evaluate_recursive(0, &ops, &[0.8, 0.8, 0.1], 0.8, 0, 5);
        assert!(result.power.blocked);
        assert!(!result.power.resolved);
        assert!(result.sub_chains.is_empty());
    }

    #[test]
    fn test_wisdom_blocked_co5_reception() {
        let mut ops = default_ops();
        ops[5] = 0.9; // CO-5 dominant
        ops[6] = 0.2; // CO-6 weak
        let result = evaluate_recursive(0, &ops, &[0.8, 0.1, 0.8], 0.8, 0, 5);
        assert!(result.wisdom.resolved);
        assert_eq!(result.wisdom.resolved_via, Some(ResolutionMechanism::KnowledgeReception));
    }

    #[test]
    fn test_wisdom_blocked_co6_decomposition() {
        let mut ops = default_ops();
        ops[5] = 0.2; // CO-5 weak
        ops[6] = 0.9; // CO-6 dominant
        let result = evaluate_recursive(0, &ops, &[0.8, 0.1, 0.8], 0.8, 0, 5);
        assert!(result.wisdom.resolved);
        assert_eq!(result.wisdom.resolved_via, Some(ResolutionMechanism::KnowledgeDecomposition));
        // CO-6 decomposition spawns parallel sub-chains
        assert!(result.sub_chains.len() >= 2);
    }

    #[test]
    fn test_desire_blocked_exposure_loop() {
        let mut ops = default_ops();
        ops[1] = 0.8; // CO-1 strong
        ops[4] = 0.8; // CO-4 strong
        ops[7] = 0.8; // CO-7 strong
        let result = evaluate_recursive(0, &ops, &[0.1, 0.8, 0.8], 0.8, 0, 5);
        assert!(result.desire.resolved);
        assert_eq!(result.desire.resolved_via, Some(ResolutionMechanism::ExposureLoop));
        assert!(result.exposure_cycles > 0);
    }

    #[test]
    fn test_desire_blocked_exposure_inactive_stays_blocked() {
        let mut ops = [0.1; 10];
        let result = evaluate_recursive(0, &ops, &[0.1, 0.8, 0.8], 0.8, 0, 5);
        assert!(result.desire.blocked);
        assert!(!result.desire.resolved);
    }

    #[test]
    fn test_max_depth_stops_recursion() {
        let ops = default_ops();
        // At max depth, should not recurse further
        let result = evaluate_recursive(0, &ops, &[0.8, 0.8, 0.1], 0.8, 5, 5);
        assert!(result.power.blocked);
        assert!(!result.power.resolved);
        assert!(result.max_depth_reached);
    }

    #[test]
    fn test_a0_fail_blocks_everything() {
        let result = evaluate_recursive(0, &default_ops(), &[0.8, 0.8, 0.8], 0.1, 0, 5);
        assert!(result.desire.blocked);
        assert!(result.wisdom.blocked);
        assert!(result.power.blocked);
        assert_eq!(result.completeness, 0.0);
    }

    #[test]
    fn test_exposure_loop_does_not_count_toward_depth() {
        let mut ops = default_ops();
        ops[1] = 0.8;
        ops[4] = 0.8;
        ops[7] = 0.8;
        // At depth 4, desire exposure should still work
        let result = evaluate_recursive(0, &ops, &[0.1, 0.8, 0.8], 0.8, 4, 5);
        assert!(result.desire.resolved);
        assert_eq!(result.desire.resolved_via, Some(ResolutionMechanism::ExposureLoop));
    }

    #[test]
    fn test_section_retraction_at_each_depth() {
        // Section law: resolving a child chain feeds Power upward
        // but does NOT retroactively change Wisdom or Desire at parent level
        let mut ops = default_ops();
        ops[8] = 0.8;
        ops[9] = 0.8;
        let result = evaluate_recursive(0, &ops, &[0.8, 0.8, 0.1], 0.8, 0, 5);
        // Power was blocked but resolved via sub-chain
        assert!(result.power.resolved);
        // Desire and Wisdom are independently evaluated (not affected by Power resolution)
        assert!(!result.desire.blocked);
        assert!(!result.wisdom.blocked);
    }
}
