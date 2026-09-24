"""Tests for the P1b job (readout plan item 8). CLAUDE_BUILT_CLAUDE_CHECKED.

THE STATED ACCEPTANCE CHECK: a laptop dry run (NO AWS call, NO network call) builds BOTH bundles -- the acceptance
bundle, and the reading bundle's shape through a rehearsal with public stand-ins -- and the reading mode is REFUSED
without the eligibility record, before anything is built. Every launcher subprocess runs with `boto3` and `botocore`
replaced by modules that raise on import, so any AWS call attempt fails loudly.
Plus the pure parts: the eligibility contract, the candidate binding (on the REAL Helm 2.0 records), the timing
projection, the cost cap and session limits, the machine's decide step (against the reader's own frozen table), the
anchor check and the laptop result reader. No torch, no model, no course load. About 15 MB of git objects are read.

    python -B -m pytest test_p1b_job.py -q -p no:cacheprovider
"""
import ast
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import launch as L  # noqa: E402
import p1b_machine as M  # noqa: E402
import read_results as RR  # noqa: E402

READER_TESTS_AT_REVISION_4 = 112          # the reader builder's own count for revision 4 (commit fee4ebec)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def no_aws(tmp_path_factory):
    """An environment in which importing boto3 or botocore raises: any AWS call attempt fails the test loudly."""
    root = tmp_path_factory.mktemp("no_aws")
    for name in ("boto3", "botocore"):
        (root / name).mkdir()
        (root / name / "__init__.py").write_text("raise RuntimeError('AWS_CALL_ATTEMPTED: %s was imported')\n" % name)
    return dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")


def run_launch(env, *args, timeout=300):
    return subprocess.run([sys.executable, "-B", str(HERE / "launch.py"), *args], capture_output=True, text=True,
                          env=env, timeout=timeout)


def bundle_members(path):
    with tarfile.open(path, mode="r:gz") as tar:
        return {m.name: tar.extractfile(m).read() for m in tar.getmembers()}


@pytest.fixture(scope="module")
def reader_dir(tmp_path_factory):
    """The reader folder at the pinned reader commit, extracted from git objects (repro_common reads its pins there)."""
    root = tmp_path_factory.mktemp("reader_root")
    rels = L.tree_files(L.READER_COMMIT, L.HERE_REL)
    for rel, data in L.read_blobs(L.READER_COMMIT, rels).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root / L.HERE_REL


