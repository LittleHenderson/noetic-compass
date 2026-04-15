"""
Evaluation harness for the CAS-Native model.

This module computes evaluation summaries with the Rust CAS engine exposed
through PyO3 bindings. The PyTorch model still does not expose native drive-
specific or social-engineering heads, so this evaluator derives the canonical
CAS score by:

1. Converting the 40-state simplex output into explicit operator/domain inputs.
2. Building conservative proxy drive/pathway inputs from the model's RPM signal.
3. Running the Rust inversion scanner and NCCS scorer for the final composite.

The scorer is therefore engine-native at the point of NCCS calculation, while
remaining transparent about the proxy inputs the current model can provide.
"""

import json
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import DataLoader

from ..model.cas_native_model import CASNativeModel, CASNativeConfig
from ..model.embedding import NUM_COGNITIVE_STATES

try:
    import cas_engine
except ImportError:  # pragma: no cover - exercised in environments without the wheel
    cas_engine = None


NUM_OPERATORS = 10
NUM_DOMAINS = 4
NUM_DRIVES = 7
RPM_CHAIN_LENGTH = 4
AXIS_NAMES = ["N", "W", "F", "E", "S", "A", "P"]


def _require_cas_engine():
    if cas_engine is None:
        raise RuntimeError(
            "cas_engine is not available. Build/install the PyO3 bindings before "
            "running CAS-Native evaluation."
        )
    return cas_engine


def _masked_mean(values: torch.Tensor, attention_mask: Optional[torch.Tensor]) -> torch.Tensor:
    """Average across sequence positions while ignoring padded tokens."""
    if attention_mask is None:
        return values.mean(dim=1)

    weights = attention_mask.to(values.dtype).unsqueeze(-1)
    weighted = values * weights
    counts = weights.sum(dim=1).clamp_min(1.0)
    return weighted.sum(dim=1) / counts


def compute_per_operator_scores(cognitive_state: torch.Tensor) -> dict[str, float]:
    """Collapse the 40-state simplex into 10 operator masses in [0, 1]."""
    scores = {}
    for co in range(NUM_OPERATORS):
        vals = [cognitive_state[d * NUM_OPERATORS + co].item() for d in range(NUM_DOMAINS)]
        scores[f"CO-{co}"] = sum(vals)
    return scores


def compute_domain_scores(cognitive_state: torch.Tensor) -> list[float]:
    """Collapse the 40-state simplex into 4 domain masses in [0, 1]."""
    domain_scores: list[float] = []
    for domain_idx in range(NUM_DOMAINS):
        start = domain_idx * NUM_OPERATORS
        end = start + NUM_OPERATORS
        domain_scores.append(cognitive_state[start:end].sum().item())
    return domain_scores


def compute_dci(domain_scores: list[float]) -> float:
    """Compute DCI = weakest domain / strongest domain."""
    max_score = max(domain_scores)
    if max_score < 1e-8:
        return 0.0
    return min(domain_scores) / max_score


def compute_involution_balance(cognitive_state: torch.Tensor) -> dict[str, float]:
    """Compute involution-pair imbalance over operator masses."""
    balances = {}
    pairs = [(2, 3), (5, 6), (8, 9)]
    operator_scores = compute_per_operator_scores(cognitive_state)
    for co_a, co_b in pairs:
        balances[f"CO-{co_a}/CO-{co_b}"] = abs(
            operator_scores[f"CO-{co_a}"] - operator_scores[f"CO-{co_b}"]
        )
    return balances


def build_drive_scores(rpm_satisfaction: float) -> list[float]:
    """Project the shared RPM signal into a conservative 7-drive profile.

    The current PyTorch model exposes only a single RPM completeness scalar.
    Until a drive-native head exists, we repeat that signal across drives so
    the Rust scorer operates on a valid, explicit drive profile.
    """
    score = float(max(0.0, min(1.0, rpm_satisfaction)))
    return [score] * NUM_DRIVES


def build_pathway_scores(rpm_satisfaction: float) -> list[list[float]]:
    """Build 7 identical RPM chains from the shared RPM signal.

    This is an explicit proxy, not a learned per-drive pathway decomposition.
    """
    score = float(max(0.0, min(1.0, rpm_satisfaction)))
    chain = [score] * RPM_CHAIN_LENGTH
    return [list(chain) for _ in range(NUM_DRIVES)]


def normalize_state_vector(cognitive_state: torch.Tensor) -> list[float]:
    """Renormalize a PyTorch simplex vector before strict Rust-side validation."""
    state = cognitive_state.detach().cpu().double()
    state = state / state.sum().clamp_min(1e-12)
    return state.tolist()


