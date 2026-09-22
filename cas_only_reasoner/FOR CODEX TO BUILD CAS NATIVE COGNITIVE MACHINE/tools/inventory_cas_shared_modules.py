"""Inventory shared CAS modules from tracked Git objects, including sparse omissions."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

CN = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
APP = "noetic-compass-scaffold/noetic-compass"
ROOT = Path(__file__).resolve().parents[3]
COMPONENTS = [
    ("diagnostic_ohm", APP+"/api/cas_ohm/quantifiers.py", "diagnostic repair task", "standard library; calibrated diagnostic contract; no model execution"),
    ("compiler_ohm", APP+"/api/notation/cas_ohm.py", "compiler/atlas task", "standard library; declared coherent scales; no calibration"),
    ("compiler", APP+"/api/notation/compiler.py", "compiler/atlas task", "standalone compiler and dynamically loaded adjacent helper"),
    ("offline_compiler", "dist/cas-offline/api/notation/compiler.py", "compiler/atlas task", "distributed compiler copy; preserve distribution identity"),
    ("offline_ohm", "dist/cas-offline/api/notation/cas_ohm.py", "compiler/atlas task", "distributed helper copy; preserve distribution identity"),
    ("synthetic_instrument", "cas_only_reasoner/CAS_OHM_INSTRUMENT_v0.1/panel/panel.py", "separate instrument workstream; read only", "synthetic calibration panel; not a diagnostic-quantifier caller"),
    ("cortex_attention", "cas_only_reasoner/CAS_CORTEX_v0.1/cortex/attention.py", "separate Cortex workstream; read only", "authored compute-only runtime reporting; observation derived from formula, not independent neural measurement"),
    ("apprenticeship_ohm", CN+"/cncm/cognitive_apprenticeship.py", "native apprenticeship workstream", "separate integer-milliunit observation type; no promotion authority"),
    ("pcba_reader", CN+"/research/helm_cas_expression_lab/pcba_reader.py", "compiler/atlas task", "strict parser; pinned source adapters; no circuit execution"),
    ("ohm_connections", CN+"/research/helm_cas_expression_lab/cas_ohm_connections.py", "compiler/atlas task", "compiler/helper and PCBA binding; design records"),
    ("rpa_coordinates", CN+"/cncm/rpa_coordinates.py", "atlas task", "declared profile arithmetic; no automatic model profile"),
    ("rpa_model", CN+"/cncm/rpa_model.py", "atlas task", "record schemas and exact identities"),
    ("rpa_native", CN+"/cncm/rpa_native_adapter.py", "native runtime adapter task", "source-bound native runtime records"),
    ("rpa_compound", CN+"/cncm/rpa_compound_adapter.py", "compound adapter task", "compound runtime records; distinct from Helm"),
    ("rpa_scoped", CN+"/cncm/rpa_scoped_compound.py", "scoped adapter task", "saved compound hierarchy"),
    ("rpa_cube", CN+"/cncm/rpa_cube_adapter.py", "cube adapter task", "cube source namespace and teacher/learner boundary"),
    ("rpa_ohm_atlas", CN+"/cncm/rpa_ohm_atlas.py", "atlas task", "declared PCBA/compiler records; separate design measurements"),
    ("rpa_recorded_helm", CN+"/cncm/rpa_recorded_helm.py", "recorded Helm task", "retained development predictions and pinned checker; no weights loaded"),
    ("renderer", CN+"/tools/render_rpa_view.py", "atlas task", "shared offline renderer across entry points"),
    ("q4_job", CN+"/research/helm_cas_expression_lab/q4_smoke_job.py", "Helm learning task", "deterministic preparation; gated CUDA execution; external trust prerequisite"),
    ("q4_neural", CN+"/research/helm_cas_expression_lab/learner_q4_neural.py", "Helm learning task", "Torch/CUDA only for authorized execution; no compiler answer injection"),
]
DISCOVERY = re.compile(r"(?:cas_ohm|quantifiers|rpa_|pcba_|learner_q4|q4_|(?:^|/)compiler\.py$)", re.I)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-ref", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    revisions = {
        "integration": args.current_ref,
        "working_atlas_before_repair": "eb9985566bd11a89f485d627186ef0efa7177f02",
        "peer_audit_and_hardening": "65ad300835c06f9feff154170cb8b103d5d13ffa",
        "independent_audit": "0922f339a2e8e4188c05ec882c552ffbd747fd77",
    }
    result = {
        "schema": "cas.shared-module-inventory/0.1",
        "scope": "Repository-wide tracked Python discovery for shared CAS/PCBA/RPA/Q4 components at explicit refs, including omitted sparse files. Not a live production import trace.",
        "repository_root": str(ROOT),
        "ownership": "Editing responsibility labels; not human authorship or authorization.",
        "coordination": {
            "integration": "codex/cas-reconcile-20260922",
            "diagnostic_edits": "codex/ohm-invalid-numbers-20260922",
            "evidence_edits": "codex/evidence-reconcile-20260922",
            "rule": "Separate write worktrees; inspect this index and tracked objects before changing shared components or asserting absence.",
        },
        "revisions": {},
    }
    for label, ref in revisions.items():
        sha = git("rev-parse", ref).decode().strip()
        tree = git("ls-tree", "-r", "-z", sha).split(b"\0")
        entries = {}
        for row in tree:
            if row:
                header, path = row.split(b"\t", 1)
                mode, kind, oid = header.decode().split()
                if kind == "blob":
                    entries[path.decode()] = oid
        components = []
        for name, path, owner, dependency in COMPONENTS:
            row = {"component": name, "path": path, "editing_owner": owner,
                   "dependency_scope": dependency, "source_revision": sha}
            if path not in entries:
                row["status"] = "ABSENT_FROM_THIS_TRACKED_REVISION"
            else:
                raw = git("cat-file", "blob", entries[path])
                tree_ast = ast.parse(raw.decode("utf-8-sig"), filename=path)
                row.update(status="TRACKED", git_blob=entries[path], bytes=len(raw),
                           sha256=hashlib.sha256(raw).hexdigest(),
                           public_entry_points=[node.name for node in tree_ast.body
                                                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                                                and not node.name.startswith("_")],
                           recent_change=git("log", "-1", "--format=%H %s", sha, "--", path).decode().strip(),
                           materialized_here=(ROOT/path).is_file())
            components.append(row)
        discovered = [{"path": path, "git_blob": oid,
                       "historical_or_pinned": any(part in path for part in ("/records/", "/pinned_", "/snapshots/"))}
                      for path, oid in sorted(entries.items())
                      if path.endswith(".py") and DISCOVERY.search(path)]
        result["revisions"][label] = {"commit": sha, "components": components,
                                     "discovered_python_files": discovered}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output),
                      "revisions": {key: {"commit": val["commit"], "components": len(val["components"]),
                                         "discovered": len(val["discovered_python_files"])}
                                    for key,val in result["revisions"].items()}}))


if __name__ == "__main__":
    main()