# ---- THE ACCEPTANCE CHECK ------------------------------------------------------------------------------------------
def test_acceptance_dry_run_builds_the_acceptance_bundle(no_aws, tmp_path):
    folder = tmp_path / "bundle_acceptance"
    proc = run_launch(no_aws, "--mode", "acceptance", "--dry-run", "--bundle-dir", str(folder))
    print(proc.stdout[-5000:])
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    out = proc.stdout
    assert "AWS_CALL_ATTEMPTED" not in out + proc.stderr
    for words in ("CUSTODY: PASS", "PLAN (mode acceptance)", "COST CAP", "cap $2.64", "allowance", "retries   none",
                  "60-minute session", "past 55 min", "DRY RUN: nothing uploaded, nothing launched, no AWS or network call"):
        assert words in out, words
    record = json.loads((folder / "dry_run_record.json").read_text(encoding="utf-8"))
    assert (record["mode"], record["dry_run"], record["rehearsal"], record["launchable"]) == ("acceptance", True, False, True)
    assert record["aws_calls"] == [] and record["network_calls"] == []
    assert record["worst_case_usd_at_client_deadline"] <= L.COST_CAP_USD == record["cost_cap_usd"]
    assert record["sources"]["tree_commit"] == L.READER_COMMIT
    body = (folder / "bundle.tar.gz").read_bytes()
    assert sha(body) == record["bundle"]["sha256"] and record["bundle"]["sha256"] in out
    files = bundle_members(folder / "bundle.tar.gz")
    anchors = json.loads(files.pop("anchors.json"))
    assert sorted(anchors["files"]) == sorted(files) and all(sha(files[n]) == anchors["files"][n]["sha256"] for n in files)
    assert L.custody_refusals(list(files) + ["anchors.json"]) == []
    tree = {n[len("tree/"):]: d for n, d in files.items() if n.startswith("tree/")}
    for name in L.READER_SOURCE_FILES + (L.TEST_FILE, "policy_pins.json", "public_panel_manifest.json",
                                         "frozen/study.json", "EXECUTION_ADMISSION.json"):
        assert L.HERE_REL + "/" + name in tree, name
    for rel in L.STAGE0_FILES + (L.ARCHIVE_REL,):
        assert rel in tree, rel
    assert sha(tree[L.ARCHIVE_REL]) == L.ARCHIVE_SHA256
    assert sha(files["ref/final.pt"]) == L.REFERENCE_PT_SHA256 and "cand/final.pt" not in files
    assert "claude/p1b_machine.py" in files and not any(n.startswith("claude/eligibility") for n in files)
    hashes = {n: sha(tree[L.HERE_REL + "/" + n]) for n in L.READER_SOURCE_FILES}
    assert record["reader"]["reader_sources_sha256"] == hashes
    assert record["reader"]["reader_source_sha256"] == L.reader_digest(hashes) == M.reader_digest(hashes)
    assert record["reader"]["expected_tests"] == READER_TESTS_AT_REVISION_4
    script = (folder / "dry_run_machine_script.sh").read_text(encoding="utf-8")
    assert record["machine_script_bytes"] < L.USER_DATA_LIMIT and not [b for b in L.BASHISMS if b in script]
    for words in ("instance_id=", "169.254.169.254", "X-aws-ec2-metadata-token", "shutdown -h +59", "sleep 3420",
                  record["bundle"]["sha256"], L.AMI, "--mode acceptance", "env -u CAS_META2_RUN_TEACHING_CYCLE",
                  "test_unchanged_repro.py -v", "p1b_machine.py preflight", "torch==2.11.0",
                  "download.pytorch.org/whl/cu128", "requirements-gpu.txt", "--no-deps", "--expected-tests 112",
                  "/opt/cas-graph6curr/package", "python3.12 python3.11 python3", L.ARCHIVE_SHA256):
        assert words in script, words
    # the machine's own anchor check passes on the real bundle, and catches a change
    unpacked = tmp_path / "pkg"
    with tarfile.open(folder / "bundle.tar.gz", mode="r:gz") as tar:
        tar.extractall(unpacked, filter="data")
    assert M.check_anchors(unpacked) == 0
    (unpacked / "tree" / L.HERE_REL / "repro_common.py").write_bytes(b"# changed\n")
    assert M.check_anchors(unpacked) == 1


def test_reading_rehearsal_dry_run_builds_the_reading_bundle(no_aws, tmp_path):
    folder = tmp_path / "bundle_reading"
    proc = run_launch(no_aws, "--mode", "reading", "--dry-run", "--rehearsal", "--bundle-dir", str(folder))
    print(proc.stdout[-4000:])
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert "AWS_CALL_ATTEMPTED" not in proc.stdout + proc.stderr
    assert "REHEARSAL: public stand-in candidate, cannot launch" in proc.stdout
    record = json.loads((folder / "dry_run_record.json").read_text(encoding="utf-8"))
    assert (record["mode"], record["rehearsal"], record["launchable"], record["eligibility"]) == ("reading", True, False, None)
    files = bundle_members(folder / "bundle.tar.gz")
    assert sha(files["cand/final.pt"]) == L.REFERENCE_PT_SHA256 == record["sources"]["candidate"]["sha256"]
    assert record["sources"]["candidate"]["job"] == L.HELM2_JOB
    tree = {n[len("tree/"):] for n in files if n.startswith("tree/")}
    assert L.HERE_REL + "/recompute_reproduction_evidence.py" in tree and L.ARCHIVE_REL in tree
    assert not [r for r in L.STAGE0_FILES if r in tree]                  # the reading ships no stage-0 extras
    script = (folder / "dry_run_machine_script.sh").read_text(encoding="utf-8")
    for words in ("--mode reading", "--candidate-sha256 " + L.REFERENCE_PT_SHA256, "--candidate-job " + L.HELM2_JOB,
                  "reproduction_evidence.json", "instance_id="):
        assert words in script, words
    assert len(script.encode("utf-8")) < L.USER_DATA_LIMIT


