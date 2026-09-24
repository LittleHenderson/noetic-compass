"""Tests for E1b (readout plan item 10). CLAUDE_BUILT_CLAUDE_CHECKED. Laptop-safe: no torch, small JSON, one process
(one test starts a two-worker pool of pure-Python workers to exercise the parallel path).

THE ACCEPTANCE CHECK (plan item 10): an end-to-end laptop run on a THROWAWAY public salt with tiny packets and stand-in
predictions emits every label and publishes no digest covering an answer; the stage script passes bash -n.

The builder code is taken from git objects at HSET2_COMMIT (the pushed pre-salt tip of claude/hset2-build-20260924),
never from a working copy, and written to a temporary folder outside every git work tree.
"""
import hashlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import custody_manifest as CM  # noqa: E402
import e1b_machine as M  # noqa: E402
import e1b_scorer as S  # noqa: E402
import e1b_throwaway as T  # noqa: E402
import launch as L  # noqa: E402

HSET2_COMMIT = "17d6ad655a2e9205bd6253f39ee230299defdbf6"
DESIGN = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_eval_design_20260923/"
SEED = "acceptance-20260924"
HEX = re.compile(r"[0-9a-f]{12,}")
REQUIRED_WORDS = {S.PASS, S.FAIL, S.NOT_TESTABLE, S.MGO, S.IAU, S.INCOMPLETE, S.EXP_PASS, S.EXP_NO, S.NOT_READ_GATE,
                  S.NO_REG, S.REG, S.LEFT_OUT}


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def code(tmp_path_factory):
    folder = tmp_path_factory.mktemp("hset2code")
    assert M.inside_git(folder) is False
    top = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         check=True).stdout.strip()
    raw = subprocess.run(["git", "-C", top, "archive", "--format=tar", HSET2_COMMIT, "--"]
                         + [DESIGN + rel for rel in L.BUILDER_FILES.values()], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        for member in tar.getmembers():
            if member.isfile():
                target = folder / member.name[len(DESIGN):]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
    assert sorted(str(p.relative_to(folder)).replace("\\", "/") for p in folder.rglob("*.py")) == sorted(
        L.BUILDER_FILES.values())
    return folder


@pytest.fixture(scope="module")
def builder(code):
    return S.load_builder(code)


def run(code, folder, scenario, *, processes=1, patch=None, extra=()):
    fx = T.build(SEED, folder / "fixture", code, scenario)
    if patch:
        path = folder / "fixture" / "stand_in_strength.json"
        strength = json.loads(path.read_bytes())
        patch(strength)
        path.write_text(json.dumps(strength), encoding="utf-8")
    out_pub, out_sealed = folder / "public", folder / "sealed"
    argv = ["--hset2-dir", str(code), "--out-public", str(out_pub), "--out-sealed", str(out_sealed),
            "--processes", str(processes)] + fx["argv"] + list(extra)
    code_ = M.main(argv)
    doc_path = out_pub / "THROWAWAY_E1B_READOUT_PUBLIC.json"
    doc = json.loads(doc_path.read_bytes()) if doc_path.is_file() else None
    return code_, doc, fx, out_pub, out_sealed


def allowed_digests(code, builder, fx, folder):
    """Every digest the public output may carry, computed HERE from the inputs (never read from the output)."""
    B, _ = builder
    ok = set(S.builder_identity(B).values())
    ok |= {S.lf_sha256(HERE / n) for n in ("e1b_scorer.py", "e1b_machine.py", "custody_manifest.py")}
    fixture = folder / "fixture"
    for name in ("THROWAWAY_HSET2_BUILD_SUMMARY.json", "runs.json", "item2_reading.json", "matched_start.json",
                 "reproduction_reading.json", "inference_ruling.json", "touched_course.json", "touched_fixtures.json",
                 "touched_probe.json") + tuple("h1h2_%d.json" % s for s in S.SEEDS):
        if (fixture / name).is_file():
            ok.add(sha((fixture / name).read_bytes()))
    ok |= {r["checkpoint_sha256"] for r in json.loads((fixture / "runs.json").read_bytes())["runs"]}
    return ok


def answer_revealing(fx, out_sealed):
    """Strings that must never be public: the sealed input's digest, every sealed output's digest, and every item's
    ids, packet digest, admissible answer and answer digest; plus the TEST class keys."""
    bad = {sha(pathlib.Path(fx["sealed"]).read_bytes())}
    bad |= {sha(p.read_bytes()) for p in pathlib.Path(out_sealed).glob("*") if p.is_file()}
    for item in fx["items"]:
        ev = item["evaluation"]
        bad |= {item["item_id"], item["cluster_id"], ev["record_id"], ev["packet_sha256"]}
        for value in ev["admissible_values"]:
            text = json.dumps(value, sort_keys=True, separators=(",", ":"))
            bad |= {sha(text.encode()), sha((text + "|true").encode()), sha((item["item_id"] + text).encode())}
            if isinstance(value, dict) and value.get("world_id"):
                bad.add(value["world_id"])
    bad |= set(fx["test6"])
    return bad


def assert_custody(text, allowed, bad):
    tokens = set(HEX.findall(text))
    stray = sorted(t for t in tokens if not any(t in a for a in allowed))
    assert not stray, "public output carries digests that are not known non-answer inputs: %s" % stray[:5]
    leaked = sorted(b for b in bad if b and b in text)
    assert not leaked, "public output carries sealed or answer-revealing strings: %s" % leaked[:5]


def check_every_label(doc, builder):
    B, _ = builder
    keys = {S.label_key(entry) for entry in doc["labels"]}
    runs = {r["run_id"] for r in doc["runs"]}
    expected = S.expected_label_keys(B) | {("RUN_READING", r) for r in runs} | {("STAGE0_CUSTODY_MANIFEST",)}
    missing = expected - keys
    assert not missing, "labels not printed: %s" % sorted(missing)[:8]
    vocabulary = {w for words in S.STATUS_VOCABULARY.values() for w in words}
    assert all(entry["status"] in vocabulary for entry in doc["labels"])
    words = {entry["status"] for entry in doc["labels"]}
    for entry in doc["labels"]:
        words |= set(entry.get("status_words_that_apply", ()))
    return words


# ============================================================================================ THE ACCEPTANCE CHECK
def test_acceptance_every_label_no_answer_digest_across_scenarios(code, builder, tmp_path, capsys):
    """Five throwaway scenarios, one process each. Every label is printed every time; across the scenarios every
    status word appears; neither the public file nor the log carries a digest covering an answer."""
    words, confirmatory = set(), {}

    def regression_and_fail(strength):
        for run_id in strength:                                  # the repaired arm loses every 5-node correspondence
            strength[run_id][S.CORR5] = {"p": 0.0 if run_id.startswith("R") else 1.0, "key": run_id}

    cases = [("all_clear", None), ("gate_open_no_ruling", None), ("controls_not_admitted", None),
             ("matched_start_failed", None), ("all_clear", regression_and_fail)]
    for index, (scenario, patch) in enumerate(cases):
        folder = tmp_path / ("case%d_%s" % (index, scenario))
        exit_code, doc, fx, out_pub, out_sealed = run(code, folder, scenario, patch=patch)
        log = capsys.readouterr().out
        assert exit_code == 0 and doc["status"] == "READOUT_WRITTEN", (scenario, exit_code)
        assert doc["readout_mode"] == "THROWAWAY_STAND_IN_NOT_A_RESULT" and doc["throwaway_warning"]
        words |= check_every_label(doc, builder)
        conf = [e for e in doc["labels"] if e["label"] == S.CONFIRMATORY][0]
        confirmatory["%d_%s" % (index, scenario)] = conf["status"]
        allowed, bad = allowed_digests(code, builder, fx, folder), answer_revealing(fx, out_sealed)
        for path in out_pub.iterdir():
            assert_custody(path.read_text(encoding="utf-8"), allowed, bad)
        assert_custody(log, allowed, bad)
        assert (out_sealed / "THROWAWAY_E1B_PREDICTIONS_SEALED.jsonl").is_file()
        if conf["status"] == S.PASS:
            assert conf["caption"] == S.CAPTION_A2_3
        else:
            assert conf["caption"] is None
    assert confirmatory == {"0_all_clear": S.PASS, "1_gate_open_no_ruling": S.MGO,
                            "2_controls_not_admitted": S.INCOMPLETE, "3_matched_start_failed": S.INCOMPLETE,
                            "4_all_clear": S.FAIL}
    assert REQUIRED_WORDS <= words, sorted(REQUIRED_WORDS - words)


def test_gate_open_scenario_masks_the_repaired_analogy_cell(code, tmp_path, capsys):
    exit_code, doc, fx, _, out_sealed = run(code, tmp_path, "gate_open_no_ruling")
    capsys.readouterr()
    conf = [e for e in doc["labels"] if e["label"] == S.CONFIRMATORY][0]
    assert conf["status"] == S.MGO and S.IAU in conf["status_words_that_apply"]
    rows = [json.loads(line) for line in (out_sealed / "THROWAWAY_E1B_PREDICTIONS_SEALED.jsonl").read_text().splitlines()]
    analogy = {i["item_id"] for i in fx["items"] if i["cell"] == "ANALOGY"}
    assert not [r for r in rows if r["run_id"].startswith("R") and r["item_id"] in analogy]   # never predicted
    assert [r for r in rows if r["run_id"] == "U17" and r["item_id"] in analogy]
    for seed in S.SEEDS:
        assert doc["paired"][str(seed)][S.ANALOGY_CELL] is None


def test_matched_start_failure_withholds_every_side_by_side_number(code, tmp_path, capsys):
    exit_code, doc, _, _, out_sealed = run(code, tmp_path, "matched_start_failed")
    capsys.readouterr()
    for seed in S.SEEDS:
        assert all(v is None for v in doc["paired"][str(seed)].values())
        for gate in ("H1", "H2"):
            assert doc["regression"][str(seed)][gate]["counts"] is None
            assert doc["regression"][str(seed)][gate]["status"] == S.INCOMPLETE
    rows = (out_sealed / "THROWAWAY_E1B_PREDICTIONS_SEALED.jsonl").read_text().splitlines()
    assert not [r for r in rows if json.loads(r)["run_id"].startswith("R")]


def test_item_fault_makes_the_run_invalid_and_its_message_stays_sealed(code, tmp_path, capsys):
    def fault(strength):
        strength["R18"][S.ANALOGY_CELL] = {"p": 1.0, "key": "R18", "fault": True}
    exit_code, doc, fx, out_pub, out_sealed = run(code, tmp_path, "all_clear", patch=fault)
    log = capsys.readouterr().out
    state = {r["run_id"]: r["status"] for r in doc["runs"]}
    assert state["R18"] == "RUN_READING_INVALID" and doc["stage3_predictions"]["errors_by_type"]["RuntimeError"] > 0
    conf = [e for e in doc["labels"] if e["label"] == S.CONFIRMATORY][0]
    assert conf["status"] == S.INCOMPLETE
    text = (out_pub / "THROWAWAY_E1B_READOUT_PUBLIC.json").read_text(encoding="utf-8") + log
    assert "STAND_IN_FAULT" not in text
    assert "STAND_IN_FAULT" in (out_sealed / "THROWAWAY_E1B_READOUT_SEALED.json").read_text(encoding="utf-8")


def test_two_worker_pool_gives_the_same_labels(code, tmp_path, capsys):
    _, one, *_ = run(code, tmp_path / "one", "all_clear", processes=1)
    _, two, *_ = run(code, tmp_path / "two", "all_clear", processes=2)
    capsys.readouterr()
    assert [(S.label_key(e), e["status"]) for e in one["labels"]] == [(S.label_key(e), e["status"]) for e in two["labels"]]
    assert two["stage3_predictions"]["processes"] == 2


def test_custody_collision_stops_before_any_prediction(code, tmp_path, capsys):
    exit_code, doc, fx, out_pub, out_sealed = run(code, tmp_path, "custody_collision")
    log = capsys.readouterr().out
    assert exit_code == M.EXIT_CUSTODY and doc["status"] == "CUSTODY_STOP_NO_TEST_READ"
    assert [e["label"] for e in doc["labels"]] == ["STAGE0_CUSTODY_MANIFEST"]
    assert doc["stage0_custody"]["matches_m1"] == 1 and doc["stage0_custody"]["matches_m2"] == 1
    assert not (out_sealed / "THROWAWAY_E1B_PREDICTIONS_SEALED.jsonl").exists()
    sealed = json.loads((out_sealed / "THROWAWAY_E1B_READOUT_SEALED.json").read_bytes())
    assert len(sealed["stage0_detail"]["matching_touched_shapes"]) == 1
    text = (out_pub / "THROWAWAY_E1B_READOUT_PUBLIC.json").read_text(encoding="utf-8") + log
    assert fx["test6"][3] not in text


# ============================================================================================ refusals
def test_refusals(code, builder, tmp_path, capsys):
    fx = T.build(SEED, tmp_path / "fixture", code, "all_clear")
    base = ["--hset2-dir", str(code), "--processes", "1"] + fx["argv"]
    # an output folder inside a git work tree is refused before anything is written
    inside = HERE / "must_not_exist_e1b_test_output"
    assert M.main(base + ["--out-public", str(inside), "--out-sealed", str(tmp_path / "s0")]) == M.EXIT_SETUP
    assert not inside.exists()
    # a sealed file that is not the one the summary binds
    sealed_path = pathlib.Path(fx["sealed"])
    original = sealed_path.read_bytes()
    sealed_path.write_bytes(original + b" ")
    assert M.main(base + ["--out-public", str(tmp_path / "p1"), "--out-sealed", str(tmp_path / "s1")]) == M.EXIT_SETUP
    sealed_path.write_bytes(original)
    # the stand-in engine refuses the real (SEALED_BUILD) mode
    B, _ = builder
    doc = json.loads(original)
    doc["identity"]["mode"] = "SEALED_BUILD"
    real_sealed = tmp_path / "fixture" / "HSET2_SEALED_TEST.json"
    real_sealed.write_bytes(json.dumps(doc).encode())
    summary_path = pathlib.Path(fx["summary"])
    summary = json.loads(summary_path.read_bytes())
    summary["mode"], summary["files"] = "SEALED_BUILD", {"HSET2_SEALED_TEST.json": sha(real_sealed.read_bytes())}
    real_summary = tmp_path / "fixture" / "HSET2_BUILD_SUMMARY.json"
    real_summary.write_bytes(json.dumps(summary).encode())
    argv = [a for a in base]
    argv[argv.index("--sealed-file") + 1] = str(real_sealed)
    argv[argv.index("--build-summary") + 1] = str(real_summary)
    assert M.main(argv + ["--out-public", str(tmp_path / "p2"), "--out-sealed", str(tmp_path / "s2")]) == M.EXIT_SETUP
    out = capsys.readouterr().out
    assert "STAND_IN_ONLY_WITH_A_THROWAWAY_FIXTURE" in out and "SUMMARY_NOT_BOUND_TO_THIS_SEALED_FILE" in out
    assert "OUTPUT_FOLDER_INSIDE_A_GIT_WORK_TREE" in out
    # builder code that is not the sealed build's
    identity = dict(S.builder_identity(B))
    identity["builder_sha256_lf"] = "0" * 64
    with pytest.raises(S.Refused, match="BUILDER_CODE_IS_NOT_THE_SEALED_BUILDS"):
        S.check_builder_identity(B, identity)


# ============================================================================================ stage 0 and the rules
def test_custody_manifest_unit(code, builder, tmp_path):
    import hset2_stage0_public as S0
    import oracle_isomorphism as oracle
    key = S0.class_key(oracle.canonical_form(6, [(0, 1), (0, 2), (1, 3), (2, 4), (3, 5)]))
    forbidden = [key]
    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps({"w": {"nodes": 5, "edges": [[0, 1], [1, 2], [2, 3], [3, 4]]}}))
    copy = tmp_path / "copy.json"                                  # the forbidden class, nodes renamed
    copy.write_text(json.dumps({"w": {"labels": list("abcdef"), "edges": [[5, 4], [5, 3], [4, 2], [3, 1], [2, 0]]}}))
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"nodes": [{"ref": "x/n0"}], "contains": [{"source": "x/n0", "target": "x/n9"}]}))
    every = ["%s=NONE:test" % k for k in CM.KINDS if k != "fixture"]
    ok, _ = CM.check(CM.parse_touched(every + ["fixture=%s" % clean]), forbidden, oracle, S0.class_key)
    assert ok["status"] == CM.PASS_WORD
    hit, detail = CM.check(CM.parse_touched(every + ["fixture=%s" % copy]), forbidden, oracle, S0.class_key)
    assert hit["status"] == CM.STOP_WORD and hit["matches_m1"] == hit["matches_m2"] == 1 and key not in json.dumps(hit)
    assert len(detail["matching_touched_shapes"]) == 1
    part, _ = CM.check(CM.parse_touched(["fixture=%s" % clean]), forbidden, oracle, S0.class_key)
    assert part["status"] == CM.STOP_WORD and part["reasons"][0].startswith("CUSTODY_MANIFEST_INCOMPLETE")
    bad, _ = CM.check(CM.parse_touched(every + ["fixture=%s" % broken]), forbidden, oracle, S0.class_key)
    assert bad["status"] == CM.STOP_WORD and any(r.startswith("CUSTODY_MANIFEST_UNREADABLE") for r in bad["reasons"])

    class BlindM1:                                               # a broken first method: the two must then disagree
        canonical_form = staticmethod(lambda n, e: (n, ()))
        all_isomorphisms_m2 = staticmethod(oracle.all_isomorphisms_m2)
    split, _ = CM.check(CM.parse_touched(every + ["fixture=%s" % copy]), forbidden, BlindM1, S0.class_key)
    assert split["status"] == CM.STOP_WORD and any(r.startswith("CUSTODY_METHODS_DISAGREE") for r in split["reasons"])


