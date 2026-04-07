"""POST /batch/compare — cohort distance comparison using Rust engine metrics."""

from __future__ import annotations

import math

from fastapi import APIRouter

import cas_engine

from api.models import (
    CohortCompareRequest,
    CohortCompareResponse,
    CohortDistance,
    CohortCluster,
)

router = APIRouter()


def _build_state_vector(
    operator_scores: list[float],
    domain_averages: list[float],
) -> cas_engine.CognitiveStateVector:
    """Build a 40-dim CognitiveStateVector from operator scores and domain averages.

    Each of the 40 states (4 domains x 10 operators) gets a probability
    proportional to domain_avg[d] * operator_score[o].
    The result is normalized to lie on the open probability simplex.
    """
    raw = []
    for d in range(4):
        for o in range(10):
            raw.append(max(1e-12, domain_averages[d] * operator_scores[o]))

    total = sum(raw)
    normed = [v / total for v in raw]

    return cas_engine.CognitiveStateVector(normed)


def _simple_cluster(
    labels: list[str],
    distance_matrix: list[list[float]],
    threshold: float = 0.5,
) -> list[CohortCluster]:
    """Single-linkage clustering: join profiles whose geodesic distance < threshold.

    Returns cluster IDs (0-indexed) for each profile.
    """
    n = len(labels)
    cluster_ids = list(range(n))

    for i in range(n):
        for j in range(i + 1, n):
            if distance_matrix[i][j] < threshold:
                old_id = cluster_ids[j]
                new_id = cluster_ids[i]
                for k in range(n):
                    if cluster_ids[k] == old_id:
                        cluster_ids[k] = new_id

    # Re-index to sequential 0, 1, 2, ...
    unique = sorted(set(cluster_ids))
    remap = {v: idx for idx, v in enumerate(unique)}

    return [
        CohortCluster(label=labels[i], cluster=remap[cluster_ids[i]])
        for i in range(n)
    ]


@router.post("/batch/compare", response_model=CohortCompareResponse)
async def compare_cohort(req: CohortCompareRequest) -> CohortCompareResponse:
    """Compare multiple candidate profiles using Fisher-Rao geometry.

    Computes pairwise geodesic distance and Bhattacharyya coefficient
    between all profiles, then clusters by proximity.
    """
    profiles = req.profiles
    n = len(profiles)

    # Build state vectors
    vectors = [
        _build_state_vector(p.operator_scores, p.domain_averages)
        for p in profiles
    ]

    # Compute pairwise distances
    distances: list[CohortDistance] = []
    dist_matrix: list[list[float]] = [[0.0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            geo = cas_engine.geodesic_distance(vectors[i], vectors[j])
            bc = cas_engine.bhattacharyya_coefficient(vectors[i], vectors[j])

            # Convert to percentages
            alignment_pct = round(max(0.0, min(100.0, (1 - geo / math.pi) * 100)), 1)
            similarity_pct = round(max(0.0, min(100.0, bc * 100)), 1)

            dist_matrix[i][j] = geo
            dist_matrix[j][i] = geo

            distances.append(CohortDistance(
                from_label=profiles[i].label,
                to_label=profiles[j].label,
                geodesic_distance=round(geo, 6),
                alignment_pct=alignment_pct,
                bhattacharyya_coefficient=round(bc, 6),
                similarity_pct=similarity_pct,
            ))

    labels = [p.label for p in profiles]
    clusters = _simple_cluster(labels, dist_matrix)

    return CohortCompareResponse(
        distances=distances,
        labels=labels,
        clusters=clusters,
    )
