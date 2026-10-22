"""assemble_evidence.py -- reviewer G-5: copy the scratch evidence of reader v7.3, A-R1W7-11 and the fix round into
docs/working/r1_wave7/v73_a11/evidence/ (in the worktree; no git command is run), then write MANIFEST.sha256 (sha256sum
format, paths relative to the evidence folder) and EVIDENCE_INDEX.json (which reviewer item each file answers). Refuses
to overwrite an existing evidence folder. Copies bytes as they are (LF/CRLF untouched)."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

S = Path(r"C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS"
         r"\3b14b8d6-0752-4f48-8a9b-4f5215493826\scratchpad\v73_scratch")
EV = Path(r"C:\tmp\helm-ctt2r-c49-read\docs\working\r1_wave7\v73_a11\evidence")
F2 = S / "fix2"
D2 = S / "a11_dryrun2"

PLAN = {
    "builder_reader_build": [S / "build" / "run" / n for n in (
        "t1_before_v72.log", "t1_after_v73.log", "after_v73_12names_one_process.log", "off_canon_v72.json",
        "off_canon_v73.json", "probe_v72.log", "probe_v73.log", "probe_items_v73.log")]
    + sorted((S / "build" / "scripts").glob("*")),
    "builder_reader_build/baseline_v72": [S / "build" / "run" / "baseline_v72" / "SUMMARY.txt"],
    "builder_reader_build/after_v73_final": [S / "build" / "run" / "after_v73_final" / "SUMMARY.txt"],
    "builder_a11_first_dry_run": sorted((S / "a11_run").glob("*")) + sorted((S / "a11_scripts").glob("*.py")),
    "design_probes": sorted((S / "finalize" / "scripts").glob("*.py")) + sorted((S / "finalize" / "run").glob("*.log"))
    + sorted((S / "critic" / "scripts").glob("*.py")),
    "fix_round/scripts": sorted((F2 / "scripts").glob("*.py")),
    "fix_round/inputs": [F2 / "H_PROBE_ITEMS.json"],
    "fix_round/run": [F2 / "run" / n for n in (
        "memory_log.jsonl", "make_helm_copies.log", "probe_reader_v72.json", "probe_reader_v73r.json",
        "probe_h2_h4_h5.json", "H_PROBE_REAL_HELM.json", "apply_check.log", "t1_fail_first_on_v72.log",
        "helm_loader_v9.log", "helm_loader_v73r.log", "helm_loader_v73.log", "all_helm_wt_orchestrator.log",
        "dryrun2_orchestrator.log", "t3_canonical_run.log", "test_t3_v73.log", "test_scorer_path_v73.log",
        "SCORER_PATH_G2_FIRST_VERSION.json", "g2_first_version.log", "h_probe_real_helm.log")],
    "fix_round/all_helm_tests_scratch": sorted((F2 / "run" / "all_helm_helm_wt").glob("*")),
    "fix_round/all_helm_tests_scratch_run1_without_compaction_tools": sorted(
        (F2 / "run" / "all_helm_helm_wt_run1_without_compaction_tools").glob("*")),
    "fix_round/helm_loader/v9": [F2 / "loader" / "v9" / "RESULT.json", F2 / "loader" / "v9" / "unittest_helm.log"],
    "fix_round/helm_loader/v73r": [F2 / "loader" / "v73r" / "RESULT.json", F2 / "loader" / "v73r" / "unittest_helm.log"],
    "fix_round/helm_loader/v73": [F2 / "loader" / "v73" / "RESULT.json", F2 / "loader" / "v73" / "unittest_helm.log"],
    "fix_round/a11_dryrun2": [D2 / n for n in ("DRYRUN2_STEPS.json", "PLANTS_ON_UNAMENDED_V9.json", "PLANTS_ON_AMENDED.json",
                                               "FIXFIRST_SCORER_unamended.json", "FIXFIRST_SCORER_amended.json")]
    + sorted((D2 / "logs").glob("*")),
}
INDEX = {
    "R-1..R-5 (reader regressions, reproduced)": ["fix_round/run/probe_reader_v72.json", "fix_round/run/probe_reader_v73r.json",
                                                   "fix_round/scripts/probe_reader_items.py"],
    "R-6 / G-11 (host-exact 12-name run)": ["fix_round/helm_loader/"],
    "H-1, H-3, H-4 (real HELM through the package)": ["fix_round/run/H_PROBE_REAL_HELM.json", "fix_round/inputs/H_PROBE_ITEMS.json"],
    "H-2, H-4, H-5 (authored records, hooked scorer)": ["fix_round/run/probe_h2_h4_h5.json", "fix_round/scripts/probe_h2_h4_h5.py"],
    "G-1 (T3 as designed)": ["../t3_score_v73.py", "../test_t3_v73.py", "../t3/T3_V73.json", "fix_round/run/test_t3_v73.log"],
    "G-2 (item revised after a run; first version of record)": ["fix_round/run/SCORER_PATH_G2_FIRST_VERSION.json"],
    "G-3 (memory gate on every laptop step)": ["fix_round/scripts/gate.py", "fix_round/run/memory_log.jsonl",
                                               "fix_round/a11_dryrun2/memory_log.jsonl"],
    "G-8 (apply tool guards)": ["fix_round/run/apply_check.log", "fix_round/scripts/apply_check.py"],
    "G-9 (fix state recorded at run time)": ["fix_round/a11_dryrun2/PLANTS_ON_UNAMENDED_V9.json"],
    "G-10 (HELM tests from a scratch copy; math_utils.py writer)": ["fix_round/all_helm_tests_scratch/SUMMARY.json"],
    "T1 fail first, re-run under the gate": ["fix_round/run/t1_fail_first_on_v72.log"],
    "builder's evidence (copied from the session scratchpad)": ["builder_reader_build/", "builder_a11_first_dry_run/",
                                                                "design_probes/"],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if EV.exists():
        raise SystemExit("REFUSED: evidence folder already exists")
    rows = []
    for sub, files in PLAN.items():
        for src in files:
            if not src.is_file():
                raise SystemExit(f"REFUSED: missing evidence file {src}")
            dst = EV / sub / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                raise SystemExit(f"REFUSED: two files map to {dst}")
            shutil.copyfile(src, dst)
            rows.append((sha(dst), dst.relative_to(EV).as_posix(), str(src)))
    (EV / "EVIDENCE_INDEX.json").write_text(json.dumps(
        {"what": "Evidence for reader v7.3 (helm_wide_turn.py), amendment A-R1W7-11 (docs/working/r1_wave7/a_r1w7_11/) and "
                 "the 2026-10-21 fix round; scratch runs only, 0 USD, laptop; nothing here is LICENSED",
         "by_reviewer_item": INDEX, "sources": {r[1]: r[2] for r in rows}}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    lines = [f"{h}  {rel}" for h, rel, _ in sorted(rows, key=lambda r: r[1])]
    lines.append(f"{sha(EV / 'EVIDENCE_INDEX.json')}  EVIDENCE_INDEX.json")
    (EV / "MANIFEST.sha256").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    total = sum((EV / r[1]).stat().st_size for r in rows)
    print(json.dumps({"files": len(rows) + 1, "bytes": total, "manifest_sha256": sha(EV / "MANIFEST.sha256")}))


if __name__ == "__main__":
    sys.exit(main())