def test_regression_rule_seven_losses_flagged_six_not(builder):
    B, A = builder

    def members(n):
        return [{"cluster_id": "c%d" % i, "view_group": "g%d" % i, "role_classes": ["k%d" % i]} for i in range(n)]
    for losses, flagged in ((7, True), (6, False)):
        m = members(losses)
        block = S.pair_block(B, A, m, {c["cluster_id"]: False for c in m}, {c["cluster_id"]: True for c in m})
        assert block["regression"]["c_prime_losses"] == losses and block["regression"]["flagged"] is flagged


def test_prerequisite_readers_fail_closed():
    runs = [{"arm": "repaired", "seed": s, "checkpoint_sha256": "a" * 64} for s in S.SEEDS]
    assert S.read_item2(None, runs)["gate"] == S.MGO
    assert S.read_item2(b"{not json", runs)["gate"] == S.MGO
    assert S.read_verdict(None, S.SCHEMA_MATCHED_START, S.MATCHED, "MATCHED_START")["admitted"] is False
    assert S.read_inference_ruling(None)["supported"] is False
    assert S.read_h1h2(json.dumps({"reader": S.H1H2_READER, "seed": 1}).encode(), S.SEEDS[0])["state"] == "INVALID"


# ============================================================================================ the job folder
def git_bash():
    exec_path = pathlib.Path(subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip())
    for parent in exec_path.parents:
        for rel in ("bin/bash.exe", "usr/bin/bash.exe", "bin/bash"):
            if (parent / rel).is_file():
                return str(parent / rel)
    found = shutil.which("bash")
    return found if found and "system32" not in found.lower() else None


