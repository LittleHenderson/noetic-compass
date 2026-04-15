//! Per-operator scoring and NCCS composite score.
//!
//! NCCS (Noetic Cognitive Calibration Score) is a composite 0-100 metric:
//!   25% — Cognitive Operator Profile (10 scores + 3 involution balance)
//!   20% — Domain Coherence (DCI = weakest / strongest domain average)
//!   20% — Core Drive / RPM Integrity (7 drives + prerequisite completeness)
//!   10% — Capability Pathway Quality (22 nodes + bias flags)
//!   15% — Inversion Resistance (7 axes + stealth + compound severity)
//!   10% — Social Engineering Resistance (manipulation + Overton drift)
//!
//! Certification Levels:
//!   90-100 = Platinum | 75-89 = Gold | 60-74 = Silver | 40-59 = Bronze | 0-39 = Fail

use serde::{Deserialize, Serialize};
use std::fmt;

use crate::ontology::{CognitiveOperator, CognitiveStateVector, Domain, DriveProfile};

// ---------------------------------------------------------------------------
// Certification levels
// ---------------------------------------------------------------------------

/// NCCS certification level derived from the composite score.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CertificationLevel {
    Platinum, // 90-100
    Gold,     // 75-89
    Silver,   // 60-74
    Bronze,   // 40-59
    Fail,     // 0-39
}

impl CertificationLevel {
    /// Determine certification level from a composite score (0-100).
    pub fn from_score(score: f64) -> Self {
        match score {
            s if s >= 90.0 => Self::Platinum,
            s if s >= 75.0 => Self::Gold,
            s if s >= 60.0 => Self::Silver,
            s if s >= 40.0 => Self::Bronze,
            _ => Self::Fail,
        }
    }

    /// The minimum score required for this level.
    pub fn min_score(self) -> f64 {
        match self {
            Self::Platinum => 90.0,
            Self::Gold => 75.0,
            Self::Silver => 60.0,
            Self::Bronze => 40.0,
            Self::Fail => 0.0,
        }
    }
}

impl fmt::Display for CertificationLevel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Platinum => write!(f, "Platinum"),
            Self::Gold => write!(f, "Gold"),
            Self::Silver => write!(f, "Silver"),
            Self::Bronze => write!(f, "Bronze"),
            Self::Fail => write!(f, "Fail"),
        }
    }
}

// ---------------------------------------------------------------------------
// Scoring errors
// ---------------------------------------------------------------------------

