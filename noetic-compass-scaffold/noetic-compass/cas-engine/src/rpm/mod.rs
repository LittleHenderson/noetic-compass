//! RPM Monad with Section-Retraction Semantics
//!
//! Implements Correction 2: RPM is section-retraction, NOT adjunction.
//!   - εI ∘ ηI = idI (realization after embedding = identity) — the SECTION LAW
//!   - ηI ∘ εI ≠ idR(I) (re-embedding after realization may lose info) — NOT reversible
//!   - Prerequisite satisfaction is ONE-DIRECTIONAL
//!
//! Implements Correction 3: Noetic Coverage uses COUNIT not UNIT.
//!   - Covering morphisms point TOWARD the covered object (ε direction).
//!
//! # RPM Chain Structure
//!
//! Each core drive n has a chain: A0 → Dn → Wn → Pn → Outcome
//!   - A0 = Pure Desire (shared root)
//!   - Dn = Drive-level aspiration
//!   - Wn = Will-level commitment
//!   - Pn = Proficiency-level mastery
//!
//! Prerequisite gating is one-directional: a node can only be satisfied if
//! its prerequisite is satisfied first. Once cached, changing downstream
//! scores does NOT retroactively alter upstream satisfaction.

use serde::{Deserialize, Serialize};
use std::fmt;
use thiserror::Error;

use crate::ontology::{CoreDrive, PathwayNode, PathwayStage};

// ---------------------------------------------------------------------------
// Error types
// ---------------------------------------------------------------------------

/// Errors arising from RPM operations.
#[derive(Debug, Error, Clone, PartialEq)]
pub enum RpmError {
    /// A raw score was outside the valid [0, 1] interval or was NaN.
    #[error("Score out of range for node {node}: {score} (must be in [0, 1])")]
    ScoreOutOfRange { node: PathwayNode, score: f64 },

    /// The satisfaction threshold was outside [0, 1] or was NaN.
    #[error("Threshold out of range: {0} (must be in [0, 1])")]
    ThresholdOutOfRange(f64),

    /// The section law εI ∘ ηI = idI was violated. This indicates a bug.
    #[error("Section law violation: embed then realize gave {output} instead of {input}")]
    SectionLawViolation { input: f64, output: f64 },
}

// ---------------------------------------------------------------------------
// EmbeddedScore — the enriched representation space R(I)
// ---------------------------------------------------------------------------

/// A score embedded into a richer representation space via η.
///
/// η(s) = (s, s², √s) — an enriched triple that captures linear, quadratic,
/// and sub-linear facets of the score. This embedding is NOT invertible:
/// ε ∘ η = id (section law), but η ∘ ε ≠ id (information loss on round-trip
/// through realization then re-embedding).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct EmbeddedScore {
    /// The three components: (s, s², √s).
    components: [f64; 3],
}

impl EmbeddedScore {
    /// Direct construction from raw components. Used internally and for testing
    /// non-reversibility (constructing an `EmbeddedScore` that is NOT the image
    /// of any single score under η).
    pub fn from_components(components: [f64; 3]) -> Self {
        Self { components }
    }

    /// The three components of the embedded score.
    pub fn components(&self) -> [f64; 3] {
        self.components
    }

    /// Accessor for the first component (the "linear" channel).
    pub fn linear(&self) -> f64 {
        self.components[0]
    }

    /// Accessor for the second component (the "quadratic" channel).
    pub fn quadratic(&self) -> f64 {
        self.components[1]
    }

    /// Accessor for the third component (the "sub-linear / sqrt" channel).
    pub fn sqrt(&self) -> f64 {
        self.components[2]
    }
}

impl fmt::Display for EmbeddedScore {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "({:.4}, {:.4}, {:.4})",
            self.components[0], self.components[1], self.components[2]
        )
    }
}

// ---------------------------------------------------------------------------
// Embedding η and Realization ε
// ---------------------------------------------------------------------------

/// Embedding map η: I → R(I).
///
/// η(s) = (s, s², √s).
///
/// Requires s ∈ [0, 1] and not NaN.
pub fn embed(score: f64) -> Result<EmbeddedScore, RpmError> {
    if score.is_nan() || !(0.0..=1.0).contains(&score) {
        return Err(RpmError::ScoreOutOfRange {
            node: PathwayNode::A0, // placeholder; caller should provide context
            score,
        });
    }
    Ok(EmbeddedScore {
        components: [score, score * score, score.sqrt()],
    })
}

/// Realization map ε: R(I) → I.
///
/// ε(a, b, c) = a (projection onto the first component).
///
/// Together with embed, this satisfies the section law: ε(η(s)) = s for all s.
/// But η(ε(e)) ≠ e in general — the quadratic and sqrt channels may not be
/// consistent after an arbitrary manipulation of the embedded representation.
pub fn realize(embedded: &EmbeddedScore) -> f64 {
    embedded.components[0]
}