def test_stage_script_passes_bash_n(tmp_path):
    bash = git_bash()
    assert bash, "no POSIX bash found"
    raw = subprocess.run([bash, "-n", str(HERE / "job.sh.template")], capture_output=True, text=True)
    assert raw.returncode == 0, raw.stderr
    template = (HERE / "job.sh.template").read_text(encoding="utf-8")
    fits, detail = L.user_data_fits(template)                    # five 2,048-byte links (P1a's convention)
    assert fits, detail
    urls = {k: "https://" + "L" * (L.LINK_BYTES_ASSUMED - 8) for k in
            ("bundle", "sealed_input", "results", "sealed_results", "progress")}
    script = L.render(template, urls, "b" * 64, "c" * 64)
    assert not re.search(r"__[A-Z][A-Z0-9_]*__", script) and len(script.encode()) < L.USER_DATA_LIMIT
    assert "--args-file e1b/readout_args.json" in script
    path = tmp_path / "rendered.sh"
    path.write_text(script, encoding="utf-8", newline="\n")
    rendered = subprocess.run([bash, "-n", str(path)], capture_output=True, text=True)
    assert rendered.returncode == 0, rendered.stderr


def test_launcher_limits_custody_and_gates(tmp_path):
    assert L.worst_case_usd() <= L.COST_CAP_USD == 2.00 and L.ALLOWANCE_USD == 0.10
    assert round(L.worst_case_usd(), 4) == 1.6639
    assert "g7.*" in L.GPU_FAMILIES and "g4dn.*" in L.GPU_FAMILIES
    assert L.custody_refusals(["hset2code/hset2/hset2_presalt_manifest.py", "x/HSET2_SEALED_TEST.json",
                               "tree/cncm/a.py"]) == ["hset2code/hset2/hset2_presalt_manifest.py",
                                                      "x/HSET2_SEALED_TEST.json"]
    with pytest.raises(L.Refused):
        L.main(["--dry-run", "--inputs", str(tmp_path / "E1B_INPUTS.json")])      # not written yet: refused, no AWS

    class Stub:
        def __init__(self, records):
            self.records = records

        def read(self, commit, path):
            return json.dumps(self.records[path]).encode()
    good = {"m": {"schema": "helm.matched-start-reading/0.1", "verdict": "MATCHED_START_REPRODUCED"},
            "r": {"schema": "cncm.helm-unchanged-reproduction-reading/0.5",
                  "verdict": "STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED"},
            "i": {"schema": "claude.item2-reading/0.3", "outcome": "ITEM2_FAIL:x"},
            "s": {"mode": "SEALED_BUILD", "build_ok": True}}
    entries = [("inputs/matched_start.json", {"commit": "c", "path": "m"}),
               ("inputs/reproduction_reading.json", {"commit": "c", "path": "r"}),
               ("inputs/item2_reading.json", {"commit": "c", "path": "i"}),
               ("inputs/build_summary.json", {"commit": "c", "path": "s"})]
    assert L.gate_records(Stub(good), entries)["mode"] == "SEALED_BUILD"
    for key, change in (("m", {"verdict": "MATCHED_START_NOT_REPRODUCED"}),
                        ("r", {"verdict": "DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY"}),
                        ("i", {"schema": "claude.item2-reading/0.2"}), ("s", {"mode": "THROWAWAY_SALTS_NOT_A_BUILD"})):
        records = json.loads(json.dumps(good))
        records[key].update(change)
        with pytest.raises(L.Refused):
            L.gate_records(Stub(records), entries)


def test_args_file_expands_in_place(tmp_path):
    path = tmp_path / "readout_args.json"
    path.write_text(json.dumps(["--touched", "dev_reading=NONE:no DEV reading; see s8", "--h1h2", "20260917=x.json"]))
    assert M.expand_args_file(["--a", "1", "--args-file", str(path), "--b"]) == [
        "--a", "1", "--touched", "dev_reading=NONE:no DEV reading; see s8", "--h1h2", "20260917=x.json", "--b"]


def test_no_torch_was_imported():
    assert "torch" not in sys.modules