def test_reading_mode_is_refused_without_the_eligibility_record(no_aws, tmp_path):
    folder = tmp_path / "never_built"
    for extra in (["--dry-run"], []):                                   # dry run and real launch alike
        proc = run_launch(no_aws, "--mode", "reading", *extra, "--bundle-dir", str(folder), timeout=120)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "LAUNCH_REFUSED: ELIGIBILITY_RECEIPT_COMMIT_REQUIRED" in proc.stdout
        # a real commit that carries no READING_ELIGIBILITY.json (the reader commit itself)
        proc = run_launch(no_aws, "--mode", "reading", *extra, "--receipt-commit", L.READER_COMMIT,
                          "--receipt-branch", L.READER_BRANCH, "--bundle-dir", str(folder), timeout=120)
        assert proc.returncode == 2, proc.stdout + proc.stderr
        assert "LAUNCH_REFUSED: ELIGIBILITY_RECORD_REQUIRED" in proc.stdout
        assert "AWS_CALL_ATTEMPTED" not in proc.stdout + proc.stderr
        assert not folder.exists()                                      # refused before anything was built
    for args in (["--mode", "reading", "--rehearsal"],                  # a rehearsal never launches
                 ["--mode", "acceptance", "--dry-run", "--rehearsal"],
                 ["--mode", "acceptance", "--dry-run", "--receipt-commit", L.READER_COMMIT],
                 ["--mode", "reading", "--dry-run", "--receipt-commit", L.READER_COMMIT, "--reader-commit", L.READER_COMMIT]):
        proc = run_launch(no_aws, *args, "--bundle-dir", str(folder), timeout=120)
        assert proc.returncode == 2 and "LAUNCH_REFUSED: USAGE" in proc.stdout, (args, proc.stdout)
    assert not folder.exists()


# ---- the eligibility contract (pure) --------------------------------------------------------------------------------
def eligibility_case():
    hashes = {n: "%064x" % (i + 1) for i, n in enumerate(L.READER_SOURCE_FILES)}
    bundled = {"frozen_job": "cas-meta2-tpntr-20260924123354-20208c92-m-20260917", "reader_sources_sha256": hashes,
               "reader_source_sha256": L.reader_digest(hashes), "policy_pins_sha256": "a" * 64,
               "decide_source_sha256": "d" * 64}
    acceptance = json.dumps({"status": "READER_ACCEPTANCE_PASS", "cases": [{"case": c} for c in L.ACCEPTANCE_CASES],
                             "producer": {"reader_source_sha256": bundled["reader_source_sha256"]}}).encode()
    raws = {"reader_acceptance": acceptance, "environment_lock": b'{"lock": 1}', "review": b'{"review": 1}'}
    record = {"schema": L.ELIGIBILITY_SCHEMA, "label": L.LABEL, "state": "READING_ELIGIBLE", "job": bundled["frozen_job"],
              "job_kind": L.JOB_KIND, "model_seed": L.MODEL_SEED, "source_sha": L.SOURCE_SHA,
              "frozen_study": {"commit": L.FREEZE_COMMIT, "path": L.REPO_PREFIX + L.HERE_REL + "/frozen/study.json",
                               "sha256": L.FROZEN_STUDY_SHA256},
              "execution_admission_as_is": {"path": L.REPO_PREFIX + L.HERE_REL + "/EXECUTION_ADMISSION.json",
                                            "sha256": L.FROZEN_ADMISSION_SHA256, "state": "NOT_READY"},
              "reader": {"reader_source_sha256": bundled["reader_source_sha256"], "reader_sources_sha256": dict(hashes)},
              "policy_pins_sha256": "a" * 64, "panel_manifest_sha256": L.PANEL_MANIFEST_SHA256,
              "launch_basis": L.LAUNCH_BASIS, "decide_source_sha256": "d" * 64, "note": "", "written_by": "x",
              "written_utc": "2026-09-25T01:40:00Z", "owner_direction_record": {},
              **{n: {"receipt_commit": "%040x" % (i + 7), "receipt_path": L.HERE_REL + "/receipts/%s.json" % n,
                     "receipt_sha256": sha(raws[n])} for i, n in enumerate(L.ELIGIBILITY_RECEIPTS)}}
    facts = {"eligibility_commits": ["e" * 40], "freeze_precedes_eligibility": True, "evidence_present": False,
             "decide_at_freeze": "d" * 64, "receipts": {n: {"raw": raws[n], "anchored": True} for n in raws}}
    return record, facts, bundled, raws


