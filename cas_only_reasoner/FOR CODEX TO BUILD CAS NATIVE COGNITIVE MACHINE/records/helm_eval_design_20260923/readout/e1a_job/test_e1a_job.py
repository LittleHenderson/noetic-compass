"""Tests for the E1a job folder (readout plan item 9). CLAUDE_BUILT_CLAUDE_CHECKED.

THE STATED ACCEPTANCE CHECK: a laptop dry run with NO AWS call builds the bundle, passes the custody filters and
refuses without the study receipts; the stage script passes `bash -n`. Plus the pure parts the machine and the laptop
reader use, with stand-ins. No torch, no course load, no model. Every launcher subprocess runs with `boto3` and
`botocore` replaced by modules that raise on import, so any AWS call attempt fails loudly. Each dry run streams about
40 MB of git objects into a bundle in a temp folder outside every git tree.

    python -m pytest test_e1a_job.py -q -p no:cacheprovider
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
PROBE = HERE.parent / "probe-v03"
sys.path.insert(0, str(HERE))
import e1a_machine as MACH  # noqa: E402
import launch as L  # noqa: E402
import read_results as RR  # noqa: E402

REPAIRED_FREEZE = "afccbcb98bb36bbea953f6918b3fe0c62429495e"    # repaired study c0d65ce8 frozen; receipts not yet committed
UNCHANGED_FREEZE = "3344ae5d7bcc0d5ff50f1bce220f77a063ece65a"   # unchanged study 60140ae0 frozen; U17 receipt not yet committed
HELM2_COMMIT = "c8d5c430eec23a8fadd98bbcd045fecf03d86239"       # Helm 2.0 receipt_20260917: the full-run layout
BASH = shutil.which("bash")


@pytest.fixture(scope="module")
def no_aws(tmp_path_factory):
    root = tmp_path_factory.mktemp("no_aws")
    for name in ("boto3", "botocore"):
        (root / name).mkdir()
        (root / name / "__init__.py").write_text("raise RuntimeError('AWS_CALL_ATTEMPTED: %s was imported')\n" % name)
    return dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")


def run_launch(env, *args, timeout=600):
    return subprocess.run([sys.executable, "-B", str(HERE / "launch.py"), *args], capture_output=True, text=True,
                          env=env, timeout=timeout)


def bash_n(path):
    done = subprocess.run([BASH, "-n", str(path)], capture_output=True, text=True, timeout=60)
    return done.returncode, done.stderr


# ================================================================ THE ACCEPTANCE CHECK
def test_dry_run_builds_the_bundle_passes_custody_and_refuses_without_the_study_receipts(no_aws, tmp_path):
    folder = tmp_path / "bundle"
    proc = run_launch(no_aws, "--dry-run", "--repaired-commit", REPAIRED_FREEZE, "--unchanged-commit", UNCHANGED_FREEZE,
                      "--bundle-dir", str(folder))
    out = proc.stdout
    print(out[-5000:])
    assert "AWS_CALL_ATTEMPTED" not in out + proc.stderr
    assert proc.returncode == 2, out[-3000:] + proc.stderr[-3000:]
    for words in ("CUSTODY: PASS", "PINS: PASS", "PLAN (E1a", "COST CAP", "cap $2.00", "$0.10 allowance",
                  "retries   none", "g7.*", "g4dn.*", "DRY RUN: nothing uploaded, nothing launched, no AWS call",
                  "LAUNCH_REFUSED: STUDY_RECEIPTS_MISSING", "receipt_analogy_on_20260917", "receipt_analogy_on_20260918",
                  "receipt_analogy_on_20260919", "receipt_unchanged_repro_20260917",
                  "probe v0.3 acceptance record: NOT GIVEN"):
        assert words in out, words
    record = json.loads((folder / "dry_run_record.json").read_text(encoding="utf-8"))
    assert record["dry_run"] is True and record["aws_calls"] == [] and record["launchable"] is False
    assert len(record["receipts_missing"]) == 4
    assert record["worst_case_usd_at_client_deadline"] <= L.COST_CAP_USD == record["cost_cap_usd"] == 2.00
    assert record["allowance_usd"] == 0.10 and record["commits"] == {"repaired": REPAIRED_FREEZE, "unchanged": UNCHANGED_FREEZE}
    digest = hashlib.sha256()
    with open(folder / "bundle.tar.gz", "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    assert digest.hexdigest() == record["bundle_sha256"] and record["bundle_sha256"] in out
    names, anchors, spec = [], None, None
    with tarfile.open(folder / "bundle.tar.gz", mode="r|gz") as tar:         # one streaming pass
        for member in tar:
            names.append(member.name)
            if member.name == "anchors.json":
                anchors = json.loads(tar.extractfile(member).read())
            elif member.name == "claude/e1a_spec.json":
                spec = json.loads(tar.extractfile(member).read())
    assert L.custody_refusals(names) == []
    assert names[-1] == "anchors.json" and sorted(anchors["files"]) == sorted(names[:-1]) and len(names) == record["files"]
    tree = {n[len("tree/"):] for n in names if n.startswith("tree/")}
    for rel in list(L.SOURCE_PINS) + list(L.READOUT_PINS) + [L.SMOKE_FINAL]:
        assert rel in tree, rel
    assert {"claude/e1a_machine.py", "claude/e1a_spec.json"} <= set(names)
    assert not any("receipt_analogy_on_2026091" in n or "receipt_unchanged_repro" in n for n in tree)
    assert not any(n.startswith(L.DESIGN_PREFIX) and n not in L.READOUT_PINS for n in tree)
    assert not any(n.endswith(("_scoring.json", "_predictions.json", "_eval.jsonl")) for n in tree)
    assert sum(n.startswith("cncm/") for n in tree) > 10 and sum("/cas_meta2/" in n for n in tree) > 10
    # the machine's instructions: 7 route containers (4 ON, 3 OFF), 18 reads, validation OFF; refused on the machine too
    assert spec["receipts_missing"] == record["receipts_missing"]
    assert [c["switch"] for c in spec["route_containers"]] == [True] * 4 + [False] * 3
    assert sum(len(v) for v in spec["reads"].values()) == 18 and spec["validation"]["container_kwargs"] == {"analogy_focus_comparison": False}
    with pytest.raises(MACH.Stop):
        MACH.load_spec(_write(tmp_path / "spec.json", spec))
    # THE STAGE SCRIPT passes bash -n (the rendered one, and the template itself)
    script = folder / "dry_run_machine_script.sh"
    assert bash_n(script) == (0, "") and bash_n(HERE / "job.sh.template") == (0, "")
    text = script.read_text(encoding="utf-8")
    assert record["machine_script_bytes"] < 16000
    for words in ("instance_id=", "169.254.169.254", "X-aws-ec2-metadata-token", "shutdown -h +%d" % L.OS_POWER_OFF_MINUTES,
                  "sleep %d" % L.MAX_SECONDS, record["bundle_sha256"], "--budget-seconds %d" % L.JOB_BUDGET_SECONDS,
                  "PREFLIGHT_OVER_WALL_LIMIT", "torch==2.11.0", "cu128", "--switch-expect false"):
        assert words in text, words
    shutil.rmtree(folder)


def test_a_real_launch_refuses_without_the_study_receipts_before_building_anything(no_aws, tmp_path):
    folder = tmp_path / "never"
    proc = run_launch(no_aws, "--repaired-commit", REPAIRED_FREEZE, "--unchanged-commit", UNCHANGED_FREEZE,
                      "--bundle-dir", str(folder), timeout=120)
    assert proc.returncode == 2 and "LAUNCH_REFUSED: STUDY_RECEIPTS_MISSING" in proc.stdout, proc.stdout + proc.stderr
    assert "AWS_CALL_ATTEMPTED" not in proc.stdout + proc.stderr and not folder.exists()
    assert not (HERE / "launch_record.json").exists()


# ================================================================ the launcher's parts
def _write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def test_custody_filter_names_every_forbidden_name():
    d = "tree/" + L.DESIGN_PREFIX
    bad = [d + "hset2/PUBLIC_EXCLUDED_v2.json", d + "readout/h1h2/h1h2_paired.py", d + "readout/probe-v03/toy_bank.py",
           "tree/records/typed_pointer_001/receipt_analogy_on_20260917/collected/results/artifacts/course_p10_scoring.json",
           "tree/records/typed_pointer_001/receipt_analogy_on_20260917/checkpoints/ablation_heads_predictions.json",
           "tree/records/typed_course_001/checks_002/private_targets.json", "tree/x/sealed_A.json", "tree/x/q_eval.jsonl",
           "claude/salt.hex", "tree/x/SEALED.json", "tree/a/__pycache__/x.pyc", "tree/../escape.py", "other/file.py",
           "tree/x/TEST_NEW_5.json", "claude/transcript.json"]
    good = ["tree/" + p for p in L.READOUT_PINS] + [
        "tree/records/typed_pointer_001/receipt_analogy_on_20260917/collected/results/evidence/main_checkpoint_0294.pt",
        "tree/records/typed_pointer_001/receipt_analogy_on_20260917/collected/results/artifacts/pass_10_updates.jsonl",
        "tree/records/typed_pointer_001/receipt_analogy_on_20260917/collected_inventory.json", "tree/cncm/kernel.py",
        "claude/e1a_machine.py", "claude/e1a_spec.json", "anchors.json"]
    assert L.custody_refusals(bad + good) == bad


def test_gpu_rule_cost_cap_limits_and_the_machine_script():
    assert "g7.*" in L.GPU_FAMILIES and "g4dn.*" in L.GPU_FAMILIES
    assert L.worst_case_usd() <= L.COST_CAP_USD == 2.00 and L.ALLOWANCE_USD == 0.10
    assert L.JOB_BUDGET_SECONDS < L.MAX_SECONDS < L.OS_POWER_OFF_MINUTES * 60 < L.CLIENT_DEADLINE_MINUTES * 60
    source = (HERE / "launch.py").read_text(encoding="utf-8")
    assert '"HttpTokens": "required"' in source and 'InstanceInitiatedShutdownBehavior="terminate"' in source
    assert source.index("def launch(") < source.index("import boto3") and source.count("import boto3") == 1
    template = (HERE / "job.sh.template").read_text(encoding="utf-8")
    long_links = {k: "https://example.invalid/" + k + "?" + "x" * 1900 for k in ("bundle", "results", "progress")}
    script = L.render(template, long_links, "0" * 64)
    assert len(script.encode("utf-8")) < L.USER_DATA_LIMIT
    assert 'wait "$p"' in template and "\nwait\n" not in template   # never a bare wait: the loops never end


def test_receipt_selection_and_inventory_binding_on_a_real_full_run_receipt():
    """Helm 2.0's receipt_20260917 (c8d5c430) has the full-run layout the repaired receipts will have. Every file the
    E1a bundle takes from a repaired receipt is present, listed once in its inventory, and streams to the listed sha256."""
    folder = "receipt_20260917"
    paths = set(L.listing(HELM2_COMMIT, L.R + folder + "/"))
    wanted, missing = L.select_receipt(paths, folder, L.REPAIRED_COLLECTED)
    assert missing == [] and len(wanted) == 1 + len(L.REPAIRED_COLLECTED) + 1      # + optional reduced_schedule.json
    blobs = L.Blobs()
    try:
        expect, reasons = L.inventory_expectations(blobs.read(HELM2_COMMIT, L.R + folder + "/collected_inventory.json"),
                                                   folder, L.REPAIRED_COLLECTED)
        assert reasons == [] and len(expect) == len(L.REPAIRED_COLLECTED)
        for rel, (sha, size) in sorted(expect.items()):
            data = blobs.read(HELM2_COMMIT, rel)
            assert hashlib.sha256(data).hexdigest() == sha and len(data) == size, rel
    finally:
        blobs.close()
    # the reduced smoke run is NOT a study receipt: its evidence checkpoints and passes 2-10 are absent
    smoke = "receipt_analogy_on_smoke_20260917"
    _w, absent = L.select_receipt(set(L.listing(L.SMOKE_COMMIT, L.R + smoke + "/")), smoke, L.REPAIRED_COLLECTED)
    assert any("main_checkpoint_0294.pt" in p for p in absent) and any("pass_10_updates.jsonl" in p for p in absent)
    tampered = json.dumps({"files": [{"relative_path": "results/artifacts/final.pt", "sha256": "x"}], "failures": ["f"]})
    _e, reasons = L.inventory_expectations(tampered.encode(), "r", ("results/artifacts/final.pt",))
    assert "INVENTORY_REPORTS_FAILURES:r" in reasons and "NOT_IN_INVENTORY:r/results/artifacts/final.pt" in reasons


def test_a_streamed_file_that_differs_from_its_inventory_or_pin_is_refused(tmp_path):
    rel = L.ROSTER_DIR + "check_roster.py"
    entries = [("tree/" + rel, L.READOUT_COMMIT, rel)]
    for raw_pins, lf_pins, expect, code in (({}, {}, {rel: ("0" * 64, None)}, "RECEIPT_FILE_DIFFERS_FROM_INVENTORY"),
                                            ({}, {rel: "1" * 64}, {}, "PIN_MISMATCH"),
                                            ({"not/bundled.json": "2" * 64}, {}, {}, "PINNED_FILE_NOT_BUNDLED")):
        blobs = L.Blobs()
        try:
            with pytest.raises(L.Refused):
                L.write_bundle(entries, raw_pins, lf_pins, expect, {}, blobs, tmp_path / (code + ".tar.gz"))
        finally:
            blobs.close()
    blobs = L.Blobs()
    try:
        anchors, *_ = L.write_bundle(entries, {}, {rel: L.READOUT_PINS[rel]}, {}, {}, blobs, tmp_path / "ok.tar.gz")
    finally:
        blobs.close()
    assert list(anchors["files"]) == ["tree/" + rel]


# ================================================================ the machine's pure parts
MEASURED = {"elapsed_s": 900.0, "load_s": 170.0, "call_s": 0.05, "calls_per_table": 2000, "table_prep_s": 5.0,
            "fixture_s": 0.6, "containers": 7, "fixtures_per_container": 37, "waves": 2, "processes_per_wave": 3}


def test_preflight_projection():
    ok = MACH.project(MEASURED, L.JOB_BUDGET_SECONDS)
    assert ok["verdict"] == "PREFLIGHT_PASS" and ok["problems"] == [] and ok["t_table_s"] == 105.0
    slow = MACH.project(dict(MEASURED, call_s=0.5), L.JOB_BUDGET_SECONDS)
    assert slow["verdict"] == "PREFLIGHT_OVER_WALL_LIMIT"
    assert any(p.startswith("PROJECTED_END_") for p in slow["problems"])
    assert any(p.startswith("READ_PROCESS_") for p in slow["problems"])
    late = MACH.project(dict(MEASURED, elapsed_s=6500.0), L.JOB_BUDGET_SECONDS)
    assert late["verdict"] == "PREFLIGHT_OVER_WALL_LIMIT" and len(late["problems"]) == 1


def test_route_verdict():
    rows = [{"label": "a", "problems": []}, {"label": "b", "problems": []}]
    assert MACH.route_verdict(rows, 2) == ("ROUTE_RECEIPT_PASS", [])
    assert MACH.route_verdict(rows, 3)[0] == "ROUTE_RECEIPT_FAIL"
    assert MACH.route_verdict(rows + [{"label": "c", "problems": ["SWITCH_STATE_MISMATCH"]}], 3) == ("ROUTE_RECEIPT_FAIL", ["c"])


def _spec(tmp_path):
    reads = {str(s): [{"label": "on_%d_%s" % (s, lab), "roster_label": lab, "checkpoint_relative_path": p,
                       "main_updates_registered": u, "checkpoint": "records/r_%d/collected/%s" % (s, c), "sha256": None}
                      for lab, p, c, u in L.A5] for s in L.SEEDS}
    return {"schema": MACH.SPEC_SCHEMA, "seeds": list(L.SEEDS), "receipts_missing": [], "reads": reads,
            "waves": [[0, 1, 2], [3, 4, 5]], "probe_dir": L.PROBE_DIR.rstrip("/"), "switch_attr": "analogy_focus_comparison",
            "read_container_kwargs": {"analogy_focus_comparison": True}, "repaired_commit": "c" * 40,
            "repaired_receipts": {str(s): "records/r_%d" % s for s in L.SEEDS}, "acceptance_record": None,
            "roster_dir": L.ROSTER_DIR.rstrip("/"), "matched_start_dir": L.MATCHED_DIR.rstrip("/"),
            "helm2_initial": {str(s): "h/%d.pt" % s for s in L.SEEDS},
            "matched_start_on_dirs": {str(s): "records/r_%d/collected/results/artifacts" % s for s in L.SEEDS}}


def _validation_summary(out, **swap):
    """Five raw validation tables built by the probe's own toy bank through the real build_score_table."""
    sys.path.insert(0, str(PROBE))
    import toy_bank
    kinds = {"V1_CONTROL_UNWRAPPED": "HELM_LIKE", "V2_POSITIVE_COMPARISON": "POSITIVE", "V3_ANTI_COMPARISON": "ANTI",
             "V4_NEGATIVE_UNIFORM": "UNIFORM", "V5_NEGATIVE_COUPLED": "COUPLED"}
    kinds.update(swap)
    folder = out / "probe" / "validation"
    folder.mkdir(parents=True)
    tables = {}
    for case, kind in kinds.items():
        raw = json.dumps(toy_bank.build_table(kind)).encode()
        (folder / (case + ".score_table.json")).write_bytes(raw)
        tables[case] = {"file": case + ".score_table.json", "sha256": hashlib.sha256(raw).hexdigest()}
    _write(folder / "validation_summary.json", {"tables": tables, "pointer_learner_sha256_lf_before_after": ["s", "s"]})


