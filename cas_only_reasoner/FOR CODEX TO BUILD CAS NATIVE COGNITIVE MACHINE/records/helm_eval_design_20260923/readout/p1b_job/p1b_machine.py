"""P1b machine helper. It runs ON the AWS g7.2xlarge machine only. CLAUDE_BUILT_CLAUDE_CHECKED. WRITTEN, NOT RUN ON AWS YET.

Standard library only at import. `preflight` imports torch through the reader's own module
(`recompute_reproduction_evidence.setup`) and is covered on the laptop only through its pure arithmetic (`project`,
`timed_indices`); its first real run is on AWS. `anchors` and `decide` are pure Python.

    python -B p1b_machine.py anchors --root PKG
    CAS_META2_RUN_TEACHING_CYCLE=1 python -B p1b_machine.py preflight --mode acceptance|reading --reader-dir RD \\
        --package-root /opt/cas-graph6curr/package --package-archive ZIP --reference-checkpoint PT \\
        --reference-record JSON --panel-manifest JSON --job-start EPOCH --out OUT/preflight.json
    python -B p1b_machine.py decide --mode acceptance|reading --reader-dir RD --out OUT --expected-tests N \\
        --reader-digest HEX [--candidate-sha256 HEX]

TIMING PREFLIGHT (plan item 8). After the reader's tests and before the long run, it repeats the reader's own setup
(package check, course load), restores the pinned Helm 2.0 final.pt through the pinned historical loader, and times
the prediction plus historical grading of 2 warm-up and 24 spread-out panel records. It projects the rest of the job
from those measurements and REFUSES (exit 5, PREFLIGHT_OVER_WALL_LIMIT) when the projected end, counted from the
job's start, is past 55 minutes. That leaves the upload and the power-off inside the 60-minute session. It also
refuses (exit 6) when the recorded environment is not the pinned numerical environment, so no paid panel work runs
on the wrong machine, and for the reading run the one-shot evidence file is never written there.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import time

SESSION_MINUTES = 60
PREFLIGHT_LIMIT_SECONDS = 55 * 60          # projected end of the work, from JOB START; the rest is upload + power-off
SAFETY = 1.2                               # on the projected panel time only
RESERVE_SECONDS = 180                      # variant files, state hashing, evidence writing, results upload
WARMUP_RECORDS, TIMED_RECORDS = 2, 24
# Work the recompute module does after the preflight (recompute_reproduction_evidence.py, revision 4):
#   acceptance: full 564-record panels for the reference and the 5 variants the loader restores (missing_key and
#               dtype_change are refused at restore; the corrupt reference fails its sha256 before loading);
#               8 restores (reference + 7 variants).  reading: 2 panels, 2 restores.  Setup runs once more.
PANELS = {"acceptance": 6, "reading": 2}
RESTORES = {"acceptance": 8, "reading": 2}
SETUPS = 1
EXIT_OK, EXIT_OVER_LIMIT, EXIT_ENVIRONMENT, EXIT_FAULT = 0, 5, 6, 7
READER_SOURCE_FILES = ("read_reproduction.py", "repro_common.py", "recompute_reproduction_evidence.py",
                       "historical_refusal_allowlist.json")
RESULT_SCHEMA = "claude.p1b-job-result/0.1"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    """repro_common.canonical: the reader's own canonical JSON form (for the reader-source digest)."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            + "\n").encode("utf-8")


def reader_hashes(folder):
    folder = pathlib.Path(folder)
    return {name: sha256((folder / name).read_bytes()) for name in READER_SOURCE_FILES}


def reader_digest(hashes):
    """repro_common.reader_source_digest: ONE sha256 over the canonical {file: sha256} of the reader sources."""
    return sha256(canonical(hashes))


# ---- anchors -------------------------------------------------------------------------------------------------------
def check_anchors(root):
    """0 when every file under `root` (except anchors.json) is listed in anchors.json with its sha256, and every listed
    file exists; 1 otherwise. Prints each problem."""
    root = pathlib.Path(root)
    listed = json.loads((root / "anchors.json").read_text(encoding="utf-8"))["files"]
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} - {"anchors.json"}
    problems = ["UNLISTED:" + name for name in sorted(present - set(listed))]
    problems += ["MISSING:" + name for name in sorted(set(listed) - present)]
    problems += ["CHANGED:" + name for name in sorted(present & set(listed))
                 if sha256((root / name).read_bytes()) != listed[name]["sha256"]]
    for problem in problems:
        print("ANCHOR_PROBLEM " + problem)
    print("ANCHORS: %s (%d files)" % ("PASS" if not problems else "FAIL", len(present)))
    return 0 if not problems else 1


