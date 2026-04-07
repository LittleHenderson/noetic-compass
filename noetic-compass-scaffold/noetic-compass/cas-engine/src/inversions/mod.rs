//! 7-Axis Inversion Scanner for the CAS Framework
//!
//! Detects 7 types of inversions in a cognitive assessment:
//! - N (Operator): Involution pair imbalance (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9)
//! - W (Domain): Domain precedence violations (P ≻ C ≻ E ≻ O)
//! - F (Drive): Drive inversion pair imbalance (F1↔F7, F2↔F6, F3↔F5)
//! - E (State): Cognitive state vector entropy deficit (rigidity)
//! - S (Sub-Drive): Cross-domain drive variance (sub-drive contradictions)
//! - A (Pathway): RPM prerequisite chain violations
//! - P (Compound): Amplified severity from multiple simultaneous inversions
//!
//! Additionally performs stealth detection (moderate severity inversions that
//! are hard to catch but still distort results) and compound severity analysis.

use serde::{Deserialize, Serialize};
use std::fmt;

use crate::ontology::{
    CognitiveOperator, CognitiveStateVector, DriveProfile,
    InversionAxis, NUM_STATES,
};
use crate::scoring::InversionResistanceInput;

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// Errors from the inversion scanning subsystem.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum InversionError {
    #[error("invalid score on axis {axis}: value {value} is not in [0, 1]")]
    InvalidScore { axis: InversionAxis, value: f64 },
}

// ---------------------------------------------------------------------------
// Stealth thresholds
// ---------------------------------------------------------------------------

/// Lower bound of the stealth range. Inversions with severity in [STEALTH_LOW, STEALTH_HIGH]
/// are classified as stealth: subtle enough to evade naive detection but impactful enough
/// to distort assessment results.
const STEALTH_LOW: f64 = 0.3;

/// Upper bound of the stealth range.
const STEALTH_HIGH: f64 = 0.7;

// ---------------------------------------------------------------------------
// Inversion Detection
// ---------------------------------------------------------------------------

/// A single detected inversion on one of the 7 axes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InversionDetection {
    /// Which axis this inversion was detected on.
    axis: InversionAxis,
    /// Severity of the inversion: 0.0 (none) to 1.0 (maximum).
    severity: f64,
    /// Whether the inversion is in the stealth range (moderate severity, hard to catch).
    is_stealth: bool,
    /// Human-readable description of the detected inversion.
    description: String,
}

impl InversionDetection {
    /// Create a new inversion detection, computing stealth status automatically.
    pub fn new(axis: InversionAxis, severity: f64, description: String) -> Self {
        let is_stealth = severity >= STEALTH_LOW && severity <= STEALTH_HIGH;
        Self {
            axis,
            severity,
            is_stealth,
            description,
        }
    }

    /// The axis this inversion was detected on.
    pub fn axis(&self) -> InversionAxis {
        self.axis
    }

    /// The severity of this inversion (0.0 to 1.0).
    pub fn severity(&self) -> f64 {
        self.severity
    }

    /// Whether this inversion is in the stealth range.
    pub fn is_stealth(&self) -> bool {
        self.is_stealth
    }

    /// Human-readable description of the inversion.
    pub fn description(&self) -> &str {
        &self.description
    }
}

impl fmt::Display for InversionDetection {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "[{}] severity={:.3}{} — {}",
            self.axis,
            self.severity,
            if self.is_stealth { " (STEALTH)" } else { "" },
            self.description,
        )
    }
}

// ---------------------------------------------------------------------------
// Inversion Scan Result
// ---------------------------------------------------------------------------

/// Complete results from an inversion scan across all 7 axes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InversionScanResult {
    /// All detected inversions (may be empty if no inversions found).
    detections: Vec<InversionDetection>,
    /// Per-axis resistance score (1.0 = no inversion, 0.0 = maximum inversion).
    /// Indexed by `InversionAxis::index()`.
    axis_scores: [f64; 7],
    /// Overall stealth resistance: 1.0 - (fraction of axes with stealth inversions).
    stealth_resistance: f64,
    /// Compound inversion severity: product of top-2 individual severities when 2+
    /// axes are inverted; 0.0 if fewer than 2 inversions.
    compound_severity: f64,
}

impl InversionScanResult {
    /// The detected inversions.
    pub fn detections(&self) -> &[InversionDetection] {
        &self.detections
    }

    /// Per-axis resistance scores. Higher = more resistant (less inverted).
    pub fn axis_scores(&self) -> &[f64; 7] {
        &self.axis_scores
    }

    /// Overall stealth resistance score.
    pub fn stealth_resistance(&self) -> f64 {
        self.stealth_resistance
    }

    /// Compound inversion severity.
    pub fn compound_severity(&self) -> f64 {
        self.compound_severity
    }

    /// Number of axes with non-zero inversions detected.
    pub fn inversion_count(&self) -> usize {
        self.detections.len()
    }

    /// Convert this scan result into an `InversionResistanceInput` for the scoring module.
    pub fn to_resistance_input(&self) -> InversionResistanceInput {
        // This should always succeed because our axis_scores are in [0,1],
        // stealth_resistance is in [0,1], and compound_severity is in [0,1].
        InversionResistanceInput::new(
            self.axis_scores,
            self.stealth_resistance,
            self.compound_severity,
        )
        .expect("InversionScanResult invariants guarantee valid resistance input")
    }
}

impl fmt::Display for InversionScanResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f, "Inversion Scan: {} detections", self.detections.len())?;
        for d in &self.detections {
            writeln!(f, "  {}", d)?;
        }
        writeln!(
            f,
            "  Stealth resistance: {:.3}",
            self.stealth_resistance
        )?;
        write!(
            f,
            "  Compound severity: {:.3}",
            self.compound_severity
        )
    }
}

// ---------------------------------------------------------------------------
// Scanner input
// ---------------------------------------------------------------------------