class FakeProc:
    def __init__(self, code=0):
        self.code = code

    def wait(self):
        return self.code


def test_the_18_reads_start_only_after_validation_pass(tmp_path):
    spec, tree = _spec(tmp_path), HERE.parents[3]
    calls = []

    def popen(cmd, **kwargs):
        calls.append(cmd)
        return FakeProc(0)
    clock = iter(range(0, 10 ** 6, 60)).__next__
    # no validation summary at all: nothing starts
    assert MACH.run_reads(spec, tree, tmp_path / "a", "py", 0, L.JOB_BUDGET_SECONDS, popen=popen, clock=clock) == 3
    assert calls == [] and "READS_NOT_STARTED" in (tmp_path / "a/probe/READS_NOT_STARTED.json").read_text(encoding="utf-8")
    # a validation that fails (the positive control swapped for the anti one): nothing starts
    _validation_summary(tmp_path / "b", V2_POSITIVE_COMPARISON="ANTI")
    assert MACH.run_reads(spec, tree, tmp_path / "b", "py", 0, L.JOB_BUDGET_SECONDS, popen=popen, clock=clock) == 3
    record = json.loads((tmp_path / "b/probe/READS_NOT_STARTED.json").read_text(encoding="utf-8"))
    assert calls == [] and record["validation"].startswith("VALIDATION_FAIL") and "V2_POSITIVE_COMPARISON" in record["validation"]
    # VALIDATION_PASS: two waves of three harness processes, 3 models each, 18 in all, switch ON asserted
    _validation_summary(tmp_path / "c")
    assert MACH.run_reads(spec, tree, tmp_path / "c", "py", 0, L.JOB_BUDGET_SECONDS, popen=popen, clock=clock) == 0
    assert len(calls) == 6 and all(c.count("--model") == 3 for c in calls)
    models = [c[i + 1] for c in calls for i, a in enumerate(c) if a == "--model"]
    assert len(set(models)) == 18 and all(c[c.index("--switch-expect") + 1] == "true" for c in calls)
    assert json.loads(calls[0][calls[0].index("--container-kwargs") + 1]) == {"analogy_focus_comparison": True}
    assert json.loads((tmp_path / "c/probe/READS_RECORD.json").read_text(encoding="utf-8"))["verdict"] == "READS_COMPLETE"
    with pytest.raises(MACH.Stop):                                     # outputs are create-only
        MACH.run_reads(spec, tree, tmp_path / "c", "py", 0, L.JOB_BUDGET_SECONDS, popen=popen, clock=clock)
    with pytest.raises(MACH.Stop):
        MACH.harness_command("py", PROBE, tree, tmp_path, spec, 20260917, [{"label": "a:b", "checkpoint": "x.pt"}])