def test_the_eligibility_contract():
    record, facts, bundled, raws = eligibility_case()
    assert sorted(record) == sorted(L.ELIGIBILITY_FIELDS)
    assert L.eligibility_problems(json.dumps(record).encode(), facts, bundled) == []

    def problems(record_change=None, fact_change=None):
        r, f, b, _ = eligibility_case()
        (record_change or (lambda x: None))(r)
        (fact_change or (lambda x: None))(f)
        return L.eligibility_problems(json.dumps(r).encode(), f, b)

    bad_acceptance = json.dumps({"status": "READER_ACCEPTANCE_FAIL", "cases": [], "producer": {}}).encode()
    cases = {
        "ELIGIBILITY_FIELDS_SCHEMA_LABEL_OR_STATE": problems(lambda r: r.update(state="NOT_READY")),
        "NOT_FOR_THE_FROZEN_JOB": problems(lambda r: r.update(job="cas-meta2-tpntr-20260101000000-20208c92-m-20260917")),
        "NOT_THE_READER_THIS_BUNDLE_SHIPS": problems(lambda r: r["reader"]["reader_sources_sha256"].update(
            {"repro_common.py": "f" * 64})),
        "ADMISSION_IS_NOT_THE_BYTE_IDENTICAL_AS_IS_RECORD": problems(lambda r: r["execution_admission_as_is"].update(
            state="ADMITTED")),
        "FROZEN_STUDY_BINDING": problems(lambda r: r["frozen_study"].update(commit="0" * 40)),
        "DECIDE_IS_NOT_THE_FROZEN_DECIDE": problems(fact_change=lambda f: f.update(decide_at_freeze="c" * 64)),
        "ELIGIBILITY_NOT_EXACTLY_ONE_COMMITTED_VERSION:2": problems(fact_change=lambda f: f.update(
            eligibility_commits=["e" * 40, "f" * 40])),
        "ELIGIBILITY_NOT_COMMITTED_AFTER_THE_FREEZE": problems(fact_change=lambda f: f.update(
            freeze_precedes_eligibility=False)),
        "EVIDENCE_ALREADY_COMMITTED": problems(fact_change=lambda f: f.update(evidence_present=True)),
        "RECEIPT_SHA256:environment_lock": problems(fact_change=lambda f: f["receipts"]["environment_lock"].update(
            raw=b'{"lock": 2}')),
        "RECEIPT_NOT_COMMITTED_BEFORE_THE_ELIGIBILITY_RECORD:review": problems(
            fact_change=lambda f: f["receipts"]["review"].update(anchored=False)),
        "RECEIPT_NOT_A_COMMITTED_BLOB:review": problems(fact_change=lambda f: f["receipts"]["review"].update(raw=None)),
        "RECEIPT_REFERENCE_FORM:review": problems(lambda r: r["review"].update(receipt_path="../x.json")),
        "ACCEPTANCE_RECEIPT_NOT_PASS": problems(
            lambda r: r["reader_acceptance"].update(receipt_sha256=sha(bad_acceptance)),
            lambda f: f["receipts"]["reader_acceptance"].update(raw=bad_acceptance)),
        "ACCEPTANCE_RAN_ANOTHER_READER": problems(
            lambda r: r["reader_acceptance"].update(receipt_sha256=sha(bad_acceptance)),
            lambda f: f["receipts"]["reader_acceptance"].update(raw=bad_acceptance)),
    }
    for code, found in cases.items():
        assert any(p.startswith(code) for p in found), (code, found)
    duplicate = b'{"state": "READING_ELIGIBLE", "state": "READING_ELIGIBLE"}'
    assert L.eligibility_problems(duplicate, facts, bundled) == ["ELIGIBILITY_NOT_A_STRICT_JSON_OBJECT"]


