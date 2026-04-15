//! Integration tests for the CAS Scoring Engine.
//!
//! These tests exercise cross-module interactions between ontology, metric,
//! scoring, and rpm modules. They verify that the full assessment pipeline
//! produces correct, internally consistent results.

use cas_engine::metric::{
    bhattacharyya_coefficient, fisher_rao_norm, geodesic_distance, validate_tangent_vector,
};
use cas_engine::ontology::{
    CognitiveOperator, CognitiveStateId, CognitiveStateVector, CoreDrive, Domain, DomainDrive,
    DriveProfile, InversionAxis, PathwayNode, NUM_STATES,
};
use cas_engine::rpm::{embed, realize, verify_section_law, RpmChain, RpmProfile};
use cas_engine::scoring::{
    compute_nccs, CertificationLevel, DomainCoherence, InversionResistanceInput, NccsInput,
    OperatorScores, PathwayQualityInput, SocialEngineeringInput, WEIGHT_DOMAIN_COHERENCE,
    WEIGHT_DRIVE_RPM, WEIGHT_INVERSION_RESISTANCE, WEIGHT_OPERATOR_PROFILE, WEIGHT_PATHWAY_QUALITY,
    WEIGHT_SOCIAL_ENGINEERING,
};

// ===========================================================================
// Helper functions
// ===========================================================================

/// Build a CognitiveStateVector from raw positive weights by normalizing them.
fn make_state_vector(weights: [f64; NUM_STATES]) -> CognitiveStateVector {
    let sum: f64 = weights.iter().sum();
    let mut probs = [0.0; NUM_STATES];
    for (i, &w) in weights.iter().enumerate() {
        probs[i] = w / sum;
    }
    CognitiveStateVector::new(probs).expect("helper should produce valid state vector")
}

/// Create a state vector shifted toward a specific index, keeping all
/// probabilities strictly positive.
fn shifted_vector(shift_index: usize, shift_amount: f64) -> CognitiveStateVector {
    let base = 1.0 / NUM_STATES as f64;
    let mut weights = [base; NUM_STATES];
    weights[shift_index] += shift_amount;
    let excess_per_other = shift_amount / (NUM_STATES - 1) as f64;
    for i in 0..NUM_STATES {
        if i != shift_index {
            weights[i] -= excess_per_other;
        }
    }
    let sum: f64 = weights.iter().sum();
    for w in weights.iter_mut() {
        *w /= sum;
    }
    CognitiveStateVector::new(weights).expect("helper should produce valid shifted vector")
}

/// Create a state vector emphasizing a particular domain.
/// Assigns `domain_weight` to each of the 10 states within `domain`,
/// and a small positive residual to the remaining 30 states.
fn domain_biased_vector(domain: Domain, domain_weight: f64) -> CognitiveStateVector {
    assert!(domain_weight > 0.0 && domain_weight < 1.0);
    let per_state_domain = domain_weight / 10.0;
    let per_state_other = (1.0 - domain_weight) / 30.0;
    let mut probs = [per_state_other; NUM_STATES];
    let start = domain.index() * 10;
    for i in start..start + 10 {
        probs[i] = per_state_domain;
    }
    CognitiveStateVector::new(probs).expect("helper should produce valid domain-biased vector")
}

/// Build a complete NccsInput with the specified sub-score levels (all uniform).
fn make_assessment(
    op_score: f64,
    domain_avg: f64,
    drive_score: f64,
    rpm_completeness: f64,
    pathway_completeness: f64,
    bias_flags: u32,
    inv_axis_scores: f64,
    stealth: f64,
    compound: f64,
    manip: f64,
    overton: f64,
) -> NccsInput {
    NccsInput {
        operator_scores: OperatorScores::new([op_score; 10]).unwrap(),
        domain_coherence: DomainCoherence::from_averages([domain_avg; 4]),
        drive_profile: DriveProfile::new([drive_score; 7]).unwrap(),
        rpm_completeness,
        pathway_quality: PathwayQualityInput::new(pathway_completeness, bias_flags).unwrap(),
        inversion_resistance: InversionResistanceInput::new(
            [inv_axis_scores; 7],
            stealth,
            compound,
        )
        .unwrap(),
        social_engineering: SocialEngineeringInput::new(manip, overton).unwrap(),
    }
}

/// Build a "perfect" NccsInput (all 1.0 scores, no bias, no compound severity).
fn make_perfect_assessment() -> NccsInput {
    make_assessment(1.0, 1.0, 1.0, 1.0, 1.0, 0, 1.0, 1.0, 0.0, 1.0, 1.0)
}

/// Build a "worst-case" NccsInput (all zeros / maximally penalized).
fn make_worst_assessment() -> NccsInput {
    NccsInput {
        operator_scores: OperatorScores::new([0.0; 10]).unwrap(),
        domain_coherence: DomainCoherence::from_averages([0.0; 4]),
        drive_profile: DriveProfile::new([0.0; 7]).unwrap(),
        rpm_completeness: 0.0,
        pathway_quality: PathwayQualityInput::new(0.0, 22).unwrap(),
        inversion_resistance: InversionResistanceInput::new([0.0; 7], 0.0, 1.0).unwrap(),
        social_engineering: SocialEngineeringInput::new(0.0, 0.0).unwrap(),
    }
}