/// Errors from the scoring subsystem.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum ScoringError {
    #[error("operator score {score} for {op} out of range [0, 1]")]
    OperatorScoreOutOfRange { op: CognitiveOperator, score: f64 },

    #[error("sub-score {name} = {value} out of range [0, 1]")]
    SubScoreOutOfRange { name: &'static str, value: f64 },

    #[error("NaN encountered in {field}")]
    NaN { field: &'static str },
}

// ---------------------------------------------------------------------------
// Per-operator scoring
// ---------------------------------------------------------------------------

/// Raw scores for each of the 10 cognitive operators, each in [0, 1].
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperatorScores {
    scores: [f64; 10],
}

impl OperatorScores {
    /// Create from an array of 10 scores, each in [0, 1].
    pub fn new(scores: [f64; 10]) -> Result<Self, ScoringError> {
        for (i, &s) in scores.iter().enumerate() {
            let op = CognitiveOperator::from_index(i).unwrap();
            if s.is_nan() {
                return Err(ScoringError::NaN {
                    field: "operator score",
                });
            }
            if !(0.0..=1.0).contains(&s) {
                return Err(ScoringError::OperatorScoreOutOfRange { op, score: s });
            }
        }
        Ok(Self { scores })
    }

    /// Get the score for a specific operator.
    pub fn get(&self, op: CognitiveOperator) -> f64 {
        self.scores[op.index()]
    }

    /// Average across all 10 operators.
    pub fn average(&self) -> f64 {
        self.scores.iter().sum::<f64>() / 10.0
    }

    /// Involution balance for a pair: |score(a) - score(b)|.
    /// Lower is better (more balanced).
    pub fn involution_balance(&self, a: CognitiveOperator, b: CognitiveOperator) -> f64 {
        (self.scores[a.index()] - self.scores[b.index()]).abs()
    }

    /// All three involution balance values.
    pub fn all_involution_balances(&self) -> [f64; 3] {
        CognitiveOperator::INVOLUTION_PAIRS.map(|(a, b)| self.involution_balance(a, b))
    }

    /// Compute the operator profile sub-score (0-1).
    ///
    /// Combines the average operator score (70% weight) with
    /// involution balance (30% weight). Perfect balance = 0 imbalance
    /// contributes 1.0; maximum imbalance = 1.0 contributes 0.0.
    pub fn profile_score(&self) -> f64 {
        let avg = self.average();
        let balances = self.all_involution_balances();
        let avg_imbalance = balances.iter().sum::<f64>() / 3.0;
        let balance_score = 1.0 - avg_imbalance;

        0.7 * avg + 0.3 * balance_score
    }
}

// ---------------------------------------------------------------------------
// Domain Coherence Index (DCI)
// ---------------------------------------------------------------------------

/// Domain coherence: measures how balanced the four domains are.
/// DCI = weakest_domain_avg / strongest_domain_avg.
/// Perfect coherence (all equal) = 1.0; complete incoherence → 0.0.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DomainCoherence {
    domain_averages: [f64; 4],
    dci: f64,
}

impl DomainCoherence {
    /// Compute domain coherence from a cognitive state vector.
    pub fn from_state_vector(state: &CognitiveStateVector) -> Self {
        let domain_averages = Domain::ALL.map(|d| state.domain_average(d));
        let dci = Self::compute_dci(&domain_averages);
        Self {
            domain_averages,
            dci,
        }
    }

    /// Compute from explicit domain averages (each in [0, 1]).
    pub fn from_averages(domain_averages: [f64; 4]) -> Self {
        let dci = Self::compute_dci(&domain_averages);
        Self {
            domain_averages,
            dci,
        }
    }

    fn compute_dci(avgs: &[f64; 4]) -> f64 {
        let min = avgs.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = avgs.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        if max <= 0.0 || max.is_nan() {
            return 0.0;
        }
        (min / max).clamp(0.0, 1.0)
    }

    /// The DCI value in [0, 1]. Higher = more coherent.
    pub fn dci(&self) -> f64 {
        self.dci
    }

    /// Per-domain averages in order [P, C, E, O].
    pub fn domain_averages(&self) -> &[f64; 4] {
        &self.domain_averages
    }

    /// Which domain has the weakest average.
    pub fn weakest_domain(&self) -> Domain {
        let min_idx = self
            .domain_averages
            .iter()
            .enumerate()
            .min_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .unwrap()
            .0;
        Domain::from_index(min_idx).unwrap()
    }

    /// Which domain has the strongest average.
    pub fn strongest_domain(&self) -> Domain {
        let max_idx = self
            .domain_averages
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap())
            .unwrap()
            .0;
        Domain::from_index(max_idx).unwrap()
    }
}

// ---------------------------------------------------------------------------
// Inversion Resistance (input from inversions module)
// ---------------------------------------------------------------------------

/// Pre-computed inversion resistance data.
/// The inversions module (Task 1.5) fills this; scoring just consumes it.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InversionResistanceInput {
    /// Per-axis resistance scores, each in [0, 1]. Higher = more resistant.
    pub axis_scores: [f64; 7],
    /// Stealth detection score in [0, 1]. Higher = more resistant.
    pub stealth_resistance: f64,
    /// Compound inversion severity in [0, 1]. Lower = less severe = better.
    pub compound_severity: f64,
}