def _module_constants(raw):
    """Module-level constants of a source file: literals, names, `+` and tuple/list/dict of them (no code run)."""
    env = {}

    def value(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.Tuple):
            return tuple(value(e) for e in node.elts)
        if isinstance(node, ast.List):
            return [value(e) for e in node.elts]
        if isinstance(node, ast.Dict):
            return {value(k): value(v) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return value(node.left) + value(node.right)
        raise ValueError(type(node).__name__)
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign):
            targets = node.targets[0].elts if isinstance(node.targets[0], ast.Tuple) else node.targets
            values = node.value.elts if isinstance(node.targets[0], ast.Tuple) and isinstance(node.value, ast.Tuple) \
                else [node.value]
            for target, item in zip(targets, values):
                try:
                    env[target.id] = value(item)
                except (ValueError, KeyError, AttributeError, TypeError):
                    pass
    return env


def test_the_launcher_pins_mirror_the_reader_it_ships():
    common = _module_constants(L.read_blobs(L.READER_COMMIT, [L.HERE_REL + "/repro_common.py"])[L.HERE_REL + "/repro_common.py"])
    pairs = {"ELIGIBILITY_FIELDS": L.ELIGIBILITY_FIELDS, "ELIGIBILITY_RECEIPTS": L.ELIGIBILITY_RECEIPTS,
             "ELIGIBILITY_SCHEMA": L.ELIGIBILITY_SCHEMA, "ELIGIBILITY_REL": L.ELIGIBILITY_REL,
             "ACCEPTANCE_CASES": L.ACCEPTANCE_CASES, "READER_SOURCE_FILES": L.READER_SOURCE_FILES,
             "FREEZE_COMMIT": L.FREEZE_COMMIT, "FROZEN_STUDY_SHA256": L.FROZEN_STUDY_SHA256,
             "FROZEN_ADMISSION_SHA256": L.FROZEN_ADMISSION_SHA256, "PANEL_MANIFEST_SHA256": L.PANEL_MANIFEST_SHA256,
             "ARCHIVE_SHA256": L.ARCHIVE_SHA256, "ARCHIVE_BYTES": L.ARCHIVE_BYTES, "PACKAGE_REL": L.PACKAGE_REL,
             "REFERENCE_COMMIT": L.REFERENCE_COMMIT, "REFERENCE_FINAL_PT_SHA256": L.REFERENCE_PT_SHA256,
             "REFERENCE_FINAL_PT_BYTES": L.REFERENCE_PT_BYTES, "HISTORICAL_AMI": L.AMI,
             "REQUIREMENTS_GPU_SHA256": L.REQUIREMENTS_SHA256, "JOB_KIND": L.JOB_KIND, "MODEL_SEED": L.MODEL_SEED,
             "SOURCE_SHA": L.SOURCE_SHA, "HELM2_JOB": L.HELM2_JOB, "LAUNCH_BASIS": L.LAUNCH_BASIS,
             "EVIDENCE_REL": L.EVIDENCE_REL, "HERE_REL": L.HERE_REL, "HISTORICAL_PACKAGE_ROOT": "/opt/cas-graph6curr/package",
             "LABEL": L.LABEL, "ACCEPTANCE_PASS": "READER_ACCEPTANCE_PASS"}
    for name, mine in pairs.items():
        assert common[name] == mine, name
    assert common["RECEIPT_REL"] + "/" == L.U17_RECEIPT and common["REFERENCE_RECEIPT_REL"] + "/" == L.REFERENCE_RECEIPT
    assert common["NUMERICAL_ENVIRONMENT"]["torch_version"] == L.TORCH_VERSION + "+cu128"
    assert common["NUMERICAL_ENVIRONMENT"]["gpu_name"] == "NVIDIA RTX PRO 4500 Blackwell Server Edition"


