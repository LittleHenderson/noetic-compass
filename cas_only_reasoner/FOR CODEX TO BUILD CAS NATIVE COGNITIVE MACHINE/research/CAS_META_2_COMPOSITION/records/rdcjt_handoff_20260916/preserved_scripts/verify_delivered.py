"""Independently verify the two delivered AWS receipts against their own bytes.

Read-only. Loads no checkpoint and imports no torch. Checks that the recorded
hashes describe the bytes actually on disk, that the sweep payload is internally
consistent with the summary, and that the arms' accounting matches the course.

A hash match proves the bytes are the ones the receipt names. It does not prove
the measurement is scientifically adequate - that is a separate question.
"""

import hashlib
import json
import sys
from pathlib import Path

COMPOSITION = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
    r"\research\CAS_META_2_COMPOSITION")

RECEIPTS = COMPOSITION / "records" / "recurrent_cjt_001"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(receipt_dir):
    out = {"receipt": receipt_dir.name, "checks": {}, "failed": []}

    def check(name, ok, detail=None):
        out["checks"][name] = {"pass": bool(ok)}
        if detail is not None:
            out["checks"][name]["detail"] = detail
        if not ok:
            out["failed"].append(name)

    summary = json.loads((receipt_dir / "curriculum_result.json").read_bytes())
    collected = receipt_dir / "collected" / "results"
    artifacts = receipt_dir / "collected" / "results" / "artifacts"

    check("status_delivered",
          summary.get("status") == "RECURRENT_EXPERIMENT_DELIVERED",
          summary.get("status"))
    check("matched_initial_weights", summary.get("matched_initial_weights") is True)

    # 1. every artifact hash the summary records must describe the bytes present
    for entry in summary["artifacts"]:
        path = artifacts / entry["name"]
        ok = path.is_file() and sha256(path) == entry["sha256"] and \
            path.stat().st_size == entry["bytes"]
        check("artifact:" + entry["name"], ok, entry["sha256"][:16])

    # 2. the collected result.json must match its own sidecar
    result = collected / "result.json"
    sidecar = collected / "result.json.sha256"
    check("result_sidecar_matches",
          result.is_file() and sidecar.is_file()
          and sidecar.read_text().strip() == sha256(result))

    # 3. the inner arm accounting must match the frozen course
    for arm, expected in (("one_pass", (128, 896, 1.0)),
                          ("recurrent", (128, 3360, 3.75))):
        a = summary["arms"][arm]["accounting"]
        ok = (a["optimizer_updates"] == expected[0]
              and a["sample_level_core_passes"] == expected[1]
              and a["mean_depth"] == expected[2])
        check("accounting:" + arm, ok,
              {k: a[k] for k in ("optimizer_updates",
                                 "sample_level_core_passes", "mean_depth")})

    # 4. no new trainable parameters in either arm
    check("no_new_trainable_matrices",
          all(v == 3 for v in summary["trainable_parameters_by_arm"].values()),
          summary["trainable_parameters_by_arm"])

    # 5. the panel must be unexamined material
    panel = summary["panel"]
    check("panel_fresh",
          panel["panel_item_count"] == 216
          and panel["examined_during_teaching"] is False,
          {k: panel[k] for k in ("panel_item_count",
                                 "examined_during_teaching")})

    # 6. the sweep payload must exist, parse, and agree with the summary
    sweep_path = artifacts / "depth_sweep.json"
    sweep = json.loads(sweep_path.read_bytes())
    s = summary["sweep_comparison"]
    inner = sweep.get("depth_sweep") or {}
    labels = sorted((inner.get("rows") or {}).keys())
    check("sweep_labels",
          labels == sorted(["R1", "R2", "R4", "R8", "RESET_8"]), labels)
    # The readout must not have moved a single weight while sweeping depth.
    check("sweep_weights_frozen",
          inner.get("weights_unchanged") is True
          and inner.get("parameter_digest_before")
          == inner.get("parameter_digest_after"),
          {"before": (inner.get("parameter_digest_before") or "")[:16],
           "after": (inner.get("parameter_digest_after") or "")[:16]})
    check("sweep_payload_agrees_with_summary",
          sweep.get("sweep_comparison", {}).get("net") == s["net"]
          and sweep.get("sweep_comparison", {}).get("baseline_correct")
          == s["baseline_correct"],
          {"payload_net": sweep.get("sweep_comparison", {}).get("net"),
           "summary_net": s["net"]})
    check("sweep_net_equals_gained_minus_lost",
          s["net"] == s["gained"] - s["lost"],
          {"net": s["net"], "gained": s["gained"], "lost": s["lost"]})
    check("per_depth_nets_consistent",
          all(v["net"] == v["gained_count"] - v["lost_count"]
              for v in s["per_depth"].values()),
          {k: v["net"] for k, v in s["per_depth"].items()})
    check("primary_is_R8", s["primary_label"] == "R8")
    check("reset_equals_one_pass", s["reset_matches_one_pass"] is True)
    check("weights_unchanged", s["weights_unchanged"] is True)

    out["direction"] = {
        "R1": s["baseline_correct"], "R8": s["primary_correct"], "net": s["net"],
        "verdict": "NEGATIVE" if s["net"] < 0 else ("POSITIVE" if s["net"] > 0
                                                    else "NULL"),
    }
    out["all_passed"] = not out["failed"]
    return out


def main():
    dirs = sorted(d for d in RECEIPTS.glob("receipt_cas-meta2-rdcjt-20260913*")
                  if (d / "curriculum_result.json").is_file())
    results = [verify(d) for d in dirs]
    print(json.dumps(results, indent=2, sort_keys=True))
    bad = [r["receipt"] for r in results if not r["all_passed"]]
    print()
    print("verified receipts:", len(results), "| with failures:", len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