/// Verify the section law εI ∘ ηI = idI for a given score.
///
/// Returns Ok(()) if realize(embed(s)) == s (within floating-point tolerance),
/// or Err(SectionLawViolation) otherwise.
pub fn verify_section_law(score: f64) -> Result<(), RpmError> {
    let embedded = embed(score)?;
    let realized = realize(&embedded);
    // Exact equality for this particular implementation (projection of first
    // component), but we allow a tiny epsilon for floating-point safety.
    if (realized - score).abs() > f64::EPSILON * 2.0 {
        return Err(RpmError::SectionLawViolation {
            input: score,
            output: realized,
        });
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// RpmState — enriched state for a single pathway node
// ---------------------------------------------------------------------------

/// The RPM-enriched state of a single pathway node.
///
/// Tracks the raw score, its embedded representation, the realized score
/// (which equals the raw score by the section law), and prerequisite-gated
/// satisfaction status.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RpmState {
    /// Which pathway node this state belongs to.
    node: PathwayNode,
    /// Raw assessment score in [0, 1].
    raw_score: f64,
    /// η(raw_score) — embedded into the richer representation space.
    embedded_score: EmbeddedScore,
    /// ε(embedded_score) — realized back. Must equal raw_score (section law).
    realized_score: f64,
    /// Whether this node meets the threshold AND all prerequisites are satisfied.
    /// Once set, this value is cached and NOT re-computed on downstream changes
    /// (one-directional prerequisite gating per Correction 2).
    satisfied: bool,
}

impl RpmState {
    /// Construct an RPM state for a node.
    ///
    /// - `score` must be in [0, 1].
    /// - `threshold` must be in [0, 1].
    /// - `prerequisite_satisfied` indicates whether the prerequisite node (if any)
    ///   has been satisfied. For A0, this should always be `true`.
    ///
    /// Satisfaction = score >= threshold AND prerequisite_satisfied.
    pub fn new(
        node: PathwayNode,
        score: f64,
        threshold: f64,
        prerequisite_satisfied: bool,
    ) -> Result<Self, RpmError> {
        if score.is_nan() || !(0.0..=1.0).contains(&score) {
            return Err(RpmError::ScoreOutOfRange { node, score });
        }
        if threshold.is_nan() || !(0.0..=1.0).contains(&threshold) {
            return Err(RpmError::ThresholdOutOfRange(threshold));
        }

        let embedded_score = EmbeddedScore {
            components: [score, score * score, score.sqrt()],
        };
        let realized_score = realize(&embedded_score);

        // Defensive assertion: section law must hold.
        debug_assert!(
            (realized_score - score).abs() <= f64::EPSILON * 2.0,
            "Section law violation in RpmState::new"
        );

        let meets_threshold = score >= threshold;
        let satisfied = meets_threshold && prerequisite_satisfied;

        Ok(Self {
            node,
            raw_score: score,
            embedded_score,
            realized_score,
            satisfied,
        })
    }

    /// The pathway node.
    pub fn node(&self) -> PathwayNode {
        self.node
    }

    /// Raw assessment score.
    pub fn raw_score(&self) -> f64 {
        self.raw_score
    }

    /// The embedded representation η(score).
    pub fn embedded_score(&self) -> &EmbeddedScore {
        &self.embedded_score
    }

    /// The realized score ε(η(score)). Equal to raw_score by the section law.
    pub fn realized_score(&self) -> f64 {
        self.realized_score
    }

    /// Whether the node is satisfied (score >= threshold AND prerequisite satisfied).
    pub fn is_satisfied(&self) -> bool {
        self.satisfied
    }

    /// Whether the raw score alone meets the threshold, regardless of prerequisites.
    pub fn meets_threshold(&self, threshold: f64) -> bool {
        self.raw_score >= threshold
    }
}

impl fmt::Display for RpmState {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}: score={:.3}, embedded={}, satisfied={}",
            self.node, self.raw_score, self.embedded_score, self.satisfied
        )
    }
}

// ---------------------------------------------------------------------------
// RpmGate — the one-directional prerequisite gate
// ---------------------------------------------------------------------------

/// The prerequisite gate. Checks whether a node's prerequisite is satisfied
/// before allowing the node itself to be satisfied.
///
/// This implements one-directional gating (Correction 2): once a node's
/// satisfaction is determined and cached, changing downstream scores does
/// NOT retroactively alter upstream status.
pub struct RpmGate;

impl RpmGate {
    /// Check whether a node's prerequisite is satisfied.
    ///
    /// - A0 has no prerequisite, so always returns `true`.
    /// - For Dn, Wn, Pn: looks up the prerequisite node's satisfaction in the
    ///   provided states array.
    ///
    /// The `states` map must contain the prerequisite node (if any). If the
    /// prerequisite node is not found, returns `false` (fail-closed).
    pub fn check(node: PathwayNode, states: &[RpmState]) -> bool {
        match node.prerequisite() {
            None => true, // A0 has no prerequisite
            Some(prereq) => states
                .iter()
                .find(|s| s.node() == prereq)
                .map_or(false, |s| s.is_satisfied()),
        }
    }

    /// Evaluate a complete chain of nodes in prerequisite order, producing
    /// `RpmState` instances with proper gating.
    ///
    /// `nodes_and_scores` must be in prerequisite order: [A0, Dn, Wn, Pn].
    /// Each entry is (PathwayNode, raw_score).
    pub fn evaluate_chain(
        nodes_and_scores: &[(PathwayNode, f64)],
        threshold: f64,
    ) -> Result<Vec<RpmState>, RpmError> {
        if threshold.is_nan() || !(0.0..=1.0).contains(&threshold) {
            return Err(RpmError::ThresholdOutOfRange(threshold));
        }

        let mut states = Vec::with_capacity(nodes_and_scores.len());

        for &(node, score) in nodes_and_scores {
            let prereq_satisfied = Self::check(node, &states);
            let state = RpmState::new(node, score, threshold, prereq_satisfied)?;
            states.push(state);
        }

        Ok(states)
    }
}

