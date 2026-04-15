"""Cognitive Lacunarity Profile — Python implementation.

Mirrors cas-engine/src/scoring/lacunarity.rs so it works without
rebuilding the Rust PyO3 wheel.
"""

from __future__ import annotations


def compute_state_lacunarity(operator_scores: list[float]) -> float:
    """Var(p) / Mean(p)^2 on operator scores."""
    n = len(operator_scores)
    if n == 0:
        return 0.0
    mean = sum(operator_scores) / n
    if mean <= 0:
        return 0.0
    variance = sum((s - mean) ** 2 for s in operator_scores) / n
    return round(variance / (mean * mean), 4)


def compute_fractal_lacunarity(fractal_sequence: list[int]) -> float:
    """1 - (unique operators / 10)."""
    if not fractal_sequence:
        return 1.0
    unique = len(set(fractal_sequence))
    return round(1.0 - unique / 10.0, 4)


def compute_domain_lacunarity(domain_scores: list[float], threshold: float = 0.2) -> float:
    """1 - (active domains / 4)."""
    active = sum(1 for s in domain_scores if s > threshold)
    return round(1.0 - active / 4.0, 4)


def compute_drive_lacunarity(drive_scores: list[float], threshold: float = 0.15) -> float:
    """1 - (active drives / 7)."""
    active = sum(1 for s in drive_scores if s > threshold)
    return round(1.0 - active / 7.0, 4)


def compute_rpm_resolution_lacunarity(resolution_details: list[dict]) -> float:
    """1 - (unique mechanisms used / 4)."""
    mechanisms_seen: set[str] = set()
    for detail in resolution_details:
        for res in detail.get("resolutions", []):
            mechanisms_seen.add(res.get("mechanism", ""))
    used = len(mechanisms_seen)
    return round(1.0 - used / 4.0, 4)


def classify_lacunarity(score: float) -> str:
    if score < 0.5:
        return "Uniform"
    if score < 1.5:
        return "Moderate"
    if score < 3.0:
        return "Concentrated"
    return "Extreme"


def generate_gap_map(
    operator_scores: list[float],
    domain_scores: list[float],
    drive_scores: list[float],
    op_threshold: float = 4.0,
    dom_threshold: float = 0.3,
    drv_threshold: float = 0.2,
) -> dict:
    op_names = [
        "Generative Potential", "Directed Attention", "Attraction",
        "Critical Evaluation", "Encoding Intensity", "Receptive Integration",
        "Projective Assertion", "Pattern Entrainment", "Causal Reasoning",
        "Consequential Grounding",
    ]
    drive_names = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
    domain_names = ["P", "C", "E", "O"]

    absent_ops = [i for i, s in enumerate(operator_scores) if s < op_threshold]
    absent_doms = [domain_names[i] for i, s in enumerate(domain_scores) if s < dom_threshold]
    absent_drvs = [i + 1 for i, s in enumerate(drive_scores) if s < drv_threshold]
    strongest = [i for i, s in enumerate(operator_scores) if s >= op_threshold * 1.5]

    if len(absent_ops) >= 5:
        names = [op_names[i] for i in absent_ops]
        largest_void = f"Critical operator void: {len(absent_ops)} operators absent ({', '.join(names)})"
    elif len(absent_doms) >= 2:
        largest_void = f"Domain void: {len(absent_doms)} processing domains inactive ({', '.join(absent_doms)})"
    elif len(absent_drvs) >= 4:
        names = [drive_names[i - 1] for i in absent_drvs]
        largest_void = f"Drive void: {len(absent_drvs)} motivational drives absent ({', '.join(names)})"
    elif not absent_ops and not absent_doms and not absent_drvs:
        largest_void = "No significant gaps detected"
    else:
        largest_void = f"{len(absent_ops)} operator(s), {len(absent_doms)} domain(s), {len(absent_drvs)} drive(s) below threshold"

    return {
        "absent_operators": absent_ops,
        "absent_domains": absent_doms,
        "absent_drives": absent_drvs,
        "strongest_cluster": strongest,
        "largest_void": largest_void,
    }


def compute_lacunarity_profile(
    operator_scores: list[float],
    domain_scores: list[float],
    drive_scores: list[float],
    fractal_sequence: list[int] | None = None,
    resolution_details: list[dict] | None = None,
) -> dict:
    """Compute the full lacunarity profile."""
    raw_10 = operator_scores if len(operator_scores) == 10 else (operator_scores + [0.0] * 10)[:10]

    state = compute_state_lacunarity(raw_10)
    fractal = compute_fractal_lacunarity(fractal_sequence or [])
    domain = compute_domain_lacunarity(domain_scores[:4] if len(domain_scores) >= 4 else domain_scores + [0.0] * 4)
    drive_flat = drive_scores[:7] if len(drive_scores) >= 7 else drive_scores + [0.0] * 7
    drv = compute_drive_lacunarity(drive_flat)
    rpm = compute_rpm_resolution_lacunarity(resolution_details or [])

    composite = round(0.30 * state + 0.20 * fractal + 0.20 * domain + 0.15 * drv + 0.15 * rpm, 4)
    classification = classify_lacunarity(composite)
    gap_map = generate_gap_map(raw_10, domain_scores[:4], drive_flat)

    return {
        "state": state,
        "fractal": fractal,
        "domain": domain,
        "drive": drv,
        "rpm_resolution": rpm,
        "composite": composite,
        "classification": classification,
        "gap_map": gap_map,
    }