// ===========================================================================
// 1. End-to-end assessment flow (6 tests)
// ===========================================================================

#[test]
fn e2e_perfect_assessment_yields_platinum() {
    let input = make_perfect_assessment();
    let result = compute_nccs(&input);

    assert!(
        (result.composite - 100.0).abs() < 1e-9,
        "perfect input should yield 100.0, got {}",
        result.composite
    );
    assert_eq!(result.certification, CertificationLevel::Platinum);

    // All sub-scores should be 1.0
    assert!((result.operator_profile - 1.0).abs() < 1e-9);
    assert!((result.domain_coherence - 1.0).abs() < 1e-9);
    assert!((result.drive_rpm_integrity - 1.0).abs() < 1e-9);
    assert!((result.pathway_quality - 1.0).abs() < 1e-9);
    assert!((result.inversion_resistance - 1.0).abs() < 1e-9);
    assert!((result.social_engineering - 1.0).abs() < 1e-9);
}

#[test]
fn e2e_worst_assessment_yields_fail() {
    let input = make_worst_assessment();
    let result = compute_nccs(&input);

    assert!(
        result.composite < 40.0,
        "worst input should yield Fail (<40), got {}",
        result.composite
    );
    assert_eq!(result.certification, CertificationLevel::Fail);
}

#[test]
fn e2e_mid_range_assessment_yields_silver_or_gold() {
    let input = make_assessment(0.7, 0.7, 0.7, 0.7, 0.7, 2, 0.7, 0.7, 0.2, 0.7, 0.7);
    let result = compute_nccs(&input);

    assert!(
        result.composite >= 50.0 && result.composite <= 90.0,
        "mid-range input should yield moderate score, got {}",
        result.composite
    );
    assert!(
        result.certification == CertificationLevel::Silver
            || result.certification == CertificationLevel::Gold,
        "expected Silver or Gold, got {} ({})",
        result.certification,
        result.composite
    );
}

#[test]
fn e2e_state_vector_to_domain_coherence_to_nccs() {
    // Build state vector, derive domain coherence, feed into NCCS
    let sv = CognitiveStateVector::uniform();
    let dc = DomainCoherence::from_state_vector(&sv);

    // Uniform vector => DCI = 1.0 (all domain averages equal)
    assert!((dc.dci() - 1.0).abs() < 1e-12);

    let input = NccsInput {
        operator_scores: OperatorScores::new([0.8; 10]).unwrap(),
        domain_coherence: dc,
        drive_profile: DriveProfile::new([0.8; 7]).unwrap(),
        rpm_completeness: 0.8,
        pathway_quality: PathwayQualityInput::new(0.8, 1).unwrap(),
        inversion_resistance: InversionResistanceInput::new([0.8; 7], 0.8, 0.1).unwrap(),
        social_engineering: SocialEngineeringInput::new(0.8, 0.8).unwrap(),
    };
    let result = compute_nccs(&input);
    assert!(
        result.composite > 70.0,
        "high-quality input should score > 70, got {}",
        result.composite
    );
}

#[test]
fn e2e_rpm_profile_feeds_into_nccs() {
    // Build RPM profile, extract completeness, use in NCCS
    let rpm_profile = RpmProfile::new(
        0.9,
        [
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
            [0.9, 0.9, 0.9],
        ],
        0.5,
    )
    .unwrap();

    let completeness = rpm_profile.overall_completeness();
    assert!(
        (completeness - 1.0).abs() < 1e-12,
        "all scores above threshold should yield completeness=1.0, got {}",
        completeness
    );

    let input = NccsInput {
        operator_scores: OperatorScores::new([0.9; 10]).unwrap(),
        domain_coherence: DomainCoherence::from_averages([0.9; 4]),
        drive_profile: DriveProfile::new([0.9; 7]).unwrap(),
        rpm_completeness: completeness,
        pathway_quality: PathwayQualityInput::new(completeness, 0).unwrap(),
        inversion_resistance: InversionResistanceInput::perfect(),
        social_engineering: SocialEngineeringInput::perfect(),
    };
    let result = compute_nccs(&input);
    assert_eq!(
        result.certification,
        CertificationLevel::Platinum,
        "high-quality RPM+everything should yield Platinum, got {} ({})",
        result.certification,
        result.composite
    );
}