// ---------------------------------------------------------------------------
// RpmChain — a complete chain for one core drive
// ---------------------------------------------------------------------------

/// A complete RPM chain for one core drive: A0 → Dn → Wn → Pn.
///
/// The chain enforces prerequisite gating: each node can only be satisfied
/// if its predecessor in the chain is also satisfied. This gating is
/// one-directional and cached at construction time.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RpmChain {
    /// The core drive this chain belongs to.
    drive: CoreDrive,
    /// The four RPM states in order: [A0, Dn, Wn, Pn].
    states: [RpmState; 4],
    /// The satisfaction threshold used.
    threshold: f64,
}

impl RpmChain {
    /// Construct a chain for a given drive.
    ///
    /// - `drive`: which of the 7 core drives
    /// - `scores`: [A0_score, Dn_score, Wn_score, Pn_score], each in [0, 1]
    /// - `threshold`: satisfaction threshold in [0, 1]
    ///
    /// Prerequisite gating is applied during construction: if A0 is unsatisfied,
    /// then Dn, Wn, Pn are all unsatisfied regardless of their scores.
    pub fn new(drive: CoreDrive, scores: [f64; 4], threshold: f64) -> Result<Self, RpmError> {
        if threshold.is_nan() || !(0.0..=1.0).contains(&threshold) {
            return Err(RpmError::ThresholdOutOfRange(threshold));
        }

        let chain_nodes = PathwayNode::chain(drive);
        let nodes_and_scores: Vec<(PathwayNode, f64)> = chain_nodes
            .iter()
            .zip(scores.iter())
            .map(|(&n, &s)| (n, s))
            .collect();

        let state_vec = RpmGate::evaluate_chain(&nodes_and_scores, threshold)?;

        // Convert Vec to [RpmState; 4]. We know evaluate_chain returns exactly
        // as many states as we passed in.
        let states: [RpmState; 4] = [
            state_vec[0].clone(),
            state_vec[1].clone(),
            state_vec[2].clone(),
            state_vec[3].clone(),
        ];

        Ok(Self {
            drive,
            states,
            threshold,
        })
    }

    /// The core drive this chain belongs to.
    pub fn drive(&self) -> CoreDrive {
        self.drive
    }

    /// The four RPM states in order: [A0, Dn, Wn, Pn].
    pub fn states(&self) -> &[RpmState; 4] {
        &self.states
    }

    /// Get the state at a specific stage.
    pub fn state_at(&self, stage: PathwayStage) -> &RpmState {
        match stage {
            PathwayStage::Aspiration => &self.states[0],
            PathwayStage::Drive => &self.states[1],
            PathwayStage::Will => &self.states[2],
            PathwayStage::Proficiency => &self.states[3],
        }
    }

    /// The satisfaction threshold.
    pub fn threshold(&self) -> f64 {
        self.threshold
    }

    /// Fraction of the chain that is satisfied (0.0 to 1.0).
    ///
    /// Each of the 4 nodes contributes 0.25. A chain where A0 and Dn are
    /// satisfied but Wn and Pn are not yields 0.5.
    pub fn completeness(&self) -> f64 {
        let count = self.states.iter().filter(|s| s.is_satisfied()).count();
        count as f64 / 4.0
    }

    /// How far the chain progresses before hitting an unsatisfied node.
    ///
    /// Returns the number of consecutively satisfied nodes from the start:
    /// 0 = A0 unsatisfied, 1 = only A0 satisfied, ... 4 = fully satisfied.
    pub fn depth(&self) -> usize {
        self.states.iter().take_while(|s| s.is_satisfied()).count()
    }

    /// Whether the entire chain is fully satisfied (all 4 nodes).
    pub fn is_complete(&self) -> bool {
        self.states.iter().all(|s| s.is_satisfied())
    }

    /// The raw scores for all 4 nodes.
    pub fn raw_scores(&self) -> [f64; 4] {
        [
            self.states[0].raw_score(),
            self.states[1].raw_score(),
            self.states[2].raw_score(),
            self.states[3].raw_score(),
        ]
    }
}

impl fmt::Display for RpmChain {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "RPM Chain {}: completeness={:.0}%, depth={}",
            self.drive,
            self.completeness() * 100.0,
            self.depth()
        )?;
        for state in &self.states {
            write!(f, "\n  {}", state)?;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// RpmProfile — complete RPM profile for all 7 drives
// ---------------------------------------------------------------------------

/// Complete RPM profile: 7 chains (one per core drive) sharing a common A0.
///
/// The A0 score is shared across all chains. Each chain has its own Dn, Wn, Pn
/// scores. Prerequisite gating flows from A0 through each drive's chain
/// independently.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RpmProfile {
    /// The 7 RPM chains, indexed by drive (F1=0, ..., F7=6).
    chains: [RpmChain; 7],
    /// The shared A0 (Pure Desire) score.
    a0_score: f64,
    /// The threshold used for all chains.
    threshold: f64,
}