def test_item2_inputs_take_every_hash_and_count_from_the_roster(tmp_path):
    spec = _spec(tmp_path)
    out = tmp_path / "out"
    (out / "probe" / "reads").mkdir(parents=True)
    (out / "probe" / "reads" / "on_20260917_final.score_table.json").write_bytes(b"{}")

    def check_receipt(folder, arm):
        assert arm == "repaired"
        rows = [{"label": lab, "sha256": "%064x" % u, "status": "OK",
                 "updates": {"cursor": u, "model_revision": u, "counters.optimizer_updates": u}} for lab, _p, _c, u in L.A5]
        rows[1]["updates"]["cursor"] = 1                               # disagreeing counters -> None, never a guess
        return {"verdict": "ROSTER_PROBLEM", "rows": rows}
    assert MACH.item2_inputs(spec, tmp_path, out, types.SimpleNamespace(check_receipt=check_receipt)) == 0
    inputs = json.loads((out / "probe" / "ITEM2_INPUTS.json").read_text(encoding="utf-8"))
    assert inputs["schema"] == "claude.item2-inputs/0.3" and len(inputs["entries"]) == 18
    first = inputs["entries"][:6]
    assert [e["main_updates"] for e in first] == [147, None, 588, 882, 1176, 1470]
    assert first[5]["checkpoint_sha256"] == "%064x" % 1470 and first[5]["score_table_sha256"] == hashlib.sha256(b"{}").hexdigest()
    assert first[0]["score_table_sha256"] is None and inputs["validation_summary_sha256"] is None
    assert inputs["acceptance_record"] is None