def compute_engine_assessment(
    cognitive_state: torch.Tensor,
    rpm_satisfaction: float,
) -> dict[str, Any]:
    """Score one cognitive state with the canonical Rust CAS engine."""
    engine = _require_cas_engine()

    state_list = normalize_state_vector(cognitive_state)
    state_vector = engine.CognitiveStateVector(state_list)

    operator_scores = compute_per_operator_scores(cognitive_state)
    operator_list = [operator_scores[f"CO-{co}"] for co in range(NUM_OPERATORS)]
    domain_scores = compute_domain_scores(cognitive_state)
    drive_scores = build_drive_scores(rpm_satisfaction)
    pathway_scores = build_pathway_scores(rpm_satisfaction)

    inversion_scan = engine.InversionScanner.scan(
        operator_scores=operator_list,
        drive_scores=drive_scores,
        state_vector=state_vector,
        domain_averages=domain_scores,
        pathway_scores=pathway_scores,
    )

    # The current model has no dedicated social-engineering head.
    # Use the inversion-resistance aggregate blended with RPM completeness as a
    # conservative proxy until those signals are modeled explicitly.
    social_proxy = 0.5 * inversion_scan["resistance_score"] + 0.5 * float(rpm_satisfaction)

    nccs = engine.compute_nccs(
        operator_scores=operator_list,
        domain_averages=domain_scores,
        drive_scores=drive_scores,
        rpm_completeness=float(rpm_satisfaction),
        pathway_rpm_completeness=float(rpm_satisfaction),
        bias_flag_count=0,
        inversion_axis_scores=inversion_scan["axis_scores"],
        stealth_resistance=inversion_scan["stealth_resistance"],
        compound_severity=inversion_scan["compound_severity"],
        manipulation_resistance=social_proxy,
        overton_drift_resistance=social_proxy,
    )

    return {
        "nccs": nccs,
        "operator_scores": operator_scores,
        "domain_scores": domain_scores,
        "dci": compute_dci(domain_scores),
        "drive_scores": drive_scores,
        "pathway_scores": pathway_scores,
        "inversion_scan": inversion_scan,
    }


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
        """Evaluate the model on a batch of data."""
        _require_cas_engine()

        all_nccs: list[float] = []
        all_certifications: list[str] = []
        all_op_scores: list[dict[str, float]] = []
        all_dci: list[float] = []
        all_inversions: list[list[float]] = []
        all_rpm_sat: list[float] = []
        all_components: list[dict[str, float]] = []

        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)

            outputs = self.model(input_ids, attention_mask=attention_mask)

            batch_cog = _masked_mean(outputs["cognitive_state"], attention_mask)
            rpm_sat = float(outputs["rpm_satisfaction"].item())

            for i in range(batch_cog.shape[0]):
                assessment = compute_engine_assessment(batch_cog[i], rpm_sat)
                nccs = assessment["nccs"]
                inversion_scan = assessment["inversion_scan"]

                all_nccs.append(float(nccs["composite"]))
                all_certifications.append(str(nccs["certification"]))
                all_op_scores.append(assessment["operator_scores"])
                all_dci.append(float(assessment["dci"]))
                all_inversions.append(list(inversion_scan["axis_scores"]))
                all_rpm_sat.append(rpm_sat)
                all_components.append(
                    {
                        "operator_profile": float(nccs["operator_profile"]),
                        "domain_coherence": float(nccs["domain_coherence"]),
                        "drive_rpm_integrity": float(nccs["drive_rpm_integrity"]),
                        "pathway_quality": float(nccs["pathway_quality"]),
                        "inversion_resistance": float(nccs["inversion_resistance"]),
                        "social_engineering": float(nccs["social_engineering"]),
                    }
                )

        n = len(all_nccs)
        if n == 0:
            return {"error": "No samples evaluated"}

        avg_nccs = sum(all_nccs) / n
        avg_dci = sum(all_dci) / n
        avg_rpm = sum(all_rpm_sat) / n

        avg_op = {}
        for co in range(NUM_OPERATORS):
            key = f"CO-{co}"
            avg_op[key] = sum(scores[key] for scores in all_op_scores) / n

        avg_inv = {}
        for axis_idx, axis_name in enumerate(AXIS_NAMES):
            avg_inv[axis_name] = sum(inv[axis_idx] for inv in all_inversions) / n

        avg_components = {}
        for name in [
            "operator_profile",
            "domain_coherence",
            "drive_rpm_integrity",
            "pathway_quality",
            "inversion_resistance",
            "social_engineering",
        ]:
            avg_components[name] = sum(c[name] for c in all_components) / n

        certification_counts: dict[str, int] = {}
        for certification in all_certifications:
            certification_counts[certification] = certification_counts.get(certification, 0) + 1

        report = {
            "num_samples": n,
            "nccs": {
                "mean": avg_nccs,
                "min": min(all_nccs),
                "max": max(all_nccs),
                "certification": max(
                    certification_counts.items(),
                    key=lambda item: item[1],
                )[0],
                "components": avg_components,
            },
            "per_operator_scores": avg_op,
            "domain_coherence_index": avg_dci,
            "rpm_satisfaction": avg_rpm,
            "inversions": avg_inv,
            "certification_counts": certification_counts,
            "all_nccs_scores": all_nccs,
        }

        return report

    def evaluate_and_save(
        self,
        dataloader: DataLoader,
        output_path: str | Path = "evaluation_report.json",
        baseline_path: Optional[str | Path] = None,
    ) -> dict[str, Any]:
        """Evaluate and save report to JSON."""
        report = self.evaluate_batch(dataloader)

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

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"Evaluation report saved to {output}")
        print(f"  NCCS: {report['nccs']['mean']:.2f} ({report['nccs']['certification']})")
        print(f"  DCI: {report['domain_coherence_index']:.4f}")
        print(f"  RPM Satisfaction: {report['rpm_satisfaction']:.4f}")

        return report