impl RpmProfile {
    /// Construct a complete RPM profile.
    ///
    /// - `a0_score`: the shared A0 (Pure Desire) score in [0, 1]
    /// - `drive_scores`: for each of the 7 drives, the [Dn, Wn, Pn] scores
    ///   in order [F1, F2, F3, F4, F5, F6, F7]
    /// - `threshold`: satisfaction threshold in [0, 1]
    ///
    /// Each chain gets scores [a0_score, Dn, Wn, Pn].
    pub fn new(
        a0_score: f64,
        drive_scores: [[f64; 3]; 7],
        threshold: f64,
    ) -> Result<Self, RpmError> {
        if a0_score.is_nan() || !(0.0..=1.0).contains(&a0_score) {
            return Err(RpmError::ScoreOutOfRange {
                node: PathwayNode::A0,
                score: a0_score,
            });
        }
        if threshold.is_nan() || !(0.0..=1.0).contains(&threshold) {
            return Err(RpmError::ThresholdOutOfRange(threshold));
        }

        let mut chains_vec = Vec::with_capacity(7);
        for (i, drive) in CoreDrive::ALL.iter().enumerate() {
            let ds = drive_scores[i];
            let chain_scores = [a0_score, ds[0], ds[1], ds[2]];
            chains_vec.push(RpmChain::new(*drive, chain_scores, threshold)?);
        }

        let chains: [RpmChain; 7] = [
            chains_vec[0].clone(),
            chains_vec[1].clone(),
            chains_vec[2].clone(),
            chains_vec[3].clone(),
            chains_vec[4].clone(),
            chains_vec[5].clone(),
            chains_vec[6].clone(),
        ];

        Ok(Self {
            chains,
            a0_score,
            threshold,
        })
    }

    /// The 7 RPM chains.
    pub fn chains(&self) -> &[RpmChain; 7] {
        &self.chains
    }

    /// Get the chain for a specific core drive.
    pub fn chain(&self, drive: CoreDrive) -> &RpmChain {
        &self.chains[drive.index()]
    }

    /// The shared A0 score.
    pub fn a0_score(&self) -> f64 {
        self.a0_score
    }

    /// The threshold used.
    pub fn threshold(&self) -> f64 {
        self.threshold
    }

    /// Whether A0 (Pure Desire) is satisfied for this profile.
    pub fn a0_satisfied(&self) -> bool {
        // All chains share the same A0; check the first one
        self.chains[0].state_at(PathwayStage::Aspiration).is_satisfied()
    }

    /// Overall completeness: average of all 7 chain completeness values.
    ///
    /// Returns a value in [0.0, 1.0]. A profile where all 7 chains are fully
    /// satisfied (all 28 nodes across all chains, with shared A0) yields 1.0.
    pub fn overall_completeness(&self) -> f64 {
        let sum: f64 = self.chains.iter().map(|c| c.completeness()).sum();
        sum / 7.0
    }

    /// Number of fully completed chains (where depth == 4).
    pub fn completed_chain_count(&self) -> usize {
        self.chains.iter().filter(|c| c.is_complete()).count()
    }

    /// Per-drive completeness values.
    pub fn per_drive_completeness(&self) -> [f64; 7] {
        let mut result = [0.0; 7];
        for (i, chain) in self.chains.iter().enumerate() {
            result[i] = chain.completeness();
        }
        result
    }

