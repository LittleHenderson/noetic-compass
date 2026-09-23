"""Read the HSET-1A job's downloaded PUBLIC results (hset1a_aws_job/results/). Reads files only.

Prints and writes RESULTS_READING.json:
  - the job status and exit codes;
  - the build verdict (build_ok and every failure counter) and, per cell: primary clusters, bar, bar accuracy,
    power at the stated model accuracies, and whether the cell can carry a claim;
  - the D-1 acceptance verdict A1-A6 as the program emitted it, with the key measured values;
  - the sealed file's sha256 as the build reported it, and as the watcher wrote it outside the repository.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"


def load(name):
    path = RES / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main():
    summary, acc, watch = load("HSET1A_BUILD_SUMMARY.json"), load("D1_ACCEPTANCE_RESULT.json"), None
    if (HERE / "watch_record.json").is_file():
        watch = json.loads((HERE / "watch_record.json").read_text(encoding="utf-8"))
    out = {"schema": "claude.hset1a-results-reading/0.1",
           "status": (RES / "STATUS").read_text().strip() if (RES / "STATUS").is_file() else None,
           "exit_codes": (RES / "EXIT_CODES").read_text().strip() if (RES / "EXIT_CODES").is_file() else None}
    if summary:
        out["build_ok"] = summary["build_ok"]
        out["problems"] = summary["problems"]
        out["counts"] = summary["counts"]
        out["seconds_build"] = summary["seconds"]
        out["salt_sha256"] = summary["identity"]["salt_sha256"]
        out["sealed_sha256_by_build"] = summary["files"]["HSET1A_SEALED_TEST_NEW_5.json"]
        out["sealed_sha256_by_watcher"] = (watch or {}).get("sealed_files_sha256", {}).get("HSET1A_SEALED_TEST_NEW_5.json")
        out["test_shapes_digest"] = summary["test_shapes_digest"]
        cells = {}
        for name, s in summary["cells"].items():
            cells[name] = {k: s.get(k) for k in ("claim_role", "primary_clusters", "bar", "bar_cluster_accuracy",
                                                 "can_carry_a_claim", "why_not", "primary_by_state", "primary_via_by_distance",
                                                 "clusters_by_role")}
            cells[name]["power"] = s.get("power_exact_sign_test", {}).get("by_model_cluster_accuracy")
            cells[name]["all_comparators"] = s["comparator_cluster_accuracy"]
        out["cells"] = cells
    if acc:
        out["d1_acceptance"] = acc.get("acceptance")
        out["d1_verdict"] = acc.get("verdict")
        out["d1_key_values"] = {
            "A1_files_equal_anchor": acc.get("A1", {}).get("files_equal_anchor"),
            "A1_profile_equals_historical_anchor": acc.get("A1", {}).get("profile_equals_historical_anchor"),
            "A2": {k: acc.get("A2", {}).get(k) for k in ("records", "predictions_compared", "error_count", "answer_set_mismatches",
                                                         "plan_byte_mismatches", "prediction_mismatches", "witness_differences",
                                                         "coverage_differences", "seconds")},
            "A3": {k: acc.get("A3", {}).get(k) for k in ("colliding_classes_tested", "analogy_questions", "correspondence_questions",
                                                         "six_node_correspondence_questions", "cap_cases", "seconds")},
            "A3_mismatch_count": len(acc.get("A3", {}).get("mismatches", [])),
            "A4": acc.get("A4"), "A5": acc.get("A5"),
            "A6": {k: acc.get("A6", {}).get(k) for k in ("questions", "bank_worlds_per_question", "single_process_seconds", "budget_seconds",
                                                         "max_permutations_per_question", "answers_equal_oracle", "six_node_seconds")},
            "X": acc.get("X_hset1a_crosscheck")}
    if watch:
        out["watch"] = {k: watch.get(k) for k in ("outcome", "job_status", "final_state", "minutes_from_launch_to_watch_end",
                                                  "cost_upper_bound_usd", "dollar_ceiling")}
    (HERE / "RESULTS_READING.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, sort_keys=True)[:12000])


if __name__ == "__main__":
    main()