def test_matched_start_reading_runs_only_after_the_self_test_passes(tmp_path):
    spec, calls = _spec(tmp_path), []

    def run(codes):
        def fake(cmd, **kwargs):
            calls.append(cmd)
            return types.SimpleNamespace(returncode=codes[len(calls) - 1])
        return fake
    assert MACH.run_matched(spec, tmp_path, tmp_path / "a", "py", run=run([4])) == 1
    assert len(calls) == 1 and "--self-test" in calls[0]
    calls.clear()
    assert MACH.run_matched(spec, tmp_path, tmp_path / "b", "py", run=run([0, 3])) == 0
    assert len(calls) == 2 and "--self-test" not in calls[1] and calls[1].count("--on") == 3 and calls[1].count("--helm2") == 3


def test_decide_reports_words_only(tmp_path):
    out = tmp_path
    for rel, body in {"smoke.json": {"verdict": "SMOKE_PASS"}, "PREFLIGHT.json": {"verdict": "PREFLIGHT_PASS"},
                      "route/ROUTE_RECEIPT.json": {"verdict": "ROUTE_RECEIPT_PASS", "failed": []},
                      "probe/READS_RECORD.json": {"verdict": "READS_COMPLETE", "validation": "VALIDATION_PASS"},
                      "probe/ITEM2_READING.json": {"outcome": "ITEM2_PASS", "mechanism_gate": "MECHANISM_GATE_OPEN",
                                                   "gate_open_reasons": ["PREREG_V0_3_NOT_ACCEPTED"],
                                                   "validation": {"validation": "VALIDATION_PASS"},
                                                   "entries": [{"summary": {"analogy_accuracy_planted": 0.8731}}]},
                      "probe/reads/on_20260917_final.harness_reading.json": {"planted_number": 0.8731},
                      "matched_start/SELF_TEST.json": {"verdict": "MATCHED_START_SELF_TEST:PASS"},
                      "matched_start/MATCHED_START_READING.json": {"verdict": "MATCHED_START_REPRODUCED", "reasons": []},
                      "roster/roster_20260917.json": {"verdict": "ROSTER_COMPLETE"},
                      "roster/roster_20260918.json": {"verdict": "ROSTER_COMPLETE"},
                      "roster/roster_20260919.json": {"verdict": "ROSTER_PROBLEM"}}.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        _write(out / rel, body)
    assert MACH.decide(out) == 0
    text = (out / "E1A_RESULT.json").read_text(encoding="utf-8")
    result = json.loads(text)
    assert result["overall"] == "E1A_STAGES_COMPLETE" and result["stages"]["item2"] == "ITEM2_PASS"
    assert "0.8731" not in text and "analogy_accuracy" not in text
    (out / "route" / "ROUTE_RECEIPT.json").unlink()
    (out / "E1A_RESULT.json").unlink()
    assert MACH.decide(out) == 1
    assert json.loads((out / "E1A_RESULT.json").read_text(encoding="utf-8"))["missing_stage_readings"] == ["route"]


