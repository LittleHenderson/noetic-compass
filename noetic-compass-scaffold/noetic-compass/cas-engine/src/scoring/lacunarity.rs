//! Cognitive Lacunarity Profile
//!
//! Lacunarity measures the DISTRIBUTION of cognitive gaps — not just whether
//! blind spots exist, but how the emptiness is structured across the entire
//! architecture. Two AI systems can score identical NCCS composites but have
//! completely different gap profiles. Lacunarity reveals this.
//!
//! Five dimensions:
//! - State lacunarity: Var(p) / Mean(p)^2 on operator scores
//! - Fractal lacunarity: 1 - (unique operators / 10) in the thinking pattern
//! - Domain lacunarity: 1 - (active domains / 4)
//! - Drive lacunarity: 1 - (active drives / 7)
//! - RPM resolution lacunarity: 1 - (mechanisms used / 4)

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Classification of lacunarity severity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LacunarityClass {
    /// < 0.5 — evenly distributed, generalist
    Uniform,
    /// 0.5-1.5 — some concentration, normal
    Moderate,
    /// 1.5-3.0 — significant gaps, specialist
    Concentrated,
    /// > 3.0 — massive voids, critical gaps
    Extreme,
}

impl LacunarityClass {
    pub fn from_score(score: f64) -> Self {
        if score < 0.5 { Self::Uniform }
        else if score < 1.5 { Self::Moderate }
        else if score < 3.0 { Self::Concentrated }
        else { Self::Extreme }
    }

    pub fn label(&self) -> &'static str {
        match self {
            Self::Uniform => "Uniform",
            Self::Moderate => "Moderate",
            Self::Concentrated => "Concentrated",
            Self::Extreme => "Extreme",
        }
    }
}

/// Map of where the gaps and concentrations are.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GapMap {
    pub absent_operators: Vec<u8>,
    pub absent_domains: Vec<String>,
    pub absent_drives: Vec<u8>,
    pub strongest_cluster: Vec<u8>,
    pub largest_void: String,
}

/// Full lacunarity profile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LacunarityProfile {
    pub state_lacunarity: f64,
    pub fractal_lacunarity: f64,
    pub domain_lacunarity: f64,
    pub drive_lacunarity: f64,
    pub rpm_resolution_lacunarity: f64,
    pub composite_lacunarity: f64,
    pub classification: LacunarityClass,
    pub gap_map: GapMap,
}

// ---------------------------------------------------------------------------
// Core computation functions
// ---------------------------------------------------------------------------

/// State lacunarity: Var(p) / Mean(p)^2  (coefficient of variation squared)
pub fn compute_state_lacunarity(operator_scores: &[f64; 10]) -> f64 {
    let mean = operator_scores.iter().sum::<f64>() / 10.0;
    if mean <= 0.0 { return 0.0; }
    let variance = operator_scores.iter()
        .map(|&s| (s - mean).powi(2))
        .sum::<f64>() / 10.0;
    variance / (mean * mean)
}

/// Fractal lacunarity: 1 - (unique operators in sequence / 10)
pub fn compute_fractal_lacunarity(fractal_sequence: &[u8]) -> f64 {
    if fractal_sequence.is_empty() { return 1.0; }
    let unique: HashSet<u8> = fractal_sequence.iter().cloned().collect();
    1.0 - (unique.len() as f64 / 10.0)
}

/// Domain lacunarity: 1 - (active domains / 4)
pub fn compute_domain_lacunarity(domain_scores: &[f64; 4], threshold: f64) -> f64 {
    let active = domain_scores.iter().filter(|&&s| s > threshold).count();
    1.0 - (active as f64 / 4.0)
}

/// Drive lacunarity: 1 - (active drives / 7)
pub fn compute_drive_lacunarity(drive_scores: &[f64; 7], threshold: f64) -> f64 {
    let active = drive_scores.iter().filter(|&&s| s > threshold).count();
    1.0 - (active as f64 / 7.0)
}

/// RPM resolution lacunarity: 1 - (mechanisms used / 4)
pub fn compute_rpm_resolution_lacunarity(
    has_causal_search: bool,
    has_knowledge_reception: bool,
    has_knowledge_decomposition: bool,
    has_exposure_loop: bool,
) -> f64 {
    let used = [has_causal_search, has_knowledge_reception,
                has_knowledge_decomposition, has_exposure_loop]
        .iter().filter(|&&b| b).count();
    1.0 - (used as f64 / 4.0)
}

/// Composite lacunarity (weighted).
pub fn compute_composite_lacunarity(
    state: f64, fractal: f64, domain: f64, drive: f64, rpm: f64,
) -> f64 {
    0.30 * state + 0.20 * fractal + 0.20 * domain + 0.15 * drive + 0.15 * rpm
}

