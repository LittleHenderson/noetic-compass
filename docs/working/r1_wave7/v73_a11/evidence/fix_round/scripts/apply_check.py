"""apply_check.py <zip> <work_dir> -- the fix round's checks of apply_amendment_11.py's new guards (reviewer G-8), each on a
FRESH extract of the sealed v9 zip under <work_dir>: (a) a tampered target file -> refused, nothing written; (b) a tampered
new-file source -> refused; (c) the tree's own freeze pin disagrees -> refused; (d) section 22 not the last section ->
refused (in-process, with the v9 pin of the preregistration and the tree's freeze pin both set to the modified bytes so
only the new rule can refuse); (e) a clean apply -> 7 files, no .partial left; a second apply -> refused. Writes one JSON
line per case to stdout. Scratch only."""
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

ZIP, WORK = Path(sys.argv[1]), Path(sys.argv[2])
TOOL_DIR = Path(r"C:\tmp\helm-ctt2r-c49-read\docs\working\r1_wave7\a_r1w7_11")
TOOL = TOOL_DIR / "apply_amendment_11.py"
TOP = "HELM_R1_W7_20261020"
PY = [sys.executable, "-X", "utf8", "-B", "-I"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fresh(name):
    d = WORK / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    zipfile.ZipFile(ZIP).extractall(d)
    return d / TOP


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def run_tool(root, tool=TOOL):
    r = subprocess.run(PY + [str(tool), str(root)], capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()


def case(label, root, before, code, lines, want_code, want_text=None):
    after = snapshot(root)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    partial = sorted(k for k in after if k.endswith(".partial"))
    ok = code == want_code and (want_text is None or any(want_text in x for x in lines))
    if want_code != 0:
        ok = ok and changed == [] and partial == []
    row = {"case": label, "exit": code, "want_exit": want_code, "changed_files": changed, "partial_files": partial,
           "out_tail": lines[-4:], "ok": ok}
    print(json.dumps(row, sort_keys=True))
    return ok


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    oks = []
    # (a) a tampered target file
    root = fresh("a_target")
    p = root / "r1w7" / "score_w7.py"
    p.write_bytes(p.read_bytes() + b"# tampered\n")
    before = snapshot(root)
    oks.append(case("a_tampered_target", root, before, *run_tool(root), 4, "is not the v9 member"))
    # (b) a tampered new-file source (a copy of the tool and its sources in a throwaway folder)
    tdir = WORK / "b_tool"
    if tdir.exists():
        shutil.rmtree(tdir)
    shutil.copytree(TOOL_DIR, tdir)
    (tdir / "honest_ask_w7.py").write_bytes((tdir / "honest_ask_w7.py").read_bytes() + b"# tampered\n")
    root = fresh("b_source")
    before = snapshot(root)
    oks.append(case("b_tampered_new_file_source", root, before, *run_tool(root, tdir / "apply_amendment_11.py"), 4,
                    "not the listed bytes"))
    # (c) the tree's own freeze pin disagrees
    root = fresh("c_freeze")
    fz = root / "PACKAGE_FREEZE.json"
    d = json.loads(fz.read_text(encoding="utf-8"))
    d["members"]["r1w7/merge_r1w7.py"]["sha256"] = "0" * 64
    fz.write_text(json.dumps(d, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    before = snapshot(root)
    oks.append(case("c_freeze_pin_disagrees", root, before, *run_tool(root), 4, "PACKAGE_FREEZE.json member pin"))
    # (d) section 22 not last (in-process; both pins moved to the modified bytes so only the new rule refuses)
    root = fresh("d_order")
    pre = root / "PREREGISTRATION_R1W7.md"
    pre.write_bytes(pre.read_bytes() + b"\n## 24. Not a real section\n\nText.\n")
    new_sha = sha(pre.read_bytes())
    d = json.loads((root / "PACKAGE_FREEZE.json").read_text(encoding="utf-8"))
    d["members"]["PREREGISTRATION_R1W7.md"]["sha256"] = new_sha
    (root / "PACKAGE_FREEZE.json").write_text(json.dumps(d, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("apply_amendment_11_probe", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.V9_TARGET_SHA256 = dict(mod.V9_TARGET_SHA256, **{"PREREGISTRATION_R1W7.md": new_sha})
    before = snapshot(root)
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = mod.main([str(root)])
    oks.append(case("d_section_22_not_last", root, before, code, buf.getvalue().strip().splitlines(), 4,
                    "section 22 is not the last section"))
    # (e) a clean apply, then a second apply
    root = fresh("e_clean")
    before = snapshot(root)
    code, lines = run_tool(root)
    after = snapshot(root)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    partial = sorted(k for k in after if k.endswith(".partial"))
    ok = code == 0 and len(changed) == 7 and partial == []
    print(json.dumps({"case": "e_clean_apply", "exit": code, "changed_files": changed, "partial_files": partial,
                      "out": lines, "ok": ok}, sort_keys=True))
    oks.append(ok)
    before = snapshot(root)
    oks.append(case("e_second_apply_refused", root, before, *run_tool(root), 4, "REFUSED"))
    print("APPLY_CHECK_ALL_OK", all(oks), f"{sum(oks)}/{len(oks)}")
    return 0 if all(oks) else 1


if __name__ == "__main__":
    sys.exit(main())
