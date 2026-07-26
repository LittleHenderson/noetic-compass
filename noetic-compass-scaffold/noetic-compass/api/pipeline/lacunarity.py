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
    dom_threshold: float = 0.2,
    drv_threshold: float = 0.2,
) -> dict:
    # Canonical Noetic names. These are authoritative and verbatim; see
    # docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md Clarification 1. Do not substitute
    # functional descriptions. The names this list previously carried
    # ("Critical Evaluation" for ^3, "Causal Reasoning" for ^8, and the rest)
    # were Scheme-B drift -- exactly the two the anti-drift rule calls out: ^3
    # Negative is visceral aversion, not analytical critique, and ^8
    # Above/Cause is associative triggering, not deductive reasoning.
    op_names = [
        "Idea", "Mind", "Positive", "Negative", "Vibration",
        "Female", "Male", "Rhythm", "Above/Cause", "Below/Effect",
    ]
    drive_names = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
    domain_names = ["P", "C", "E", "O"]

    # Pad to full width before scanning. A short list means the caller supplied
    # no evidence for the trailing entries, and absent evidence is exactly what
    # a lacunarity scan exists to report -- treating it as "nothing to see"
    # would make the short-list case a silent false negative. Truncating on the
    # long side keeps the name lookups below in range.
    ops = (list(operator_scores) + [0.0] * len(op_names))[:len(op_names)]
    doms = (list(domain_scores) + [0.0] * len(domain_names))[:len(domain_names)]
    drvs = (list(drive_scores) + [0.0] * len(drive_names))[:len(drive_names)]

    absent_ops = [i for i, s in enumerate(ops) if s < op_threshold]
    absent_doms = [domain_names[i] for i, s in enumerate(doms) if s < dom_threshold]
    absent_drvs = [i + 1 for i, s in enumerate(drvs) if s < drv_threshold]
    strongest = [i for i, s in enumerate(ops) if s >= op_threshold * 1.5]

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
    # Pad-then-truncate in one step. The previous form padded without
    # truncating on the short branch, so a 2-element domain list became a
    # 6-element one and a short drive list produced out-of-range drive indices.
    domain_flat = (list(domain_scores) + [0.0] * 4)[:4]
    drive_flat = (list(drive_scores) + [0.0] * 7)[:7]
    domain = compute_domain_lacunarity(domain_flat)
    drv = compute_drive_lacunarity(drive_flat)
    rpm = compute_rpm_resolution_lacunarity(resolution_details or [])

    composite = round(0.30 * state + 0.20 * fractal + 0.20 * domain + 0.15 * drv + 0.15 * rpm, 4)
    classification = classify_lacunarity(composite)
    gap_map = generate_gap_map(raw_10, domain_flat, drive_flat)

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