/// Generate the gap map describing where activation is absent and concentrated.
pub fn generate_gap_map(
    operator_scores: &[f64; 10],
    domain_scores: &[f64; 4],
    drive_scores: &[f64; 7],
    op_threshold: f64,
    dom_threshold: f64,
    drv_threshold: f64,
) -> GapMap {
    let absent_operators: Vec<u8> = operator_scores.iter()
        .enumerate()
        .filter(|(_, &s)| s < op_threshold)
        .map(|(i, _)| i as u8)
        .collect();

    let domain_names = ["P", "C", "E", "O"];
    let absent_domains: Vec<String> = domain_scores.iter()
        .enumerate()
        .filter(|(_, &s)| s < dom_threshold)
        .map(|(i, _)| domain_names[i].to_string())
        .collect();

    let absent_drives: Vec<u8> = drive_scores.iter()
        .enumerate()
        .filter(|(_, &s)| s < drv_threshold)
        .map(|(i, _)| (i + 1) as u8)
        .collect();

    let strongest_cluster: Vec<u8> = operator_scores.iter()
        .enumerate()
        .filter(|(_, &s)| s >= op_threshold * 1.5)
        .map(|(i, _)| i as u8)
        .collect();

    let largest_void = describe_largest_gap(&absent_operators, &absent_domains, &absent_drives);

    GapMap { absent_operators, absent_domains, absent_drives, strongest_cluster, largest_void }
}

fn describe_largest_gap(absent_ops: &[u8], absent_doms: &[String], absent_drvs: &[u8]) -> String {
    let op_names = [
        "Idea", "Mind", "Positive", "Negative",
        "Vibration", "Female", "Male",
        "Rhythm", "Above/Cause", "Below/Effect",
    ];
    let drive_names = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"];

    if absent_ops.len() >= 5 {
        let names: Vec<&str> = absent_ops.iter().map(|&i| op_names[i as usize]).collect();
        format!("Critical operator void: {} operators absent ({})", absent_ops.len(), names.join(", "))
    } else if absent_doms.len() >= 2 {
        format!("Domain void: {} processing domains inactive ({})", absent_doms.len(), absent_doms.join(", "))
    } else if absent_drvs.len() >= 4 {
        let names: Vec<&str> = absent_drvs.iter().map(|&i| drive_names[(i - 1) as usize]).collect();
        format!("Drive void: {} motivational drives absent ({})", absent_drvs.len(), names.join(", "))
    } else if absent_ops.is_empty() && absent_doms.is_empty() && absent_drvs.is_empty() {
        "No significant gaps detected".to_string()
    } else {
        format!("{} operator(s), {} domain(s), {} drive(s) below threshold",
                absent_ops.len(), absent_doms.len(), absent_drvs.len())
    }
}