# ---- the candidate binding, on the REAL committed Helm 2.0 seed-17 records -----------------------------------------
def test_candidate_binding_on_the_real_helm2_records():
    receipt = L.REFERENCE_RECEIPT
    got = L.read_blobs(L.REFERENCE_COMMIT, [receipt + L.FINAL_PT] + [receipt + r for r in L.RECORDS.values()])
    final_pt = got[receipt + L.FINAL_PT]
    records = {n: got[receipt + r] for n, r in L.RECORDS.items()}
    assert sha(final_pt) == L.REFERENCE_PT_SHA256
    assert L.candidate_problems(final_pt, records, L.HELM2_JOB) == []
    other = L.candidate_problems(final_pt, records, "cas-meta2-tpntr-20260924123354-20208c92-m-20260917")
    assert "CANDIDATE_INVENTORY_IS_FOR_ANOTHER_JOB" in other and "CANDIDATE_CHECKPOINT_IS_FOR_ANOTHER_JOB" in other
    changed = L.candidate_problems(final_pt[:-1] + bytes([final_pt[-1] ^ 1]), records, L.HELM2_JOB)
    assert sorted(changed) == ["CANDIDATE_RECORD_DOES_NOT_NAME_THIS_FINAL_PT:" + n for n in ("checkpoint", "inventory", "manifest")]
    assert "CANDIDATE_RECORD_MISSING_OR_UNREADABLE:manifest" in L.candidate_problems(final_pt, dict(records, manifest=None),
                                                                                    L.HELM2_JOB)
    assert L.candidate_problems(None, records, L.HELM2_JOB) == ["CANDIDATE_FINAL_PT_MISSING"]


# ---- the timing preflight, the cost cap and the session limits -----------------------------------------------------
def test_the_timing_preflight_refuses_a_projection_past_the_limit():
    common = dict(elapsed_seconds=900, setup_seconds=200, restore_seconds=5, warmup_seconds=2, records=564)
    fits = M.project("acceptance", per_record_seconds=0.40, **common)
    assert fits["fits"] is True and fits["projected_total_seconds"] <= M.PREFLIGHT_LIMIT_SECONDS
    over = M.project("acceptance", per_record_seconds=0.57, **common)      # the Helm 2.0 upper bound per prediction
    assert over["fits"] is False and over["projected_total_seconds"] > M.PREFLIGHT_LIMIT_SECONDS
    assert M.project("reading", per_record_seconds=0.57, **common)["fits"] is True
    assert M.project("acceptance", per_record_seconds=0.0, **dict(common, elapsed_seconds=3400))["fits"] is False
    positions = M.timed_indices(564)
    assert positions[:2] == [0, 1] and len(positions) == 26 and positions == sorted(set(positions)) and positions[-1] < 564
    assert (M.PANELS, M.RESTORES) == ({"acceptance": 6, "reading": 2}, {"acceptance": 8, "reading": 2})


def test_cost_cap_and_session_limits():
    assert L.worst_case_usd() <= L.COST_CAP_USD < L.worst_case_usd(L.CLIENT_DEADLINE_MINUTES + 1)
    assert round(L.worst_case_usd(), 4) == 2.6177
    assert M.PREFLIGHT_LIMIT_SECONDS < L.MAX_SECONDS < L.POWER_OFF_MINUTES * 60 < L.SESSION_MINUTES * 60 \
        < L.CLIENT_DEADLINE_MINUTES * 60
    assert M.SESSION_MINUTES == L.SESSION_MINUTES and "g7.*" in L.GPU_FAMILIES
    template = (HERE / "job.sh.template").read_text(encoding="utf-8")
    assert not [b for b in L.BASHISMS if b in template] and 'wait "$CHILD"' in template
    long_links = {k: "https://example.invalid/" + k + "?" + "x" * 2000 for k in ("bundle", "results", "progress")}
    facts = {"reader_source_sha256": "a" * 64, "expected_tests": 112}
    candidate = {"sha256": "c" * 64, "job": L.HELM2_JOB}
    for mode, cand in (("acceptance", None), ("reading", candidate)):
        script = L.render(template, L.script_values(mode, long_links, "b" * 64, facts, cand, "1" * 40))
        assert len(script.encode("utf-8")) < L.USER_DATA_LIMIT and "__" not in script
        assert ('if [ "%s" = "acceptance" ]' % mode) in script
    with pytest.raises(AssertionError):
        L.render(template + "\n[[ x ]]\n", L.script_values("reading", long_links, "b" * 64, facts, candidate, "1" * 40))


