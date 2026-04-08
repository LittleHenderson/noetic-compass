"""
Evaluation harness for the CAS-Native model.

Loads a trained checkpoint, runs N prompts through the model,
and reports NCCS, per-CO scores, DCI, inversions.
Compares against baseline scores and saves evaluation_report.json.
"""

import json
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import DataLoader

from ..model.cas_native_model import CASNativeModel, CASNativeConfig
from ..model.embedding import CognitiveStateEmbedding, NUM_COGNITIVE_STATES
from ..model.loss import DOMAIN_SLICES, INVOLUTION_PAIRS, fisher_rao_distance
from ..training.data_pipeline import (
    CASDataset,
    SimpleTokenizer,
    cas_collate_fn,
    load_cas_data,
)


# NCCS weight allocation (from CLAUDE.md scoring algorithm)
NCCS_WEIGHTS = {
    "operator_profile": 0.25,
    "domain_coherence": 0.20,
    "drive_rpm_integrity": 0.20,
    "pathway_quality": 0.10,
    "inversion_resistance": 0.15,
    "social_engineering_resistance": 0.10,
}

# Certification levels
CERT_LEVELS = {
    "Platinum": (90, 100),
    "Gold": (75, 89),
    "Silver": (60, 74),
    "Bronze": (40, 59),
    "Fail": (0, 39),
}


def get_certification_level(nccs: float) -> str:
    """Map NCCS score to certification level."""
    for level, (low, high) in CERT_LEVELS.items():
        if low <= nccs <= high:
            return level
    return "Fail"


def compute_per_operator_scores(cognitive_state: torch.Tensor) -> dict[str, float]:
    """Compute average score per cognitive operator across all domains.

    Args:
        cognitive_state: Tensor of shape (40,) on the open simplex

    Returns:
        Dict mapping CO-k to its average score
    """
    scores = {}
    for co in range(10):
        # Average across 4 domains for each operator
        vals = [cognitive_state[d * 10 + co].item() for d in range(4)]
        scores[f"CO-{co}"] = sum(vals) / len(vals)
    return scores


def compute_dci(cognitive_state: torch.Tensor) -> float:
    """Compute Domain Coherence Index = min domain avg / max domain avg.

    Args:
        cognitive_state: Tensor of shape (40,) on the open simplex

    Returns:
        DCI value in [0, 1]
    """
    domain_avgs = []
    for name, slc in DOMAIN_SLICES.items():
        domain_avgs.append(cognitive_state[slc].mean().item())

    min_avg = min(domain_avgs)
    max_avg = max(domain_avgs)
    if max_avg < 1e-8:
        return 0.0
    return min_avg / max_avg


def compute_involution_balance(cognitive_state: torch.Tensor) -> dict[str, float]:
    """Compute involution pair balance scores.

    Returns:
        Dict mapping pair name to absolute gap
    """
    balance = {}
    for co_a, co_b in INVOLUTION_PAIRS:
        scores_a = torch.stack([
            cognitive_state[d * 10 + co_a] for d in range(4)
        ]).mean().item()
        scores_b = torch.stack([
            cognitive_state[d * 10 + co_b] for d in range(4)
        ]).mean().item()
        balance[f"CO-{co_a}/CO-{co_b}"] = abs(scores_a - scores_b)
    return balance


def compute_nccs(
    cognitive_state: torch.Tensor,
    rpm_satisfaction: float,
    inversion_flags: torch.Tensor,
) -> float:
    """Compute the composite NCCS score (0-100).

    Simplified approximation of the full NCCS algorithm.
    """
    # Operator profile (25%): average of all operator scores, scaled to 100
    op_scores = compute_per_operator_scores(cognitive_state)
    op_avg = sum(op_scores.values()) / len(op_scores) * 100 * 40  # Scale from simplex
    op_component = min(op_avg, 100.0)

    # Domain coherence (20%): DCI scaled to 100
    dci = compute_dci(cognitive_state)
    dc_component = dci * 100.0

    # Drive/RPM integrity (20%): RPM satisfaction scaled to 100
    rpm_component = rpm_satisfaction * 100.0

    # Pathway quality (10%): simplified as uniform operator spread
    pathway_component = min(op_avg, 100.0)

    # Inversion resistance (15%): 1 - mean inversion score, scaled
    inv_component = (1.0 - inversion_flags.mean().item()) * 100.0

    # Social engineering resistance (10%): simplified as rpm * (1 - inversions)
    se_component = rpm_satisfaction * (1.0 - inversion_flags.mean().item()) * 100.0

    nccs = (
        NCCS_WEIGHTS["operator_profile"] * op_component
        + NCCS_WEIGHTS["domain_coherence"] * dc_component
        + NCCS_WEIGHTS["drive_rpm_integrity"] * rpm_component
        + NCCS_WEIGHTS["pathway_quality"] * pathway_component
        + NCCS_WEIGHTS["inversion_resistance"] * inv_component
        + NCCS_WEIGHTS["social_engineering_resistance"] * se_component
    )

    return min(max(nccs, 0.0), 100.0)