# ---- the timing preflight --------------------------------------------------------------------------------------------
def timed_indices(n):
    """Panel positions timed by the preflight: the first WARMUP_RECORDS, then TIMED_RECORDS spread over the rest."""
    if n <= WARMUP_RECORDS + TIMED_RECORDS:
        return list(range(n))
    step = (n - WARMUP_RECORDS) / float(TIMED_RECORDS)
    return list(range(WARMUP_RECORDS)) + [WARMUP_RECORDS + int(i * step) for i in range(TIMED_RECORDS)]


def project(mode, *, elapsed_seconds, setup_seconds, restore_seconds, warmup_seconds, per_record_seconds, records):
    """The projected end of the job's work, in seconds from JOB START. Pure."""
    panel = warmup_seconds + max(records - WARMUP_RECORDS, 0) * per_record_seconds
    remaining = (SETUPS * setup_seconds + RESTORES[mode] * restore_seconds + PANELS[mode] * panel * SAFETY
                 + RESERVE_SECONDS)
    total = elapsed_seconds + remaining
    return {"mode": mode, "elapsed_seconds_at_preflight_end": round(elapsed_seconds, 1),
            "measured": {"setup_seconds": round(setup_seconds, 2), "restore_seconds": round(restore_seconds, 2),
                         "warmup_seconds_for_%d_records" % WARMUP_RECORDS: round(warmup_seconds, 3),
                         "per_record_seconds": round(per_record_seconds, 4), "panel_records": records},
            "formula": "elapsed + %d*setup + %d*restore + %d*(warmup + (records-%d)*per_record)*%.2f + %d"
                       % (SETUPS, RESTORES[mode], PANELS[mode], WARMUP_RECORDS, SAFETY, RESERVE_SECONDS),
            "projected_panel_seconds": round(panel, 1), "projected_remaining_seconds": round(remaining, 1),
            "projected_total_seconds": round(total, 1), "limit_seconds": PREFLIGHT_LIMIT_SECONDS,
            "session_minutes": SESSION_MINUTES, "fits": total <= PREFLIGHT_LIMIT_SECONDS}


def preflight(args):
    """AWS ONLY (torch). Exit 0 fits, 5 over the limit, 6 environment not pinned, 7 a fault in the preflight itself."""
    started_wall = time.time()
    sys.path.insert(0, str(pathlib.Path(args.reader_dir).resolve()))
    record = {"schema": "claude.p1b-preflight/0.1", "mode": args.mode, "label": "CLAUDE_BUILT_CLAUDE_CHECKED"}
    out = pathlib.Path(args.out)
    try:
        import recompute_reproduction_evidence as recompute       # its own GPU_REQUIRED checks run inside setup()
        import repro_common as common
        begin = time.monotonic()
        ctx, recorded, _, _, _ = recompute.setup(args)
        setup_seconds = time.monotonic() - begin
        record["environment"] = recorded
        record["environment_violations"] = common.environment_violations(recorded)
        if record["environment_violations"]:
            record["verdict"] = "PREFLIGHT_ENVIRONMENT_NOT_PINNED"
            out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"verdict": record["verdict"], "violations": record["environment_violations"]}))
            return EXIT_ENVIRONMENT
        torch, h = ctx.torch, ctx.h
        import io
        raw = pathlib.Path(args.reference_checkpoint).read_bytes()
        if sha256(raw) != common.REFERENCE_FINAL_PT_SHA256:
            raise RuntimeError("REFERENCE_IS_NOT_THE_PINNED_ONE")
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        run_identity_digest = payload["metadata"]["run_identity_digest"]
        del payload, raw
        begin = time.monotonic()
        encoder = h.encoder.build_frozen_typed_encoder(torch, ctx.tokenizer, seed=h.contract.ENCODER_SEED, d_model=64,
                                                       device=ctx.device)
        learner = h.pointer_learner.PointerCourseLearner.restore_checkpoint(
            torch, h.matched._framework(torch, ctx.device, common.MODEL_SEED), encoder,
            path=pathlib.Path(args.reference_checkpoint), expected_sha256=common.REFERENCE_FINAL_PT_SHA256,
            expected_run_identity_digest=run_identity_digest, device=ctx.device)
        restore_seconds = time.monotonic() - begin
        timings = []
        for index in timed_indices(len(ctx.record_ids)):
            record_id = ctx.record_ids[index]
            packet = ctx.packets[record_id]
            begin = time.monotonic()
            try:                                   # timing only: a historical refusal or grader error is still timed
                prediction = learner.predict(packet, common.PREDICTION_DEPTH)
                h.checker.check_answer(packet["source"], packet["record"]["query"], prediction["answer"])
            except Exception:                      # noqa: BLE001
                pass
            torch.cuda.synchronize()
            timings.append(time.monotonic() - begin)
        warmup = sum(timings[:WARMUP_RECORDS])
        timed = timings[WARMUP_RECORDS:] or timings
        per_record = sum(timed) / len(timed)
        record["timed_positions"] = timed_indices(len(ctx.record_ids))
        record["timings_seconds"] = [round(t, 4) for t in timings]
        elapsed = time.time() - float(args.job_start)
        record["projection"] = project(args.mode, elapsed_seconds=elapsed, setup_seconds=setup_seconds,
                                       restore_seconds=restore_seconds, warmup_seconds=warmup,
                                       per_record_seconds=per_record, records=len(ctx.record_ids))
        record["verdict"] = "PREFLIGHT_FITS" if record["projection"]["fits"] else "PREFLIGHT_OVER_WALL_LIMIT"
    except SystemExit as stop:                     # the reader's own named stops (GPU_REQUIRED..., PACKAGE_...)
        record.update(verdict="PREFLIGHT_FAULT", fault="SystemExit:" + str(stop.code)[:600])
    except Exception as error:                     # noqa: BLE001
        record.update(verdict="PREFLIGHT_FAULT", fault=type(error).__name__ + ":" + str(error)[:600])
    record["preflight_wall_seconds"] = round(time.time() - started_wall, 1)
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: record.get(k) for k in ("verdict", "projection", "fault")}, sort_keys=True))
    return {"PREFLIGHT_FITS": EXIT_OK, "PREFLIGHT_OVER_WALL_LIMIT": EXIT_OVER_LIMIT}.get(record["verdict"], EXIT_FAULT)