# ---- the machine's decide step, against the reader's own frozen table ----------------------------------------------
def passing_receipt(common, digest):
    cases = []
    for name in common.ACCEPTANCE_CASES:
        expected = common.ACCEPTANCE_EXPECTED[name]
        if "status" in expected:
            cases.append({"case": name, "status": expected["status"], "reference_buffers": [],
                          "reference_buffer_count": 0, "why": "no buffers", "pass": True})
            continue
        values = {level: expected["levels"].get(level, True) for level in common.LEVEL_LABELS}
        cases.append({"case": name, "expected_verdict": expected["verdict"], "expected_levels": expected["levels"],
                      "observed_verdict": expected["verdict"],
                      "observed_levels": {lv: common.LEVEL_LABELS[lv][0 if v else 1] for lv, v in values.items()},
                      "invalid_reasons": ["SYNTHETIC"] if expected["verdict"] == common.INVALID_STOP else [], "pass": True})
    return {"schema": common.ACCEPTANCE_SCHEMA, "status": common.ACCEPTANCE_PASS, "cases": cases,
            "registered_cases": list(common.ACCEPTANCE_CASES), "environment_violations": [],
            "producer": {"reader_source_sha256": digest}}


def write_acceptance_outputs(out, receipt, log="Ran 112 tests in 4.2s\n\nOK (skipped=31)\n", codes=None):
    out.mkdir()
    for key, value in (codes or {"stage0": 0, "preflight": 0, "recompute": 0}).items():
        (out / ("EXIT_" + key)).write_text("%s=%s\n" % (key, value), encoding="utf-8")
    (out / "stage0_tests.log").write_text(log, encoding="utf-8")
    (out / "preflight.json").write_text(json.dumps({"verdict": "PREFLIGHT_FITS", "projection": {}}), encoding="utf-8")
    (out / "reader_acceptance_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")


def test_decide_acceptance_passes_only_on_the_frozen_table(tmp_path, reader_dir):
    sys.path.insert(0, str(reader_dir))
    import repro_common as common
    assert pathlib.Path(common.__file__).resolve().parent == reader_dir.resolve()   # the extracted copy, not a worktree
    digest = M.reader_digest(M.reader_hashes(reader_dir))
    receipt = passing_receipt(common, digest)
    assert [v for c in receipt["cases"] for v in common.acceptance_case_violations(c)] == []
    write_acceptance_outputs(tmp_path / "a", receipt)
    assert M.decide("acceptance", tmp_path / "a", reader_dir, 112, digest) == 0
    result = json.loads((tmp_path / "a" / "P1B_JOB_RESULT.json").read_text(encoding="utf-8"))
    assert result["overall"] == "P1B_ACCEPTANCE_RUN_PASS" and result["stage0"]["skipped"] == 31

    def failing(folder, **kw):
        write_acceptance_outputs(tmp_path / folder, kw.pop("receipt", receipt), **kw)
        assert M.decide("acceptance", tmp_path / folder, reader_dir, 112, kw.get("digest", digest)) == 1
        return json.loads((tmp_path / folder / "P1B_JOB_RESULT.json").read_text(encoding="utf-8"))["problems"]
    flipped = json.loads(json.dumps(receipt))
    flipped["cases"][3]["observed_verdict"] = common.REPRODUCED                    # changed_value read as reproduced
    assert any(p.startswith("CASE:changed_value") for p in failing("b", receipt=flipped))
    assert "STAGE0_TEST_COUNT:111!=112" in failing("c", log="Ran 111 tests in 4.0s\n\nOK\n")
    assert "STAGE0_TESTS_NOT_PASSED" in failing("d", log="Ran 112 tests in 4.0s\n\nFAILED (failures=1, skipped=2)\n")
    other = json.loads(json.dumps(receipt))
    other["producer"]["reader_source_sha256"] = "0" * 64
    assert "ACCEPTANCE_RAN_ANOTHER_READER" in failing("e", receipt=other)
    reordered = json.loads(json.dumps(receipt))
    reordered["cases"][0], reordered["cases"][1] = reordered["cases"][1], reordered["cases"][0]
    assert "ACCEPTANCE_CASES_NOT_THE_REGISTERED_ELEVEN_IN_ORDER" in failing("f", receipt=reordered)
    assert "PREFLIGHT_NOT_PASSED" in failing("g", codes={"stage0": 0, "preflight": 5, "recompute": 0})
    counts = M.parse_unittest_log("Ran 9 tests in 1s\n\nFAILED (failures=1, errors=2, expected failures=3, skipped=4)\n")
    assert (counts["ran"], counts["ok"], counts["failures"], counts["errors"], counts["expected_failures"],
            counts["skipped"]) == (9, False, 1, 2, 3, 4)


