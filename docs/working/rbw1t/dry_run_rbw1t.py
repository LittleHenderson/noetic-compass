"""Builder dry run (NOT in the sealed package): the whole RB-W1T pipeline on the PUBLISHED practice seed only.

    python -X utf8 -B dry_run_rbw1t.py <package dir> <out dir>

1. zip the package as it stands (a DRY zip, never the sealed one); a MOCK approval record with the real owner line;
2. the custodian's `seal --practice-mock` (draw = the published practice draw; the seed derived from the DRY zip is
   recorded but not used); the receiver's check;
3. the host pool with --dry-practice (the spent X5 units are skipped: the builder never touches the spent files);
4. HELM's suites (on a scratch copy of helm_now) and the RB-W1T suites; a MOCK run record;
5. the frozen reader on all of it (it must print INSTRUMENT_ERROR: I0 practice mock, I6 X5 units missing);
6. the D-W-1 sensitivity: the WIDE arm on the same items with "ran out of {HEAD}" lessons (X-REAL v2's form).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
FRAMES = r"C:\Users\wakil\Documents\Codex\2026-10-19\x_real\frames"
W1 = r"C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3"
sys.path.insert(0, str(PKG))
from rbw1t import common_rbw1t as C   # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd, log, extra_env=None, timeout=280):
    env = dict(os.environ, PYTHONPATH=str(PKG), PYTHONDONTWRITEBYTECODE="1", HELM_CANONICAL_BRAIN_DIR=W1)
    env.pop("HELM_WIDE_BRAIN", None)
    env.update(extra_env or {})
    t0 = time.time()
    with open(log, "wb") as fh:
        code = subprocess.run(cmd, cwd=str(cwd), env=env, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
    return code, round(time.time() - t0, 2)


def parse(text):
    summary = re.findall(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$', text, flags=re.MULTILINE)
    ran = re.findall(r'^Ran ([0-9]+) tests?', text, flags=re.MULTILINE)
    return {"verdict": summary[0][0] if len(summary) == 1 else None, "ran": [int(x) for x in ran],
            "detail": summary[0][1] if len(summary) == 1 else None}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "logs").mkdir(parents=True)
    timing = {}
    # 1. dry zip + mock approval
    z = OUT / "DRY_PACKAGE_NOT_SEALED.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                zf.write(p, (C.PACKAGE_DIR + "/" + p.relative_to(PKG).as_posix()))
    zsha = sha(z)
    line = C.OWNER_LINE
    approval = {"schema": "helm.rbw1t.approval/1", "MOCK_FOR_DRY_RUN": True, "owner_line_verbatim": line,
                "owner_line_utf8_bytes": len(line.encode("utf-8")),
                "owner_line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                "package_zip_sha256": zsha, "package_freeze_sha256": "DRY_NO_FREEZE", "cap_usd": C.CAP_USD,
                "attempts": C.ATTEMPTS}
    C.write_json(OUT / "APPROVAL_MOCK_DRY.json", approval)
    # 2. custody (practice mock)
    code, s = run([sys.executable, "-X", "utf8", "-B", "-m", "rbw1t.custody_rbw1t", "seal", "--frames-dir", FRAMES,
                   "--approval", str(OUT / "APPROVAL_MOCK_DRY.json"), "--zip", str(z), "--out-dir",
                   str(OUT / "custody"), "--practice-mock"], PKG, OUT / "logs" / "custody.log")
    timing["custody_seal"] = s
    assert code == 0, (OUT / "logs" / "custody.log").read_text()
    carrier_inputs = json.loads((OUT / "custody" / "carrier" / "rw" / "INPUTS_RBW1T.json").read_text(encoding="utf-8"))
    practice_inputs = json.loads((PKG / "practice" / "INPUTS_PRACTICE_RBW1T.json").read_text(encoding="utf-8"))
    same_as_published = carrier_inputs["items"] == practice_inputs["items"]
    # 3. host pool, dry
    isha = sha(OUT / "custody" / "carrier" / "rw" / "INPUTS_RBW1T.json")
    code, s = run([sys.executable, "-X", "utf8", "-B", "-m", "rbw1t.pool_rbw1t", "run", "--inputs",
                   str(OUT / "custody" / "carrier" / "rw" / "INPUTS_RBW1T.json"), "--inputs-sha256", isha,
                   "--spent-dir", str(OUT / "no_spent_files"), "--out-dir", str(OUT / "host_out"), "--workers", "1",
                   "--dry-practice"], PKG, OUT / "logs" / "pool.log")
    timing["pool"] = s
    # 4. suites
    helm_copy = OUT / "helm_now_tests"
    shutil.copytree(PKG / "helm_now", helm_copy)
    hc, s1 = run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "test_helm_brain_wide",
                  "test_helm_end_to_end_loop", "test_helm_english_in", "test_helm_english_in_stock_frame",
                  "test_helm_voice", "test_helm_faces_in", "test_helm_triad"], helm_copy, OUT / "logs" / "unittest_helm.log",
                 {"PYTHONPATH": str(helm_copy)})
    rc, s2 = run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "tests_rbw1t.test_units_rbw1t",
                  "tests_rbw1t.test_kit_rbw1t"], PKG, OUT / "logs" / "unittest_rbw1t.log")
    timing["helm_suites"], timing["rbw1t_suites"] = s1, s2
    shutil.rmtree(helm_copy)
    w1tree = hashlib.sha256(b"".join(p.relative_to(W1).as_posix().encode() + sha(p).encode()
                                     for p in sorted(Path(W1).rglob("*")) if p.is_file()
                                     and "__pycache__" not in p.parts)).hexdigest()
    rr = {"schema": "helm.rbw1t.run-record/1", "MOCK_FOR_DRY_RUN": True, "package_freeze_sha256": "DRY_NO_FREEZE",
          "package_members": {"bad": []}, "carrier_files": sorted(p.name for p in (OUT / "custody" / "carrier" / "rw")
                                                                 .iterdir()),
          "helm_exit_code": hc, "helm_parsed": parse((OUT / "logs" / "unittest_helm.log").read_text(errors="replace")),
          "rbw1t_exit_code": rc,
          "rbw1t_parsed": parse((OUT / "logs" / "unittest_rbw1t.log").read_text(errors="replace")),
          "w1_tree_sha256_start": w1tree, "w1_tree_sha256_end": w1tree}
    C.write_json(OUT / "RUN_RECORD_MOCK_DRY.json", rr)
    # 5. the reader
    mi = {"practice_mock": True, "host_reading": str(OUT / "host_out" / "RBW1T_HOST.json"),
          "host_reading_sha256": sha(OUT / "host_out" / "RBW1T_HOST.json"),
          "run_record": str(OUT / "RUN_RECORD_MOCK_DRY.json"), "run_record_sha256": sha(OUT / "RUN_RECORD_MOCK_DRY.json"),
          "keys": str(OUT / "custody" / "exam" / "KEYS_RBW1T.json"),
          "keys_sha256": sha(OUT / "custody" / "exam" / "KEYS_RBW1T.json"),
          "approval_record": str(OUT / "APPROVAL_MOCK_DRY.json"),
          "approval_record_sha256": sha(OUT / "APPROVAL_MOCK_DRY.json"),
          "exam_dir": str(OUT / "custody" / "exam"), "carrier_dir": str(OUT / "custody" / "carrier" / "rw"),
          "frames_dir": FRAMES, "package_zip": str(z), "package_zip_sha256": zsha,
          "package_freeze_sha256": "DRY_NO_FREEZE"}
    C.write_json(OUT / "MERGE_INPUT_DRY.json", mi)
    code, s = run([sys.executable, "-X", "utf8", "-B", "-m", "rbw1t.merge_rbw1t", "--merge-input",
                   str(OUT / "MERGE_INPUT_DRY.json"), "--out", str(OUT / "DRY_READING_RBW1T.json")], PKG,
                  OUT / "logs" / "merge.log")
    timing["merge"] = s
    assert code == 0, (OUT / "logs" / "merge.log").read_text()
    # 6. D-W-1 sensitivity: HEAD-only ran-out names
    pr = json.loads((PKG / "practice" / "PRACTICE_DRAW_RBW1T.json").read_text(encoding="utf-8"))
    from rbw1t import exam_rbw1t as X
    alt = []
    for it in pr["items"]:
        v = X.host_view(it)
        heads = [k["head"] for k in next(k for k in pr["keys"] if k["id"] == it["id"])["lessons"]]
        names = [X.G.parse_line(x) for x in it["raw_lines"]]
        turns = list(v["turns"])
        for j, (p, h) in enumerate(zip(names, heads)):
            phrase = X.name_phrase(p)
            assert turns[j].endswith("and ran out of " + phrase + ".")
            turns[j] = turns[j][: -len(phrase) - 1] + h + "."
        alt.append(dict(v, turns=turns))
    C.write_json(OUT / "INPUTS_SENSITIVITY_HEAD_ONLY.json", {"schema": "helm.rbw1t.inputs/1", "items": alt})
    asha = sha(OUT / "INPUTS_SENSITIVITY_HEAD_ONLY.json")
    code, s = run([sys.executable, "-X", "utf8", "-B", "-m", "rbw1t.arms_rbw1t", "main", "--arm", "WIDE", "--inputs",
                   str(OUT / "INPUTS_SENSITIVITY_HEAD_ONLY.json"), "--inputs-sha256", asha, "--out",
                   str(OUT / "SENS_MAIN_WIDE_HEAD_ONLY.json")], PKG, OUT / "logs" / "sens.log")
    from rbw1t import merge_rbw1t as MR
    keys = {k["id"]: k for k in pr["keys"]}
    sens = MR.score_main(json.loads((OUT / "SENS_MAIN_WIDE_HEAD_ONLY.json").read_text(encoding="utf-8")), keys, {})
    reading = json.loads((OUT / "DRY_READING_RBW1T.json").read_text(encoding="utf-8"))
    summary = {"schema": "helm.rbw1t.dry-run/1", "practice_seed_text": C.PRACTICE_SEED_TEXT,
               "carrier_inputs_equal_published_practice": same_as_published, "timing_seconds": timing,
               "verdict": reading["verdict"], "status_word": reading["status_word"],
               "instrument_rows": reading["instrument_rows"], "hard_gates": reading["hard_gates"],
               "marks": reading["marks"], "main": reading["main"], "nh": {k: {x: v[x] for x in v if x != "lost_ids"}
                                                                           for k, v in reading["nh"].items()},
               "notes": reading["notes"], "sensitivity_D_W_1_head_only_WIDE": sens["totals"],
               "helm_suites": rr["helm_parsed"], "rbw1t_suites": rr["rbw1t_parsed"]}
    C.write_json(OUT / "DRY_RUN_SUMMARY_RBW1T.json", summary)
    print(json.dumps({k: summary[k] for k in ("verdict", "status_word", "marks", "timing_seconds",
                                              "carrier_inputs_equal_published_practice")}, sort_keys=True))


if __name__ == "__main__":
    main()