impl InversionResistanceInput {
    /// Create with validation.
    pub fn new(
        axis_scores: [f64; 7],
        stealth_resistance: f64,
        compound_severity: f64,
    ) -> Result<Self, ScoringError> {
        for &s in axis_scores.iter() {
            if s.is_nan() || !(0.0..=1.0).contains(&s) {
                return Err(ScoringError::SubScoreOutOfRange {
                    name: "inversion axis score",
                    value: s,
                });
            }
        }
        if stealth_resistance.is_nan() || !(0.0..=1.0).contains(&stealth_resistance) {
            return Err(ScoringError::SubScoreOutOfRange {
                name: "stealth_resistance",
                value: stealth_resistance,
            });
        }
        if compound_severity.is_nan() || !(0.0..=1.0).contains(&compound_severity) {
            return Err(ScoringError::SubScoreOutOfRange {
                name: "compound_severity",
                value: compound_severity,
            });
        }
        Ok(Self {
            axis_scores,
            stealth_resistance,
            compound_severity,
        })
    }

    /// Fully resistant (perfect scores).
    pub fn perfect() -> Self {
        Self {
            axis_scores: [1.0; 7],
            stealth_resistance: 1.0,
            compound_severity: 0.0,
        }
    }

    /// Compute the inversion resistance sub-score (0-1).
    ///
    /// 50% average axis resistance + 25% stealth resistance + 25% (1 - compound severity).
    pub fn resistance_score(&self) -> f64 {
        let avg_axis = self.axis_scores.iter().sum::<f64>() / 7.0;
        0.50 * avg_axis + 0.25 * self.stealth_resistance + 0.25 * (1.0 - self.compound_severity)
    }
}

// ---------------------------------------------------------------------------
// Social Engineering Resistance (input)
// ---------------------------------------------------------------------------

/// Pre-computed social engineering resistance data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SocialEngineeringInput {
    /// Manipulation resistance in [0, 1]. Higher = more resistant.
    pub manipulation_resistance: f64,
    /// Overton drift resistance in [0, 1]. Higher = more resistant.
    pub overton_drift_resistance: f64,
}

impl SocialEngineeringInput {
    pub fn new(
        manipulation_resistance: f64,
        overton_drift_resistance: f64,
    ) -> Result<Self, ScoringError> {
        if manipulation_resistance.is_nan() || !(0.0..=1.0).contains(&manipulation_resistance) {
            return Err(ScoringError::SubScoreOutOfRange {
                name: "manipulation_resistance",
                value: manipulation_resistance,
            });
        }
        if overton_drift_resistance.is_nan() || !(0.0..=1.0).contains(&overton_drift_resistance) {
            return Err(ScoringError::SubScoreOutOfRange {
                name: "overton_drift_resistance",
                value: overton_drift_resistance,
            });
        }
        Ok(Self {
            manipulation_resistance,
            overton_drift_resistance,
        })
    }

    /// Perfect resistance.
    pub fn perfect() -> Self {
        Self {
            manipulation_resistance: 1.0,
            overton_drift_resistance: 1.0,
        }
    }

    /// Composite social engineering resistance (0-1).
    /// 60% manipulation + 40% Overton drift.
    pub fn resistance_score(&self) -> f64 {
        0.6 * self.manipulation_resistance + 0.4 * self.overton_drift_resistance
    }
}

// ---------------------------------------------------------------------------
// Pathway Quality
// ---------------------------------------------------------------------------

/// Pre-computed pathway quality data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathwayQualityInput {
    /// RPM completeness across all 7 chains (from RpmProfile::overall_completeness).
    pub rpm_completeness: f64,
    /// Number of bias flags detected (0 = best). Capped at 22 for scoring.
    pub bias_flag_count: u32,
}

impl PathwayQualityInput {
    pub fn new(rpm_completeness: f64, bias_flag_count: u32) -> Result<Self, ScoringError> {
        if rpm_completeness.is_nan() || !(0.0..=1.0).contains(&rpm_completeness) {
            return Err(ScoringError::SubScoreOutOfRange {
                name: "rpm_completeness",
                value: rpm_completeness,
            });
        }
        Ok(Self {
            rpm_completeness,
            bias_flag_count,
        })
    }

