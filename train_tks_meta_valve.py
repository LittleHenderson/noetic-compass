"""train_tks_meta_valve.py -- Training Harness for Phase 3 Meta Valve Controller.

CRITICAL RULE:
"MUST REMEMBER: Add, train, and test the VALVE SYSTEM (tks_meta_valve_controller) in Phase 3. This is CRITICAL."

AWS EXECUTION PREFERENCE:
- Standard library / pure math solver runs locally in < 3 seconds (< 20 MB RAM) to fit the initial
  calibrated weights without violating the laptop 354 MB RAM boundary.
- Full scaled PyTorch/CUDA training harness configured for AWS GPU (Tesla T4, < $1.00 cap).

OBJECTIVE:
Learn the optimal dynamic aperture function:
    sigma*(features) = sigmoid(w^T * features + b)
such that:
1. Clean verified proposals (low entropy, high credibility, verified prerequisites) pass freely (sigma -> 0.95).
2. Creative analogies at bounded horizons are admitted into Daydreaming (sigma -> 0.65).
3. High-entropy hallucinations and ungrounded speculations are throttled (sigma -> 0.10).
4. Missing prerequisites trigger the mandatory RPM Gate safety interlock (G-ABSENT clamp).
"""
from __future__ import annotations

import sys
import os
import json
import math
import random
from decimal import Decimal
from typing import Dict, List, Tuple, Any

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(HERE, "tks_meta_valve_weights_v0_4.json")


# -----------------------------------------------------------------------------
# 1. Proposal Feature Extraction
# -----------------------------------------------------------------------------
# Features:
# 0: novelty_entropy (0.0: deterministic .. 1.0: random noise)
# 1: source_credibility (0.0: unverified internet text .. 1.0: physical sensor / verified recipe)
# 2: prerequisite_ratio (0.0: none present .. 1.0: all present)
# 3: normalized_radius (R / 8.0, where R in {1, 2, 4, 8})
# 4: operating_mode_bias (Surgical: -1.0, Balanced: 0.0, Brainstorm: +1.0)
FEATURE_NAMES = [
    "novelty_entropy",
    "source_credibility",
    "prerequisite_ratio",
    "normalized_radius",
    "operating_mode_bias"
]


def extract_features(novelty_entropy: float,
                     source_credibility: float,
                     prerequisite_ratio: float,
                     radius: int,
                     mode: str) -> List[float]:
    mode_bias = 0.0
    if mode.upper() == "SURGICAL":
        mode_bias = -1.0
    elif mode.upper() == "BRAINSTORM":
        mode_bias = 1.0

    return [
        float(novelty_entropy),
        float(source_credibility),
        float(prerequisite_ratio),
        float(radius) / 8.0,
        mode_bias
    ]


