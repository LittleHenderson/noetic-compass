"""Build CJT_OHM_ARTIFACT_MANIFEST.json -- one row per artifact the claim ledger cites.

For every path referenced by CJT_OHM_CLAIM_LEDGER.json (union of artifact_paths) plus the
paths listed in EXTRA_PATHS, record:
  exists_at_head        git cat-file -e HEAD:<path>
  git_blob              git rev-parse HEAD:<path>          (content id, line-ending independent)
  sha256_lf             sha256 of the working-tree bytes with CRLF normalised to LF
  bytes_lf              size after normalisation
  last_commit           git log -1 --format=%H -- <path>
  last_commit_date      git log -1 --format=%ad --date=iso -- <path>
  cited_by              claim ids that cite the path
Control-plane work only: git, hashing, JSON. No model, no GPU, no network.

Run from the repository root:  python cas_only_reasoner/CJT_OHM_CLEANROOM/build_artifact_manifest.py
"""
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LEDGER = HERE / "CJT_OHM_CLAIM_LEDGER.json"
OUT = HERE / "CJT_OHM_ARTIFACT_MANIFEST.json"

# Paths the owner's handoff names that must be checked even if no claim cites them.
EXTRA_PATHS = [
    "REFERENCE/AUDITS/CJT_OHM_0R_cbffa4a0_GLM_AUDIT.md",
    "REFERENCE/AUDITS/CMB_R1_RGM01_CLAUDE_AUDIT.md",
    "REFERENCE/AUDITS/CMB_R1_RGM0_CLAUDE_AUDIT.md",
    "cas_only_reasoner/recursive_cjt_rc0/RECURSIVE_CJT_TICK_SEMANTICS_v0_1.md",
    "cas_only_reasoner/recursive_cjt_rc0/RECURSIVE_CJT_TICK_SEMANTICS_v0_2.md",
    # handoff-named locations (do not exist at HEAD) and where the documents actually live
    "cas_only_reasoner/RECURSIVE_CJT_BIAS_CONTROLLER_v0_2.md",
    "cas_only_reasoner/RECURSIVE_CJT_BIAS_CONTROLLER_v0_3.md",
    "docs/research/RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md",
    "docs/research/RECURSIVE_CJT_BIAS_CONTROLLER_v0_2_CANDIDATE.md",
    "docs/research/RECURSIVE_CJT_BIAS_CONTROLLER_v0_3_CANDIDATE.md",
    # other handoff-named audit files, checked by name (none exist at HEAD at time of writing)
    "REFERENCE/AUDITS/CJT_OHM_D1_DESIGN_ATTACK_AUDIT.md",
    "REFERENCE/AUDITS/PRECEDENCE_CLOSURE_AUDIT.md",
    "REFERENCE/AUDITS/TRIGGER_CONFORMANCE.md",
    "cas_only_reasoner/CJT_PREC_CLOSURE/p6_order_test.py",
    "cas_only_reasoner/CJT_PREC_CLOSURE/audits/deepseek-r1_audit.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/p6_heldout_repro.py",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/p6_committed_repro_stdout.txt",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/p6_heldout_repro_stdout.txt",
    "docs/CAS_HARNESS_SPEC_SHEET.md",
    "CHANGELOG.md",
    # the clean-room deliverables themselves
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_OHM_STATE_OF_EVIDENCE.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_OHM_CLAIM_LEDGER.json",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_OHM_CLAIM_TABLES.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/cleanroom_claims.json",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/agent_outputs/ledger_raw_agent_outputs.json",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_MECH_0_DESIGN_BRIEF_v0_1.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_OHM_PROJECT_GOALS_v1.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/CAS_CJT_TRANSFORMER_POSSIBILITY_v0_1.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/P6_RESOLUTION.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/P6_AUDIT_PACKAGE.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/audits/deepseek-r1_p6_audit.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/audits/llama3-3-70b_p6_audit.md",
    "cas_only_reasoner/CJT_OHM_CLEANROOM/p6/audits/DISPATCH_RECEIPT.json",
]


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    head = git("rev-parse", "HEAD")[1]
    cited = {}
    if LEDGER.exists():
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        for c in ledger.get("claims", []):
            for p in c.get("artifact_paths", []):
                cited.setdefault(p.replace("\\", "/"), []).append(c["claim_id"])
    paths = sorted(set(cited) | set(EXTRA_PATHS))
    rows = []
    for p in paths:
        code, blob, _ = git("rev-parse", f"HEAD:{p}")
        exists = code == 0
        row = {"path": p, "exists_at_head": exists, "git_blob": blob if exists else None,
               "cited_by": sorted(set(cited.get(p, [])))}
        wt = ROOT / p
        if wt.is_file():
            data = wt.read_bytes().replace(b"\r\n", b"\n")
            row["sha256_lf"] = hashlib.sha256(data).hexdigest()
            row["bytes_lf"] = len(data)
        elif wt.is_dir():
            row["kind"] = "directory"
        else:
            row["sha256_lf"] = None
            row["bytes_lf"] = None
        if exists:
            row["last_commit"] = git("log", "-1", "--format=%H", "--", p)[1]
            row["last_commit_date"] = git("log", "-1", "--format=%ad", "--date=iso", "--", p)[1]
        rows.append(row)
    missing = [r["path"] for r in rows if not r["exists_at_head"] and r.get("sha256_lf") is None and r.get("kind") != "directory"]
    uncommitted = [r["path"] for r in rows if not r["exists_at_head"] and r.get("sha256_lf") is not None]
    manifest = {
        "manifest_version": "1.0",
        "built_from_head": head,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD")[1],
        "note": ("missing_everywhere: paths the handoff or the ledger named that exist neither at HEAD nor in "
                 "the worktree. uncommitted_at_build: clean-room files written in this worktree and committed "
                 "in the same commit as this manifest (sha256_lf recorded; git_blob null at build time)."),
        "artifact_count": len(rows),
        "missing_everywhere": missing,
        "uncommitted_at_build": uncommitted,
        "artifacts": rows,
    }
    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"HEAD {head}  artifacts {len(rows)}  missing_everywhere {len(missing)}  uncommitted_at_build {len(uncommitted)}")
    for m in missing:
        print(f"  MISSING {m}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