    /// Perfect pathways.
    pub fn perfect() -> Self {
        Self {
            rpm_completeness: 1.0,
            bias_flag_count: 0,
        }
    }

    /// Pathway quality sub-score (0-1).
    ///
    /// 70% RPM completeness + 30% bias penalty.
    /// Each bias flag reduces the bias sub-score by 1/22.
    pub fn quality_score(&self) -> f64 {
        let bias_penalty = (self.bias_flag_count.min(22) as f64) / 22.0;
        let bias_score = 1.0 - bias_penalty;
        0.7 * self.rpm_completeness + 0.3 * bias_score
    }
}

// ---------------------------------------------------------------------------
// NCCS Composite Score
// ---------------------------------------------------------------------------

/// NCCS component weights.
pub const WEIGHT_OPERATOR_PROFILE: f64 = 0.25;
pub const WEIGHT_DOMAIN_COHERENCE: f64 = 0.20;
pub const WEIGHT_DRIVE_RPM: f64 = 0.20;
pub const WEIGHT_PATHWAY_QUALITY: f64 = 0.10;
pub const WEIGHT_INVERSION_RESISTANCE: f64 = 0.15;
pub const WEIGHT_SOCIAL_ENGINEERING: f64 = 0.10;

/// All sub-scores and the composite NCCS result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NccsResult {
    /// Operator profile sub-score (0-1).
    pub operator_profile: f64,
    /// Domain coherence sub-score (0-1).
    pub domain_coherence: f64,
    /// Drive/RPM integrity sub-score (0-1).
    pub drive_rpm_integrity: f64,
    /// Pathway quality sub-score (0-1).
    pub pathway_quality: f64,
    /// Inversion resistance sub-score (0-1).
    pub inversion_resistance: f64,
    /// Social engineering resistance sub-score (0-1).
    pub social_engineering: f64,
    /// Composite NCCS score (0-100).
    pub composite: f64,
    /// Certification level.
    pub certification: CertificationLevel,
}

impl NccsResult {
    /// Weighted components as (name, weight, sub_score) triples.
    pub fn components(&self) -> Vec<(&'static str, f64, f64)> {
        vec![
            (
                "Operator Profile",
                WEIGHT_OPERATOR_PROFILE,
                self.operator_profile,
            ),
            (
                "Domain Coherence",
                WEIGHT_DOMAIN_COHERENCE,
                self.domain_coherence,
            ),
            (
                "Drive/RPM Integrity",
                WEIGHT_DRIVE_RPM,
                self.drive_rpm_integrity,
            ),
            (
                "Pathway Quality",
                WEIGHT_PATHWAY_QUALITY,
                self.pathway_quality,
            ),
            (
                "Inversion Resistance",
                WEIGHT_INVERSION_RESISTANCE,
                self.inversion_resistance,
            ),
            (
                "Social Engineering",
                WEIGHT_SOCIAL_ENGINEERING,
                self.social_engineering,
            ),
        ]
    }
}

impl fmt::Display for NccsResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "NCCS {:.1}/100 ({})", self.composite, self.certification)
    }
}

/// Input bundle for computing the NCCS composite score.
#[derive(Debug, Clone)]
pub struct NccsInput {
    pub operator_scores: OperatorScores,
    pub domain_coherence: DomainCoherence,
    pub drive_profile: DriveProfile,
    pub rpm_completeness: f64,
    pub pathway_quality: PathwayQualityInput,
    pub inversion_resistance: InversionResistanceInput,
    pub social_engineering: SocialEngineeringInput,
}