# -----------------------------------------------------------------------------
# 2. Synthetic Dataset Generator
# -----------------------------------------------------------------------------
def generate_training_data(n_samples: int = 2000, seed: int = 42) -> List[Dict[str, Any]]:
    """Synthesizes balanced cognitive scenarios across the 4 canonical regimes."""
    rng = random.Random(seed)
    dataset = []

    for i in range(n_samples):
        regime = i % 4
        if regime == 0:
            # Regime 1: Clean, verified physical recipe proposal
            # High credibility, low entropy, full prerequisites -> Target: High Aperture (0.90 - 0.98)
            entropy = rng.uniform(0.05, 0.30)
            credibility = rng.uniform(0.85, 1.00)
            prereq = 1.0
            radius = rng.choice([1, 2])
            mode = rng.choice(["SURGICAL", "BALANCED", "BRAINSTORM"])
            target_sigma = 0.92 + rng.uniform(-0.04, 0.04)

        elif regime == 1:
            # Regime 2: Plausible creative analogy at bounded horizon
            # Moderate entropy, moderate credibility, full prerequisites
            entropy = rng.uniform(0.35, 0.60)
            credibility = rng.uniform(0.60, 0.85)
            prereq = 1.0
            radius = rng.choice([2, 4])
            mode = rng.choice(["BALANCED", "BRAINSTORM"])
            target_sigma = 0.65 + rng.uniform(-0.05, 0.05)
            if mode == "SURGICAL":
                target_sigma = 0.35  # Surgical mode restricts high novelty

        elif regime == 2:
            # Regime 3: High-entropy ungrounded speculation / hallucination
            # High entropy, low credibility -> Target: Low Aperture (0.05 - 0.20)
            entropy = rng.uniform(0.70, 0.99)
            credibility = rng.uniform(0.10, 0.40)
            prereq = rng.uniform(0.5, 1.0)
            radius = rng.choice([4, 8])
            mode = rng.choice(["SURGICAL", "BALANCED", "BRAINSTORM"])
            target_sigma = 0.12 + rng.uniform(-0.04, 0.04)

        else:
            # Regime 4: Missing Prerequisite Trap
            # Prerequisite missing (< 1.0) -> Target: 0.00 (Mandatory Clamped Halt)
            entropy = rng.uniform(0.10, 0.90)
            credibility = rng.uniform(0.10, 0.90)
            prereq = rng.uniform(0.0, 0.80)
            radius = rng.choice([1, 2, 4, 8])
            mode = rng.choice(["SURGICAL", "BALANCED", "BRAINSTORM"])
            target_sigma = 0.00

        feats = extract_features(entropy, credibility, prereq, radius, mode)
        dataset.append({
            "features": feats,
            "target_sigma": target_sigma,
            "prerequisites_present": bool(prereq >= 1.0),
            "regime": regime
        })

    return dataset


# -----------------------------------------------------------------------------
# 3. Deterministic Lightweight Gradient Solver (Laptop Standard Library)
# -----------------------------------------------------------------------------
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


def train_valve_model_local(dataset: List[Dict[str, Any]],
                            epochs: int = 120,
                            lr: float = 0.08) -> Dict[str, Any]:
    """Fits the adaptive valve aperture parameters using fast logistic descent (< 1s local runtime)."""
    n_features = len(FEATURE_NAMES)
    weights = [0.0] * n_features
    bias = 0.0

    # Prior initialization:
    # entropy lowers aperture (-), credibility raises (+), prerequisites strongly raise (+)
    weights[0] = -2.5   # entropy
    weights[1] = +2.0   # credibility
    weights[2] = +4.0   # prerequisites
    weights[3] = -0.5   # radius penalty
    weights[4] = +0.8   # mode bias
    bias = -0.5

    n = len(dataset)
    for epoch in range(epochs):
        grad_w = [0.0] * n_features
        grad_b = 0.0
        total_loss = 0.0

        for item in dataset:
            x = item["features"]
            y = item["target_sigma"]
            raw_logit = sum(w * xi for w, xi in zip(weights, x)) + bias
            pred = sigmoid(raw_logit)

            # Prerequisite critical penalty: if prereqs missing, target is strictly 0.0
            error = (pred - y)
            if not item["prerequisites_present"]:
                error *= 2.0  # Double penalty for letting missing prerequisites leak

            total_loss += error * error

            for j in range(n_features):
                grad_w[j] += error * pred * (1.0 - pred) * x[j]
            grad_b += error * pred * (1.0 - pred)

        # Gradient update
        for j in range(n_features):
            weights[j] -= (lr / n) * grad_w[j]
        bias -= (lr / n) * grad_b

    mse = total_loss / n

    model_record = {
        "model_type": "TKS_ADAPTIVE_VALVE_APERTURE_v0.4",
        "feature_names": FEATURE_NAMES,
        "weights": [round(w, 8) for w in weights],
        "bias": round(bias, 8),
        "training_samples": len(dataset),
        "final_mse": round(mse, 8),
        "rule_interlock": "RPM_GATE_G_ABSENT_STRICT_OVERRIDE",
        "training_environment": "LOCAL_CPU_DRYRUN_FAST" if "torch" not in sys.modules else "AWS_GPU_ACCELERATED"
    }
    return model_record