#[test]
fn e2e_all_subscores_contribute_to_composite() {
    // Start with a perfect assessment and verify each component is accounted for
    let result = compute_nccs(&make_perfect_assessment());
    let components = result.components();

    assert_eq!(components.len(), 6, "should have exactly 6 NCCS components");

    let reconstructed: f64 = components.iter().map(|(_, w, s)| w * s).sum::<f64>() * 100.0;
    assert!(
        (reconstructed - result.composite).abs() < 1e-9,
        "sum of weighted sub-scores should equal composite: reconstructed={}, composite={}",
        reconstructed,
        result.composite
    );
}

// ===========================================================================
// 2. Ontology <-> Metric integration (6 tests)
// ===========================================================================

#[test]
fn metric_uniform_self_distance_is_zero() {
    let u = CognitiveStateVector::uniform();
    let d = geodesic_distance(&u, &u);
    assert!(
        d.abs() < 1e-12,
        "d(uniform, uniform) should be 0, got {}",
        d
    );
}

#[test]
fn metric_different_state_vectors_positive_distance() {
    let p = CognitiveStateVector::uniform();
    let q = shifted_vector(0, 0.01);
    let d = geodesic_distance(&p, &q);
    assert!(
        d > 0.0,
        "different distributions should have positive distance, got {}",
        d
    );
}

#[test]
fn metric_larger_divergence_implies_larger_distance() {
    let base = CognitiveStateVector::uniform();
    let q_small = shifted_vector(0, 0.005);
    let q_large = shifted_vector(0, 0.015);

    let d_small = geodesic_distance(&base, &q_small);
    let d_large = geodesic_distance(&base, &q_large);

    assert!(
        d_large > d_small,
        "larger divergence should produce larger distance: d_small={}, d_large={}",
        d_small,
        d_large
    );
}

#[test]
fn metric_domain_biased_vectors_distance_correlates_with_dci() {
    // Two vectors biased toward different domains should be far apart,
    // while vectors biased the same way should be close.
    let p_biased = domain_biased_vector(Domain::Principled, 0.5);
    let o_biased = domain_biased_vector(Domain::Operational, 0.5);
    let p_biased_2 = domain_biased_vector(Domain::Principled, 0.45);

    let d_different = geodesic_distance(&p_biased, &o_biased);
    let d_similar = geodesic_distance(&p_biased, &p_biased_2);

    assert!(
        d_different > d_similar,
        "vectors biased to different domains should be farther apart: d_diff={}, d_similar={}",
        d_different,
        d_similar
    );

    // Also verify their DCI values reflect the bias
    let dc_p = DomainCoherence::from_state_vector(&p_biased);
    let dc_u = DomainCoherence::from_state_vector(&CognitiveStateVector::uniform());
    assert!(
        dc_p.dci() < dc_u.dci(),
        "biased vector should have lower DCI than uniform"
    );
}

#[test]
fn metric_fisher_rao_norm_at_nonuniform_base() {
    // At a non-uniform base point, the norm should differ from the uniform case
    let mut weights = [1.0; NUM_STATES];
    weights[0] = 20.0;
    let p_nonuniform = make_state_vector(weights);
    let p_uniform = CognitiveStateVector::uniform();

    let mut raw = [0.0; NUM_STATES];
    raw[0] = 1.0;
    raw[1] = -1.0;
    let u = validate_tangent_vector(&raw).unwrap();

    let norm_nonuniform = fisher_rao_norm(&p_nonuniform, &u);
    let norm_uniform = fisher_rao_norm(&p_uniform, &u);

    // At a non-uniform point with high p[0], u[0]^2/p[0] is smaller => lower component for index 0
    // but u[1]^2/p[1] is larger => different overall norm
    assert!(
        (norm_nonuniform - norm_uniform).abs() > 1e-6,
        "norm at non-uniform point should differ from uniform: nonuniform={}, uniform={}",
        norm_nonuniform,
        norm_uniform
    );
}

#[test]
fn metric_bhattacharyya_coefficient_bounds() {
    let p = shifted_vector(3, 0.01);
    let q = shifted_vector(20, 0.008);

    let bc = bhattacharyya_coefficient(&p, &q);
    assert!(bc > 0.0 && bc <= 1.0, "BC should be in (0, 1], got {}", bc);

    // And consistency with geodesic distance
    let d = geodesic_distance(&p, &q);
    let expected = 2.0 * bc.clamp(0.0, 1.0).acos();
    assert!(
        (d - expected).abs() < 1e-14,
        "geodesic distance should equal 2*arccos(BC): d={}, expected={}",
        d,
        expected
    );
}

// ===========================================================================
// 3. Ontology <-> Scoring integration (6 tests)
// ===========================================================================

