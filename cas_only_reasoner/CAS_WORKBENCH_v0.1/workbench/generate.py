"""The workbench generator: run the six boards, seal the evidence.

Emits workbench_data.json and a self-contained glass_brain.html with
the data inlined. Deterministic: regenerating produces the identical
pane digest (conformance-tested). The renderer only projects these
structures; it never computes a verdict.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Dict

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKBENCH_ROOT = os.path.dirname(FILE_DIR)          # CAS_WORKBENCH_v0.1
CAS_ONLY = os.path.dirname(WORKBENCH_ROOT)          # cas_only_reasoner
REPO_ROOT = os.path.dirname(CAS_ONLY)               # tksCAS repo root

for path in (REPO_ROOT,
             os.path.join(REPO_ROOT, "cas-rr"),
             os.path.join(CAS_ONLY, "CAS_RRK_v0.1"),
             os.path.join(CAS_ONLY, "CAS_RLP_v0.1"),
             os.path.join(CAS_ONLY, "CCB_M1_v0.1"),
             os.path.join(CAS_ONLY, "CCB_L1_v0.1"),
             os.path.join(CAS_ONLY, "CAS_SEM_v0.1")):
    if path not in sys.path:
        sys.path.insert(0, path)


def _digest(obj: Dict) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Pane 1: Task and Dialogue (CCB-L1 -> kernel -> English)
# --------------------------------------------------------------------------
def _dialogue_pane() -> Dict:
    import json as _json

    from lang.l1 import CCB_L1

    seed_path = os.path.join(CAS_ONLY, "CCB_L1_v0.1", "fixtures",
                             "seed_lexicon.json")
    with open(seed_path, "r", encoding="utf-8") as fh:
        seed = _json.load(fh)
    l1 = CCB_L1(seed)
    return {
        "questions": [
            l1.ask("is the cat gray?"),
            l1.ask("is the dog gray?"),
        ],
    }


# --------------------------------------------------------------------------
# Panes 2, 4, 6: goal map, branch tree, memory (cas-rr)
# --------------------------------------------------------------------------
def _cas_rr_panes() -> Dict:
    from cas_rr.runtime import CASRuntime, default_constitution
    from tasks import battery

    packet = CASRuntime(default_constitution(),
                        battery.task_transitive()).run()

    goal = packet["goal_frames"][0]
    scan = packet["rpm"]["scan_history"][0] if packet["rpm"]["scan_history"] else {}

    candidates = []
    for batch in packet["candidates"]:
        for cand in batch["candidates"]:
            entry = dict(cand)
            entry["inference"] = packet["inferences"].get(
                cand["candidate_id"], {})
            candidates.append(entry)

    eliminated = {}
    for tour in packet["comparisons"]:
        for cid, reason in tour.get("eliminated", {}).items():
            eliminated[cid] = reason

    memory_records = []
    for mem in packet["memory"]:
        for item in mem.get("selected_items", []):
            memory_records.append(item)
    lacunae = []
    for mem in packet["memory"]:
        for lac in mem.get("lacunae", []):
            lacunae.append(lac)

    return {
        "goal_map": {
            "goal_id": goal.get("goal_id"),
            "foundation_ref": goal.get("foundation_ref"),
            "desired_outcome": goal.get("desired_outcome"),
            "kind": goal.get("kind"),
            "scan": scan,
            "adapter": {"TF2b": {"F2": 1.0}},
        },
        "branch_tree": {
            "candidates": candidates,
            "eliminated": eliminated,
            "winner": packet["output"]["conclusion"] if packet["output"] else None,
            "gates": packet.get("commitment", {}).get("gates", []),
        },
        "memory": {
            "records": memory_records,
            "lacunae": lacunae,
        },
    }


# --------------------------------------------------------------------------
# Panes 3, 5, 8: live board, RPM stack, trace timeline (kernel)
# --------------------------------------------------------------------------
def _kernel_panes() -> Dict:
    from kernel.fixtures import load_problem
    from kernel.kernel import CAS_RRK

    packet = CAS_RRK(load_problem("rpm_recursion"),
                     run_id="workbench", seed=0).run()
    trace_rows = []
    rpm_rows = []
    live_components = []
    for event in packet["trace"]:
        trace_rows.append({
            "tick": event["logical_tick"],
            "scheduled": event["scheduled_components"],
            "authorized": len(event["authorized_intents"]),
            "rejected": len(event["rejected_intents"]),
            "pre_state_hash": event["pre_state_hash"],
            "post_state_hash": event["post_state_hash"],
            "terminal_status": event["terminal_status"],
        })
        live_components.append({
            "tick": event["logical_tick"],
            "components": event["scheduled_components"],
        })
        for mutation in event["committed_mutations"]:
            if mutation.get("kind") in ("push_rpm", "return_rpm"):
                rpm_rows.append({
                    "tick": event["logical_tick"],
                    "kind": mutation.get("kind"),
                    "goal": mutation.get("goal") or mutation.get("child"),
                    "parent": mutation.get("parent"),
                })
    return {
        "live_board": {
            "ticks": live_components,
            "components": sorted({c for row in live_components
                                  for c in row["components"]}),
        },
        "rpm_stack": {"transitions": rpm_rows},
        "trace": {"rows": trace_rows,
                  "terminal_status": packet["terminal_status"],
                  "final_state_hash": packet["final_state_hash"],
                  "trace_digest": packet["trace_digest"]},
    }


# --------------------------------------------------------------------------
# Pane 7: Truth and Evidence (CAS-Sem + CCB-M1)
# --------------------------------------------------------------------------
def _truth_pane() -> Dict:
    import copy
    import json as _json

    from cassem.coherence import CoherenceChecker
    from cassem.store import SemanticCMB
    from cas_math.m1 import CCB_M1

    story_path = os.path.join(CAS_ONLY, "CAS_SEM_v0.1", "fixtures",
                              "story_good.json")
    with open(story_path, "r", encoding="utf-8") as fh:
        story = _json.load(fh)
    cmb = SemanticCMB(story)

    broken = copy.deepcopy(story)
    broken["claims"].append({
        "idea": {"kind": "property", "entity": "cat_1", "property": "gray"},
        "truth": "CONTRADICTED",
        "provenance": {"source": "book"},
        "conflict": {"a": "observation t1", "b": "book page 9"},
    })
    violations = [v.to_json() for v in CoherenceChecker(broken).check()]

    mistake_path = os.path.join(CAS_ONLY, "CCB_M1_v0.1", "fixtures",
                                "mistake_package.json")
    with open(mistake_path, "r", encoding="utf-8") as fh:
        mistake = _json.load(fh)
    m1 = CCB_M1(mistake)
    cycle = m1.mistake_cycle(mistake["mistake_task"])
    corrected = m1.verify_identity(m1.package["held_out"][0], m1.package)

    return {
        "semantic_claims": [
            {"idea": r["idea"], "truth": r["truth"],
             "provenance": r.get("provenance")}
            for r in story["claims"]
        ],
        "coherence": {"good": cmb.coherent(),
                      "broken_violations": violations},
        "math": {
            "attempt": cycle["attempt_outcome"],
            "fault": cycle["fault"],
            "corrected_verdict": corrected["outcome"]["verdict"],
            "corrected_steps": len(corrected["steps"]),
        },
    }


# --------------------------------------------------------------------------
# Panes 9, 10: learning dashboard and evolution lab (CAS-RLP)
# --------------------------------------------------------------------------
def _learning_panes() -> Dict:
    from rlp.fixture_loader import load_package
    from rlp.procedural import ProceduralLearner
    from rlp.rlp import CAS_RLP

    training = load_package("r1_overgeneralization")
    held_out = load_package("r1_bigger_held_out")

    improve_cycle = CAS_RLP(training).improve()
    procedural_cycle = ProceduralLearner(training, held_out,
                                         budget=1).learn()

    return {
        "learning": {
            "rule_decisions": [
                {"mutation": d["mutation"], "verdict": d["verdict"]}
                for d in improve_cycle["decisions"]
                if d.get("verdict") in ("PROMOTED", "REJECTED",
                                        "QUARANTINED")
            ],
            "experience_count": improve_cycle["experience_count"],
            "current_revision": improve_cycle["current_revision"],
        },
        "evolution": {
            "strategies": [
                {"strategy": d["strategy"], "verdict": d["verdict"],
                 "checks": d["checks"]}
                for d in procedural_cycle["decisions"]
            ],
            "promoted_strategy": procedural_cycle["promoted_strategy"],
            "regression_ok": procedural_cycle["regression_ok"],
            "budget": procedural_cycle["budget"],
        },
    }


# --------------------------------------------------------------------------
ORGAN_SUMMARY = [
    {"board": "cas-rr", "role": "CAS-RR prototype (R3 capability)", "tests": 43,
     "demo": "python run.py report"},
    {"board": "CAS_RRK_v0.1", "role": "authority-contract reasoning kernel",
     "tests": 28, "demo": "python run_demo.py"},
    {"board": "CAS_SEM_v0.1", "role": "semantic content and binding",
     "tests": 19, "demo": "python run_demo.py"},
    {"board": "CAS_RLP_v0.1", "role": "recursive learning, four rings",
     "tests": 23, "demo": "python run_demo_procedural.py"},
    {"board": "CCB_M1_v0.1", "role": "mathematics: checker decides",
     "tests": 27, "demo": "python run_demo.py"},
    {"board": "CCB_L1_v0.1", "role": "English: acquired interface",
     "tests": 18, "demo": "python run_demo.py"},
]


def build_bundle() -> Dict:
    panes: Dict = {}
    panes["dialogue"] = _dialogue_pane()
    panes.update(_cas_rr_panes())
    panes.update(_kernel_panes())
    panes["truth"] = _truth_pane()
    panes.update(_learning_panes())
    total_tests = sum(o["tests"] for o in ORGAN_SUMMARY)
    return {
        "workbench_version": "0.1.0",
        "digest": _digest(panes),
        "program_tests": total_tests,
        "organs": ORGAN_SUMMARY,
        "panes": panes,
    }


# --------------------------------------------------------------------------
def load_app_js() -> str:
    with open(os.path.join(FILE_DIR, "app.js"), "r",
              encoding="utf-8") as fh:
        return fh.read()


def render_html(bundle: Dict) -> str:
    data_json = json.dumps(bundle, default=str, sort_keys=True)
    app_js = load_app_js()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CAS Cognitive Workbench v0.1</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0;
          background: #0d1117; color: #e6edf3; }}
  header {{ padding: 18px 28px; border-bottom: 1px solid #21262d;
            background: #010409; }}
  header h1 {{ margin: 0 0 4px 0; font-size: 22px; }}
  header p {{ margin: 0; color: #8b949e; font-size: 13px; }}
  #app {{ padding: 18px 28px; }}
  section.pane {{ border: 1px solid #21262d; border-radius: 8px;
                  margin-bottom: 18px; background: #161b22; }}
  section.pane h2 {{ margin: 0; padding: 10px 14px; font-size: 15px;
                     border-bottom: 1px solid #21262d; color: #58a6ff; }}
  .pane-body {{ padding: 12px 14px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
  th, td {{ border: 1px solid #21262d; padding: 5px 8px;
            text-align: left; vertical-align: top; }}
  th {{ background: #010409; color: #8b949e; }}
  .chip {{ display: inline-block; padding: 1px 8px; border-radius: 10px;
           font-size: 11px; font-weight: 600; }}
  .chip.ok {{ background: #12261e; color: #3fb950; }}
  .chip.bad {{ background: #2d1516; color: #f85149; }}
  .chip.warn {{ background: #2b2300; color: #d29922; }}
  .chip.info {{ background: #121d2f; color: #58a6ff; }}
  .candidate {{ border: 1px solid #30363d; border-radius: 6px;
                padding: 8px 10px; margin-bottom: 8px; cursor: pointer; }}
  .candidate:hover {{ border-color: #58a6ff; }}
  .candidate .detail {{ display: none; margin-top: 8px; font-size: 12px;
                        color: #8b949e; }}
  .candidate.open .detail {{ display: block; }}
  .mono {{ font-family: Consolas, monospace; font-size: 11px; }}
  .hash {{ color: #79c0ff; }}
  ul.clean {{ margin: 6px 0; padding-left: 20px; }}
  li {{ margin-bottom: 3px; }}
</style>
</head>
<body>
<header>
  <h1>CAS Cognitive Workbench v0.1</h1>
  <p>The glass-brain interface. Every pane is a projection of real sealed
  board output - nothing here is simulated. Program: six boards,
  {bundle["program_tests"]} conformance tests.</p>
</header>
<div id="app"></div>
<script>
const WORKBENCH_DATA = {data_json};
</script>
<script>
{app_js}
</script>
</body>
</html>
"""


def main(out_dir: str = "output") -> None:
    bundle = build_bundle()
    os.makedirs(out_dir, exist_ok=True)
    data_path = os.path.join(out_dir, "workbench_data.json")
    html_path = os.path.join(out_dir, "glass_brain.html")
    with open(data_path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, default=str, indent=2, sort_keys=True)
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(render_html(bundle))
    print(f"workbench bundle written:")
    print(f"  {data_path}")
    print(f"  {html_path}")
    print(f"  pane digest: {bundle['digest']}")


if __name__ == "__main__":
    main()
