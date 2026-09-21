"""T01 -- the evaluator boundary. Rescore RAW PREDICTIONS with the run's own private checker, against an anchor
that lives OUTSIDE any receipt directory, and compare with what the frozen grader printed.

WHY. `evaluate_gates.py` (frozen, sha256 d3e0ea97...) reads the `correct` flags out of `course_p00_scoring.json`
and `course_p10_scoring.json` and prints the label from them. It never checks those two files against
anything. The independent audit of 2026-09-20 demonstrated the consequence: a hand-edited scoring file
produced `LEARNS_NEW_WORLDS` with `integrity: pass`. `verify_evidence_hashes.py` closes part of that gap
(byte agreement with the run's own manifest) but a run directory can be rewritten wholesale, manifest
included. This program closes the rest, in the way the directive's Q0 and the owner-side response ask:

  1. THE ANCHOR is a file outside every receipt: `trust_anchor_<study>.json`. It records the grader's
     identity, the private checker's identity (its profile digest and the sha256 of its source files), the
     frozen course digest, the frozen population (18 question ids with kind and world), the pass rule, and
     -- per seed -- the sha256 of the RAW PREDICTION files. It is written ONCE by `--write-anchor`, and the
     test pins the anchor's own sha256. Whoever rewrites a receipt cannot rewrite the anchor without
     failing the test.
  2. THE RESCORE ignores every `correct` flag on disk. For every raw prediction it calls
     `checker.check_answer(public, query, answer)` -- the same function the run used -- and compares the
     FULL `check_digest` of that fresh result to the scoring row the run stored. Any disagreement is a
     REJECT, not a warning.
  3. THE LABEL is re-derived from the fresh results with the frozen rule (b >= 7, c == 0, >= 2 kinds,
     >= 2 worlds, every seed) and COMPARED with the frozen grader's `gate_reading.json`. Agreement is
     recorded; disagreement is a finding.

REJECTS, typed (directive Q0 list): EVALUATOR_IDENTITY, CHECKER_IDENTITY, COURSE_IDENTITY, POPULATION_IDENTITY,
PREDICTIONS_IDENTITY (altered predictions, or the wrong phase/split file), DUPLICATE_IDS, MISSING_OR_EXTRA_PREDICTIONS,
MALFORMED_PREDICTION, NONFINITE_NUMBER, SCORING_FILE_DISAGREES_WITH_RESCORE (altered scores, with or without a
rewritten manifest -- the manifest is not consulted), FROZEN_GRADER_DISAGREES.

LIMIT, stated plainly: an anchor written by the same session that built the model is not independent
custody. The reading carries `custody: EVALUATION_NOT_INDEPENDENT` until a separate session holds the
final split. What this program DOES establish is that no one can move the label by editing a receipt.

Usage:
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --write-anchor      # once, reviewed
    python records/typed_pointer_001/trusted_rescore.py --study <study.json>                     # rescore + compare
    python records/typed_pointer_001/trusted_rescore.py --study <study.json> --receipt <seed>=<dir> ...   # override dirs (tests)
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[1]
sys.path.insert(0, str(PACKAGE / "research" / "CAS_META_2_COMPOSITION"))

SCHEMA = "cncm.trusted-rescore-reading/0.1"
PHASES = ("course_p00", "course_p10")
MIN_PASSING_B, MIN_IMPROVED_KINDS, MIN_IMPROVED_WORLDS = 7, 2, 2
GRADER = HERE / "evaluate_gates.py"
CHECKER_SOURCES = ("checker.py", "answers.py", "source.py")


def _lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# Every file hash here is LF-normalised: the receipts, anchors and readings are text files that git stores
# with LF while a Windows working copy may hold CRLF; a raw-byte pin would fire on a fresh checkout.


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _load_frozen_and_checker():
    from cas_meta2.typed_teaching import pointer_contract as contract, checker
    frozen = contract.load_material(PACKAGE)[0]
    packets = dict(contract.public_packets(frozen))
    population = contract.relational_population(frozen)
    kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
    world_of = {r["query"]["query_id"]: r["source_world_id"] for r in frozen["registry"]}
    record_ids = sorted(r["record_id"] for r in frozen["registry"])
    return frozen, packets, population, kind_of, world_of, record_ids, checker, contract


def checker_identity(checker):
    src_dir = PACKAGE / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching"
    return {"profile_digest": checker.checker_profile()["profile_digest"],
            "sources": {name: _lf_sha(src_dir / name) for name in CHECKER_SOURCES if (src_dir / name).is_file()}}


def _count(value):
    """A transition count as the frozen grader may store it: an int, or a list of keys, or absent (None)."""
    if value is None:
        return None
    return len(value) if isinstance(value, (list, dict)) else int(value)


def _has_nonfinite(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_nonfinite(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_nonfinite(v) for v in value)
    return False


# ---------------------------------------------------------------------------------------------
def write_anchor(study_path, anchor_path, receipt_override, material=None):
    # `material` lets a test suite load the frozen course and the checker ONCE (the load re-validates every
    # public world for all 564 packets and takes minutes); the CLI always loads fresh.
    frozen, packets, population, kind_of, world_of, record_ids, checker, contract = material or _load_frozen_and_checker()
    study = json.loads(pathlib.Path(study_path).read_text(encoding="utf-8"))
    seeds = {}
    for job in study["jobs"]:
        seed = str(job["model_seed"])
        rdir = pathlib.Path(receipt_override.get(seed, job["receipt_dir"]))
        art = rdir / "collected/results/artifacts"
        seeds[seed] = {"receipt_dir_at_anchor_time": str(rdir),
                       "predictions_sha256_lf": {ph: _lf_sha(art / ("%s_predictions.json" % ph)) for ph in PHASES}}
    anchor = {
        "schema": "cncm.trusted-rescore-anchor/0.1", "written": "2026-09-21",
        "study_path": str(study_path), "study_sha256_lf": _lf_sha(study_path),
        "grader": {"path": "records/typed_pointer_001/evaluate_gates.py", "sha256_lf": _lf_sha(GRADER)},
        "checker": checker_identity(checker),
        "course_digest": frozen["course_digest"],
        "population": {"digest": population["digest"], "question_ids": population["question_ids"],
                       "kind_of": {q: kind_of[q] for q in population["question_ids"]},
                       "world_of": {q: world_of[q] for q in population["question_ids"]}},
        "pass_rule": {"min_passing_b": MIN_PASSING_B, "min_improved_kinds": MIN_IMPROVED_KINDS, "min_improved_worlds": MIN_IMPROVED_WORLDS,
                      "broken_must_be": 0, "all_seeds_must_pass": True},
        "expected_record_ids_sha256": hashlib.sha256(_canon(record_ids)).hexdigest(), "expected_record_count": len(record_ids),
        "seeds": seeds,
        "custody": "EVALUATION_NOT_INDEPENDENT -- written by the session that also built the model and the lab",
    }
    with open(anchor_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(anchor, indent=1, sort_keys=True))
    print("anchor written: %s  sha256_lf %s" % (anchor_path, _lf_sha(anchor_path)[:16]))
    return 0


# ---------------------------------------------------------------------------------------------
def rescore(study_path, anchor_path, receipt_override, out_path, material=None, frozen_reading=None):
    reasons = []
    frozen, packets, population, kind_of, world_of, record_ids, checker, contract = material or _load_frozen_and_checker()
    anchor = json.loads(pathlib.Path(anchor_path).read_text(encoding="utf-8"))
    # 1. identities, against the anchor
    if _lf_sha(GRADER) != anchor["grader"]["sha256_lf"]:
        reasons.append("EVALUATOR_IDENTITY:grader sha256 %s != anchored %s" % (_lf_sha(GRADER)[:12], anchor["grader"]["sha256_lf"][:12]))
    ident = checker_identity(checker)
    if ident != anchor["checker"]:
        reasons.append("CHECKER_IDENTITY:checker profile or sources differ from the anchor")
    if frozen["course_digest"] != anchor["course_digest"]:
        reasons.append("COURSE_IDENTITY:%s != %s" % (frozen["course_digest"][:12], anchor["course_digest"][:12]))
    if population["digest"] != anchor["population"]["digest"] or population["question_ids"] != anchor["population"]["question_ids"]:
        reasons.append("POPULATION_IDENTITY:the relational population does not match the anchor")
    expected_ids = set(record_ids)
    study = json.loads(pathlib.Path(study_path).read_text(encoding="utf-8"))
    pop = anchor["population"]["question_ids"]

    per_seed = {}
    for job in study["jobs"]:
        seed = str(job["model_seed"])
        rdir = pathlib.Path(receipt_override.get(seed, job["receipt_dir"]))
        art = rdir / "collected/results/artifacts"
        seed_report = {"receipt_dir": str(rdir), "phases": {}}
        question_correct = {}
        for ph in PHASES:
            ppath, spath = art / ("%s_predictions.json" % ph), art / ("%s_scoring.json" % ph)
            entry = {"predictions_sha256_lf": None, "rescored": 0, "scoring_rows_compared": 0, "disagreements": 0}
            if not ppath.is_file():
                reasons.append("MISSING_OR_EXTRA_PREDICTIONS:%s:%s:file absent" % (seed, ph))
                seed_report["phases"][ph] = entry
                continue
            entry["predictions_sha256_lf"] = _lf_sha(ppath)
            if entry["predictions_sha256_lf"] != anchor["seeds"].get(seed, {}).get("predictions_sha256_lf", {}).get(ph):
                reasons.append("PREDICTIONS_IDENTITY:%s:%s:raw predictions differ from the anchor (altered, or the wrong phase/split file)" % (seed, ph))
            try:
                preds = json.loads(ppath.read_text(encoding="utf-8"))["predictions"]
            except Exception as error:
                reasons.append("MALFORMED_PREDICTION:%s:%s:%s" % (seed, ph, type(error).__name__))
                seed_report["phases"][ph] = entry
                continue
            ids = [p.get("record_id") for p in preds]
            if len(ids) != len(set(ids)):
                reasons.append("DUPLICATE_IDS:%s:%s:%d duplicate record ids" % (seed, ph, len(ids) - len(set(ids))))
            if set(ids) != expected_ids:
                reasons.append("MISSING_OR_EXTRA_PREDICTIONS:%s:%s:missing %d, extra %d" % (seed, ph, len(expected_ids - set(ids)), len(set(ids) - expected_ids)))
            stored = {}
            if spath.is_file():
                try:
                    stored = {r["prediction_id"]: r for r in json.loads(spath.read_text(encoding="utf-8"))["rows"]}
                except Exception as error:
                    reasons.append("MALFORMED_PREDICTION:%s:%s:scoring file unreadable %s" % (seed, ph, type(error).__name__))
            fresh_by_query = collections.defaultdict(list)
            for p in preds:
                if _has_nonfinite(p):
                    reasons.append("NONFINITE_NUMBER:%s:%s:%s" % (seed, ph, str(p.get("record_id"))[:30]))
                    continue
                rid = p.get("record_id")
                if rid not in packets:
                    continue
                try:
                    row = checker.check_answer(packets[rid]["source"], packets[rid]["record"]["query"], p["answer"])
                except Exception as error:
                    reasons.append("MALFORMED_PREDICTION:%s:%s:%s:%s" % (seed, ph, str(rid)[:30], type(error).__name__))
                    continue
                entry["rescored"] += 1
                fresh_by_query[row["query_id"]].append(row["correct"])
                s = stored.get(p.get("prediction_id"))
                if s is not None:
                    entry["scoring_rows_compared"] += 1
                    if s.get("check_digest") != row["check_digest"] or bool(s.get("correct")) != row["correct"]:
                        entry["disagreements"] += 1
            if entry["disagreements"]:
                reasons.append("SCORING_FILE_DISAGREES_WITH_RESCORE:%s:%s:%d rows" % (seed, ph, entry["disagreements"]))
            question_correct[ph] = {q: (len(v) > 0 and all(v)) for q, v in fresh_by_query.items()}
            seed_report["phases"][ph] = entry
        # 3. the label, re-derived from the FRESH results only
        before, after = question_correct.get("course_p00", {}), question_correct.get("course_p10", {})
        gained = [q for q in pop if not before.get(q, False) and after.get(q, False)]
        lost = [q for q in pop if before.get(q, False) and not after.get(q, False)]
        kinds = sorted({anchor["population"]["kind_of"][q] for q in gained})
        worlds = sorted({anchor["population"]["world_of"][q] for q in gained})
        passed = (len(gained) >= MIN_PASSING_B and len(lost) == 0 and len(kinds) >= MIN_IMPROVED_KINDS and len(worlds) >= MIN_IMPROVED_WORLDS)
        seed_report.update({"frozen_18_before": sum(1 for q in pop if before.get(q, False)), "frozen_18_after": sum(1 for q in pop if after.get(q, False)),
                            "gained": len(gained), "broken": len(lost), "kinds_improved": kinds, "worlds_improved": len(worlds), "passed": passed})
        per_seed[seed] = seed_report

    complete = bool(per_seed) and all(s["phases"].get(ph, {}).get("rescored", 0) == len(expected_ids) for s in per_seed.values() for ph in PHASES)
    label = ("LEARNS_NEW_WORLDS" if complete and all(s["passed"] for s in per_seed.values()) else "NO_TRANSFER_TO_NEW_WORLDS") if not reasons else "VOID_REJECTED"
    # 4. compare with the frozen grader's reading, if present beside the study
    # default: the frozen grader's reading beside the study; the certified 1.0 study keeps its reading in a
    # sibling folder (admission_helm1_certified/), so the CLI takes --frozen-reading for that case
    frozen_reading = pathlib.Path(frozen_reading) if frozen_reading else pathlib.Path(study_path).parent / "gate_reading.json"
    comparison = {"frozen_reading_present": frozen_reading.is_file(), "frozen_reading_path": str(frozen_reading)}
    if frozen_reading.is_file():
        g = json.loads(frozen_reading.read_text(encoding="utf-8"))
        comparison["frozen_label"] = g.get("label")
        comparison["labels_agree"] = (g.get("label") == label) if label != "VOID_REJECTED" else None
        per = {}
        for seed, s in per_seed.items():
            gs = (g.get("seeds") or {}).get(seed, {}).get("G_LEARN_population", {})
            # the frozen grader stores the transitions as wrong_to_right / right_to_wrong (a count, or the list of keys)
            fb, fc = (_count(gs.get("wrong_to_right")), _count(gs.get("right_to_wrong")))
            per[seed] = {"rescored_gained_broken": [s["gained"], s["broken"]], "frozen_gained_broken": [fb, fc],
                         "agree": fb == s["gained"] and fc == s["broken"]}
        comparison["per_seed"] = per
        if label != "VOID_REJECTED" and (not comparison["labels_agree"] or not all(v["agree"] for v in per.values())):
            reasons.append("FROZEN_GRADER_DISAGREES:label or per-seed counts differ between the fresh rescore and gate_reading.json")
            label = "VOID_REJECTED"
    reading = {"schema": SCHEMA, "verdict": "REJECT" if reasons else "RESCORE_OK", "label_rederived": label, "reject_reasons": reasons,
               "anchor": {"path": str(anchor_path), "sha256_lf": _lf_sha(anchor_path)}, "grader_sha256_lf": _lf_sha(GRADER),
               "checker": ident, "course_digest": frozen["course_digest"], "population_digest": population["digest"],
               "per_seed": per_seed, "comparison_with_frozen_grader": comparison, "custody": anchor.get("custody"),
               "boundary": "the scoring files' correct flags were NOT read for the label; every prediction was rechecked with the private checker"}
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(reading, indent=1, sort_keys=True))
    print(json.dumps({k: reading[k] for k in ("verdict", "label_rederived", "reject_reasons")}, indent=1))
    for seed, s in per_seed.items():
        print("  seed %s: frozen18 %s -> %s, gained %d broken %d, rescored %s, disagreements %s" % (
            seed, s["frozen_18_before"], s["frozen_18_after"], s["gained"], s["broken"],
            [s["phases"][ph]["rescored"] for ph in PHASES], [s["phases"][ph]["disagreements"] for ph in PHASES]))
    print("  frozen grader:", comparison)
    return 0 if not reasons else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True)
    parser.add_argument("--anchor", default=None)
    parser.add_argument("--write-anchor", action="store_true")
    parser.add_argument("--receipt", action="append", default=[], help="seed=dir override (tests)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--frozen-reading", default=None, help="gate_reading.json to compare against (default: beside the study)")
    args = parser.parse_args()
    study = pathlib.Path(args.study)
    anchor = pathlib.Path(args.anchor) if args.anchor else HERE / ("trust_anchor_%s.json" % study.parent.name)
    override = dict(r.split("=", 1) for r in args.receipt)
    if args.write_anchor:
        return write_anchor(study, anchor, override)
    return rescore(study, anchor, override, args.out, frozen_reading=args.frozen_reading)


if __name__ == "__main__":
    sys.exit(main())
