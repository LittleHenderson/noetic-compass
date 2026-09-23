"""Read the AWS job's downloaded results (aws_probe_job/results/) against the rules fixed BEFORE the run.

Prints and writes RESULTS_READING.json:
  - the probe v0.2 verdict for all 9 unchanged Helm 2.0 models (predicted: FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT, delta0 0)
  - the self-test verdicts against PREREG_PROBE_SELF_TEST.md (POSITIVE -> PRESENT_GRAPH_AND_DOMAIN; NEGATIVE_UNIFORM ->
    ABSENT; NEGATIVE_COUPLED -> not PRESENT_*)
  - the T4 preservation digests for all 9 models, and seed 20260919 compared bit for bit with the RTX 4070 reference
  - the laptop's earlier probe readings beside the T4 ones (verdicts must agree)
Reads files only.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
PROBE = HERE.parent / "analogy_wiring_probe"
SEEDS = ("20260917", "20260918", "20260919")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main():
    out = {"schema": "claude.aws-probe-results-reading/0.1", "status_file": (RES / "STATUS").read_text().strip() if (RES / "STATUS").is_file() else None}
    probe = {}
    for s in SEEDS:
        d = load(RES / ("before_reading_v0_2_T4_seed%s.json" % s))
        probe[s] = None if d is None else {"complete": d.get("complete"), "results": [
            {"label": r["label"], "verdict": r["verdict"], "delta0": r["M0_delta0"], "M1z": r["M1z"], "M2z": r["M2z"],
             "max_M3z": r["summary"]["max_M3z"], "max_K": r["summary"]["max_K"]} for r in d["results"]]}
    out["probe_T4"] = probe
    rows = [r for s in SEEDS if probe[s] for r in probe[s]["results"]]
    out["probe_prediction_holds"] = (len(rows) == 9 and all(r["verdict"] == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
                                                           and r["delta0"] == 0.0 for r in rows))
    laptop = {}
    for s in ("20260917", "20260918"):
        d = load(PROBE / ("before_reading_v0_2_seed%s.json" % s))
        if d:
            laptop.update({r["label"]: r["verdict"] for r in d["results"]})
    out["laptop_vs_T4_verdicts_agree"] = all(r["verdict"] == laptop[r["label"]] for r in rows if r["label"] in laptop)
    out["laptop_models_compared"] = sorted(set(laptop) & {r["label"] for r in rows})
    st = load(RES / "probe_self_test_result_T4.json")
    if st:
        v = {k: st["results"][k]["verdict"] for k in st["results"]}
        exp = {"POSITIVE_COMPARISON": v.get("POSITIVE_COMPARISON") == "PRESENT_GRAPH_AND_DOMAIN",
               "NEGATIVE_UNIFORM": v.get("NEGATIVE_UNIFORM") == "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT",
               "NEGATIVE_COUPLED": v.get("NEGATIVE_COUPLED") not in ("PRESENT_GRAPH", "PRESENT_GRAPH_AND_DOMAIN")}
        out["self_test"] = {"verdicts": v, "expectation_met": exp, "all_met": all(exp.values()),
                            "summaries": {k: st["results"][k]["summary"] for k in st["results"]},
                            "pointer_learner_unchanged": len(set(st["pointer_learner_sha256_lf_before_after"])) == 1}
    pres = {}
    for s in SEEDS:
        d = load(RES / ("preservation_reference_20208c92_T4_seed%s.json" % s))
        pres[s] = None if d is None else {"complete": d.get("complete"), "digests": {r["label"]: r["overall_digest"] for r in d["results"]},
                                          "parameter_counts": sorted({r["parameter_count"] for r in d["results"]})}
    out["preservation_T4"] = pres
    local19 = load(PROBE / "preservation_reference_20208c92_seed20260919.json")
    if local19 and pres.get("20260919"):
        l = {r["label"]: r["overall_digest"] for r in local19["results"]}
        t = pres["20260919"]["digests"]
        out["cross_gpu_seed20260919"] = {k: {"rtx4070": l.get(k), "t4": t.get(k), "bit_identical": l.get(k) == t.get(k)} for k in sorted(t)}
    printed = {"h2_fresh_20260917": "8bce418f5ea641f0241f9cbfebdca30f1e3393b3beda8c98bb364454802b3749",
               "h2_initial_20260917": "0138af72c05a4e05ddbe6b03c049dad5afae7e47ec0fa69ead191b0e2103d975",
               "h2_fresh_20260918": "2e8dbaead32b6eb565fc80b24ee75c009122228ee8127c5f504ecc88f749fbd5",
               "h2_initial_20260918": "b5aae9c55f3d8a5798d0442199109ba4ce35414a0f2c496744999d85dbe6d84d"}
    allt4 = {k: v for s in SEEDS if pres[s] for k, v in pres[s]["digests"].items()}
    out["cross_gpu_printed_rtx4070"] = {k: {"rtx4070": v, "t4": allt4.get(k), "bit_identical": allt4.get(k) == v} for k, v in printed.items()}
    (HERE / "RESULTS_READING.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, sort_keys=True)[:6000])


if __name__ == "__main__":
    main()