#[test]
fn scoring_state_vector_to_dci_feeds_nccs() {
    let sv = CognitiveStateVector::uniform();
    let dc = DomainCoherence::from_state_vector(&sv);

    // Uniform => DCI = 1.0
    assert!((dc.dci() - 1.0).abs() < 1e-12);

    // Use DCI as domain coherence in NCCS
    let input = NccsInput {
        operator_scores: OperatorScores::new([0.5; 10]).unwrap(),
        domain_coherence: dc,
        drive_profile: DriveProfile::new([0.5; 7]).unwrap(),
        rpm_completeness: 0.5,
        pathway_quality: PathwayQualityInput::new(0.5, 0).unwrap(),
        inversion_resistance: InversionResistanceInput::new([0.5; 7], 0.5, 0.5).unwrap(),
        social_engineering: SocialEngineeringInput::new(0.5, 0.5).unwrap(),
    };
    let result = compute_nccs(&input);

    // The domain coherence sub-score = DCI = 1.0, which is the highest possible
    assert!(
        (result.domain_coherence - 1.0).abs() < 1e-12,
        "uniform SV should yield DCI=1.0, got {}",
        result.domain_coherence
    );
}

#[test]
fn scoring_operator_involution_balance_affects_profile() {
    // Balanced operators (all same score)
    let balanced = OperatorScores::new([0.8; 10]).unwrap();
    let balanced_profile = balanced.profile_score();

    // Imbalanced operators (involution pairs differ by 0.6)
    let mut imbalanced_vals = [0.8; 10];
    imbalanced_vals[2] = 0.5; // CO2
    imbalanced_vals[3] = 1.0; // CO3 (partner)
    imbalanced_vals[5] = 0.4; // CO5
    imbalanced_vals[6] = 1.0; // CO6 (partner)
    let imbalanced = OperatorScores::new(imbalanced_vals).unwrap();
    let imbalanced_profile = imbalanced.profile_score();

    assert!(
        balanced_profile > imbalanced_profile,
        "balanced operators should score higher: balanced={}, imbalanced={}",
        balanced_profile,
        imbalanced_profile
    );
}

#[test]
fn scoring_drive_profile_inversion_balance_affects_nccs() {
    // Balanced drives
    let balanced_dp = DriveProfile::new([0.8; 7]).unwrap();
    let balanced_balances = balanced_dp.all_inversion_balances();
    for &b in &balanced_balances {
        assert!(b.abs() < 1e-12, "balanced drives should have 0 imbalance");
    }

    // Imbalanced drives (F1=1.0, F7=0.2 => imbalance 0.8)
    let imbalanced_dp = DriveProfile::new([1.0, 0.8, 0.8, 0.8, 0.8, 0.8, 0.2]).unwrap();
    let imbalanced_balances = imbalanced_dp.all_inversion_balances();

    // F1<->F7 balance should be 0.8
    assert!(
        (imbalanced_balances[0] - 0.8).abs() < 1e-12,
        "F1<->F7 imbalance should be 0.8, got {}",
        imbalanced_balances[0]
    );

    // The balanced profile should contribute more to NCCS
    let balanced_input = make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 0.8, 0.8, 0.1, 0.8, 0.8);
    let balanced_nccs = compute_nccs(&balanced_input);

    let imbalanced_input = NccsInput {
        drive_profile: imbalanced_dp,
        ..make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 0.8, 0.8, 0.1, 0.8, 0.8)
    };
    let imbalanced_nccs = compute_nccs(&imbalanced_input);

    assert!(
        balanced_nccs.composite >= imbalanced_nccs.composite,
        "balanced drives should yield >= NCCS: balanced={}, imbalanced={}",
        balanced_nccs.composite,
        imbalanced_nccs.composite
    );
}

#[test]
fn scoring_equal_domain_averages_yield_max_dci() {
    let dc = DomainCoherence::from_averages([0.5, 0.5, 0.5, 0.5]);
    assert!(
        (dc.dci() - 1.0).abs() < 1e-12,
        "equal domain averages should give DCI=1.0, got {}",
        dc.dci()
    );
}

#[test]
fn scoring_unequal_domain_averages_yield_reduced_dci() {
    let dc = DomainCoherence::from_averages([0.9, 0.3, 0.6, 0.5]);
    // DCI = min/max = 0.3/0.9 = 1/3
    assert!(
        (dc.dci() - 1.0 / 3.0).abs() < 1e-12,
        "DCI should be 0.3/0.9 = 1/3, got {}",
        dc.dci()
    );
    assert_eq!(dc.weakest_domain(), Domain::Cognitive);
    assert_eq!(dc.strongest_domain(), Domain::Principled);
}

#[test]
fn scoring_domain_coherence_from_biased_state_vector() {
    let sv = domain_biased_vector(Domain::Principled, 0.6);
    let dc = DomainCoherence::from_state_vector(&sv);

    // Principled domain should have highest average
    assert_eq!(dc.strongest_domain(), Domain::Principled);
    // DCI should be < 1.0 due to bias
    assert!(
        dc.dci() < 1.0,
        "biased vector should have DCI < 1.0, got {}",
        dc.dci()
    );
}

// ===========================================================================
// 4. RPM <-> Scoring integration (6 tests)
// ===========================================================================