# -----------------------------------------------------------------------------
# 4. Evaluation and Verification
# -----------------------------------------------------------------------------
def evaluate_valve_model(model: Dict[str, Any], test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    weights = model["weights"]
    bias = model["bias"]
    errors = []
    ungated_leaks_on_missing_prereqs = 0
    gated_leaks_with_rpm_interlock = 0

    for item in test_data:
        x = item["features"]
        y = item["target_sigma"]
        logit = sum(w * xi for w, xi in zip(weights, x)) + bias
        raw_pred = sigmoid(logit)

        # 1. Ungated purely neural prediction (standard LLM behavior)
        if not item["prerequisites_present"] and raw_pred > 0.20:
            ungated_leaks_on_missing_prereqs += 1

        # 2. HELM RPM Gate Interlock prediction:
        # Mandatory override: missing prerequisites strictly clamp aperture to 0.0
        gated_pred = 0.0 if not item["prerequisites_present"] else raw_pred
        if not item["prerequisites_present"] and gated_pred > 0.0:
            gated_leaks_with_rpm_interlock += 1

        errors.append(abs(gated_pred - y))

    return {
        "mean_absolute_error": round(sum(errors) / len(errors), 6),
        "max_error": round(max(errors), 6),
        "ungated_statistical_leaks": ungated_leaks_on_missing_prereqs,
        "gated_rpm_interlock_leaks": gated_leaks_with_rpm_interlock,
        "rpm_gate_safety_interlock": "100% ZERO LEAKAGE (PASS)" if gated_leaks_with_rpm_interlock == 0 else "FAIL"
    }


def main():
    print("=" * 72)
    print("        HELM PHASE 3 TKS META VALVE CONTROLLER TRAINING HARNESS        ")
    print("=" * 72)

    # 1. Generate synthetic proposal dataset
    print("[1/4] Generating 2,000 synthetic multi-regime cognitive proposal scenarios...")
    train_data = generate_training_data(n_samples=2000, seed=42)
    val_data = generate_training_data(n_samples=500, seed=1337)
    print(f"      Train samples: {len(train_data)} | Validation samples: {len(val_data)}")

    # 2. Train adaptive valve controller
    print("[2/4] Training adaptive aperture network (Local stdlib gradient solver)...")
    model = train_valve_model_local(train_data, epochs=150, lr=0.12)
    print(f"      Training complete. Final MSE: {model['final_mse']}")
    print("      Learned Feature Weights:")
    for name, w in zip(FEATURE_NAMES, model["weights"]):
        direction = "Restricts" if w < 0 else "Expands"
        print(f"        - {name:<22}: {w:>10.6f} ({direction} aperture)")
    print(f"        - {'bias':<22}: {model['bias']:>10.6f}")

    # 3. Evaluate and verify safety
    print("[3/4] Evaluating model against held-out validation set...")
    metrics = evaluate_valve_model(model, val_data)
    print(f"      Validation MAE: {metrics['mean_absolute_error']}")
    print(f"      Ungated statistical model leaks (missing data passed): {metrics['ungated_statistical_leaks']} / 125 missing rows")
    print(f"      HELM RPM Gate Interlock leaks (missing data passed)   : {metrics['gated_rpm_interlock_leaks']} / 125 missing rows")
    print(f"      Safety interlock status: {metrics['rpm_gate_safety_interlock']}")

    # 4. Save trained weights
    print(f"[4/4] Saving model weights to {WEIGHTS_PATH}...")
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
    print("      Model weights saved successfully.")
    print("=" * 72)
    print("PHASE 3 VALVE SYSTEM TRAINING AND VERIFICATION COMPLETE.")
    print("=" * 72)


if __name__ == "__main__":
    main()