    /// The weakest chain (lowest completeness). Breaks ties by drive index.
    pub fn weakest_chain(&self) -> &RpmChain {
        self.chains
            .iter()
            .min_by(|a, b| {
                a.completeness()
                    .partial_cmp(&b.completeness())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap() // Safe: chains is always length 7
    }

    /// The strongest chain (highest completeness). Breaks ties by drive index.
    pub fn strongest_chain(&self) -> &RpmChain {
        self.chains
            .iter()
            .max_by(|a, b| {
                a.completeness()
                    .partial_cmp(&b.completeness())
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap()
    }
}

impl fmt::Display for RpmProfile {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(
            f,
            "RPM Profile: A0={:.3}, threshold={:.3}, overall_completeness={:.0}%",
            self.a0_score,
            self.threshold,
            self.overall_completeness() * 100.0
        )?;
        for chain in &self.chains {
            writeln!(f, "  {}", chain.drive())?;
            writeln!(f, "    completeness: {:.0}%", chain.completeness() * 100.0)?;
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Covering morphism direction (Correction 3)
// ---------------------------------------------------------------------------

/// Direction marker for noetic coverage morphisms.
///
/// Per Correction 3, covering morphisms use the COUNIT ε (toward the target),
/// NOT the unit η (away from the target). This type documents the direction
/// at the type level to prevent accidental misuse.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CoverageMorphismDirection {
    /// ε: R(I) → I — the counit, pointing TOWARD the covered object.
    /// This is the CORRECT direction for Noe-Cov-3.
    Counit,
    /// η: I → R(I) — the unit, pointing AWAY from the covered object.
    /// This is INCORRECT for Noe-Cov-3 and must not be used for coverage.
    #[allow(dead_code)]
    Unit,
}

impl CoverageMorphismDirection {
    /// The correct direction for noetic coverage (always Counit).
    pub fn correct() -> Self {
        Self::Counit
    }
}

// ===========================================================================
// Tests
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // -----------------------------------------------------------------------
    // Section law tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_section_law_boundary_values() {
        // ε(η(s)) = s must hold for all valid s in [0, 1]
        for &s in &[0.0, 0.25, 0.5, 0.75, 1.0] {
            let embedded = embed(s).unwrap();
            let realized = realize(&embedded);
            assert!(
                (realized - s).abs() < f64::EPSILON * 2.0,
                "Section law failed for s={}: got {}",
                s,
                realized
            );
        }
    }

    #[test]
    fn test_section_law_fine_grained() {
        // Test section law across 1001 evenly-spaced points
        for i in 0..=1000 {
            let s = i as f64 / 1000.0;
            assert!(verify_section_law(s).is_ok(), "Section law failed for s={}", s);
        }
    }

    #[test]
    fn test_section_law_via_verify() {
        assert!(verify_section_law(0.0).is_ok());
        assert!(verify_section_law(0.5).is_ok());
        assert!(verify_section_law(1.0).is_ok());
    }

    // -----------------------------------------------------------------------
    // Non-reversibility tests (η ∘ ε ≠ id)
    // -----------------------------------------------------------------------

    #[test]
    fn test_non_reversibility() {
        // Construct an EmbeddedScore that is NOT the image of any single score
        // under η. For instance, (0.5, 0.1, 0.9) — if this came from η(s),
        // we'd need s=0.5, s²=0.25, √s≈0.707, but we have 0.1 and 0.9.
        let arbitrary = EmbeddedScore::from_components([0.5, 0.1, 0.9]);
        let realized = realize(&arbitrary);
        assert_eq!(realized, 0.5);

        // Re-embed the realized value
        let re_embedded = embed(realized).unwrap();
        // The re-embedded score should differ from the arbitrary one
        assert_ne!(
            re_embedded.components(),
            arbitrary.components(),
            "η(ε(e)) should NOT equal e for non-trivial embedded scores"
        );

        // Specifically: re_embedded = (0.5, 0.25, 0.707...) vs arbitrary = (0.5, 0.1, 0.9)
        assert!(
            (re_embedded.quadratic() - 0.25).abs() < 1e-12,
            "Re-embedded quadratic should be 0.5² = 0.25"
        );
        assert!(
            (arbitrary.quadratic() - 0.1).abs() < 1e-12,
            "Arbitrary quadratic was 0.1"
        );
    }

    #[test]
    fn test_embed_is_consistent() {
        // η(s) = (s, s², √s) — verify the embedding formula itself
        let s = 0.64;
        let embedded = embed(s).unwrap();
        assert!((embedded.linear() - 0.64).abs() < 1e-12);
        assert!((embedded.quadratic() - 0.4096).abs() < 1e-12);
        assert!((embedded.sqrt() - 0.8).abs() < 1e-12);
    }

    // -----------------------------------------------------------------------
    // Score bounds validation
    // -----------------------------------------------------------------------

    #[test]
    fn test_embed_rejects_out_of_range() {
        assert!(embed(-0.01).is_err());
        assert!(embed(1.01).is_err());
        assert!(embed(f64::NAN).is_err());
        assert!(embed(f64::INFINITY).is_err());
        assert!(embed(f64::NEG_INFINITY).is_err());
    }

    #[test]
    fn test_embed_accepts_boundary_values() {
        assert!(embed(0.0).is_ok());
        assert!(embed(1.0).is_ok());
        assert!(embed(0.5).is_ok());
    }

    #[test]
    fn test_rpm_state_rejects_bad_score() {
        let result = RpmState::new(PathwayNode::A0, -0.1, 0.5, true);
        assert!(matches!(
            result,
            Err(RpmError::ScoreOutOfRange { score, .. }) if (score - (-0.1)).abs() < 1e-12
        ));

        let result = RpmState::new(PathwayNode::A0, 1.5, 0.5, true);
        assert!(matches!(result, Err(RpmError::ScoreOutOfRange { .. })));

        let result = RpmState::new(PathwayNode::A0, f64::NAN, 0.5, true);
        assert!(matches!(result, Err(RpmError::ScoreOutOfRange { .. })));
    }

    #[test]
    fn test_rpm_state_rejects_bad_threshold() {
        let result = RpmState::new(PathwayNode::A0, 0.5, -0.1, true);
        assert!(matches!(result, Err(RpmError::ThresholdOutOfRange(_))));

        let result = RpmState::new(PathwayNode::A0, 0.5, 1.5, true);
        assert!(matches!(result, Err(RpmError::ThresholdOutOfRange(_))));

        let result = RpmState::new(PathwayNode::A0, 0.5, f64::NAN, true);
        assert!(matches!(result, Err(RpmError::ThresholdOutOfRange(_))));
    }

    // -----------------------------------------------------------------------
    // Prerequisite gating tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_prerequisite_gating_blocks_downstream() {
        // A0 is below threshold => all downstream nodes must be unsatisfied,
        // even if their own scores exceed the threshold.
        let chain = RpmChain::new(
            CoreDrive::F1Unity,
            [0.3, 0.9, 0.9, 0.9], // A0=0.3 below threshold
            0.5,                    // threshold
        )
        .unwrap();

        assert!(!chain.state_at(PathwayStage::Aspiration).is_satisfied());
        assert!(!chain.state_at(PathwayStage::Drive).is_satisfied());
        assert!(!chain.state_at(PathwayStage::Will).is_satisfied());
        assert!(!chain.state_at(PathwayStage::Proficiency).is_satisfied());

        assert_eq!(chain.completeness(), 0.0);
        assert_eq!(chain.depth(), 0);
    }

    #[test]
    fn test_prerequisite_gating_partial_chain() {
        // A0 and D1 satisfied, but W1 below threshold => P1 unsatisfied too
        let chain = RpmChain::new(
            CoreDrive::F1Unity,
            [0.8, 0.7, 0.3, 0.9], // W1=0.3 below threshold
            0.5,
        )
        .unwrap();

        assert!(chain.state_at(PathwayStage::Aspiration).is_satisfied());
        assert!(chain.state_at(PathwayStage::Drive).is_satisfied());
        assert!(!chain.state_at(PathwayStage::Will).is_satisfied());
        assert!(!chain.state_at(PathwayStage::Proficiency).is_satisfied());

        assert!((chain.completeness() - 0.5).abs() < 1e-12);
        assert_eq!(chain.depth(), 2);
    }

    #[test]
    fn test_prerequisite_gating_full_chain() {
        let chain = RpmChain::new(
            CoreDrive::F3Vitality,
            [0.8, 0.7, 0.6, 0.5],
            0.5,
        )
        .unwrap();

        assert!(chain.state_at(PathwayStage::Aspiration).is_satisfied());
        assert!(chain.state_at(PathwayStage::Drive).is_satisfied());
        assert!(chain.state_at(PathwayStage::Will).is_satisfied());
        assert!(chain.state_at(PathwayStage::Proficiency).is_satisfied());

        assert!((chain.completeness() - 1.0).abs() < 1e-12);
        assert_eq!(chain.depth(), 4);
        assert!(chain.is_complete());
    }

    #[test]
    fn test_gating_is_one_directional() {
        // Key test for Correction 2: once cached, upstream satisfaction does
        // NOT change even if we imagine "re-computing" with different downstream.
        //
        // We test this by verifying that a chain where only A0 is satisfied
        // has the correct cached states, and that the A0 state is fully
        // independent of the downstream scores.
        let chain_a = RpmChain::new(
            CoreDrive::F2Wisdom,
            [0.8, 0.3, 0.9, 0.9],
            0.5,
        )
        .unwrap();

        let chain_b = RpmChain::new(
            CoreDrive::F2Wisdom,
            [0.8, 0.3, 0.1, 0.1],
            0.5,
        )
        .unwrap();

        // A0 satisfaction is identical regardless of downstream scores
        assert_eq!(
            chain_a.state_at(PathwayStage::Aspiration).is_satisfied(),
            chain_b.state_at(PathwayStage::Aspiration).is_satisfied()
        );

        // D2 is unsatisfied in both (score 0.3 < threshold 0.5)
        assert!(!chain_a.state_at(PathwayStage::Drive).is_satisfied());
        assert!(!chain_b.state_at(PathwayStage::Drive).is_satisfied());

        // W2 is unsatisfied in both (D2 prerequisite failed)
        assert!(!chain_a.state_at(PathwayStage::Will).is_satisfied());
        assert!(!chain_b.state_at(PathwayStage::Will).is_satisfied());
    }

    // -----------------------------------------------------------------------
    // RpmGate tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_rpm_gate_a0_always_passes() {
        assert!(RpmGate::check(PathwayNode::A0, &[]));
    }

    #[test]
    fn test_rpm_gate_missing_prerequisite_fails() {
        // D1 requires A0, but states list is empty => fail-closed
        assert!(!RpmGate::check(PathwayNode::D(CoreDrive::F1Unity), &[]));
    }

    #[test]
    fn test_rpm_gate_with_satisfied_prerequisite() {
        let a0_state = RpmState::new(PathwayNode::A0, 0.8, 0.5, true).unwrap();
        assert!(RpmGate::check(
            PathwayNode::D(CoreDrive::F1Unity),
            &[a0_state]
        ));
    }

    #[test]
    fn test_rpm_gate_with_unsatisfied_prerequisite() {
        let a0_state = RpmState::new(PathwayNode::A0, 0.3, 0.5, true).unwrap();
        assert!(!RpmGate::check(
            PathwayNode::D(CoreDrive::F1Unity),
            &[a0_state]
        ));
    }

    #[test]
    fn test_rpm_gate_evaluate_chain() {
        let nodes_and_scores = vec![
            (PathwayNode::A0, 0.8),
            (PathwayNode::D(CoreDrive::F4Connection), 0.7),
            (PathwayNode::W(CoreDrive::F4Connection), 0.4), // below threshold
            (PathwayNode::P(CoreDrive::F4Connection), 0.9),
        ];

        let states = RpmGate::evaluate_chain(&nodes_and_scores, 0.5).unwrap();

        assert!(states[0].is_satisfied());  // A0: 0.8 >= 0.5
        assert!(states[1].is_satisfied());  // D4: 0.7 >= 0.5, prereq OK
        assert!(!states[2].is_satisfied()); // W4: 0.4 < 0.5
        assert!(!states[3].is_satisfied()); // P4: prereq W4 failed
    }

    // -----------------------------------------------------------------------
    // Chain completeness tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_chain_completeness_all_satisfied() {
        let chain = RpmChain::new(
            CoreDrive::F7Purpose,
            [0.9, 0.8, 0.7, 0.6],
            0.5,
        )
        .unwrap();
        assert!((chain.completeness() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_chain_completeness_none_satisfied() {
        let chain = RpmChain::new(
            CoreDrive::F7Purpose,
            [0.1, 0.8, 0.7, 0.6],
            0.5,
        )
        .unwrap();
        assert!((chain.completeness() - 0.0).abs() < 1e-12);
    }

    #[test]
    fn test_chain_completeness_three_satisfied() {
        let chain = RpmChain::new(
            CoreDrive::F5Agency,
            [0.9, 0.8, 0.7, 0.3], // P5 below threshold
            0.5,
        )
        .unwrap();
        assert!((chain.completeness() - 0.75).abs() < 1e-12);
        assert_eq!(chain.depth(), 3);
    }

    #[test]
    fn test_chain_raw_scores() {
        let chain = RpmChain::new(
            CoreDrive::F6Structure,
            [0.1, 0.2, 0.3, 0.4],
            0.5,
        )
        .unwrap();
        assert_eq!(chain.raw_scores(), [0.1, 0.2, 0.3, 0.4]);
    }

    // -----------------------------------------------------------------------
    // RpmProfile tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_profile_all_complete() {
        let drive_scores = [[0.9, 0.8, 0.7]; 7];
        let profile = RpmProfile::new(0.95, drive_scores, 0.5).unwrap();

        assert!((profile.overall_completeness() - 1.0).abs() < 1e-12);
        assert_eq!(profile.completed_chain_count(), 7);
        assert!(profile.a0_satisfied());
    }

    #[test]
    fn test_profile_a0_blocks_everything() {
        let drive_scores = [[0.9, 0.9, 0.9]; 7];
        let profile = RpmProfile::new(0.3, drive_scores, 0.5).unwrap();

        // A0=0.3 is below threshold=0.5, so nothing should be satisfied
        assert!(!profile.a0_satisfied());
        assert!((profile.overall_completeness() - 0.0).abs() < 1e-12);
        assert_eq!(profile.completed_chain_count(), 0);
    }

    #[test]
    fn test_profile_mixed_completeness() {
        let drive_scores = [
            [0.8, 0.7, 0.6], // F1: all satisfied => 1.0 completeness (with A0)
            [0.8, 0.7, 0.3], // F2: D,W satisfied, P not => 0.75
            [0.8, 0.3, 0.9], // F3: D satisfied, W not => 0.50
            [0.3, 0.9, 0.9], // F4: D not => 0.25
            [0.8, 0.7, 0.6], // F5: all => 1.0
            [0.8, 0.7, 0.6], // F6: all => 1.0
            [0.8, 0.7, 0.6], // F7: all => 1.0
        ];
        let profile = RpmProfile::new(0.9, drive_scores, 0.5).unwrap();

        assert!(profile.a0_satisfied());

        let completeness_values = profile.per_drive_completeness();
        assert!((completeness_values[0] - 1.0).abs() < 1e-12);    // F1
        assert!((completeness_values[1] - 0.75).abs() < 1e-12);   // F2
        assert!((completeness_values[2] - 0.5).abs() < 1e-12);    // F3
        assert!((completeness_values[3] - 0.25).abs() < 1e-12);   // F4
        assert!((completeness_values[4] - 1.0).abs() < 1e-12);    // F5
        assert!((completeness_values[5] - 1.0).abs() < 1e-12);    // F6
        assert!((completeness_values[6] - 1.0).abs() < 1e-12);    // F7

        // Expected overall: (1.0 + 0.75 + 0.5 + 0.25 + 1.0 + 1.0 + 1.0) / 7
        let expected_overall = (1.0 + 0.75 + 0.5 + 0.25 + 1.0 + 1.0 + 1.0) / 7.0;
        assert!((profile.overall_completeness() - expected_overall).abs() < 1e-12);

        assert_eq!(profile.completed_chain_count(), 4);
    }

    #[test]
    fn test_profile_weakest_and_strongest() {
        let drive_scores = [
            [0.8, 0.7, 0.6], // F1: complete (1.0)
            [0.3, 0.9, 0.9], // F2: only A0 satisfied (0.25)
            [0.8, 0.7, 0.6], // F3: complete (1.0)
            [0.8, 0.7, 0.6], // F4: complete (1.0)
            [0.8, 0.7, 0.6], // F5: complete (1.0)
            [0.8, 0.7, 0.6], // F6: complete (1.0)
            [0.8, 0.7, 0.6], // F7: complete (1.0)
        ];
        let profile = RpmProfile::new(0.9, drive_scores, 0.5).unwrap();

        assert_eq!(profile.weakest_chain().drive(), CoreDrive::F2Wisdom);
        // Strongest: F7Purpose (last with completeness 1.0, max_by returns last tie)
        assert_eq!(profile.strongest_chain().drive(), CoreDrive::F7Purpose);
    }

    #[test]
    fn test_profile_rejects_bad_a0() {
        let drive_scores = [[0.5, 0.5, 0.5]; 7];
        assert!(matches!(
            RpmProfile::new(-0.1, drive_scores, 0.5),
            Err(RpmError::ScoreOutOfRange { .. })
        ));
        assert!(matches!(
            RpmProfile::new(f64::NAN, drive_scores, 0.5),
            Err(RpmError::ScoreOutOfRange { .. })
        ));
    }

    #[test]
    fn test_profile_rejects_bad_threshold() {
        let drive_scores = [[0.5, 0.5, 0.5]; 7];
        assert!(matches!(
            RpmProfile::new(0.5, drive_scores, -0.1),
            Err(RpmError::ThresholdOutOfRange(_))
        ));
    }

    #[test]
    fn test_profile_rejects_bad_drive_score() {
        let mut drive_scores = [[0.5, 0.5, 0.5]; 7];
        drive_scores[3] = [0.5, 1.5, 0.5]; // F4 W-score out of range
        assert!(matches!(
            RpmProfile::new(0.5, drive_scores, 0.5),
            Err(RpmError::ScoreOutOfRange { .. })
        ));
    }

    // -----------------------------------------------------------------------
    // RpmState detail tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_rpm_state_section_law_at_construction() {
        // For any valid state, realized_score must equal raw_score
        let state = RpmState::new(PathwayNode::A0, 0.73, 0.5, true).unwrap();
        assert!(
            (state.realized_score() - state.raw_score()).abs() < f64::EPSILON * 2.0,
            "Section law: realized must equal raw"
        );
    }

    #[test]
    fn test_rpm_state_embedded_values() {
        let s = 0.49;
        let state = RpmState::new(PathwayNode::A0, s, 0.5, true).unwrap();
        let emb = state.embedded_score();
        assert!((emb.linear() - s).abs() < 1e-12);
        assert!((emb.quadratic() - s * s).abs() < 1e-12);
        assert!((emb.sqrt() - s.sqrt()).abs() < 1e-12);
    }

    #[test]
    fn test_rpm_state_satisfaction_with_prereq() {
        // Score meets threshold, prerequisite satisfied => satisfied
        let state = RpmState::new(PathwayNode::A0, 0.6, 0.5, true).unwrap();
        assert!(state.is_satisfied());

        // Score meets threshold, prerequisite NOT satisfied => NOT satisfied
        let state = RpmState::new(
            PathwayNode::D(CoreDrive::F1Unity),
            0.6,
            0.5,
            false,
        )
        .unwrap();
        assert!(!state.is_satisfied());

        // Score below threshold, prerequisite satisfied => NOT satisfied
        let state = RpmState::new(PathwayNode::A0, 0.3, 0.5, true).unwrap();
        assert!(!state.is_satisfied());
    }

    #[test]
    fn test_rpm_state_meets_threshold() {
        let state = RpmState::new(PathwayNode::A0, 0.6, 0.5, false).unwrap();
        // meets_threshold only checks score, not prerequisite
        assert!(state.meets_threshold(0.5));
        assert!(!state.meets_threshold(0.7));
        // but is_satisfied should be false because prereq is false
        assert!(!state.is_satisfied());
    }

    // -----------------------------------------------------------------------
    // Display formatting tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_rpm_state_display() {
        let state = RpmState::new(PathwayNode::A0, 0.5, 0.5, true).unwrap();
        let display = format!("{}", state);
        assert!(display.contains("A0"));
        assert!(display.contains("0.500"));
        assert!(display.contains("satisfied=true"));
    }