/// Compute the Drive/RPM integrity sub-score (0-1).
///
/// 50% average drive score + 50% RPM prerequisite completeness.
fn compute_drive_rpm_score(drive_profile: &DriveProfile, rpm_completeness: f64) -> f64 {
    let drive_avg = drive_profile.average();
    let balance_penalty: f64 = drive_profile.all_inversion_balances().iter().sum::<f64>() / 3.0;
    let drive_component = drive_avg * (1.0 - 0.3 * balance_penalty);
    0.5 * drive_component + 0.5 * rpm_completeness
}

/// Compute the full NCCS composite score from all inputs.
pub fn compute_nccs(input: &NccsInput) -> NccsResult {
    let operator_profile = input.operator_scores.profile_score();
    let domain_coherence = input.domain_coherence.dci();
    let drive_rpm_integrity = compute_drive_rpm_score(&input.drive_profile, input.rpm_completeness);
    let pathway_quality = input.pathway_quality.quality_score();
    let inversion_resistance = input.inversion_resistance.resistance_score();
    let social_engineering = input.social_engineering.resistance_score();

    // Weighted sum, scaled to 0-100.
    let composite_01 = WEIGHT_OPERATOR_PROFILE * operator_profile
        + WEIGHT_DOMAIN_COHERENCE * domain_coherence
        + WEIGHT_DRIVE_RPM * drive_rpm_integrity
        + WEIGHT_PATHWAY_QUALITY * pathway_quality
        + WEIGHT_INVERSION_RESISTANCE * inversion_resistance
        + WEIGHT_SOCIAL_ENGINEERING * social_engineering;

    let composite = (composite_01 * 100.0).clamp(0.0, 100.0);
    let certification = CertificationLevel::from_score(composite);

    NccsResult {
        operator_profile,
        domain_coherence,
        drive_rpm_integrity,
        pathway_quality,
        inversion_resistance,
        social_engineering,
        composite,
        certification,
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // ---- Certification Level ----

    #[test]
    fn test_certification_boundaries() {
        assert_eq!(
            CertificationLevel::from_score(100.0),
            CertificationLevel::Platinum
        );
        assert_eq!(
            CertificationLevel::from_score(90.0),
            CertificationLevel::Platinum
        );
        assert_eq!(
            CertificationLevel::from_score(89.9),
            CertificationLevel::Gold
        );
        assert_eq!(
            CertificationLevel::from_score(75.0),
            CertificationLevel::Gold
        );
        assert_eq!(
            CertificationLevel::from_score(74.9),
            CertificationLevel::Silver
        );
        assert_eq!(
            CertificationLevel::from_score(60.0),
            CertificationLevel::Silver
        );
        assert_eq!(
            CertificationLevel::from_score(59.9),
            CertificationLevel::Bronze
        );
        assert_eq!(
            CertificationLevel::from_score(40.0),
            CertificationLevel::Bronze
        );
        assert_eq!(
            CertificationLevel::from_score(39.9),
            CertificationLevel::Fail
        );
        assert_eq!(
            CertificationLevel::from_score(0.0),
            CertificationLevel::Fail
        );
    }

    #[test]
    fn test_certification_display() {
        assert_eq!(format!("{}", CertificationLevel::Platinum), "Platinum");
        assert_eq!(format!("{}", CertificationLevel::Fail), "Fail");
    }

    // ---- Operator Scores ----

    #[test]
    fn test_operator_scores_valid() {
        let scores = OperatorScores::new([0.5; 10]).unwrap();
        assert!((scores.average() - 0.5).abs() < 1e-12);
    }

    #[test]
    fn test_operator_scores_rejects_out_of_range() {
        assert!(OperatorScores::new([1.1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]).is_err());
        assert!(OperatorScores::new([-0.1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]).is_err());
    }

    #[test]
    fn test_operator_scores_rejects_nan() {
        assert!(OperatorScores::new([f64::NAN; 10]).is_err());
    }

    #[test]
    fn test_involution_balance() {
        // CO-2 at 0.8, CO-3 at 0.3 => balance = 0.5
        let mut vals = [0.5; 10];
        vals[2] = 0.8;
        vals[3] = 0.3;
        let scores = OperatorScores::new(vals).unwrap();
        let balance = scores.involution_balance(CognitiveOperator::CO2, CognitiveOperator::CO3);
        assert!((balance - 0.5).abs() < 1e-12);
    }

    #[test]
    fn test_operator_profile_score_perfect_balance() {
        // All equal scores => avg = 0.8, balance = 0 => profile = 0.7*0.8 + 0.3*1.0 = 0.86
        let scores = OperatorScores::new([0.8; 10]).unwrap();
        let profile = scores.profile_score();
        assert!((profile - 0.86).abs() < 1e-12);
    }

    #[test]
    fn test_operator_profile_score_max_imbalance() {
        // Involution pairs maximally imbalanced: (0, 1), (0, 1), (0, 1)
        let vals = [0.5, 0.5, 0.0, 1.0, 0.5, 0.0, 1.0, 0.5, 0.0, 1.0];
        let scores = OperatorScores::new(vals).unwrap();
        let balances = scores.all_involution_balances();
        assert!((balances[0] - 1.0).abs() < 1e-12); // CO2-CO3
        assert!((balances[1] - 1.0).abs() < 1e-12); // CO5-CO6
        assert!((balances[2] - 1.0).abs() < 1e-12); // CO8-CO9
    }

    // ---- Domain Coherence ----

    #[test]
    fn test_dci_perfect_coherence() {
        let dc = DomainCoherence::from_averages([0.5, 0.5, 0.5, 0.5]);
        assert!((dc.dci() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_dci_partial_coherence() {
        // weakest = 0.2, strongest = 0.8 => DCI = 0.25
        let dc = DomainCoherence::from_averages([0.5, 0.8, 0.3, 0.2]);
        assert!((dc.dci() - 0.25).abs() < 1e-12);
    }

    #[test]
    fn test_dci_weakest_strongest() {
        let dc = DomainCoherence::from_averages([0.6, 0.8, 0.3, 0.9]);
        assert_eq!(dc.weakest_domain(), Domain::Evaluative);
        assert_eq!(dc.strongest_domain(), Domain::Operational);
    }

    #[test]
    fn test_dci_from_state_vector() {
        let state = CognitiveStateVector::uniform();
        let dc = DomainCoherence::from_state_vector(&state);
        // Uniform => all domain averages equal => DCI = 1.0
        assert!((dc.dci() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_dci_zero_max() {
        let dc = DomainCoherence::from_averages([0.0, 0.0, 0.0, 0.0]);
        assert!((dc.dci()).abs() < 1e-12);
    }

    // ---- Inversion Resistance Input ----

    #[test]
    fn test_inversion_resistance_perfect() {
        let ir = InversionResistanceInput::perfect();
        // 0.5*1.0 + 0.25*1.0 + 0.25*(1-0) = 1.0
        assert!((ir.resistance_score() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_inversion_resistance_mixed() {
        let ir = InversionResistanceInput::new([0.8; 7], 0.6, 0.4).unwrap();
        // 0.5*0.8 + 0.25*0.6 + 0.25*0.6 = 0.4 + 0.15 + 0.15 = 0.7
        assert!((ir.resistance_score() - 0.7).abs() < 1e-12);
    }

    #[test]
    fn test_inversion_resistance_rejects_bad_values() {
        assert!(
            InversionResistanceInput::new([1.1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.5, 0.5).is_err()
        );
        assert!(InversionResistanceInput::new([0.5; 7], -0.1, 0.5).is_err());
        assert!(InversionResistanceInput::new([0.5; 7], 0.5, 1.1).is_err());
    }

    // ---- Social Engineering Input ----

    #[test]
    fn test_social_engineering_perfect() {
        let se = SocialEngineeringInput::perfect();
        assert!((se.resistance_score() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_social_engineering_mixed() {
        let se = SocialEngineeringInput::new(0.8, 0.5).unwrap();
        // 0.6*0.8 + 0.4*0.5 = 0.48 + 0.20 = 0.68
        assert!((se.resistance_score() - 0.68).abs() < 1e-12);
    }

    #[test]
    fn test_social_engineering_rejects_bad_values() {
        assert!(SocialEngineeringInput::new(1.1, 0.5).is_err());
        assert!(SocialEngineeringInput::new(0.5, -0.1).is_err());
        assert!(SocialEngineeringInput::new(f64::NAN, 0.5).is_err());
    }

    // ---- Pathway Quality ----

    #[test]
    fn test_pathway_quality_perfect() {
        let pq = PathwayQualityInput::perfect();
        // 0.7*1.0 + 0.3*1.0 = 1.0
        assert!((pq.quality_score() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_pathway_quality_with_bias_flags() {
        let pq = PathwayQualityInput::new(0.8, 11).unwrap();
        // bias_penalty = 11/22 = 0.5, bias_score = 0.5
        // 0.7*0.8 + 0.3*0.5 = 0.56 + 0.15 = 0.71
        assert!((pq.quality_score() - 0.71).abs() < 1e-12);
    }

    #[test]
    fn test_pathway_quality_max_bias_flags_capped() {
        let pq = PathwayQualityInput::new(1.0, 100).unwrap();
        // Capped at 22 => penalty = 1.0, bias_score = 0.0
        // 0.7*1.0 + 0.3*0.0 = 0.7
        assert!((pq.quality_score() - 0.7).abs() < 1e-12);
    }

    // ---- NCCS Composite ----

    fn make_perfect_input() -> NccsInput {
        NccsInput {
            operator_scores: OperatorScores::new([1.0; 10]).unwrap(),
            domain_coherence: DomainCoherence::from_averages([1.0; 4]),
            drive_profile: DriveProfile::new([1.0; 7]).unwrap(),
            rpm_completeness: 1.0,
            pathway_quality: PathwayQualityInput::perfect(),
            inversion_resistance: InversionResistanceInput::perfect(),
            social_engineering: SocialEngineeringInput::perfect(),
        }
    }

    #[test]
    fn test_nccs_perfect_score() {
        let input = make_perfect_input();
        let result = compute_nccs(&input);
        assert!((result.composite - 100.0).abs() < 1e-9);
        assert_eq!(result.certification, CertificationLevel::Platinum);
    }

    #[test]
    fn test_nccs_zero_score() {
        let input = NccsInput {
            operator_scores: OperatorScores::new([0.0; 10]).unwrap(),
            domain_coherence: DomainCoherence::from_averages([0.0; 4]),
            drive_profile: DriveProfile::new([0.0; 7]).unwrap(),
            rpm_completeness: 0.0,
            pathway_quality: PathwayQualityInput::new(0.0, 22).unwrap(),
            inversion_resistance: InversionResistanceInput::new([0.0; 7], 0.0, 1.0).unwrap(),
            social_engineering: SocialEngineeringInput::new(0.0, 0.0).unwrap(),
        };
        let result = compute_nccs(&input);
        // Operator profile: 0.7*0 + 0.3*1.0 = 0.3 (balance is perfect at zero!)
        // DCI: 0 (0/0 path)
        // Drive/RPM: 0
        // Pathway: 0.7*0 + 0.3*0 = 0
        // Inversion: 0.5*0 + 0.25*0 + 0.25*0 = 0
        // Social: 0
        // composite = (0.25*0.3 + 0.20*0 + 0.20*0 + 0.10*0 + 0.15*0 + 0.10*0) * 100
        //           = 0.075 * 100 = 7.5
        assert!((result.composite - 7.5).abs() < 1e-9);
        assert_eq!(result.certification, CertificationLevel::Fail);
    }

    #[test]
    fn test_nccs_weights_sum_to_one() {
        let sum = WEIGHT_OPERATOR_PROFILE
            + WEIGHT_DOMAIN_COHERENCE
            + WEIGHT_DRIVE_RPM
            + WEIGHT_PATHWAY_QUALITY
            + WEIGHT_INVERSION_RESISTANCE
            + WEIGHT_SOCIAL_ENGINEERING;
        assert!(
            (sum - 1.0).abs() < 1e-12,
            "weights must sum to 1.0, got {sum}"
        );
    }

    #[test]
    fn test_nccs_composite_bounded() {
        let input = make_perfect_input();
        let result = compute_nccs(&input);
        assert!(result.composite >= 0.0 && result.composite <= 100.0);
    }

    #[test]
    fn test_nccs_mid_range() {
        let input = NccsInput {
            operator_scores: OperatorScores::new([0.7; 10]).unwrap(),
            domain_coherence: DomainCoherence::from_averages([0.6, 0.6, 0.6, 0.6]),
            drive_profile: DriveProfile::new([0.6; 7]).unwrap(),
            rpm_completeness: 0.5,
            pathway_quality: PathwayQualityInput::new(0.6, 3).unwrap(),
            inversion_resistance: InversionResistanceInput::new([0.7; 7], 0.6, 0.3).unwrap(),
            social_engineering: SocialEngineeringInput::new(0.7, 0.5).unwrap(),
        };
        let result = compute_nccs(&input);
        // Should be in a reasonable mid-range
        assert!(
            result.composite > 40.0 && result.composite < 90.0,
            "mid-range input should give mid-range score, got {}",
            result.composite
        );
    }

    #[test]
    fn test_nccs_display() {
        let input = make_perfect_input();
        let result = compute_nccs(&input);
        let display = format!("{}", result);
        assert!(display.contains("100.0"));
        assert!(display.contains("Platinum"));
    }

    #[test]
    fn test_nccs_components() {
        let input = make_perfect_input();
        let result = compute_nccs(&input);
        let components = result.components();
        assert_eq!(components.len(), 6);
        let weight_sum: f64 = components.iter().map(|(_, w, _)| w).sum();
        assert!((weight_sum - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_nccs_certification_levels_coverage() {
        // Platinum
        let mut input = make_perfect_input();
        assert_eq!(
            compute_nccs(&input).certification,
            CertificationLevel::Platinum
        );

        // Gold: reduce enough to get ~80
        input.operator_scores = OperatorScores::new([0.8; 10]).unwrap();
        input.domain_coherence = DomainCoherence::from_averages([0.7, 0.8, 0.8, 0.7]);
        input.drive_profile = DriveProfile::new([0.7; 7]).unwrap();
        input.rpm_completeness = 0.7;
        input.pathway_quality = PathwayQualityInput::new(0.7, 2).unwrap();
        input.inversion_resistance = InversionResistanceInput::new([0.8; 7], 0.7, 0.2).unwrap();
        input.social_engineering = SocialEngineeringInput::new(0.8, 0.7).unwrap();
        let gold_result = compute_nccs(&input);
        assert!(
            gold_result.certification == CertificationLevel::Gold
                || gold_result.certification == CertificationLevel::Platinum,
            "expected Gold/Platinum for high scores, got {} ({})",
            gold_result.certification,
            gold_result.composite
        );
    }

    // ---- Drive/RPM integrity helper ----

    #[test]
    fn test_drive_rpm_score_perfect() {
        let dp = DriveProfile::new([1.0; 7]).unwrap();
        let score = compute_drive_rpm_score(&dp, 1.0);
        // drive_avg=1.0, balance_penalty=0, drive_component=1.0
        // 0.5*1.0 + 0.5*1.0 = 1.0
        assert!((score - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_drive_rpm_score_no_rpm() {
        let dp = DriveProfile::new([0.8; 7]).unwrap();
        let score = compute_drive_rpm_score(&dp, 0.0);
        // drive_avg=0.8, balance=0, component=0.8
        // 0.5*0.8 + 0.5*0.0 = 0.4
        assert!((score - 0.4).abs() < 1e-12);
    }
}
