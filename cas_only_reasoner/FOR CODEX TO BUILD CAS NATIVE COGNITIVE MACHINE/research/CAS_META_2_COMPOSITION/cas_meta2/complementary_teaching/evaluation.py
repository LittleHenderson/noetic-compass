"""Reproduce paired results only from complete retained rows; no model access."""
from __future__ import annotations

from collections import defaultdict
import random

from .course import CONDITIONS, SEEDS, require


def _mean(values):
    values = list(values)
    require(values, "COMPLEMENTARY_EMPTY_ANALYSIS")
    return sum(values) / len(values)


def _accuracy(rows):
    return _mean(float(row["correct"]) for row in rows)


def bootstrap(values, *, seed=404, replicates=10000):
    values = list(values)
    require(values, "COMPLEMENTARY_BOOTSTRAP_EMPTY")
    rng = random.Random(seed)
    sampled = sorted(_mean(rng.choices(values, k=len(values))) for _ in range(replicates))
    return [sampled[int(0.025 * (replicates - 1))], sampled[int(0.975 * (replicates - 1))]]


def _paired(left, right):
    require(len({row["record_id"] for row in left}) == len(left), "COMPLEMENTARY_DUPLICATE_AUDIT_ROW")
    require(len({row["record_id"] for row in right}) == len(right), "COMPLEMENTARY_DUPLICATE_AUDIT_ROW")
    rindex = {row["record_id"]: row for row in right}
    require(set(rindex) == {row["record_id"] for row in left}, "COMPLEMENTARY_PAIRED_ROWS_MISSING")
    families = defaultdict(list)
    for row in left:
        other = rindex[row["record_id"]]
        require(row["family_id"] == other["family_id"], "COMPLEMENTARY_PAIRED_FAMILY_MISMATCH")
        families[row["family_id"]].append(float(row["correct"]) - float(other["correct"]))
    return {key: _mean(values) for key, values in families.items()}


def contrast(index, control):
    by_seed, grouped = {}, defaultdict(list)
    for seed in SEEDS:
        left = index[(CONDITIONS[0], seed)]["final"]["rows"]["final_application"]
        right = index[(control, seed)]["final"]["rows"]["final_application"]
        differences = _paired(left, right)
        require(len(differences) == 30, "COMPLEMENTARY_PRIMARY_30_FAMILIES")
        by_seed[str(seed)] = _mean(differences.values())
        for family, difference in differences.items():
            grouped[family].append(difference)
    require(all(len(values) == 3 for values in grouped.values()), "COMPLEMENTARY_FAMILY_SEED_COVERAGE")
    averaged = {family: _mean(values) for family, values in grouped.items()}
    interval = bootstrap(averaged.values())
    difference = _mean(averaged.values())
    positive = sum(value > 0 for value in by_seed.values())
    passed = difference >= .05 and interval[0] > 0 and positive >= 2
    return {"control": control, "difference": difference, "interval_95": interval,
            "by_seed": by_seed, "positive_seeds": positive, "root_families": averaged,
            "status": "SUPPORTED" if passed else "NOT_ESTABLISHED",
            "bootstrap_replicates": 10000, "analysis_seed": 404,
            "interval_scope": "per-contrast, conditional on three fixed seeds; not simultaneous 95% coverage"}