/// Input data for the inversion scanner.
///
/// Bundles all assessment data needed to scan for inversions across all 7 axes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InversionScanInput {
    /// Per-operator scores (10 values, each in [0, 1]).
    pub operator_scores: [f64; 10],
    /// Per-domain average scores in precedence order [P, C, E, O], each in [0, 1].
    pub domain_averages: [f64; 4],
    /// Core drive profile (7 scores).
    pub drive_profile: DriveProfile,
    /// Cognitive state vector (40-dimensional probability distribution).
    pub state_vector: CognitiveStateVector,
    /// Domain-specific drive scores: a 7x4 matrix where
    /// `domain_drive_scores[drive_index][domain_index]` is the score for that
    /// drive in that domain. Each value in [0, 1].
    pub domain_drive_scores: [[f64; 4]; 7],
    /// Per-pathway-stage scores for each of the 7 RPM chains.
    /// `pathway_scores[chain_index]` = [A0_score, D_score, W_score, P_score].
    /// Each value in [0, 1].
    pub pathway_scores: [[f64; 4]; 7],
}

// ---------------------------------------------------------------------------
// Shannon entropy helper
// ---------------------------------------------------------------------------

/// Compute the Shannon entropy H = -sum(pk * ln(pk)) for a probability distribution.
/// Components with pk <= 0 are skipped (should not occur on the open simplex).
fn shannon_entropy(probs: &[f64]) -> f64 {
    probs
        .iter()
        .filter(|&&p| p > 0.0)
        .map(|&p| -p * p.ln())
        .sum()
}

// ---------------------------------------------------------------------------
// Inversion Scanner
// ---------------------------------------------------------------------------

/// The 7-axis inversion scanner.
///
/// Takes assessment data and produces a complete scan result covering all
/// inversion axes, stealth detection, and compound severity.
#[derive(Debug, Clone)]
pub struct InversionScanner {
    /// Minimum severity threshold below which an axis is not considered inverted.
    /// Used for compound severity calculation (only axes above this threshold count).
    severity_threshold: f64,
}

impl Default for InversionScanner {
    fn default() -> Self {
        Self::new()
    }
}

impl InversionScanner {
    /// Create a new scanner with default settings.
    pub fn new() -> Self {
        Self {
            severity_threshold: 0.05,
        }
    }

    /// Create a scanner with a custom severity threshold.
    pub fn with_threshold(severity_threshold: f64) -> Self {
        Self {
            severity_threshold: severity_threshold.clamp(0.0, 1.0),
        }
    }