#[test]
fn rpm_complete_chains_yield_high_pathway_score() {
    let profile = RpmProfile::new(0.9, [[0.9, 0.9, 0.9]; 7], 0.5).unwrap();

    let completeness = profile.overall_completeness();
    assert!(
        (completeness - 1.0).abs() < 1e-12,
        "all above threshold should give completeness=1.0"
    );

    let pq = PathwayQualityInput::new(completeness, 0).unwrap();
    assert!(
        (pq.quality_score() - 1.0).abs() < 1e-12,
        "full completeness + 0 bias should give pathway quality=1.0"
    );
}

#[test]
fn rpm_blocked_a0_yields_low_pathway_score() {
    // A0 below threshold blocks all chains
    let profile = RpmProfile::new(0.1, [[0.9, 0.9, 0.9]; 7], 0.5).unwrap();

    let completeness = profile.overall_completeness();
    assert!(
        (completeness).abs() < 1e-12,
        "blocked A0 should yield completeness=0.0, got {}",
        completeness
    );
    assert_eq!(profile.completed_chain_count(), 0);
    assert!(!profile.a0_satisfied());

    let pq = PathwayQualityInput::new(completeness, 0).unwrap();
    // 0.7*0 + 0.3*1.0 = 0.3
    assert!(
        (pq.quality_score() - 0.3).abs() < 1e-12,
        "blocked RPM should give pathway quality=0.3, got {}",
        pq.quality_score()
    );
}

#[test]
fn rpm_partial_chains_yield_intermediate_pathway_score() {
    // A0 and D satisfied, but W below threshold
    let profile = RpmProfile::new(0.8, [[0.8, 0.3, 0.3]; 7], 0.5).unwrap();

    let completeness = profile.overall_completeness();
    // Each chain: A0 + D satisfied = 2/4 = 0.5
    assert!(
        (completeness - 0.5).abs() < 1e-12,
        "partial chains should yield completeness=0.5, got {}",
        completeness
    );
    assert_eq!(profile.completed_chain_count(), 0);

    let pq = PathwayQualityInput::new(completeness, 0).unwrap();
    // 0.7*0.5 + 0.3*1.0 = 0.35 + 0.30 = 0.65
    assert!(
        (pq.quality_score() - 0.65).abs() < 1e-12,
        "partial RPM should give pathway quality=0.65, got {}",
        pq.quality_score()
    );
}

#[test]
fn rpm_section_law_holds_through_pipeline() {
    // Verify section law for scores used throughout the pipeline
    let test_scores = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0];
    for &s in &test_scores {
        assert!(
            verify_section_law(s).is_ok(),
            "section law should hold for s={}",
            s
        );

        let embedded = embed(s).unwrap();
        let realized = realize(&embedded);
        assert!(
            (realized - s).abs() < f64::EPSILON * 2.0,
            "realize(embed({})) should equal {}, got {}",
            s,
            s,
            realized
        );
    }
}

#[test]
fn rpm_profile_completeness_into_nccs_pipeline() {
    // Mixed RPM profile: some chains complete, others partial
    let profile = RpmProfile::new(
        0.8,
        [
            [0.9, 0.9, 0.9], // F1: fully complete
            [0.9, 0.9, 0.9], // F2: fully complete
            [0.9, 0.3, 0.3], // F3: partial (W blocked)
            [0.9, 0.9, 0.9], // F4: fully complete
            [0.3, 0.9, 0.9], // F5: partial (D blocked, so W,P also blocked)
            [0.9, 0.9, 0.9], // F6: fully complete
            [0.9, 0.9, 0.9], // F7: fully complete
        ],
        0.5,
    )
    .unwrap();

    assert_eq!(profile.completed_chain_count(), 5);
    let completeness = profile.overall_completeness();
    // 5 complete chains (4/4 each) + 1 at 2/4 + 1 at 1/4
    // = (5*1.0 + 0.5 + 0.25) / 7 = 5.75/7 ≈ 0.8214
    assert!(
        (completeness - 5.75 / 7.0).abs() < 1e-12,
        "expected completeness ≈ 0.8214, got {}",
        completeness
    );

    // Integrate into NCCS
    let input = NccsInput {
        operator_scores: OperatorScores::new([0.8; 10]).unwrap(),
        domain_coherence: DomainCoherence::from_averages([0.8; 4]),
        drive_profile: DriveProfile::new([0.8; 7]).unwrap(),
        rpm_completeness: completeness,
        pathway_quality: PathwayQualityInput::new(completeness, 2).unwrap(),
        inversion_resistance: InversionResistanceInput::new([0.8; 7], 0.8, 0.1).unwrap(),
        social_engineering: SocialEngineeringInput::new(0.8, 0.8).unwrap(),
    };
    let result = compute_nccs(&input);
    assert!(
        result.composite > 60.0 && result.composite < 95.0,
        "mixed RPM should give moderate-to-high score, got {}",
        result.composite
    );
}

