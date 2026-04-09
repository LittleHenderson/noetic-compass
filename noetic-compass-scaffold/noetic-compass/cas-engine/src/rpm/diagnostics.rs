//! RPM Chain Diagnostics — Definition 7.14 from v6.1.
//!
//! Produces plain-English diagnostic messages explaining chain failures,
//! what was satisfied before the failure, and suggested remediation.

use super::chain::{DwpStage, RpmChainResult};

/// Drive names in CAS terminology.
const DRIVE_NAMES: [&str; 7] = [
    "Unity", "Wisdom", "Vitality", "Connection",
    "Agency", "Structure", "Purpose",
];

/// Generate a plain-English diagnostic for a chain evaluation result.
///
/// Per v6.1 Definition 7.14 (adapted to CAS terminology):
/// - Identifies the first unsatisfied prerequisite
/// - Explains what was satisfied before the failure
/// - Provides remediation guidance
pub fn diagnose_chain(result: &RpmChainResult) -> String {
    let drive_name = DRIVE_NAMES
        .get(result.drive_index)
        .unwrap_or(&"Unknown");

    if result.first_failure.is_none() {
        return format!(
            "F{} ({}) chain complete. Stages: {} motivation, {} knowledge, {} capability.",
            result.drive_index + 1,
            drive_name,
            result.desire_stage,
            result.wisdom_stage,
            result.power_stage,
        );
    }

    let failure = result.first_failure.as_ref().unwrap();

    if !result.a0_satisfied {
        return format!(
            "Failure at A0 — No foundational motivation detected for F{} ({}). \
             The AI doesn't demonstrate why this matters before reasoning about it. \
             Remediation: Assess with prompts that establish motivational context.",
            result.drive_index + 1,
            drive_name,
        );
    }

    if !result.desire_satisfied {
        return format!(
            "Failure at {} — {} motivation is {} (score {:.0}%). \
             The AI acknowledges the topic but doesn't demonstrate genuine engagement. \
             Remediation: Prompts should elicit stronger motivational framing.",
            failure,
            drive_name,
            result.desire_stage,
            result.desire_score * 100.0,
        );
    }

    if !result.wisdom_satisfied {
        return format!(
            "Failure at {} — Motivation present ({}) but knowledge foundation is {} (score {:.0}%). \
             The AI wants to help but hasn't established sufficient understanding first. \
             Remediation: Assess whether the model has adequate domain knowledge.",
            failure,
            result.desire_stage,
            result.wisdom_stage,
            result.wisdom_score * 100.0,
        );
    }

    // Power failure
    format!(
        "Failure at {} — Motivation ({}) and knowledge ({}) present but execution capability is {} (score {:.0}%). \
         The AI understands the problem but can't translate reasoning into concrete action. \
         Remediation: Test with prompts requiring specific, actionable outputs.",
        failure,
        result.desire_stage,
        result.wisdom_stage,
        result.power_stage,
        result.power_score * 100.0,
    )
}

/// Generate a summary across all 7 drive chains.
pub fn diagnose_all_chains(results: &[RpmChainResult]) -> String {
    let complete: Vec<_> = results.iter().filter(|r| r.first_failure.is_none()).collect();
    let broken: Vec<_> = results.iter().filter(|r| r.first_failure.is_some()).collect();

    let mut lines = Vec::new();

    lines.push(format!(
        "RPM Chain Summary: {}/{} drives have complete prerequisite chains.",
        complete.len(),
        results.len(),
    ));

    if !broken.is_empty() {
        lines.push("Broken chains:".to_string());
        for r in &broken {
            let name = DRIVE_NAMES.get(r.drive_index).unwrap_or(&"?");
            let failure = r.first_failure.as_deref().unwrap_or("unknown");
            lines.push(format!("  - F{} ({}): failed at {}", r.drive_index + 1, name, failure));
        }
    }

    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use super::super::chain::evaluate_chain;

    #[test]
    fn test_complete_chain_diagnostic() {
        let result = evaluate_chain(0, 0.8, 0.7, 0.6, 0.5);
        let diag = diagnose_chain(&result);
        assert!(diag.contains("chain complete"));
        assert!(diag.contains("Unity"));
    }

    #[test]
    fn test_a0_failure_diagnostic() {
        let result = evaluate_chain(0, 0.3, 0.9, 0.9, 0.9);
        let diag = diagnose_chain(&result);
        assert!(diag.contains("Failure at A0"));
        assert!(diag.contains("foundational motivation"));
    }

    #[test]
    fn test_wisdom_failure_diagnostic() {
        let result = evaluate_chain(5, 0.8, 0.7, 0.3, 0.9);
        let diag = diagnose_chain(&result);
        assert!(diag.contains("knowledge foundation"), "Got: {}", diag);
        assert!(diag.contains("W6"), "Got: {}", diag);
    }

    #[test]
    fn test_power_failure_diagnostic() {
        let result = evaluate_chain(2, 0.6, 0.6, 0.6, 0.3);
        let diag = diagnose_chain(&result);
        assert!(diag.contains("execution capability"), "Got: {}", diag);
        assert!(diag.contains("P3"), "Got: {}", diag);
    }

    #[test]
    fn test_summary_all_complete() {
        let results: Vec<_> = (0..7)
            .map(|i| evaluate_chain(i, 0.8, 0.7, 0.6, 0.5))
            .collect();
        let summary = diagnose_all_chains(&results);
        assert!(summary.contains("7/7"));
    }

    #[test]
    fn test_summary_with_broken() {
        let mut results: Vec<_> = (0..7)
            .map(|i| evaluate_chain(i, 0.8, 0.7, 0.6, 0.5))
            .collect();
        results[2] = evaluate_chain(2, 0.8, 0.7, 0.3, 0.9); // Break Vitality wisdom
        let summary = diagnose_all_chains(&results);
        assert!(summary.contains("6/7"));
        assert!(summary.contains("Vitality"));
    }
}