    /// Run the full inversion scan on the provided input.
    pub fn scan(&self, input: &InversionScanInput) -> Result<InversionScanResult, InversionError> {
        // Validate inputs
        self.validate_input(input)?;

        let mut detections = Vec::new();
        let mut axis_scores = [1.0_f64; 7];

        // --- N: Operator inversion ---
        let op_severity = self.detect_operator_inversion(&input.operator_scores);
        axis_scores[InversionAxis::Operator.index()] = 1.0 - op_severity;
        if op_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::Operator,
                op_severity,
                format!(
                    "Involution pair imbalance detected (max imbalance: {:.3})",
                    op_severity
                ),
            ));
        }

        // --- W: Domain inversion ---
        let dom_severity = self.detect_domain_inversion(&input.domain_averages);
        axis_scores[InversionAxis::Domain.index()] = 1.0 - dom_severity;
        if dom_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::Domain,
                dom_severity,
                format!(
                    "Domain precedence violation detected (severity: {:.3})",
                    dom_severity
                ),
            ));
        }

        // --- F: Drive inversion ---
        let drive_severity = self.detect_drive_inversion(&input.drive_profile);
        axis_scores[InversionAxis::Drive.index()] = 1.0 - drive_severity;
        if drive_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::Drive,
                drive_severity,
                format!(
                    "Drive inversion pair imbalance detected (max imbalance: {:.3})",
                    drive_severity
                ),
            ));
        }

        // --- E: State inversion ---
        let state_severity = self.detect_state_inversion(&input.state_vector);
        axis_scores[InversionAxis::State.index()] = 1.0 - state_severity;
        if state_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::State,
                state_severity,
                format!(
                    "State vector entropy deficit detected (normalized deficit: {:.3})",
                    state_severity
                ),
            ));
        }

        // --- S: Sub-Drive inversion ---
        let subdrive_severity =
            self.detect_subdrive_inversion(&input.domain_drive_scores);
        axis_scores[InversionAxis::SubDrive.index()] = 1.0 - subdrive_severity;
        if subdrive_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::SubDrive,
                subdrive_severity,
                format!(
                    "Sub-drive cross-domain variance detected (max variance: {:.3})",
                    subdrive_severity
                ),
            ));
        }

        // --- A: Pathway inversion ---
        let pathway_severity = self.detect_pathway_inversion(&input.pathway_scores);
        axis_scores[InversionAxis::Pathway.index()] = 1.0 - pathway_severity;
        if pathway_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::Pathway,
                pathway_severity,
                format!(
                    "Pathway RPM chain violation detected (violation fraction: {:.3})",
                    pathway_severity
                ),
            ));
        }

        // --- P: Compound inversion ---
        let compound_severity = self.compute_compound_severity(&detections);
        axis_scores[InversionAxis::Compound.index()] = 1.0 - compound_severity;
        if compound_severity > self.severity_threshold {
            detections.push(InversionDetection::new(
                InversionAxis::Compound,
                compound_severity,
                format!(
                    "Compound inversion amplification detected (severity: {:.3})",
                    compound_severity
                ),
            ));
        }

        // --- Stealth resistance ---
        let stealth_count = detections.iter().filter(|d| d.is_stealth).count();
        // Total axes = 7. Stealth resistance = 1 - (stealth_count / 7).
        let stealth_resistance = 1.0 - (stealth_count as f64 / 7.0);

        Ok(InversionScanResult {
            detections,
            axis_scores,
            stealth_resistance,
            compound_severity,
        })
    }

    // -----------------------------------------------------------------------
    // Input validation
    // -----------------------------------------------------------------------

    fn validate_input(&self, input: &InversionScanInput) -> Result<(), InversionError> {
        for &s in &input.operator_scores {
            if s.is_nan() || !(0.0..=1.0).contains(&s) {
                return Err(InversionError::InvalidScore {
                    axis: InversionAxis::Operator,
                    value: s,
                });
            }
        }
        for &s in &input.domain_averages {
            if s.is_nan() || !(0.0..=1.0).contains(&s) {
                return Err(InversionError::InvalidScore {
                    axis: InversionAxis::Domain,
                    value: s,
                });
            }
        }
        for row in &input.domain_drive_scores {
            for &s in row {
                if s.is_nan() || !(0.0..=1.0).contains(&s) {
                    return Err(InversionError::InvalidScore {
                        axis: InversionAxis::SubDrive,
                        value: s,
                    });
                }
            }
        }
        for chain in &input.pathway_scores {
            for &s in chain {
                if s.is_nan() || !(0.0..=1.0).contains(&s) {
                    return Err(InversionError::InvalidScore {
                        axis: InversionAxis::Pathway,
                        value: s,
                    });
                }
            }
        }
        Ok(())
    }

    // -----------------------------------------------------------------------
    // N: Operator inversion detection
    // -----------------------------------------------------------------------

    /// Detect operator inversion by checking involution pair imbalance.
    ///
    /// Checks the 3 involution pairs (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9).
    /// Severity = maximum |score(a) - score(b)| across the 3 pairs.
    fn detect_operator_inversion(&self, operator_scores: &[f64; 10]) -> f64 {
        let mut max_imbalance = 0.0_f64;
        for &(a, b) in &CognitiveOperator::INVOLUTION_PAIRS {
            let diff = (operator_scores[a.index()] - operator_scores[b.index()]).abs();
            max_imbalance = max_imbalance.max(diff);
        }
        max_imbalance.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // W: Domain inversion detection
    // -----------------------------------------------------------------------

    /// Detect domain inversion by checking if the total order P > C > E > O
    /// is violated.
    ///
    /// For each adjacent pair (P,C), (C,E), (E,O), checks if the lower-precedence
    /// domain dominates the higher-precedence one. Severity is the normalized sum
    /// of violations: sum(max(0, lower - higher)) / 3.
    fn detect_domain_inversion(&self, domain_averages: &[f64; 4]) -> f64 {
        // Domain order: [0]=P, [1]=C, [2]=E, [3]=O
        // Expected: P >= C >= E >= O
        // A violation at pair (i, i+1) occurs when domain_averages[i+1] > domain_averages[i].
        let mut total_violation = 0.0;
        for i in 0..3 {
            let higher = domain_averages[i]; // higher-precedence domain
            let lower = domain_averages[i + 1]; // lower-precedence domain
            if lower > higher {
                total_violation += lower - higher;
            }
        }
        // Normalize: max possible violation per pair is 1.0, 3 pairs total.
        let severity = total_violation / 3.0;
        severity.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // F: Drive inversion detection
    // -----------------------------------------------------------------------

    /// Detect drive inversion by checking drive inversion pairs.
    ///
    /// Checks the 3 inversion pairs (F1↔F7, F2↔F6, F3↔F5).
    /// Severity = maximum |score(a) - score(b)| across the 3 pairs.
    fn detect_drive_inversion(&self, drive_profile: &DriveProfile) -> f64 {
        let balances = drive_profile.all_inversion_balances();
        let max_imbalance = balances
            .iter()
            .cloned()
            .fold(0.0_f64, f64::max);
        max_imbalance.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // E: State inversion detection
    // -----------------------------------------------------------------------

    /// Detect state inversion via entropy deficit.
    ///
    /// Computes Shannon entropy of the cognitive state vector and compares to
    /// the maximum possible entropy (uniform distribution over 40 states).
    /// A low entropy indicates cognitive rigidity / concentration.
    ///
    /// Severity = 1.0 - (H / H_max), where H_max = ln(40).
    fn detect_state_inversion(&self, state_vector: &CognitiveStateVector) -> f64 {
        let h = shannon_entropy(state_vector.as_slice());
        let h_max = (NUM_STATES as f64).ln();
        if h_max <= 0.0 {
            return 0.0;
        }
        let normalized = h / h_max;
        let severity = 1.0 - normalized;
        severity.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // S: Sub-Drive inversion detection
    // -----------------------------------------------------------------------

    /// Detect sub-drive inversion via cross-domain variance.
    ///
    /// For each of the 7 core drives, computes the variance of its score across
    /// the 4 domains. High variance means the drive manifests inconsistently
    /// across domains, indicating sub-drive contradictions.
    ///
    /// Severity = max variance across all 7 drives.
    /// The maximum possible variance for values in [0,1] is 0.25 (half at 0, half at 1),
    /// so we normalize by dividing by 0.25.
    fn detect_subdrive_inversion(&self, domain_drive_scores: &[[f64; 4]; 7]) -> f64 {
        let mut max_variance = 0.0_f64;
        for drive_scores in domain_drive_scores {
            let mean = drive_scores.iter().sum::<f64>() / 4.0;
            let variance = drive_scores
                .iter()
                .map(|&s| (s - mean) * (s - mean))
                .sum::<f64>()
                / 4.0;
            max_variance = max_variance.max(variance);
        }
        // Normalize: max possible variance for [0,1] values is 0.25.
        let severity = (max_variance / 0.25).min(1.0);
        severity.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // A: Pathway inversion detection
    // -----------------------------------------------------------------------

    /// Detect pathway inversion via RPM prerequisite chain violations.
    ///
    /// For each of the 7 RPM chains, checks whether later stages score higher
    /// than earlier unsatisfied stages. A chain has 4 stages: [A0, D, W, P].
    /// A violation occurs when stage j > stage i and stage i < 0.5 (unsatisfied)
    /// for any j > i.
    ///
    /// Severity = fraction of chains with at least one violation.
    fn detect_pathway_inversion(&self, pathway_scores: &[[f64; 4]; 7]) -> f64 {
        let satisfaction_threshold = 0.5;
        let mut violated_chains = 0;

        for chain in pathway_scores {
            let mut has_violation = false;
            // Check all pairs (i, j) where j > i
            for i in 0..4 {
                if chain[i] < satisfaction_threshold {
                    // Earlier stage is unsatisfied; check if any later stage is higher
                    for j in (i + 1)..4 {
                        if chain[j] > chain[i] {
                            has_violation = true;
                            break;
                        }
                    }
                }
                if has_violation {
                    break;
                }
            }
            if has_violation {
                violated_chains += 1;
            }
        }

        let severity = violated_chains as f64 / 7.0;
        severity.clamp(0.0, 1.0)
    }

    // -----------------------------------------------------------------------
    // P: Compound inversion
    // -----------------------------------------------------------------------

    /// Compute compound inversion severity.
    ///
    /// When 2 or more axes are simultaneously inverted, their effects amplify
    /// each other. Severity = product of the top-2 individual severities.
    /// Returns 0.0 if fewer than 2 inversions are present.
    fn compute_compound_severity(&self, detections: &[InversionDetection]) -> f64 {
        if detections.len() < 2 {
            return 0.0;
        }

        let mut severities: Vec<f64> = detections.iter().map(|d| d.severity).collect();
        // Sort descending
        severities.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));

        let compound = severities[0] * severities[1];
        compound.clamp(0.0, 1.0)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ontology::{CognitiveStateVector, DriveProfile, NUM_STATES};

    // Helpers

    /// Create a balanced (no inversions) scan input.
    fn balanced_input() -> InversionScanInput {
        InversionScanInput {
            operator_scores: [0.5; 10],
            domain_averages: [0.7, 0.6, 0.5, 0.4], // P > C > E > O, correct order
            drive_profile: DriveProfile::new([0.5; 7]).unwrap(),
            state_vector: CognitiveStateVector::uniform(),
            domain_drive_scores: [[0.5; 4]; 7],
            pathway_scores: [[0.8, 0.7, 0.6, 0.5]; 7], // decreasing, no violation
        }
    }

    /// Create a state vector concentrated on a single state.
    fn concentrated_state_vector() -> CognitiveStateVector {
        let mut probs = [1e-15; NUM_STATES];
        // Put almost all probability on state 0
        let small_total = 1e-15 * (NUM_STATES as f64 - 1.0);
        probs[0] = 1.0 - small_total;
        CognitiveStateVector::new(probs).unwrap()
    }

    // -----------------------------------------------------------------------
    // N: Operator inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_operator_inversion_balanced() {
        let scanner = InversionScanner::new();
        let scores = [0.5; 10];
        let severity = scanner.detect_operator_inversion(&scores);
        assert!(severity.abs() < 1e-12, "balanced operators should have 0 severity");
    }

    #[test]
    fn test_operator_inversion_max_imbalance() {
        let scanner = InversionScanner::new();
        // CO-2 at 1.0, CO-3 at 0.0 => max imbalance = 1.0
        let mut scores = [0.5; 10];
        scores[2] = 1.0;
        scores[3] = 0.0;
        let severity = scanner.detect_operator_inversion(&scores);
        assert!((severity - 1.0).abs() < 1e-12, "max imbalance should be 1.0");
    }

    #[test]
    fn test_operator_inversion_partial() {
        let scanner = InversionScanner::new();
        let mut scores = [0.5; 10];
        // CO-5 at 0.8, CO-6 at 0.3 => imbalance = 0.5
        scores[5] = 0.8;
        scores[6] = 0.3;
        let severity = scanner.detect_operator_inversion(&scores);
        assert!((severity - 0.5).abs() < 1e-12);
    }

    #[test]
    fn test_operator_inversion_picks_maximum_pair() {
        let scanner = InversionScanner::new();
        let mut scores = [0.5; 10];
        // CO-2↔CO-3: imbalance = 0.2
        scores[2] = 0.6;
        scores[3] = 0.4;
        // CO-5↔CO-6: imbalance = 0.7
        scores[5] = 0.9;
        scores[6] = 0.2;
        // CO-8↔CO-9: imbalance = 0.1
        scores[8] = 0.55;
        scores[9] = 0.45;
        let severity = scanner.detect_operator_inversion(&scores);
        assert!((severity - 0.7).abs() < 1e-12, "should pick max pair imbalance");
    }

    // -----------------------------------------------------------------------
    // W: Domain inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_domain_inversion_correct_order() {
        let scanner = InversionScanner::new();
        // P > C > E > O: no violation
        let averages = [0.8, 0.6, 0.4, 0.2];
        let severity = scanner.detect_domain_inversion(&averages);
        assert!(severity.abs() < 1e-12, "correct domain order should have 0 severity");
    }

    #[test]
    fn test_domain_inversion_complete_reversal() {
        let scanner = InversionScanner::new();
        // O > E > C > P: complete reversal
        let averages = [0.0, 0.3, 0.6, 0.9];
        // Violations: C-P = 0.3, E-C = 0.3, O-E = 0.3 => total = 0.9 / 3 = 0.3
        let severity = scanner.detect_domain_inversion(&averages);
        assert!((severity - 0.3).abs() < 1e-12);
    }

    #[test]
    fn test_domain_inversion_partial_violation() {
        let scanner = InversionScanner::new();
        // P=0.5, C=0.7 (C > P, violation), E=0.4, O=0.3
        // Violation only at (P,C): 0.7 - 0.5 = 0.2
        let averages = [0.5, 0.7, 0.4, 0.3];
        let severity = scanner.detect_domain_inversion(&averages);
        assert!((severity - 0.2 / 3.0).abs() < 1e-12);
    }

    #[test]
    fn test_domain_inversion_equal_is_ok() {
        let scanner = InversionScanner::new();
        let averages = [0.5, 0.5, 0.5, 0.5];
        let severity = scanner.detect_domain_inversion(&averages);
        assert!(severity.abs() < 1e-12, "equal domains should not be a violation");
    }

    // -----------------------------------------------------------------------
    // F: Drive inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_drive_inversion_balanced() {
        let scanner = InversionScanner::new();
        let profile = DriveProfile::new([0.5; 7]).unwrap();
        let severity = scanner.detect_drive_inversion(&profile);
        assert!(severity.abs() < 1e-12, "balanced drives should have 0 severity");
    }

    #[test]
    fn test_drive_inversion_max_imbalance() {
        let scanner = InversionScanner::new();
        // F1=1.0, F7=0.0 => imbalance = 1.0
        let profile = DriveProfile::new([1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0]).unwrap();
        let severity = scanner.detect_drive_inversion(&profile);
        assert!((severity - 1.0).abs() < 1e-12, "max drive imbalance should be 1.0");
    }

    #[test]
    fn test_drive_inversion_partial() {
        let scanner = InversionScanner::new();
        // F2=0.8, F6=0.2 => imbalance = 0.6
        let profile = DriveProfile::new([0.5, 0.8, 0.5, 0.5, 0.5, 0.2, 0.5]).unwrap();
        let severity = scanner.detect_drive_inversion(&profile);
        assert!((severity - 0.6).abs() < 1e-12);
    }

    // -----------------------------------------------------------------------
    // E: State inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_state_inversion_uniform() {
        let scanner = InversionScanner::new();
        let state = CognitiveStateVector::uniform();
        let severity = scanner.detect_state_inversion(&state);
        assert!(
            severity.abs() < 1e-9,
            "uniform state vector should have near-zero severity, got {}",
            severity
        );
    }

    #[test]
    fn test_state_inversion_concentrated() {
        let scanner = InversionScanner::new();
        let state = concentrated_state_vector();
        let severity = scanner.detect_state_inversion(&state);
        // Should be close to 1.0 (very low entropy)
        assert!(
            severity > 0.95,
            "concentrated state vector should have high severity, got {}",
            severity
        );
    }

    #[test]
    fn test_state_inversion_moderate() {
        let scanner = InversionScanner::new();
        // Create a moderately concentrated distribution: 5 states get most probability
        let n = NUM_STATES;
        let high_prob = 0.19; // 5 states * 0.19 = 0.95
        let low_prob = (1.0 - 5.0 * high_prob) / (n as f64 - 5.0);
        let mut probs = vec![low_prob; n];
        for i in 0..5 {
            probs[i] = high_prob;
        }
        let state = CognitiveStateVector::from_slice(&probs).unwrap();
        let severity = scanner.detect_state_inversion(&state);
        assert!(
            severity > 0.1 && severity < 0.9,
            "moderately concentrated should have moderate severity, got {}",
            severity
        );
    }

    // -----------------------------------------------------------------------
    // S: Sub-Drive inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_subdrive_inversion_uniform() {
        let scanner = InversionScanner::new();
        let scores = [[0.5; 4]; 7];
        let severity = scanner.detect_subdrive_inversion(&scores);
        assert!(severity.abs() < 1e-12, "uniform sub-drives should have 0 severity");
    }

    #[test]
    fn test_subdrive_inversion_max_variance() {
        let scanner = InversionScanner::new();
        // Drive 0: [1.0, 0.0, 1.0, 0.0] => mean=0.5, variance=0.25 => severity=1.0
        let mut scores = [[0.5; 4]; 7];
        scores[0] = [1.0, 0.0, 1.0, 0.0];
        let severity = scanner.detect_subdrive_inversion(&scores);
        assert!((severity - 1.0).abs() < 1e-12, "max variance should give severity 1.0");
    }

    #[test]
    fn test_subdrive_inversion_partial() {
        let scanner = InversionScanner::new();
        // Drive 2: [0.8, 0.4, 0.6, 0.6] => mean=0.6, var = avg((0.04, 0.04, 0, 0)) = 0.02
        // normalized: 0.02 / 0.25 = 0.08
        let mut scores = [[0.5; 4]; 7];
        scores[2] = [0.8, 0.4, 0.6, 0.6];
        let severity = scanner.detect_subdrive_inversion(&scores);
        assert!((severity - 0.08).abs() < 1e-12, "got {}", severity);
    }

    // -----------------------------------------------------------------------
    // A: Pathway inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_pathway_inversion_correct_order() {
        let scanner = InversionScanner::new();
        // All chains: A0=0.9, D=0.8, W=0.7, P=0.6 (decreasing, no violation)
        let scores = [[0.9, 0.8, 0.7, 0.6]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!(severity.abs() < 1e-12, "correct pathway order should have 0 severity");
    }

    #[test]
    fn test_pathway_inversion_all_violated() {
        let scanner = InversionScanner::new();
        // All chains: A0=0.1, D=0.2, W=0.3, P=0.8
        // A0 < 0.5 and D > A0, so violation; also W > A0, P > A0; D < 0.5 and W > D, etc.
        let scores = [[0.1, 0.2, 0.3, 0.8]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!((severity - 1.0).abs() < 1e-12, "all chains violated should give severity 1.0");
    }

    #[test]
    fn test_pathway_inversion_one_chain_violated() {
        let scanner = InversionScanner::new();
        let mut scores = [[0.9, 0.8, 0.7, 0.6]; 7]; // all correct
        // Violate chain 3: A0=0.2 (unsatisfied), P=0.9
        scores[3] = [0.2, 0.1, 0.1, 0.9];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!(
            (severity - 1.0 / 7.0).abs() < 1e-12,
            "one violated chain out of 7 = 1/7, got {}",
            severity
        );
    }

    #[test]
    fn test_pathway_inversion_satisfied_early_stages() {
        let scanner = InversionScanner::new();
        // A0=0.8 (satisfied), D=0.7 (satisfied), W=0.3 (unsatisfied), P=0.9 (higher)
        // W < 0.5 and P > W => violation
        let scores = [[0.8, 0.7, 0.3, 0.9]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!((severity - 1.0).abs() < 1e-12, "all chains have W<0.5 with P>W");
    }

    // -----------------------------------------------------------------------
    // P: Compound inversion tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_compound_severity_no_inversions() {
        let scanner = InversionScanner::new();
        let detections: Vec<InversionDetection> = vec![];
        let severity = scanner.compute_compound_severity(&detections);
        assert!(severity.abs() < 1e-12, "no inversions should give 0 compound severity");
    }

    #[test]
    fn test_compound_severity_one_inversion() {
        let scanner = InversionScanner::new();
        let detections = vec![InversionDetection::new(
            InversionAxis::Operator,
            0.8,
            "test".to_string(),
        )];
        let severity = scanner.compute_compound_severity(&detections);
        assert!(
            severity.abs() < 1e-12,
            "one inversion should give 0 compound severity"
        );
    }

    #[test]
    fn test_compound_severity_two_inversions() {
        let scanner = InversionScanner::new();
        let detections = vec![
            InversionDetection::new(InversionAxis::Operator, 0.8, "test".to_string()),
            InversionDetection::new(InversionAxis::Drive, 0.6, "test".to_string()),
        ];
        let severity = scanner.compute_compound_severity(&detections);
        // top-2 product: 0.8 * 0.6 = 0.48
        assert!((severity - 0.48).abs() < 1e-12);
    }

    #[test]
    fn test_compound_severity_three_inversions_picks_top2() {
        let scanner = InversionScanner::new();
        let detections = vec![
            InversionDetection::new(InversionAxis::Operator, 0.3, "test".to_string()),
            InversionDetection::new(InversionAxis::Drive, 0.9, "test".to_string()),
            InversionDetection::new(InversionAxis::State, 0.7, "test".to_string()),
        ];
        let severity = scanner.compute_compound_severity(&detections);
        // top-2: 0.9 * 0.7 = 0.63
        assert!((severity - 0.63).abs() < 1e-12);
    }

    #[test]
    fn test_compound_severity_max() {
        let scanner = InversionScanner::new();
        let detections = vec![
            InversionDetection::new(InversionAxis::Operator, 1.0, "test".to_string()),
            InversionDetection::new(InversionAxis::Drive, 1.0, "test".to_string()),
        ];
        let severity = scanner.compute_compound_severity(&detections);
        assert!((severity - 1.0).abs() < 1e-12);
    }

    // -----------------------------------------------------------------------
    // Stealth detection tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_stealth_in_range() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.5, "test".to_string());
        assert!(det.is_stealth(), "severity 0.5 should be stealth");
    }

    #[test]
    fn test_stealth_at_lower_boundary() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.3, "test".to_string());
        assert!(det.is_stealth(), "severity 0.3 should be stealth (inclusive)");
    }

    #[test]
    fn test_stealth_at_upper_boundary() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.7, "test".to_string());
        assert!(det.is_stealth(), "severity 0.7 should be stealth (inclusive)");
    }

    #[test]
    fn test_not_stealth_below_range() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.2, "test".to_string());
        assert!(!det.is_stealth(), "severity 0.2 should not be stealth");
    }

    #[test]
    fn test_not_stealth_above_range() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.8, "test".to_string());
        assert!(!det.is_stealth(), "severity 0.8 should not be stealth");
    }

    #[test]
    fn test_not_stealth_zero() {
        let det = InversionDetection::new(InversionAxis::Operator, 0.0, "test".to_string());
        assert!(!det.is_stealth(), "severity 0.0 should not be stealth");
    }

    // -----------------------------------------------------------------------
    // Full scan: no inversions
    // -----------------------------------------------------------------------

    #[test]
    fn test_full_scan_no_inversions() {
        let scanner = InversionScanner::new();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();

        assert!(
            result.detections().is_empty(),
            "balanced input should produce no detections, got {:?}",
            result.detections()
        );
        for (i, &score) in result.axis_scores().iter().enumerate() {
            assert!(
                (score - 1.0).abs() < 1e-6,
                "axis {} should have resistance 1.0, got {}",
                i,
                score
            );
        }
        assert!(
            (result.stealth_resistance() - 1.0).abs() < 1e-12,
            "no stealth inversions should give stealth_resistance = 1.0"
        );
        assert!(
            result.compound_severity().abs() < 1e-12,
            "no compound severity expected"
        );
    }

    // -----------------------------------------------------------------------
    // Full scan: all inversions
    // -----------------------------------------------------------------------

    #[test]
    fn test_full_scan_all_inverted() {
        let scanner = InversionScanner::new();
        let input = InversionScanInput {
            // Max operator imbalance
            operator_scores: [0.5, 0.5, 1.0, 0.0, 0.5, 1.0, 0.0, 0.5, 1.0, 0.0],
            // Reversed domain order
            domain_averages: [0.1, 0.3, 0.6, 0.9],
            // Max drive imbalance
            drive_profile: DriveProfile::new([1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0]).unwrap(),
            // Concentrated state
            state_vector: concentrated_state_vector(),
            // Max sub-drive variance
            domain_drive_scores: {
                let mut s = [[0.5; 4]; 7];
                s[0] = [1.0, 0.0, 1.0, 0.0];
                s
            },
            // All pathways violated
            pathway_scores: [[0.1, 0.2, 0.3, 0.9]; 7],
        };

        let result = scanner.scan(&input).unwrap();

        // Should have detections on multiple axes
        assert!(
            result.detections().len() >= 6,
            "highly inverted input should produce many detections, got {}",
            result.detections().len()
        );

        // Compound severity should be positive
        assert!(
            result.compound_severity() > 0.0,
            "compound severity should be positive with multiple inversions"
        );

        // All axis scores should be < 1.0
        for (i, &score) in result.axis_scores().iter().enumerate() {
            assert!(
                score < 1.0,
                "axis {} should have resistance < 1.0 when inverted, got {}",
                i,
                score
            );
        }
    }

    // -----------------------------------------------------------------------
    // Conversion to InversionResistanceInput
    // -----------------------------------------------------------------------

    #[test]
    fn test_to_resistance_input_balanced() {
        let scanner = InversionScanner::new();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        let resistance = result.to_resistance_input();

        // Perfect resistance
        let score = resistance.resistance_score();
        assert!(
            (score - 1.0).abs() < 1e-6,
            "balanced input should give perfect resistance score, got {}",
            score
        );
    }

    #[test]
    fn test_to_resistance_input_inverted() {
        let scanner = InversionScanner::new();
        let input = InversionScanInput {
            operator_scores: [0.5, 0.5, 1.0, 0.0, 0.5, 1.0, 0.0, 0.5, 1.0, 0.0],
            domain_averages: [0.1, 0.3, 0.6, 0.9],
            drive_profile: DriveProfile::new([1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0]).unwrap(),
            state_vector: concentrated_state_vector(),
            domain_drive_scores: {
                let mut s = [[0.5; 4]; 7];
                s[0] = [1.0, 0.0, 1.0, 0.0];
                s
            },
            pathway_scores: [[0.1, 0.2, 0.3, 0.9]; 7],
        };

        let result = scanner.scan(&input).unwrap();
        let resistance = result.to_resistance_input();

        // Resistance score should be significantly below 1.0
        let score = resistance.resistance_score();
        assert!(
            score < 0.8,
            "inverted input should give low resistance score, got {}",
            score
        );
    }

    #[test]
    fn test_to_resistance_input_fields_valid() {
        let scanner = InversionScanner::new();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        let resistance = result.to_resistance_input();

        for &s in resistance.axis_scores.iter() {
            assert!(s >= 0.0 && s <= 1.0, "axis score out of range: {}", s);
        }
        assert!(
            resistance.stealth_resistance >= 0.0 && resistance.stealth_resistance <= 1.0,
            "stealth_resistance out of range: {}",
            resistance.stealth_resistance
        );
        assert!(
            resistance.compound_severity >= 0.0 && resistance.compound_severity <= 1.0,
            "compound_severity out of range: {}",
            resistance.compound_severity
        );
    }

    // -----------------------------------------------------------------------
    // Stealth resistance in full scan
    // -----------------------------------------------------------------------

    #[test]
    fn test_stealth_resistance_all_stealth() {
        let scanner = InversionScanner::with_threshold(0.0);
        // Create input where most axes have moderate (stealth) severity
        let input = InversionScanInput {
            // Moderate operator imbalance (severity ~0.4)
            operator_scores: {
                let mut s = [0.5; 10];
                s[2] = 0.7;
                s[3] = 0.3;
                s
            },
            // Moderate domain violation
            domain_averages: [0.5, 0.55, 0.45, 0.4],
            // Moderate drive imbalance
            drive_profile: DriveProfile::new([0.65, 0.5, 0.5, 0.5, 0.5, 0.5, 0.35]).unwrap(),
            state_vector: CognitiveStateVector::uniform(),
            domain_drive_scores: [[0.5; 4]; 7],
            pathway_scores: [[0.8, 0.7, 0.6, 0.5]; 7],
        };

        let result = scanner.scan(&input).unwrap();
        let stealth_count = result.detections().iter().filter(|d| d.is_stealth()).count();
        // At least some stealth inversions should be detected
        assert!(
            stealth_count > 0,
            "moderate severities should produce stealth detections"
        );
        assert!(
            result.stealth_resistance() < 1.0,
            "stealth inversions should reduce stealth resistance"
        );
    }

    // -----------------------------------------------------------------------
    // Edge cases
    // -----------------------------------------------------------------------

    #[test]
    fn test_all_zeros_operator_scores() {
        let scanner = InversionScanner::new();
        let scores = [0.0; 10];
        let severity = scanner.detect_operator_inversion(&scores);
        assert!(severity.abs() < 1e-12, "all zero operators have 0 imbalance");
    }

    #[test]
    fn test_all_ones_operator_scores() {
        let scanner = InversionScanner::new();
        let scores = [1.0; 10];
        let severity = scanner.detect_operator_inversion(&scores);
        assert!(severity.abs() < 1e-12, "all 1.0 operators have 0 imbalance");
    }

    #[test]
    fn test_all_zeros_domain_averages() {
        let scanner = InversionScanner::new();
        let averages = [0.0; 4];
        let severity = scanner.detect_domain_inversion(&averages);
        assert!(severity.abs() < 1e-12, "all zero domains have no violation");
    }

    #[test]
    fn test_all_ones_domain_averages() {
        let scanner = InversionScanner::new();
        let averages = [1.0; 4];
        let severity = scanner.detect_domain_inversion(&averages);
        assert!(severity.abs() < 1e-12, "all 1.0 domains have no violation");
    }

    #[test]
    fn test_pathway_all_satisfied() {
        let scanner = InversionScanner::new();
        // All stages fully satisfied (above 0.5), but later < earlier: no violation
        let scores = [[0.9, 0.8, 0.7, 0.6]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!(severity.abs() < 1e-12);
    }

    #[test]
    fn test_pathway_all_stages_equal() {
        let scanner = InversionScanner::new();
        // All stages equal at 0.8 (satisfied): no violation since later <= earlier
        let scores = [[0.8, 0.8, 0.8, 0.8]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!(severity.abs() < 1e-12);
    }

    #[test]
    fn test_pathway_all_stages_equal_below_threshold() {
        let scanner = InversionScanner::new();
        // All stages equal at 0.3 (unsatisfied): no violation since later == earlier
        let scores = [[0.3, 0.3, 0.3, 0.3]; 7];
        let severity = scanner.detect_pathway_inversion(&scores);
        assert!(severity.abs() < 1e-12, "equal low values should not violate");
    }

    // -----------------------------------------------------------------------
    // Validation
    // -----------------------------------------------------------------------

    #[test]
    fn test_validation_rejects_nan_operator() {
        let scanner = InversionScanner::new();
        let mut input = balanced_input();
        input.operator_scores[3] = f64::NAN;
        assert!(scanner.scan(&input).is_err());
    }

    #[test]
    fn test_validation_rejects_out_of_range_operator() {
        let scanner = InversionScanner::new();
        let mut input = balanced_input();
        input.operator_scores[0] = 1.5;
        assert!(scanner.scan(&input).is_err());
    }

    #[test]
    fn test_validation_rejects_nan_domain() {
        let scanner = InversionScanner::new();
        let mut input = balanced_input();
        input.domain_averages[1] = f64::NAN;
        assert!(scanner.scan(&input).is_err());
    }

    #[test]
    fn test_validation_rejects_out_of_range_pathway() {
        let scanner = InversionScanner::new();
        let mut input = balanced_input();
        input.pathway_scores[2][1] = -0.1;
        assert!(scanner.scan(&input).is_err());
    }

    #[test]
    fn test_validation_rejects_nan_subdrive() {
        let scanner = InversionScanner::new();
        let mut input = balanced_input();
        input.domain_drive_scores[4][2] = f64::NAN;
        assert!(scanner.scan(&input).is_err());
    }

    // -----------------------------------------------------------------------
    // Display / formatting
    // -----------------------------------------------------------------------

    #[test]
    fn test_detection_display() {
        let det = InversionDetection::new(
            InversionAxis::Operator,
            0.5,
            "test description".to_string(),
        );
        let display = format!("{}", det);
        assert!(display.contains("N (Operator)"));
        assert!(display.contains("0.500"));
        assert!(display.contains("STEALTH"));
        assert!(display.contains("test description"));
    }

    #[test]
    fn test_scan_result_display() {
        let scanner = InversionScanner::new();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        let display = format!("{}", result);
        assert!(display.contains("Inversion Scan"));
        assert!(display.contains("Stealth resistance"));
        assert!(display.contains("Compound severity"));
    }

    // -----------------------------------------------------------------------
    // Scanner construction
    // -----------------------------------------------------------------------

    #[test]
    fn test_scanner_default() {
        let scanner = InversionScanner::default();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        assert!(result.detections().is_empty());
    }

    #[test]
    fn test_scanner_with_zero_threshold() {
        // With zero threshold, even tiny floating-point differences might register
        let scanner = InversionScanner::with_threshold(0.0);
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        // Balanced input should still have ~0 severity, so even with 0 threshold
        // most axes should be clean (operator/drive balanced, state uniform)
        // But domain has descending order so severity = 0.
        // This test verifies the scanner works with extreme threshold.
        assert!(result.axis_scores()[InversionAxis::Operator.index()] >= 0.99);
    }

    // -----------------------------------------------------------------------
    // Shannon entropy helper
    // -----------------------------------------------------------------------

    #[test]
    fn test_shannon_entropy_uniform() {
        let n = 40;
        let probs = vec![1.0 / n as f64; n];
        let h = shannon_entropy(&probs);
        let expected = (n as f64).ln();
        assert!(
            (h - expected).abs() < 1e-10,
            "uniform distribution entropy should be ln({}), got {}",
            n,
            h
        );
    }

    #[test]
    fn test_shannon_entropy_degenerate() {
        // All probability on one element (with others at near-zero)
        let mut probs = vec![1e-15; 40];
        let rest_total = 1e-15 * 39.0;
        probs[0] = 1.0 - rest_total;
        let h = shannon_entropy(&probs);
        assert!(
            h < 0.01,
            "near-degenerate distribution should have very low entropy, got {}",
            h
        );
    }

    #[test]
    fn test_shannon_entropy_two_equal() {
        let probs = vec![0.5, 0.5];
        let h = shannon_entropy(&probs);
        let expected = 2.0_f64.ln();
        assert!(
            (h - expected).abs() < 1e-10,
            "two equal probabilities should give ln(2), got {}",
            h
        );
    }

    // -----------------------------------------------------------------------
    // Integration: InversionScanResult inversion_count
    // -----------------------------------------------------------------------

    #[test]
    fn test_inversion_count() {
        let scanner = InversionScanner::new();
        let input = balanced_input();
        let result = scanner.scan(&input).unwrap();
        assert_eq!(result.inversion_count(), 0);
    }

    #[test]
    fn test_inversion_count_with_inversions() {
        let scanner = InversionScanner::new();
        let input = InversionScanInput {
            operator_scores: [0.5, 0.5, 1.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
            domain_averages: [0.7, 0.6, 0.5, 0.4],
            drive_profile: DriveProfile::new([0.5; 7]).unwrap(),
            state_vector: CognitiveStateVector::uniform(),
            domain_drive_scores: [[0.5; 4]; 7],
            pathway_scores: [[0.8, 0.7, 0.6, 0.5]; 7],
        };

        let result = scanner.scan(&input).unwrap();
        // Only operator inversion should be detected (severity = 1.0 for CO2-CO3)
        assert_eq!(
            result.inversion_count(),
            1,
            "only operator inversion expected, got {:?}",
            result.detections()
        );
        assert_eq!(result.detections()[0].axis(), InversionAxis::Operator);
    }
}