#[test]
fn rpm_non_reversibility_documented_in_chain() {
    // Demonstrate that η ∘ ε ≠ id by checking embedded components
    let chain = RpmChain::new(CoreDrive::F1Unity, [0.64, 0.81, 0.49, 0.25], 0.5).unwrap();

    for state in chain.states() {
        let s = state.raw_score();
        let emb = state.embedded_score();

        // Section law: realized should equal raw
        assert!(
            (state.realized_score() - s).abs() < f64::EPSILON * 2.0,
            "section law should hold: raw={}, realized={}",
            s,
            state.realized_score()
        );

        // Embedding formula: (s, s^2, sqrt(s))
        assert!((emb.linear() - s).abs() < 1e-12);
        assert!((emb.quadratic() - s * s).abs() < 1e-12);
        if s >= 0.0 {
            assert!((emb.sqrt() - s.sqrt()).abs() < 1e-12);
        }
    }
}

// ===========================================================================
// 5. Operator algebra properties (6 tests)
// ===========================================================================

#[test]
fn algebra_monoid_associativity_exhaustive() {
    // (a ∘ b) ∘ c = a ∘ (b ∘ c) for all triples
    for a in CognitiveOperator::ALL {
        for b in CognitiveOperator::ALL {
            for c in CognitiveOperator::ALL {
                let left = a.compose(b).compose(c);
                let right = a.compose(b.compose(c));
                assert_eq!(
                    left, right,
                    "associativity failed: ({} ∘ {}) ∘ {} ≠ {} ∘ ({} ∘ {})",
                    a, b, c, a, b, c
                );
            }
        }
    }
}

#[test]
fn algebra_identity_property_exhaustive() {
    // CO0 ∘ x = x ∘ CO0 = x for all x
    for op in CognitiveOperator::ALL {
        assert_eq!(
            CognitiveOperator::CO0.compose(op),
            op,
            "left identity failed for {}",
            op
        );
        assert_eq!(
            op.compose(CognitiveOperator::CO0),
            op,
            "right identity failed for {}",
            op
        );
    }
}

#[test]
fn algebra_involution_is_involution() {
    // involute(involute(x)) = x for all x
    for op in CognitiveOperator::ALL {
        assert_eq!(
            op.involute().involute(),
            op,
            "involution failed for {}: involute(involute({})) = {} ≠ {}",
            op,
            op,
            op.involute().involute(),
            op
        );
    }
}

#[test]
fn algebra_admissibility_co0_diagonal_only() {
    // CO-0 is identity: only admissible on the diagonal (source == target)
    for source in CognitiveStateId::all() {
        for target in CognitiveStateId::all() {
            let admissible = CognitiveOperator::CO0.is_admissible(source, target);
            if source == target {
                assert!(
                    admissible,
                    "CO0 should be admissible on diagonal: {} -> {}",
                    source, target
                );
            } else {
                assert!(
                    !admissible,
                    "CO0 should NOT be admissible off diagonal: {} -> {}",
                    source, target
                );
            }
        }
    }
}

#[test]
fn algebra_non_identity_operators_have_broader_admissibility() {
    // Non-identity operators should admit at least intra-domain transitions
    for op in &CognitiveOperator::ALL[1..] {
        let mut found_admissible = false;
        for source in CognitiveStateId::all() {
            for target in CognitiveStateId::all() {
                if source != target && op.is_admissible(source, target) {
                    found_admissible = true;
                    break;
                }
            }
            if found_admissible {
                break;
            }
        }
        assert!(
            found_admissible,
            "non-identity operator {} should admit at least one off-diagonal transition",
            op
        );
    }
}

#[test]
fn algebra_self_dual_operators_are_correct() {
    let expected_self_duals = [
        CognitiveOperator::CO0,
        CognitiveOperator::CO1,
        CognitiveOperator::CO4,
        CognitiveOperator::CO7,
    ];
    for op in CognitiveOperator::ALL {
        if expected_self_duals.contains(&op) {
            assert!(op.is_self_dual(), "{} should be self-dual", op);
            assert_eq!(op.involute(), op, "{} should involute to itself", op);
        } else {
            assert!(!op.is_self_dual(), "{} should NOT be self-dual", op);
            assert_ne!(
                op.involute(),
                op,
                "{} should involute to a different operator",
                op
            );
        }
    }
}

// ===========================================================================
// 6. Mathematical invariant tests (7 tests)
// ===========================================================================

#[test]
fn invariant_nccs_weights_sum_to_one() {
    let sum = WEIGHT_OPERATOR_PROFILE
        + WEIGHT_DOMAIN_COHERENCE
        + WEIGHT_DRIVE_RPM
        + WEIGHT_PATHWAY_QUALITY
        + WEIGHT_INVERSION_RESISTANCE
        + WEIGHT_SOCIAL_ENGINEERING;
    assert!(
        (sum - 1.0).abs() < 1e-12,
        "NCCS weights must sum to 1.0, got {}",
        sum
    );
}