def test_anchor_check_finds_a_changed_missing_or_unlisted_file(tmp_path):
    (tmp_path / "tree").mkdir()
    (tmp_path / "tree" / "a.py").write_bytes(b"x = 1\n")
    _write(tmp_path / "anchors.json", {"files": {"tree/a.py": {"sha256": hashlib.sha256(b"x = 1\n").hexdigest()}}})
    assert MACH.check_anchors(tmp_path) == 0
    (tmp_path / "tree" / "b.py").write_bytes(b"")
    assert MACH.check_anchors(tmp_path) == 1
    (tmp_path / "tree" / "b.py").unlink()
    (tmp_path / "tree" / "a.py").write_bytes(b"x = 2\n")
    assert MACH.check_anchors(tmp_path) == 1


def test_the_laptop_reader_binds_results_to_the_launched_instance(tmp_path):
    iid, launched, ended = "i-0123456789abcdef0", "2026-09-25T02:00:00Z", "2026-09-25T03:10:00Z"
    _write(tmp_path / "launch_record.json", {"instance_id": iid, "launched_utc": launched, "bundle_sha256": "f" * 64})
    _write(tmp_path / "watch_record.json", {"instance_id": iid, "launched_utc": launched, "watch_ended_utc": ended,
                                            "outcome": "RESULTS_RECEIVED", "files_downloaded": 60, "final_state": "terminated",
                                            "job_status": "done", "volumes_tagged_with_job_name": [], "cost_upper_bound_usd": 0.9})
    res = tmp_path / "results"
    res.mkdir()
    (res / "STATUS").write_text("done\n", encoding="utf-8")
    (res / "job.log").write_text("JOB START 2026-09-25T02:01:10Z\nJOB FINISH 2026-09-25T03:05:00Z status=done\n", encoding="utf-8")
    (res / "env.txt").write_text("instance_id=%s\nbundle_sha256=%s\n" % (iid, "f" * 64), encoding="utf-8")
    _write(res / "E1A_RESULT.json", {"overall": "E1A_STAGES_COMPLETE", "stages": {}, "mechanism_gate": "MECHANISM_GATE_OPEN"})
    assert RR.read(tmp_path)["verdict"] == "JOB_ACCEPTED"
    (res / "env.txt").write_text("instance_id=i-0fffffffffffffff0\nbundle_sha256=%s\n" % ("f" * 64), encoding="utf-8")
    reading = RR.read(tmp_path)
    assert reading["verdict"] == "JOB_NOT_ACCEPTED" and any(p.startswith("MACHINE_INSTANCE_ID") for p in reading["problems"])


def test_watch_extracts_only_plain_paths_under_out():
    import watch
    assert watch.safe_member("out/probe/reads/on_20260917_final.score_table.json")
    for bad in ("out/../x", "/etc/passwd", "x/out/a", "out/a/b/c/d/e", "out/a b"):
        assert not watch.safe_member(bad), bad