    #[test]
    fn test_chain_display() {
        let chain = RpmChain::new(
            CoreDrive::F1Unity,
            [0.8, 0.7, 0.6, 0.5],
            0.5,
        )
        .unwrap();
        let display = format!("{}", chain);
        assert!(display.contains("F1 Unity"));
        assert!(display.contains("completeness=100%"));
    }

    // -----------------------------------------------------------------------
    // Coverage direction test (Correction 3)
    // -----------------------------------------------------------------------

    #[test]
    fn test_coverage_direction_is_counit() {
        let dir = CoverageMorphismDirection::correct();
        assert_eq!(dir, CoverageMorphismDirection::Counit);
    }

    // -----------------------------------------------------------------------
    // Edge case tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_boundary_threshold_equals_score() {
        // Score == threshold => satisfied (>=, not >)
        let chain = RpmChain::new(
            CoreDrive::F4Connection,
            [0.5, 0.5, 0.5, 0.5],
            0.5,
        )
        .unwrap();
        assert!(chain.is_complete());
        assert!((chain.completeness() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_zero_threshold() {
        // threshold=0.0 => all scores >= 0.0 are satisfied
        let chain = RpmChain::new(
            CoreDrive::F1Unity,
            [0.0, 0.0, 0.0, 0.0],
            0.0,
        )
        .unwrap();
        assert!(chain.is_complete());
    }

    #[test]
    fn test_max_threshold() {
        // threshold=1.0 => only score=1.0 satisfies
        let chain = RpmChain::new(
            CoreDrive::F1Unity,
            [1.0, 1.0, 1.0, 1.0],
            1.0,
        )
        .unwrap();
        assert!(chain.is_complete());

        let chain2 = RpmChain::new(
            CoreDrive::F1Unity,
            [0.999, 1.0, 1.0, 1.0],
            1.0,
        )
        .unwrap();
        assert!(!chain2.state_at(PathwayStage::Aspiration).is_satisfied());
        assert_eq!(chain2.depth(), 0);
    }

    #[test]
    fn test_chain_all_drives() {
        // Ensure chains can be constructed for all 7 drives
        for drive in CoreDrive::ALL {
            let chain = RpmChain::new(drive, [0.8, 0.7, 0.6, 0.5], 0.5).unwrap();
            assert_eq!(chain.drive(), drive);
            assert!(chain.is_complete());
        }
    }

    #[test]
    fn test_embedded_score_display() {
        let emb = EmbeddedScore::from_components([0.5, 0.25, 0.7071]);
        let display = format!("{}", emb);
        assert!(display.contains("0.5000"));
        assert!(display.contains("0.2500"));
        assert!(display.contains("0.7071"));
    }
}