#[test]
fn invariant_all_subscores_in_unit_interval() {
    let test_inputs = [
        make_perfect_assessment(),
        make_worst_assessment(),
        make_assessment(0.5, 0.5, 0.5, 0.5, 0.5, 5, 0.5, 0.5, 0.5, 0.5, 0.5),
    ];

    for input in &test_inputs {
        let result = compute_nccs(input);
        assert!(
            result.operator_profile >= 0.0 && result.operator_profile <= 1.0,
            "operator_profile out of [0,1]: {}",
            result.operator_profile
        );
        assert!(
            result.domain_coherence >= 0.0 && result.domain_coherence <= 1.0,
            "domain_coherence out of [0,1]: {}",
            result.domain_coherence
        );
        assert!(
            result.drive_rpm_integrity >= 0.0 && result.drive_rpm_integrity <= 1.0,
            "drive_rpm_integrity out of [0,1]: {}",
            result.drive_rpm_integrity
        );
        assert!(
            result.pathway_quality >= 0.0 && result.pathway_quality <= 1.0,
            "pathway_quality out of [0,1]: {}",
            result.pathway_quality
        );
        assert!(
            result.inversion_resistance >= 0.0 && result.inversion_resistance <= 1.0,
            "inversion_resistance out of [0,1]: {}",
            result.inversion_resistance
        );
        assert!(
            result.social_engineering >= 0.0 && result.social_engineering <= 1.0,
            "social_engineering out of [0,1]: {}",
            result.social_engineering
        );
    }
}

#[test]
fn invariant_composite_in_zero_to_hundred() {
    let test_inputs = [
        make_perfect_assessment(),
        make_worst_assessment(),
        make_assessment(0.3, 0.3, 0.3, 0.3, 0.3, 10, 0.3, 0.3, 0.7, 0.3, 0.3),
        make_assessment(0.9, 0.9, 0.9, 0.9, 0.9, 1, 0.9, 0.9, 0.05, 0.9, 0.9),
    ];

    for input in &test_inputs {
        let result = compute_nccs(input);
        assert!(
            result.composite >= 0.0 && result.composite <= 100.0,
            "composite out of [0, 100]: {}",
            result.composite
        );
    }
}

#[test]
fn invariant_certification_level_boundaries() {
    // Verify that from_score matches documented boundaries exactly
    assert_eq!(
        CertificationLevel::from_score(100.0),
        CertificationLevel::Platinum
    );
    assert_eq!(
        CertificationLevel::from_score(90.0),
        CertificationLevel::Platinum
    );
    assert_eq!(
        CertificationLevel::from_score(89.999),
        CertificationLevel::Gold
    );
    assert_eq!(
        CertificationLevel::from_score(75.0),
        CertificationLevel::Gold
    );
    assert_eq!(
        CertificationLevel::from_score(74.999),
        CertificationLevel::Silver
    );
    assert_eq!(
        CertificationLevel::from_score(60.0),
        CertificationLevel::Silver
    );
    assert_eq!(
        CertificationLevel::from_score(59.999),
        CertificationLevel::Bronze
    );
    assert_eq!(
        CertificationLevel::from_score(40.0),
        CertificationLevel::Bronze
    );
    assert_eq!(
        CertificationLevel::from_score(39.999),
        CertificationLevel::Fail
    );
    assert_eq!(
        CertificationLevel::from_score(0.0),
        CertificationLevel::Fail
    );

    // Min scores
    assert!((CertificationLevel::Platinum.min_score() - 90.0).abs() < 1e-12);
    assert!((CertificationLevel::Gold.min_score() - 75.0).abs() < 1e-12);
    assert!((CertificationLevel::Silver.min_score() - 60.0).abs() < 1e-12);
    assert!((CertificationLevel::Bronze.min_score() - 40.0).abs() < 1e-12);
    assert!((CertificationLevel::Fail.min_score()).abs() < 1e-12);
}

#[test]
fn invariant_domain_total_order_consistent() {
    // P > C > E > O (total order)
    let domains = Domain::ALL;
    for i in 0..domains.len() {
        for j in (i + 1)..domains.len() {
            assert!(
                domains[i].dominates(domains[j]),
                "{:?} should dominate {:?}",
                domains[i],
                domains[j]
            );
            assert!(
                !domains[j].dominates(domains[i]),
                "{:?} should NOT dominate {:?}",
                domains[j],
                domains[i]
            );
        }
    }

    // Verify no domain dominates itself
    for d in Domain::ALL {
        assert!(!d.dominates(d), "{:?} should not dominate itself", d);
    }

    // Verify Rust Ord is consistent (higher precedence = "greater")
    assert!(Domain::Principled > Domain::Cognitive);
    assert!(Domain::Cognitive > Domain::Evaluative);
    assert!(Domain::Evaluative > Domain::Operational);
}