/// Compute the full lacunarity profile.
pub fn compute_lacunarity_profile(
    operator_scores: &[f64; 10],
    domain_scores: &[f64; 4],
    drive_scores: &[f64; 7],
    fractal_sequence: &[u8],
    has_causal_search: bool,
    has_knowledge_reception: bool,
    has_knowledge_decomposition: bool,
    has_exposure_loop: bool,
) -> LacunarityProfile {
    let state = compute_state_lacunarity(operator_scores);
    let fractal = compute_fractal_lacunarity(fractal_sequence);
    let domain = compute_domain_lacunarity(domain_scores, 0.2);
    let drive = compute_drive_lacunarity(drive_scores, 0.15);
    let rpm = compute_rpm_resolution_lacunarity(
        has_causal_search, has_knowledge_reception,
        has_knowledge_decomposition, has_exposure_loop,
    );
    let composite = compute_composite_lacunarity(state, fractal, domain, drive, rpm);
    let classification = LacunarityClass::from_score(composite);
    let gap_map = generate_gap_map(operator_scores, domain_scores, drive_scores, 4.0, 0.2, 0.2);

    LacunarityProfile {
        state_lacunarity: (state * 1000.0).round() / 1000.0,
        fractal_lacunarity: (fractal * 1000.0).round() / 1000.0,
        domain_lacunarity: (domain * 1000.0).round() / 1000.0,
        drive_lacunarity: (drive * 1000.0).round() / 1000.0,
        rpm_resolution_lacunarity: (rpm * 1000.0).round() / 1000.0,
        composite_lacunarity: (composite * 1000.0).round() / 1000.0,
        classification,
        gap_map,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_uniform_scores_zero_lacunarity() {
        let scores = [5.0; 10];
        assert_eq!(compute_state_lacunarity(&scores), 0.0);
    }

    #[test]
    fn test_single_dominant_high_lacunarity() {
        let mut scores = [0.0; 10];
        scores[3] = 10.0;
        let lac = compute_state_lacunarity(&scores);
        assert!(lac > 5.0, "single dominant should produce high lacunarity, got {lac}");
    }

    #[test]
    fn test_all_operators_equal_zero_state_lac() {
        let scores = [7.0; 10];
        assert_eq!(compute_state_lacunarity(&scores), 0.0);
    }

    #[test]
    fn test_two_operator_fractal_high_lacunarity() {
        let seq = vec![3, 8, 3, 8, 3];
        let lac = compute_fractal_lacunarity(&seq);
        assert!((lac - 0.8).abs() < 0.001, "2 unique of 10 = 0.8 lacunarity, got {lac}");
    }

    #[test]
    fn test_all_domains_active_zero_lacunarity() {
        let scores = [0.5, 0.6, 0.4, 0.3];
        assert_eq!(compute_domain_lacunarity(&scores, 0.2), 0.0);
    }

    #[test]
    fn test_one_domain_skipped() {
        let scores = [0.5, 0.6, 0.1, 0.3]; // E below 0.2
        assert!((compute_domain_lacunarity(&scores, 0.2) - 0.25).abs() < 0.001);
    }

    #[test]
    fn test_all_drives_active_zero_lacunarity() {
        let scores = [0.5, 0.4, 0.3, 0.6, 0.5, 0.4, 0.3];
        assert_eq!(compute_drive_lacunarity(&scores, 0.15), 0.0);
    }

    #[test]
    fn test_three_drives_absent() {
        let scores = [0.5, 0.1, 0.4, 0.1, 0.5, 0.1, 0.3]; // F2, F4, F6 below 0.15
        let lac = compute_drive_lacunarity(&scores, 0.15);
        let expected = 1.0 - 4.0 / 7.0;
        assert!((lac - expected).abs() < 0.001, "got {lac}, expected {expected}");
    }

    #[test]
    fn test_all_rpm_mechanisms_zero_lacunarity() {
        assert_eq!(compute_rpm_resolution_lacunarity(true, true, true, true), 0.0);
    }

    #[test]
    fn test_no_rpm_mechanisms_full_lacunarity() {
        assert_eq!(compute_rpm_resolution_lacunarity(false, false, false, false), 1.0);
    }

    #[test]
    fn test_gap_map_identifies_absent_operators() {
        let op = [1.0, 8.0, 2.0, 9.0, 3.0, 1.0, 7.0, 1.0, 8.0, 2.0];
        let dom = [0.5; 4];
        let drv = [0.5; 7];
        let gm = generate_gap_map(&op, &dom, &drv, 4.0, 0.3, 0.2);
        assert!(gm.absent_operators.contains(&0)); // CO-0 = 1.0 < 4.0
        assert!(gm.absent_operators.contains(&2)); // CO-2 = 2.0 < 4.0
        assert!(!gm.absent_operators.contains(&1)); // CO-1 = 8.0 >= 4.0
    }

    #[test]
    fn test_gap_map_balanced_domain_simplex_is_active() {
        let op = [6.0; 10];
        let dom = [0.25; 4];
        let drv = [0.5; 7];
        let profile = compute_lacunarity_profile(&op, &dom, &drv, &[0, 2, 3, 5, 6, 8, 9], true, true, true, true);
        assert!(profile.gap_map.absent_domains.is_empty());
    }

    #[test]
    fn test_gap_map_largest_void_description() {
        let op = [1.0; 10]; // all below 4.0
        let dom = [0.5; 4];
        let drv = [0.5; 7];
        let gm = generate_gap_map(&op, &dom, &drv, 4.0, 0.3, 0.2);
        assert!(gm.largest_void.contains("Critical operator void"));
        assert!(gm.largest_void.contains("10 operators absent"));
    }

    #[test]
    fn test_composite_weighted_correctly() {
        let c = compute_composite_lacunarity(1.0, 1.0, 1.0, 1.0, 1.0);
        assert!((c - 1.0).abs() < 0.001, "all 1.0 inputs should give 1.0 composite, got {c}");
    }

    #[test]
    fn test_classification_thresholds() {
        assert_eq!(LacunarityClass::from_score(0.3), LacunarityClass::Uniform);
        assert_eq!(LacunarityClass::from_score(0.8), LacunarityClass::Moderate);
        assert_eq!(LacunarityClass::from_score(2.0), LacunarityClass::Concentrated);
        assert_eq!(LacunarityClass::from_score(4.0), LacunarityClass::Extreme);
    }
}