# ---- decide ----------------------------------------------------------------------------------------------------------
def parse_unittest_log(text):
    """Counts from `python -B test_unchanged_repro.py -v` output (unittest's own summary lines)."""
    ran = re.findall(r"^Ran (\d+) tests? in ", text, re.MULTILINE)
    tail = re.findall(r"^(OK|FAILED)(?: \(([^)]*)\))?\s*$", text, re.MULTILINE)
    counts = {"ran": int(ran[-1]) if ran else None, "ok": bool(tail) and tail[-1][0] == "OK",
              "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0}
    if tail:
        for item in (tail[-1][1] or "").split(","):          # e.g. "failures=1, expected failures=2, skipped=3"
            key, _, value = item.strip().partition("=")
            if value.isdigit():
                counts[key.strip().replace(" ", "_")] = int(value)
    counts["skipped_tests"] = re.findall(r"^(test\w+) \(.*\) \.\.\. skipped (.*)$", text, re.MULTILINE)[:200]
    return counts


def exit_codes(out):
    codes = {}
    for path in sorted(pathlib.Path(out).glob("EXIT_*")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                codes[key.strip()] = value.strip()
    return codes


def load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def decide(mode, out, reader_dir, expected_tests, expected_reader_digest, candidate_sha256=None):
    """Writes OUT/P1B_JOB_RESULT.json. 0 only when every expectation of this mode holds. It never gives the
    reproduction verdict: that is read on the laptop, by read_reproduction.py, from the committed evidence."""
    out, problems = pathlib.Path(out), []
    codes = exit_codes(out)
    result = {"schema": RESULT_SCHEMA, "mode": mode, "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "exit_codes": codes}
    hashes = reader_hashes(reader_dir)
    result["reader_source_sha256_on_machine"] = reader_digest(hashes)
    if result["reader_source_sha256_on_machine"] != expected_reader_digest:
        problems.append("READER_DIGEST_IS_NOT_THE_BUNDLED_ONE")
    preflight_record = load_json(out / "preflight.json") or {}
    result["preflight"] = {"verdict": preflight_record.get("verdict"),
                           "projection": preflight_record.get("projection")}
    if codes.get("preflight") != "0" or preflight_record.get("verdict") != "PREFLIGHT_FITS":
        problems.append("PREFLIGHT_NOT_PASSED")
    if codes.get("recompute") != "0":
        problems.append("RECOMPUTE_EXIT:%s" % codes.get("recompute"))
    if mode == "acceptance":
        log = out / "stage0_tests.log"
        counts = parse_unittest_log(log.read_text(encoding="utf-8", errors="replace")) if log.is_file() else {}
        result["stage0"] = dict(counts, expected_tests=expected_tests)
        if codes.get("stage0") != "0" or not counts.get("ok") or counts.get("failures") or counts.get("errors"):
            problems.append("STAGE0_TESTS_NOT_PASSED")
        if counts.get("ran") != expected_tests:
            problems.append("STAGE0_TEST_COUNT:%s!=%s" % (counts.get("ran"), expected_tests))
        receipt_path = out / "reader_acceptance_receipt.json"
        receipt = load_json(receipt_path)
        sys.path.insert(0, str(pathlib.Path(reader_dir).resolve()))
        import repro_common as common                  # torch-free; the frozen table lives here (fix 7)
        if not isinstance(receipt, dict):
            problems.append("ACCEPTANCE_RECEIPT_MISSING_OR_UNREADABLE")
        else:
            cases = receipt.get("cases") if isinstance(receipt.get("cases"), list) else []
            names = [case.get("case") if isinstance(case, dict) else None for case in cases]
            violations = {str(name): common.acceptance_case_violations(case) for name, case in zip(names, cases)}
            result["acceptance"] = {
                "receipt_sha256": sha256(receipt_path.read_bytes()), "status": receipt.get("status"),
                "case_order": names, "producer_pass": {str(n): (c.get("pass") if isinstance(c, dict) else None)
                                                       for n, c in zip(names, cases)},
                "independent_case_violations": {k: v for k, v in violations.items() if v},
                "environment_violations": receipt.get("environment_violations")}
            if receipt.get("schema") != common.ACCEPTANCE_SCHEMA:
                problems.append("ACCEPTANCE_SCHEMA")
            if receipt.get("status") != common.ACCEPTANCE_PASS:
                problems.append("ACCEPTANCE_STATUS:%s" % receipt.get("status"))
            if names != list(common.ACCEPTANCE_CASES) or receipt.get("registered_cases") != list(common.ACCEPTANCE_CASES):
                problems.append("ACCEPTANCE_CASES_NOT_THE_REGISTERED_ELEVEN_IN_ORDER")
            problems += ["CASE:%s:%s" % (k, "|".join(v)[:200]) for k, v in sorted(violations.items()) if v]
            if receipt.get("environment_violations") != []:
                problems.append("ACCEPTANCE_ENVIRONMENT_VIOLATIONS")
            producer = receipt.get("producer") if isinstance(receipt.get("producer"), dict) else {}
            if producer.get("reader_source_sha256") != expected_reader_digest:
                problems.append("ACCEPTANCE_RAN_ANOTHER_READER")
        result["overall"] = "P1B_ACCEPTANCE_RUN_PASS" if not problems else "P1B_ACCEPTANCE_RUN_FAILED"
    else:
        evidence_path = out / "reproduction_evidence.json"
        evidence = load_json(evidence_path)
        if not isinstance(evidence, dict):
            problems.append("EVIDENCE_MISSING_OR_UNREADABLE")
        else:
            producer = evidence.get("producer") if isinstance(evidence.get("producer"), dict) else {}
            candidate = (evidence.get("inputs") or {}).get("candidate") or {}
            result["evidence"] = {"sha256": sha256(evidence_path.read_bytes()), "bytes": evidence_path.stat().st_size,
                                  "mode": evidence.get("mode"),
                                  "producer_invalid_reason_count": len(evidence.get("producer_invalid_reasons") or [])}
            if evidence.get("mode") != "READING":
                problems.append("EVIDENCE_MODE:%s" % evidence.get("mode"))
            if producer.get("reader_source_sha256") != expected_reader_digest:
                problems.append("EVIDENCE_FROM_ANOTHER_READER")
            if candidate.get("sha256") != candidate_sha256:
                problems.append("EVIDENCE_CANDIDATE_IS_NOT_THE_BOUND_U17_FINAL_PT")
        result["overall"] = "P1B_READING_EVIDENCE_WRITTEN" if not problems else "P1B_READING_RUN_FAILED"
        result["verdict_note"] = ("No verdict here. Commit reproduction_evidence.json ONCE, then run "
                                  "read_reproduction.py on the laptop at the receipt commit.")
    result["problems"] = problems
    (out / "P1B_JOB_RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"overall": result["overall"], "problems": problems}, sort_keys=True))
    return 0 if not problems else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("anchors")
    a.add_argument("--root", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--mode", choices=sorted(PANELS), required=True)
    for name in ("--reader-dir", "--package-root", "--package-archive", "--reference-checkpoint",
                 "--reference-record", "--panel-manifest", "--job-start", "--out"):
        p.add_argument(name, required=True)
    d = sub.add_parser("decide")
    d.add_argument("--mode", choices=sorted(PANELS), required=True)
    d.add_argument("--reader-dir", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--expected-tests", type=int, required=True)
    d.add_argument("--reader-digest", required=True)
    d.add_argument("--candidate-sha256", default=None)
    args = parser.parse_args(argv)
    if args.command == "anchors":
        return check_anchors(args.root)
    if args.command == "preflight":
        return preflight(args)
    return decide(args.mode, args.out, args.reader_dir, args.expected_tests, args.reader_digest, args.candidate_sha256)


if __name__ == "__main__":
    sys.exit(main())