#[test]
fn invariant_40_states_cover_all_operator_domain_pairs() {
    let all_states = CognitiveStateId::all();
    assert_eq!(all_states.len(), NUM_STATES);

    // Every (operator, domain) pair should appear exactly once
    let mut seen = std::collections::HashSet::new();
    for s in &all_states {
        let key = (s.operator(), s.domain());
        assert!(seen.insert(key), "duplicate state: {:?}", key);
    }

    // Should have 10 operators * 4 domains = 40 pairs
    assert_eq!(seen.len(), 40);

    // Linear index should be unique and span [0, 39]
    let mut indices: Vec<usize> = all_states.iter().map(|s| s.linear_index()).collect();
    indices.sort();
    assert_eq!(indices, (0..40).collect::<Vec<_>>());
}

#[test]
fn invariant_drive_and_pathway_counts() {
    // 7 core drives
    assert_eq!(CoreDrive::ALL.len(), 7);
    // 28 domain-specific drives
    assert_eq!(DomainDrive::all().len(), 28);
    // 22 pathway nodes
    assert_eq!(PathwayNode::all().len(), 22);
    // 7 inversion axes
    assert_eq!(InversionAxis::ALL.len(), 7);
    // 3 drive inversion pairs
    assert_eq!(CoreDrive::INVERSION_PAIRS.len(), 3);
    // 3 operator involution pairs
    assert_eq!(CognitiveOperator::INVOLUTION_PAIRS.len(), 3);
}

// ===========================================================================
// 7. Sensitivity / regression tests (5 tests)
// ===========================================================================

#[test]
fn sensitivity_small_perturbation_small_change() {
    let base = make_assessment(0.7, 0.7, 0.7, 0.7, 0.7, 2, 0.7, 0.7, 0.2, 0.7, 0.7);
    let perturbed = make_assessment(0.71, 0.7, 0.7, 0.7, 0.7, 2, 0.7, 0.7, 0.2, 0.7, 0.7);

    let base_result = compute_nccs(&base);
    let perturbed_result = compute_nccs(&perturbed);

    let delta = (perturbed_result.composite - base_result.composite).abs();
    assert!(
        delta < 2.0,
        "small perturbation (0.01 in operator scores) should cause small NCCS change, got delta={}",
        delta
    );
    assert!(
        delta > 0.0,
        "perturbation should cause some change, got delta=0"
    );
}

#[test]
fn sensitivity_extreme_operator_imbalance_lowers_profile() {
    // Extreme imbalance in involution pairs
    let extreme = OperatorScores::new([0.5, 0.5, 0.0, 1.0, 0.5, 0.0, 1.0, 0.5, 0.0, 1.0]).unwrap();
    let balanced = OperatorScores::new([0.5; 10]).unwrap();

    assert!(
        balanced.profile_score() > extreme.profile_score(),
        "extreme imbalance should lower profile: balanced={}, extreme={}",
        balanced.profile_score(),
        extreme.profile_score()
    );
}

#[test]
fn sensitivity_single_drive_failure_reduces_nccs() {
    // All drives at 0.8
    let healthy = make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 0.8, 0.8, 0.1, 0.8, 0.8);
    let healthy_result = compute_nccs(&healthy);

    // One drive at 0.0
    let failed_dp = DriveProfile::new([0.8, 0.8, 0.0, 0.8, 0.8, 0.8, 0.8]).unwrap();
    let failed = NccsInput {
        drive_profile: failed_dp,
        ..make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 0.8, 0.8, 0.1, 0.8, 0.8)
    };
    let failed_result = compute_nccs(&failed);

    assert!(
        healthy_result.composite > failed_result.composite,
        "single drive failure should reduce NCCS: healthy={}, failed={}",
        healthy_result.composite,
        failed_result.composite
    );
}

#[test]
fn sensitivity_rpm_completeness_zero_vs_full() {
    // Full RPM completeness
    let full = make_assessment(0.7, 0.7, 0.7, 1.0, 0.7, 2, 0.7, 0.7, 0.2, 0.7, 0.7);
    let full_result = compute_nccs(&full);

    // Zero RPM completeness
    let zero = make_assessment(0.7, 0.7, 0.7, 0.0, 0.7, 2, 0.7, 0.7, 0.2, 0.7, 0.7);
    let zero_result = compute_nccs(&zero);

    let delta = full_result.composite - zero_result.composite;
    assert!(
        delta > 5.0,
        "RPM completeness 0->1 should have significant impact on NCCS, got delta={}",
        delta
    );
}

#[test]
fn sensitivity_inversion_resistance_impacts_certification() {
    // High inversion resistance
    let high_ir = make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 1.0, 1.0, 0.0, 0.8, 0.8);
    let high_result = compute_nccs(&high_ir);

    // Low inversion resistance (high compound severity, low axis scores)
    let low_ir = make_assessment(0.8, 0.8, 0.8, 0.8, 0.8, 0, 0.2, 0.2, 0.9, 0.8, 0.8);
    let low_result = compute_nccs(&low_ir);

    assert!(
        high_result.composite > low_result.composite,
        "higher inversion resistance should yield higher NCCS: high={}, low={}",
        high_result.composite,
        low_result.composite
    );
}
