"""The Self-Model: the machine's typed representation of its own
capabilities - DERIVED from evidence, never asserted.

Laws:
  - a capability claim exists only with a checkable artifact path AND
    a live probe that exercises the real machinery; a claim whose
    probe fails is downgraded on the spot;
  - the model answers can(x) with a TYPED verdict: CAN (with evidence),
    CANNOT (with the reason), or UNKNOWN (with what evidence is
    missing) - it never bluffs;
  - LIMITS are first-class: every capability carries its recorded
    bounds (the spec-sheet caveats), and the model can recite what it
    CANNOT do as precisely as what it can;
  - the model is deterministic and sealed with a digest.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Callable, Dict, List, Optional

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _board in ("CAS_RRK_v0.1", "CCB_M1_v0.1", "CCB_L1_v0.1",
               "CAS_RLP_v0.1", "CCB_T1_v0.1", "CAS_LTG_v0.1"):
    _path = os.path.join(_CAS_ONLY, _board)
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _digest(obj) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------
# Live probes: each one exercises the REAL board machinery. A probe
# returns (ok, note). Probes are small on purpose - they are existence
# proofs, not benchmarks; the artifact path carries the full evidence.
def _probe_reasoning() -> tuple:
    from kernel.fixtures import load_problem
    from kernel.kernel import CAS_RRK
    packet = CAS_RRK(load_problem("modux_ponens"), run_id="sm", seed=0).run()
    return (packet["terminal_status"] == "CONCLUDED",
            f"kernel modus ponens: {packet['terminal_status']}")


def _probe_mathematics() -> tuple:
    from cas_math.exact import compare, parse_q
    from cas_math.expr import Add, Mul, Var, equal
    x, y = Var("x"), Var("y")
    ok = (compare(parse_q("2/3") + parse_q("3/4"), parse_q("1")) == "gt"
          and equal(Mul((x, y)), Mul((y, x))))
    return ok, "exact arithmetic + canonical identity check"


def _probe_discovery() -> tuple:
    from cas_math.discovery import discover
    packet = discover()
    return (len(packet["theorems"]) >= 1,
            f"{len(packet['theorems'])} machine-novel theorems proved")


def _probe_language() -> tuple:
    import json as _json
    from lang.l1 import CCB_L1
    seed_path = os.path.join(_CAS_ONLY, "CCB_L1_v0.1", "fixtures",
                             "seed_lexicon.json")
    board = CCB_L1(_json.load(open(seed_path, encoding="utf-8")))
    result = board.ask("is the cat gray?")
    return (result["answer"] == "yes, the cat is gray.",
            "CCB-L1 parse -> kernel -> decoded answer")


def _probe_tools() -> tuple:
    import json as _json
    from toolboard.toolboard import CCB_T1
    from toolboard.tools import default_registry
    problem_path = os.path.join(_CAS_ONLY, "CCB_T1_v0.1", "fixtures",
                                "tool_need_problem.json")
    result = CCB_T1(_json.load(open(problem_path, encoding="utf-8")),
                    registry=default_registry()).run()
    return (result["terminal_status"] == "CONCLUDED",
            f"tool loop: {result['terminal_status']}")


def _probe_learning() -> tuple:
    from rlp.fixture_loader import load_package
    from rlp.rlp import CAS_RLP
    cycle = CAS_RLP(load_package("r1_overgeneralization")).improve()
    return (any(d["verdict"] == "PROMOTED" for d in cycle["decisions"]),
            "RLP correction promoted under the acceptance law")


def _probe_self_improvement() -> tuple:
    from rlp.fixture_loader import load_package
    from rlp.self_improvement import SelfImprover
    packet = SelfImprover(load_package("r1_overgeneralization"),
                          load_package("r1_bigger_held_out"),
                          budget=1).run()
    return (packet["status"] == "PROMOTED",
            f"self-improvement cycle: {packet['status']}")


def _probe_long_term_goals() -> tuple:
    from goals.store import GoalStore
    store = GoalStore()
    store.begin_episode()
    store.add("probe", "probe goal", {"pred": "p", "args": []},
              provenance="self_model_probe")
    store.start("probe", provenance="sm")
    ok = store.goals["probe"]["status"] == "IN_PROGRESS"
    return ok, "goal store lifecycle"


def _probe_absent() -> tuple:
    return False, "no machinery exists for this capability"


# ----------------------------------------------------------------------
CAPABILITIES: List[Dict] = [
    {"name": "reasoning", "probe": _probe_reasoning,
     "artifact": "CAS_RRK_v0.1/ (34 tests; sealed traces, replay)",
     "limits": "propositional fragment; bounded proof depth"},
    {"name": "mathematics", "probe": _probe_mathematics,
     "artifact": "CCB_M1_v0.1/ (34 tests; exact, never floats)",
     "limits": "polynomial identities and exact rationals; no "
               "linear-equation checker yet"},
    {"name": "discovery", "probe": _probe_discovery,
     "artifact": "CCB_M1_v0.1/cas_math/discovery.py (7 tests)",
     "limits": "novel to this machine, trivial to human mathematics; "
               "exhaustive search at v0.1 scale"},
    {"name": "language", "probe": _probe_language,
     "artifact": "CCB_L1_v0.1/ (18 tests) + CORTEX_H2H_v0.1/output/"
                 "h2h_results.json (digest db34d2e9d0214df4)",
     "limits": "fragment grammar; breadth 0% by construction - the "
               "head-to-head measured a 0.5B cortex at 73% breadth "
               "but 25% honesty; no cortex is wired in"},
    {"name": "tools", "probe": _probe_tools,
     "artifact": "CCB_T1_v0.1/ (20 tests; typed fault halts)",
     "limits": "two in-process tools; no external world"},
    {"name": "learning", "probe": _probe_learning,
     "artifact": "CAS_RLP_v0.1/tests/test_g8_suite.py (9 tests)",
     "limits": "one fault class; 3-guard strategy space"},
    {"name": "self_improvement", "probe": _probe_self_improvement,
     "artifact": "CAS_RLP_v0.1/rlp/self_improvement.py (13 tests)",
     "limits": "procedure synthesis over a 3-guard permutation space"},
    {"name": "long_term_goals", "probe": _probe_long_term_goals,
     "artifact": "CAS_LTG_v0.1/ (10 tests; kernel-earned completion)",
     "limits": "single store; no scheduling policy"},
    {"name": "vision", "probe": _probe_absent,
     "artifact": None, "limits": "no machinery exists"},
    {"name": "coding", "probe": _probe_absent,
     "artifact": None, "limits": "no machinery exists"},
]


class SelfModel:
    """Build by RUNNING the probes; query with typed verdicts."""

    def __init__(self) -> None:
        self.entries: Dict[str, Dict] = {}
        for spec in CAPABILITIES:
            ok, note = spec["probe"]()
            has_artifact = bool(spec["artifact"])
            if ok and has_artifact:
                verdict = "CAN"
            elif not has_artifact and not ok:
                verdict = "CANNOT"
            else:
                # probe and artifact disagree: honesty demands UNKNOWN
                verdict = "UNKNOWN"
            self.entries[spec["name"]] = {
                "verdict": verdict,
                "probe_ok": ok,
                "probe_note": note,
                "artifact": spec["artifact"],
                "limits": spec["limits"],
            }
        self.model_digest = _digest(self.entries)

    # ------------------------------------------------------------------
    def can(self, capability: str) -> Dict:
        entry = self.entries.get(capability)
        if entry is None:
            return {"capability": capability, "verdict": "UNKNOWN",
                    "reason": "no evidence exists either way; the "
                              "self-model does not bluff"}
        answer = {"capability": capability, "verdict": entry["verdict"],
                  "limits": entry["limits"]}
        if entry["verdict"] == "CAN":
            answer["evidence"] = entry["artifact"]
            answer["probe"] = entry["probe_note"]
        elif entry["verdict"] == "CANNOT":
            answer["reason"] = entry["limits"]
        else:
            answer["reason"] = ("artifact and live probe disagree: "
                                + entry["probe_note"])
        return answer

    def cannot_list(self) -> List[str]:
        return sorted(name for name, e in self.entries.items()
                      if e["verdict"] == "CANNOT")

    def to_json(self) -> Dict:
        return {"entries": self.entries, "model_digest": self.model_digest}