def retention(index):
    rows, assessed, passed = [], True, True
    for seed in SEEDS:
        alt = index[(CONDITIONS[0], seed)]
        for panel, control in (("final_components", CONDITIONS[1]),
                               ("final_earlier_skills", CONDITIONS[2])):
            initial = alt["initial"]["rows"].get(panel, [])
            final = alt["final"]["rows"].get(panel, [])
            comparison = index[(control, seed)]["final"]["rows"].get(panel, [])
            if not initial or not final or not comparison or _accuracy(initial) < .5:
                assessed = False
                rows.append({"seed": seed, "panel": panel, "status": "RETENTION_UNASSESSED"})
                continue
            initial_delta = _paired(final, initial)
            control_delta = _paired(final, comparison)
            initial_difference, control_difference = _mean(initial_delta.values()), _mean(control_delta.values())
            met = initial_difference >= -.02 and control_difference >= -.02
            passed &= met
            breakdown = []
            keys = sorted({(row.get("op", "unspecified"), row.get("audit_face", 0)) for row in final})
            for operation, face in keys:
                def subset(values):
                    return [row for row in values if (row.get("op", "unspecified"), row.get("audit_face", 0)) == (operation, face)]
                frows, irows, crows = subset(final), subset(initial), subset(comparison)
                initial_by_family = _paired(frows, irows)
                control_by_family = _paired(frows, crows)
                breakdown.append({"operation": operation, "face": face or None, "count": len(frows),
                    "initial_accuracy": _accuracy(irows), "final_accuracy": _accuracy(frows),
                    "control_accuracy": _accuracy(crows), "difference_from_initial": _mean(initial_by_family.values()),
                    "difference_from_control": _mean(control_by_family.values()),
                    "initial_difference_interval_95": bootstrap(initial_by_family.values()),
                    "control_difference_interval_95": bootstrap(control_by_family.values())})
            rows.append({"seed": seed, "panel": panel, "initial_accuracy": _accuracy(initial),
                         "final_accuracy": _accuracy(final), "control_accuracy": _accuracy(comparison),
                         "difference_from_initial": initial_difference, "difference_from_control": control_difference,
                         "initial_difference_interval_95": bootstrap(initial_delta.values()),
                         "control_difference_interval_95": bootstrap(control_delta.values()),
                         "per_operation_face": breakdown,
                         "status": "OBSERVED_TOLERANCE_MET" if met else "OBSERVED_TOLERANCE_FAILED"})
    return {"status": "RETENTION_UNASSESSED" if not assessed else
                      "OBSERVED_RETENTION_CONSTRAINT_MET" if passed else "OBSERVED_RETENTION_CONSTRAINT_NOT_MET",
            "rows": rows, "boundary": "Observed audit tolerance; not a statistical noninferiority guarantee or all-capability retention."}


def analyze(report):
    courses = report.get("courses", [])
    expected = {(condition, seed) for condition in CONDITIONS for seed in SEEDS}
    index = {(row["condition"], row["seed"]): row for row in courses}
    require(len(courses) == 9 and set(index) == expected, "COMPLEMENTARY_NINE_COMPLETE_COURSES_REQUIRED")
    for course in courses:
        require(course["training"]["status"] == "TEACHING_COMPLETE" and
                course["training"]["next_cursor"] == 160 and len(course["training"]["rows"]) == 160,
                "COMPLEMENTARY_TEACHING_INCOMPLETE")
        require(len(course["observations"]) == 17 and course["reload_equal"] and
                course["numerical"]["status"] == "PASS" and course["containment"]["contained"],
                "COMPLEMENTARY_REQUIRED_EVIDENCE_MISSING")
        for panel, count in (("final_application", 90), ("final_components", 30), ("final_earlier_skills", 96)):
            require(len(course["final"]["rows"].get(panel, [])) == count, "COMPLEMENTARY_FINAL_ROWS_MISSING:" + panel)
    supplement = contrast(index, CONDITIONS[2])
    order = contrast(index, CONDITIONS[1])
    retained = retention(index)
    accuracy = _mean(_accuracy(index[(CONDITIONS[0], seed)]["final"]["rows"]["final_application"]) for seed in SEEDS)
    qualified = supplement["status"] == "SUPPORTED" and retained["status"] == "OBSERVED_RETENTION_CONSTRAINT_MET" and accuracy >= .5
    breakdown = []
    for course in courses:
        groups = defaultdict(list)
        for panel, values in course["final"]["rows"].items():
            for row in values:
                groups[(panel, row["op"], row.get("audit_face"))].append(row)
        breakdown.extend({"condition": course["condition"], "seed": course["seed"], "panel": key[0],
                          "operation": key[1], "face": key[2], "count": len(values), "accuracy": _accuracy(values)}
                         for key, values in groups.items())
    return {"status": "COMPLEMENTARY_TEACHING_CANDIDATE_QUALIFIED" if qualified else "NOT_ESTABLISHED",
            "supplement_benefit": supplement, "alternation_order_benefit": order,
            "retention": retained, "alt_application_accuracy": accuracy,
            "per_operation_face_seed": breakdown, "automatic_promotion": False}