def test_decide_reading_reports_evidence_and_never_a_verdict(tmp_path, reader_dir):
    digest = M.reader_digest(M.reader_hashes(reader_dir))
    out = tmp_path / "r"
    out.mkdir()
    for key in ("preflight", "recompute"):
        (out / ("EXIT_" + key)).write_text("%s=0\n" % key, encoding="utf-8")
    (out / "preflight.json").write_text(json.dumps({"verdict": "PREFLIGHT_FITS"}), encoding="utf-8")
    evidence = {"mode": "READING", "producer": {"reader_source_sha256": digest},
                "inputs": {"candidate": {"sha256": "c" * 64}}, "producer_invalid_reasons": [],
                "producer_levels": {"learned_state": True, "output": True}}
    (out / "reproduction_evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
    assert M.decide("reading", out, reader_dir, 112, digest, "c" * 64) == 0
    result = json.loads((out / "P1B_JOB_RESULT.json").read_text(encoding="utf-8"))
    assert result["overall"] == "P1B_READING_EVIDENCE_WRITTEN" and "producer_levels" not in json.dumps(result)
    assert "verdict" not in {k for k in result if k != "verdict_note"}
    assert M.decide("reading", out, reader_dir, 112, digest, "d" * 64) == 1


# ---- the laptop result reader --------------------------------------------------------------------------------------
def test_the_laptop_reader_binds_results_to_the_launched_instance(tmp_path):
    iid, launched = "i-0123456789abcdef0", "2026-09-25T02:00:00Z"
    (tmp_path / "launch_record_acceptance.json").write_text(json.dumps(
        {"instance_id": iid, "launched_utc": launched, "ami": L.AMI, "approved": {"machine": L.INSTANCE_TYPE},
         "bundle": {"sha256": "f" * 64}}), encoding="utf-8")
    (tmp_path / "watch_record_acceptance.json").write_text(json.dumps(
        {"instance_id": iid, "final_state": "terminated", "cost_upper_bound_usd": 2.1}), encoding="utf-8")
    res = tmp_path / "results_acceptance"
    res.mkdir()
    (res / "STATUS").write_text("done\n", encoding="utf-8")
    env = "instance_id=%s\nami_id=%s\ninstance_type=%s\nbundle_sha256=%s\n" % (iid, L.AMI, L.INSTANCE_TYPE, "f" * 64)
    (res / "env.txt").write_text(env, encoding="utf-8")
    (res / "P1B_JOB_RESULT.json").write_text(json.dumps({"overall": "P1B_ACCEPTANCE_RUN_PASS", "problems": []}), encoding="utf-8")
    (res / "reader_acceptance_receipt.json").write_bytes(b'{"status": "READER_ACCEPTANCE_PASS"}')
    reading = RR.read(tmp_path, "acceptance")
    assert reading["verdict"] == "JOB_ACCEPTED" and reading["product"]["sha256"] == sha(b'{"status": "READER_ACCEPTANCE_PASS"}')
    (res / "env.txt").write_text(env.replace(iid, "i-0fffffffffffffff0"), encoding="utf-8")
    reading = RR.read(tmp_path, "acceptance")
    assert reading["verdict"] == "JOB_NOT_ACCEPTED" and any(p.startswith("MACHINE_INSTANCE_ID") for p in reading["problems"])


def test_custody_filter_names_every_forbidden_name():
    bad = ["tree/records/typed_course_001/checks_002/private_targets.json", "tree/x/sealed_A_eval.jsonl", "sealed/salt.hex",
           "tree/records/helm_eval_design_20260923/hset2/PUBLIC_EXCLUDED_v1.json", "tree/a/SEALED.json",
           "tree/a/__pycache__/x.pyc", "tree/../escape.py", "claude/transcript.json", "cand/protected.pt"]
    good = ["tree/" + L.HERE_REL + "/repro_common.py", "tree/" + L.ARCHIVE_REL, "ref/final.pt", "cand/final.pt",
            "claude/p1b_machine.py", "anchors.json"]
    assert L.custody_refusals(bad + good) == bad