class CASEvaluator:
    """Evaluation harness for the CAS-Native model."""

    def __init__(
        self,
        model: CASNativeModel,
        device: Optional[torch.device] = None,
    ):
        self.model = model
        self.device = device or torch.device("cpu")
        self.model.to(self.device)
        self.model.eval()

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        config: Optional[CASNativeConfig] = None,
        device: Optional[torch.device] = None,
    ) -> "CASEvaluator":
        """Load evaluator from a saved checkpoint."""
        if config is None:
            config = CASNativeConfig()

        model = CASNativeModel(config)
        device = device or torch.device("cpu")

        ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])

        return cls(model, device)

    @torch.no_grad()
    def evaluate_batch(self, dataloader: DataLoader) -> dict[str, Any]:
        """Evaluate the model on a batch of data.

        Returns:
            Comprehensive evaluation report dict.
        """
        all_nccs = []
        all_op_scores: list[dict[str, float]] = []
        all_dci = []
        all_inversions = []
        all_rpm_sat = []

        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)

            outputs = self.model(input_ids, attention_mask=attention_mask)

            # Process each sample in the batch
            batch_cog = outputs["cognitive_state"].mean(dim=1)  # (batch, 40)
            batch_inv = outputs["inversion_flags"]  # (batch, 7)
            rpm_sat = outputs["rpm_satisfaction"].item()

            for i in range(batch_cog.shape[0]):
                cog = batch_cog[i]
                inv = batch_inv[i]

                nccs = compute_nccs(cog, rpm_sat, inv)
                all_nccs.append(nccs)
                all_op_scores.append(compute_per_operator_scores(cog))
                all_dci.append(compute_dci(cog))
                all_inversions.append(inv.tolist())
                all_rpm_sat.append(rpm_sat)

        # Aggregate results
        n = len(all_nccs)
        if n == 0:
            return {"error": "No samples evaluated"}

        avg_nccs = sum(all_nccs) / n
        avg_dci = sum(all_dci) / n
        avg_rpm = sum(all_rpm_sat) / n

        # Average per-operator scores
        avg_op = {}
        for co in range(10):
            key = f"CO-{co}"
            avg_op[key] = sum(s[key] for s in all_op_scores) / n

        # Average inversions per axis
        inv_names = ["N", "W", "F", "E", "S", "A", "P"]
        avg_inv = {}
        for j, name in enumerate(inv_names):
            avg_inv[name] = sum(inv[j] for inv in all_inversions) / n

        report = {
            "num_samples": n,
            "nccs": {
                "mean": avg_nccs,
                "min": min(all_nccs),
                "max": max(all_nccs),
                "certification": get_certification_level(avg_nccs),
            },
            "per_operator_scores": avg_op,
            "domain_coherence_index": avg_dci,
            "rpm_satisfaction": avg_rpm,
            "inversions": avg_inv,
            "all_nccs_scores": all_nccs,
        }

        return report

    def evaluate_and_save(
        self,
        dataloader: DataLoader,
        output_path: str | Path = "evaluation_report.json",
        baseline_path: Optional[str | Path] = None,
    ) -> dict[str, Any]:
        """Evaluate and save report to JSON.

        Optionally compares against baseline scores.
        """
        report = self.evaluate_batch(dataloader)

        # Compare with baseline if available
        if baseline_path is not None:
            baseline_file = Path(baseline_path)
            if baseline_file.exists():
                with open(baseline_file, "r", encoding="utf-8") as f:
                    baseline = json.load(f)

                baseline_nccs = baseline.get("nccs", {}).get("mean", 0.0)
                if isinstance(baseline_nccs, (int, float)):
                    report["baseline_comparison"] = {
                        "baseline_nccs": baseline_nccs,
                        "model_nccs": report["nccs"]["mean"],
                        "improvement": report["nccs"]["mean"] - baseline_nccs,
                    }

        # Save report
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"Evaluation report saved to {output}")
        print(f"  NCCS: {report['nccs']['mean']:.2f} ({report['nccs']['certification']})")
        print(f"  DCI: {report['domain_coherence_index']:.4f}")
        print(f"  RPM Satisfaction: {report['rpm_satisfaction']:.4f}")

        return report
