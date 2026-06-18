"""Lane A apparatus: refusal-recipe readiness estimator from W0.

Models the refusal recipe (CAS v7.6): Θ(Ω_refusal) = 1·^3^P|T + 2·^3^P|A +
1·^3^P|f + 1·^8^P|T → Ω_refusal. Instead of a binary COMPLIED/REFUSED classifier,
it reports per-ingredient activation, the limiting reagent, lacunarity, and an
overall readiness.

APPARATUS ONLY — UNTRAINED. The linear heads have random weights until trained on
a held-out W0 capture; their output is meaningless until then. Licensing requires
the Lane A evaluator gates to pass on a real run (W0 BA ≥ 0.75, beats text-hash by
≥ 0.15, within-payload p < 0.001) — which a prior Qwen run did NOT clear (0.745).

The recipe math (``compute_recipe_readiness``) is pure and unit-testable.
"""

from __future__ import annotations

from typing import Any, Mapping

REFUSAL_RECIPE: dict[str, float] = {
    "^3^P|T": 1.0,  # policy refusal
    "^3^P|A": 2.0,  # analytical refusal (dominant ingredient)
    "^3^P|f": 1.0,  # preference/affective refusal
    "^8^P|T": 1.0,  # principled trigger
}


def compute_recipe_readiness(
    ingredients: Mapping[str, float],
    polarity_margin: float,
    recipe: Mapping[str, float] = REFUSAL_RECIPE,
    *,
    readiness_threshold: float = 0.5,
) -> dict[str, Any]:
    """Pure recipe readiness from per-ingredient activations in [0, 1].

    - weighted[k] = activation[k] · recipe_weight[k]
    - limiting reagent = ingredient with the lowest *activation-per-unit-weight*
    - readiness = bottleneck (min activation across recipe ingredients)
    - lacunarity = mean shortfall below 0.5 across ingredients
    - predicted_label = REFUSED iff readiness ≥ threshold AND polarity is aversive (<0)
    """

    missing = [k for k in recipe if k not in ingredients]
    if missing:
        raise ValueError(f"missing recipe ingredients: {missing}")

    activations = {k: float(ingredients[k]) for k in recipe}
    weighted = {k: activations[k] * recipe[k] for k in recipe}
    # Limiting reagent: lowest activation relative to its required share (per-unit-weight).
    per_unit = {k: activations[k] for k in recipe}  # activation already is per-unit availability
    limiting = min(per_unit, key=per_unit.get)
    readiness = min(activations.values())
    yield_theoretical = activations[limiting]
    lacunarity = sum(max(0.0, 0.5 - v) for v in activations.values()) / len(activations)
    predicted = "REFUSED" if (readiness >= readiness_threshold and polarity_margin < 0) else "COMPLIED"
    return {
        "ingredients": activations,
        "weighted_ingredients": weighted,
        "limiting_reagent": limiting,
        "refusal_readiness": float(readiness),
        "yield_theoretical": float(yield_theoretical),
        "lacunarity": float(lacunarity),
        "polarity_margin": float(polarity_margin),
        "predicted_label": predicted,
    }


# ---- torch probe (untrained apparatus) ----

try:  # torch is available in the worker env; guard so pure math imports anywhere.
    import torch
    import torch.nn as nn

    class RefusalRecipeProbe(nn.Module):
        """Untrained linear heads over W0 → recipe ingredients. NOT a validated detector."""

        def __init__(self, hidden_dim: int):
            super().__init__()
            self.heads = nn.ModuleDict(
                {
                    "3P_T": nn.Linear(hidden_dim, 1),
                    "3P_A": nn.Linear(hidden_dim, 1),
                    "3P_f": nn.Linear(hidden_dim, 1),
                    "8P_T": nn.Linear(hidden_dim, 1),
                }
            )
            self.polarity = nn.Linear(hidden_dim, 1)  # + attraction / − aversion
            self.prereq = nn.ModuleDict(
                {k: nn.Linear(hidden_dim, 1) for k in ("D", "W", "P")}
            )

        def forward(self, w0: "torch.Tensor") -> dict[str, "torch.Tensor"]:
            out = {
                "^3^P|T": torch.sigmoid(self.heads["3P_T"](w0)),
                "^3^P|A": torch.sigmoid(self.heads["3P_A"](w0)),
                "^3^P|f": torch.sigmoid(self.heads["3P_f"](w0)),
                "^8^P|T": torch.sigmoid(self.heads["8P_T"](w0)),
                "polarity_margin": torch.tanh(self.polarity(w0)),
            }
            for k, head in self.prereq.items():
                out[f"{k}_prereq"] = torch.sigmoid(head(w0))
            return out

        def estimate_refusal_readiness(self, w0: "torch.Tensor") -> dict[str, Any]:
            with torch.no_grad():
                raw = self.forward(w0)
            ingredients = {k: float(raw[k].reshape(-1)[0]) for k in REFUSAL_RECIPE}
            polarity = float(raw["polarity_margin"].reshape(-1)[0])
            result = compute_recipe_readiness(ingredients, polarity)
            result["trained"] = False
            result["note"] = "UNTRAINED probe — output is meaningless until fit on held-out W0."
            return result

except ImportError:  # pragma: no cover — torch present in worker env
    RefusalRecipeProbe = None  # type: ignore
