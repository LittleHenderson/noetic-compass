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
import torch.nn.functional as F
from torch.utils.data import DataLoader

from ..model.cas_native_model import CASNativeModel, CASNativeConfig
from ..model.embedding import NUM_COGNITIVE_STATES
from ..model.register_film import REGISTER_INDEX

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

    # ------------------------------------------------------------------
    # CAS v2 evaluation extensions (ADR-01 / ADR-02 / ADR-04 / ADR-06).
    # These metrics are available only when the corresponding v2 components
    # are attached to the model (via CASTrainer with v2 flags enabled). When
    # disabled, the methods return ``None`` so the caller can omit the key
    # from reports.
    # ------------------------------------------------------------------

    def _v2_components(self) -> dict[str, Any]:
        """Return the v2 ModuleDict attached to the model, empty if absent."""
        container = getattr(self.model, "v2_components", None)
        if container is None:
            return {}
        # nn.ModuleDict -> regular dict for read-only access.
        return {k: container[k] for k in container.keys()}

    @torch.no_grad()
    def register_prediction_accuracy(
        self, dataloader: DataLoader
    ) -> Optional[float]:
        """Accuracy of register inference against ``register_labels``.

        Uses the RegisterFiLM module's per-register similarity to the pooled
        hidden state as a prediction signal. Returns ``None`` when either the
        v2 register embedding is missing or no labeled examples are present.
        """
        components = self._v2_components()
        reg_embedding = components.get("register_embedding")
        if reg_embedding is None:
            return None

        correct = 0
        total = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)
            register_labels_batch = batch.get(
                "register_labels", [[] for _ in range(input_ids.size(0))]
            )

            outputs = self.model(input_ids, attention_mask=attention_mask)
            # pooled is in simplex space (40-dim) because cognitive_state is
            # post-projection. register_film modulates at register_dim (= 40
            # by default), so this path is dim-aligned by construction — no
            # dim-mismatch None return here.
            pooled = _masked_mean(outputs["cognitive_state"], attention_mask)

            film = reg_embedding.register_film
            for i, reg_list in enumerate(register_labels_batch):
                if not reg_list:
                    continue
                for entry in reg_list:
                    label = entry.get("register")
                    if label not in REGISTER_INDEX:
                        continue
                    truth_idx = REGISTER_INDEX[label]
                    # Score each register: apply FiLM and take the register
                    # producing the highest L2-norm (proxy for activation).
                    scores: list[float] = []
                    for r_idx in range(film.num_registers):
                        modulated = film.apply_register(pooled[i], r_idx)
                        scores.append(float(torch.linalg.norm(modulated).item()))
                    predicted = int(torch.tensor(scores).argmax().item())
                    total += 1
                    if predicted == truth_idx:
                        correct += 1

        if total == 0:
            return None
        return correct / total

    @torch.no_grad()
    def rule_four_compliance_rate(
        self,
        dataloader: DataLoader,
        rust_bridge: Optional[Any] = None,
    ) -> Optional[float]:
        """Fraction of emergent-register outputs that pass Rust Rule 4.

        Requires a :class:`RustValidationBridge` (injected or pulled from the
        trainer). Returns ``None`` when no bridge is available.
        """
        if rust_bridge is None:
            return None
        try:
            from ..validation.structural_hash import StructuralPattern
        except Exception:  # pragma: no cover - defensive
            return None

        patterns: list[StructuralPattern] = []
        call_args: list[Any] = []
        for batch in dataloader:
            register_labels_batch = batch.get("register_labels", [])
            for reg_list in register_labels_batch:
                regs = [
                    entry.get("register")
                    for entry in reg_list
                    if "register" in entry
                ]
                regs = [r for r in regs if r in REGISTER_INDEX]
                if len(regs) < 2:
                    continue
                operands = [(3, 0, None, r) for r in regs]
                pattern = StructuralPattern(
                    noetics=(3,),
                    domains=("P",),
                    drives=tuple(),
                    registers=tuple(sorted(set(regs))),
                    register_sets=(tuple(sorted(regs)),),
                    emergent_register_name=None,
                    recipe_shape=None,
                    validation_kind="rule_four",
                )
                patterns.append(pattern)
                call_args.append((operands, None))

        if not patterns:
            return None

        results = rust_bridge.validate_rule_four_batch(patterns, call_args=call_args)
        valid = sum(1 for r in results if getattr(r, "kind", None) == "valid")
        return valid / len(results)

    @torch.no_grad()
    def omega_activation_accuracy(
        self, dataloader: DataLoader
    ) -> Optional[float]:
        """Accuracy of Ω_* identification against ``omega_labels``.

        Compares the top-1 registered Ω_* (by cosine similarity to the
        binding-head output) against the labeled ground truth. Returns
        ``None`` when the emergent register pipeline is not attached or no
        Ω_*-labeled examples are present.
        """
        components = self._v2_components()
        pipeline = components.get("emergent_register")
        reg_embedding = components.get("register_embedding")
        if pipeline is None or reg_embedding is None:
            return None
        if pipeline.registry.active_size == 0:
            return None

        name_to_slot = {
            n: i for i, n in enumerate(pipeline.registry.get_active_names())
        }

        correct = 0
        total = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)
            omega_labels_batch = batch.get(
                "omega_labels", [[] for _ in range(input_ids.size(0))]
            )

            # Synthesize d_model-hidden pooled state.
            tok = self.model.token_embedding(input_ids)
            tok = self.model.pos_encoding(tok)
            if attention_mask is not None:
                tok = tok * attention_mask.unsqueeze(-1).float()
            pooled = tok.mean(dim=1)  # (B, d_model)

            # Use register_film_dmodel (sized at config.d_model) not
            # register_film (40-dim). Both FiLM modules are instantiated on
            # the same CognitiveStateEmbeddingWithRegister — see embedding.py.
            film = reg_embedding.register_film_dmodel
            if pooled.shape[-1] != film.d_model:
                # Dim propagation invariant: register_film_dmodel is sized at
                # config.d_model and pooled is drawn from the d_model token-
                # embedding pathway, so this should be impossible absent a
                # programming error. Raise loudly rather than silently returning
                # None — per Wave 7A follow-up #5 (d_model alignment).
                raise RuntimeError(
                    "Omega-activation dim mismatch: pooled last-dim "
                    f"{pooled.shape[-1]} != register_film_dmodel.d_model "
                    f"{film.d_model}; indicates broken dim propagation from "
                    "CASNativeConfig.d_model."
                )

            # Build register-modulated states + bind.
            register_states = []
            for r_idx in range(film.num_registers):
                register_states.append(film.apply_register(pooled, r_idx))
            reg_states = torch.stack(register_states, dim=-2)
            bound = pipeline.binding_head(
                reg_states,
                prereq_mask=torch.ones(
                    reg_states.shape[:-2],
                    device=reg_states.device,
                    dtype=torch.bool,
                ),
            )
            active_emb = pipeline.registry.get_active_embeddings()
            bind_norm = F.normalize(bound, p=2, dim=-1, eps=1e-12)
            reg_norm = F.normalize(active_emb, p=2, dim=-1, eps=1e-12)
            logits = bind_norm @ reg_norm.transpose(0, 1)  # (B, k)
            predictions = logits.argmax(dim=-1)

            for i, omega_list in enumerate(omega_labels_batch):
                if not omega_list:
                    continue
                entry = omega_list[0]
                name = entry.get("omega_name")
                if name not in name_to_slot:
                    continue
                total += 1
                if int(predictions[i].item()) == name_to_slot[name]:
                    correct += 1

        if total == 0:
            return None
        return correct / total

    @torch.no_grad()
    def production_semantics_accuracy(
        self, dataloader: DataLoader
    ) -> Optional[dict[str, float]]:
        """Per-recipe prerequisite / yield-prediction accuracy.

        Returns ``{"prereq_accuracy": ..., "yield_mae": ...}`` or ``None``
        when the production head is missing / no labeled examples.
        """
        components = self._v2_components()
        prod_head = components.get("production_semantics")
        if prod_head is None:
            return None

        correct_prereq = 0
        total_prereq = 0
        total_abs_err = 0.0
        total_yield = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(self.device)
            attention_mask = batch.get("attention_mask")
            if attention_mask is not None:
                attention_mask = attention_mask.to(self.device)
            production_targets_batch = batch.get(
                "production_target",
                [None for _ in range(input_ids.size(0))],
            )

            labelled = [
                (i, t)
                for i, t in enumerate(production_targets_batch)
                if t is not None
            ]
            if not labelled:
                continue

            tok = self.model.token_embedding(input_ids)
            tok = self.model.pos_encoding(tok)
            if attention_mask is not None:
                tok = tok * attention_mask.unsqueeze(-1).float()
            pooled = tok.mean(dim=1)

            for i, target in labelled:
                out = prod_head(
                    pooled[i].unsqueeze(0),
                    mode="inference",
                )
                # Prereq correctness: first labeled prereq state_id must
                # appear in predictions.
                prereqs = target.get("prereqs", [])
                if prereqs:
                    predicted_ids = (
                        out["prereq_identifications"][0].cpu().tolist()
                    )
                    gold_ids = {int(p[0]) for p in prereqs}
                    total_prereq += 1
                    if gold_ids & set(predicted_ids):
                        correct_prereq += 1

                observed = target.get("observed_yield")
                if observed is not None:
                    predicted_yield = float(
                        out["theoretical_yield"].cpu().item()
                    )
                    total_abs_err += abs(predicted_yield - float(observed))
                    total_yield += 1

        if total_prereq == 0 and total_yield == 0:
            return None
        result: dict[str, float] = {}
        if total_prereq > 0:
            result["prereq_accuracy"] = correct_prereq / total_prereq
        if total_yield > 0:
            result["yield_mae"] = total_abs_err / total_yield
        return result

    def evaluate_v2_metrics(
        self,
        dataloader: DataLoader,
        rust_bridge: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Run every v2 metric against a dataloader and return a dict.

        Keys whose corresponding v2 component is absent are omitted from the
        returned dict (i.e. not set to ``None``). When all v2 components are
        absent, an empty dict is returned.
        """
        results: dict[str, Any] = {}

        reg_acc = self.register_prediction_accuracy(dataloader)
        if reg_acc is not None:
            results["register_prediction_accuracy"] = reg_acc

        rule_four = self.rule_four_compliance_rate(
            dataloader, rust_bridge=rust_bridge
        )
        if rule_four is not None:
            results["rule_four_compliance_rate"] = rule_four

        omega_acc = self.omega_activation_accuracy(dataloader)
        if omega_acc is not None:
            results["omega_activation_accuracy"] = omega_acc

        prod_acc = self.production_semantics_accuracy(dataloader)
        if prod_acc is not None:
            results["production_semantics_accuracy"] = prod_acc

        return results

    # ------------------------------------------------------------------
    # Composite v2 score — Wave 8A evaluation extension.
    # ------------------------------------------------------------------

    # Default composite weights — equal quarters across the four v2 metrics.
    # Documented constant so tests and checkpoint-selection callers stay in
    # sync with the evaluator.
    COMPOSITE_V2_WEIGHTS: dict[str, float] = {
        "register_prediction_accuracy": 0.25,
        "rule_four_compliance_rate": 0.25,
        "omega_activation_accuracy": 0.25,
        "production_semantics_accuracy": 0.25,
    }

    def composite_v2_score(
        self,
        dataloader: DataLoader,
        rust_bridge: Optional[Any] = None,
        weights: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        """Weighted composite of the four v2 metrics + per-component scores.

        The composite is used as a checkpoint-selection criterion while v2
        training is active (see ``TrainingConfig.effective_checkpoint_selection_metric``).
        Returns a dict with:

          - ``"components"``: per-metric float dict (subset of the four v2
            metrics; metrics whose v2 component is absent are omitted).
          - ``"weights"``: the weight applied to each component.
          - ``"composite"``: weighted mean of the components that WERE
            computed — i.e. when a metric is absent its weight is removed
            from the denominator so the composite remains in ``[0, 1]``.
            ``None`` when no v2 metric could be computed at all.
          - ``"production_yield_mae"`` (optional): forwarded from the
            production-semantics metric when that metric returns a
            ``yield_mae`` sub-field (lower is better — informational only,
            not part of the composite).

        The composite specifically consumes ``prereq_accuracy`` from the
        production-semantics metric (a ``[0, 1]`` accuracy) — ``yield_mae``
        is reported alongside for diagnostic use but never enters the sum.

        Args:
            dataloader: Validation loader with v2-labeled batches.
            rust_bridge: Optional pre-built ``RustValidationBridge``. When
                ``None``, the evaluator's owning trainer may inject its own
                bridge — so callers at the trainer level should thread
                ``self._rust_bridge`` through.
            weights: Optional override for the default 25/25/25/25 weighting.
                Unknown keys are silently ignored; missing keys default to
                the class-level ``COMPOSITE_V2_WEIGHTS``.
        """
        w = dict(self.COMPOSITE_V2_WEIGHTS)
        if weights is not None:
            for k, v in weights.items():
                if k in w:
                    w[k] = float(v)

        metrics = self.evaluate_v2_metrics(dataloader, rust_bridge=rust_bridge)
        components: dict[str, float] = {}

        if "register_prediction_accuracy" in metrics:
            components["register_prediction_accuracy"] = float(
                metrics["register_prediction_accuracy"]
            )
        if "rule_four_compliance_rate" in metrics:
            components["rule_four_compliance_rate"] = float(
                metrics["rule_four_compliance_rate"]
            )
        if "omega_activation_accuracy" in metrics:
            components["omega_activation_accuracy"] = float(
                metrics["omega_activation_accuracy"]
            )

        yield_mae: Optional[float] = None
        if "production_semantics_accuracy" in metrics:
            prod = metrics["production_semantics_accuracy"]
            # ``production_semantics_accuracy`` returns a sub-dict with
            # ``prereq_accuracy`` and/or ``yield_mae``. Only ``prereq_accuracy``
            # is a ``[0,1]`` accuracy suitable for the composite.
            if isinstance(prod, dict):
                if "prereq_accuracy" in prod:
                    components["production_semantics_accuracy"] = float(
                        prod["prereq_accuracy"]
                    )
                if "yield_mae" in prod:
                    yield_mae = float(prod["yield_mae"])
            else:
                components["production_semantics_accuracy"] = float(prod)

        # Compute weighted composite only over present components; re-normalize
        # the denominator so missing metrics do not pull the composite toward 0.
        active_weight_sum = sum(w[k] for k in components.keys())
        if active_weight_sum > 0:
            composite: Optional[float] = sum(
                w[k] * components[k] for k in components.keys()
            ) / active_weight_sum
        else:
            composite = None

        result: dict[str, Any] = {
            "components": components,
            "weights": {k: w[k] for k in components.keys()},
            "composite": composite,
        }
        if yield_mae is not None:
            result["production_yield_mae"] = yield_mae
        return result

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
