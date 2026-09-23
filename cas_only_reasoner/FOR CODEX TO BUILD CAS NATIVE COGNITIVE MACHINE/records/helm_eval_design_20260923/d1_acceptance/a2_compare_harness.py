"""D-1 acceptance test A2 (Claude): checker v2 must change NOTHING on records of 4 nodes or fewer.

For every record of the frozen course registry (564):
  - `derive_target(public, query)` of v2 equals the frozen checker's (the accepted-answer VALUES, canonical JSON)
For every saved prediction of the two historical studies (course_p00 and course_p10, 3 seeds each):
  - `check_answer(public, query, answer)["correct"]` of v2 equals the frozen checker's
It also records both profile digests (they must DIFFER -- A4) and the frozen files' LF hashes (A1).

    python -B a2_compare_harness.py --v2-module cas_meta2.typed_teaching.<v2 module> --out a2_result.json
          [--v2-package-root DIR]   # where v2's package lives, if not in this checkout (read-only)

Non-neural, local CPU. Expect > 30 minutes: the frozen course load alone is minutes, and 6,768 predictions are
re-checked twice. No model, no GPU, no network.
"""
import argparse
import hashlib
import importlib
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
FROZEN_FILES = ["research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + f for f in
                ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py")]
STUDIES = {"helm1_certified": ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")],
           "helm2_experimental": ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]}
PHASES = ("course_p00", "course_p10")


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-module", required=True)
    ap.add_argument("--v2-package-root", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.monotonic()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(PACKAGE / "research" / "CAS_META_2_COMPOSITION"))
    from cas_meta2.typed_teaching import pointer_contract as contract, checker as frozen
    if args.v2_package_root:
        sys.path.insert(0, str(pathlib.Path(args.v2_package_root) / "research" / "CAS_META_2_COMPOSITION"))
    v2 = importlib.import_module(args.v2_module)
    material = contract.load_material(PACKAGE)[0]
    packets = dict(contract.public_packets(material))
    result = {"schema": "claude.d1-a2-compare/0.1", "v2_module": args.v2_module,
              "frozen_files_sha256_lf": {f: lf_sha(PACKAGE / f) for f in FROZEN_FILES},
              "frozen_profile_digest": frozen.checker_profile()["profile_digest"],
              "v2_profile_digest": v2.checker_profile()["profile_digest"]}
    # The target body carries the checker profile (which MUST differ) and witnesses (a faster search may pick a
    # different first mapping); the answer SET is `admissible_answers`, and that is what must be identical.
    target_mismatch, witness_differences = [], 0
    for rid, pk in sorted(packets.items()):
        public, query = pk["source"], pk["record"]["query"]
        a = frozen.derive_target(public, query)
        b = v2.derive_target(public, query)
        if canon(a["admissible_answers"]) != canon(b["admissible_answers"]):
            target_mismatch.append(rid)
        witness_differences += canon(a["witnesses"]) != canon(b["witnesses"])
    result["targets_compared"] = len(packets)
    result["target_mismatches"] = target_mismatch
    result["witness_differences_reported_not_scored"] = witness_differences
    check_mismatch, checked = [], 0
    for study, receipts in STUDIES.items():
        for receipt in receipts:
            art = PACKAGE / "records/typed_pointer_001" / receipt / "collected/results/artifacts"
            for ph in PHASES:
                for p in json.loads((art / ("%s_predictions.json" % ph)).read_text(encoding="utf-8"))["predictions"]:
                    pk = packets[p["record_id"]]
                    a = frozen.check_answer(pk["source"], pk["record"]["query"], p["answer"])["correct"]
                    b = v2.check_answer(pk["source"], pk["record"]["query"], p["answer"])["correct"]
                    checked += 1
                    if a != b:
                        check_mismatch.append([study, receipt, ph, p["record_id"]])
    result["predictions_compared"] = checked
    result["check_mismatches"] = check_mismatch
    result["A2"] = "PASS" if not target_mismatch and not check_mismatch and checked == 6768 else "FAIL"
    result["A4_profiles_differ"] = result["frozen_profile_digest"] != result["v2_profile_digest"]
    result["seconds"] = time.monotonic() - t0
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps({k: result[k] for k in ("A2", "A4_profiles_differ", "targets_compared", "predictions_compared")}))


if __name__ == "__main__":
    main()
