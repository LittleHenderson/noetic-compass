"""The multi-domain long-horizon episode (the CAS-G10 suite core).

One persistent goal store, THREE episodes separated by REAL process
boundaries, SEVEN domains exercised on the real boards:

  Episode 1  language (CCB-L1 answers an English question), the
             long-term goals born, the kernel's typed NEEDS_INFORMATION
             blocking goal g_total, the self-model consulted for typed
             capability routing (including an honest CANNOT).
  Episode 2  tools + exact math (CCB-T1 serves the missing sum through
             the calculator; the kernel concludes; goal g_total
             COMPLETES through the kernel's own proof).
  Episode 3  learning (the strategy memory drives a budgeted repair)
             + discovery (machine-novel theorems proved by the trusted
             checker; goal g_discover completes on the sealed
             evidence).

Every step is recorded in the goal store with provenance + episode;
completion is EARNED through the kernel; the whole pipeline is
deterministic (digest-checked when run twice).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict

_CAS_ONLY = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
for _board in ("CAS_RRK_v0.1", "CCB_M1_v0.1", "CCB_L1_v0.1",
               "CAS_RLP_v0.1", "CCB_T1_v0.1", "CAS_LTG_v0.1",
               "CAS_SM_v0.1"):
    _path = os.path.join(_CAS_ONLY, _board)
    if _path not in sys.path:
        sys.path.insert(0, _path)

STORE = "goal_store.json"
LOG = "episode_log.json"

TOOL_PROBLEM_PATH = os.path.join(_CAS_ONLY, "CCB_T1_v0.1", "fixtures",
                                 "tool_need_problem.json")
SEED_PATH = os.path.join(_CAS_ONLY, "CCB_L1_v0.1", "fixtures",
                         "seed_lexicon.json")


def _write_log(workdir: str, name: str, payload: Dict) -> None:
    path = os.path.join(workdir, LOG)
    log = {}
    if os.path.exists(path):
        log = json.load(open(path, encoding="utf-8"))
    log[name] = payload
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1, sort_keys=True)


# ----------------------------------------------------------------------
def episode1(workdir: str) -> Dict:
    from goals.store import GoalStore
    from lang.l1 import CCB_L1
    from selfmodel.model import SelfModel
    from kernel.kernel import CAS_RRK

    store = GoalStore()
    store.begin_episode()

    # LANGUAGE: an English question answered through the kernel
    board = CCB_L1(json.load(open(SEED_PATH, encoding="utf-8")))
    language = board.ask("is the cat gray?")
    assert language["answer"] == "yes, the cat is gray."

    # SELF-MODEL: typed capability routing BEFORE planning
    model = SelfModel()
    route_tools = model.can("tools")
    route_vision = model.can("vision")
    assert route_tools["verdict"] == "CAN"
    assert route_vision["verdict"] == "CANNOT"      # honest boundary

    # LONG-TERM GOALS: born, then BLOCKED by the kernel's typed halt
    store.add("g_total",
              "settle whether the exact total of x and y exceeds one",
              {"pred": "greater_than_one", "args": []},
              provenance="owner_question")
    store.add("g_discover",
              "discover and prove one machine-novel identity",
              {"pred": "theorem_proved", "args": ["?D"]},
              provenance="standing_directive")

    problem = json.load(open(TOOL_PROBLEM_PATH, encoding="utf-8"))
    packet = CAS_RRK(problem, run_id="g10_e1", seed=0).run()
    assert packet["terminal_status"] == "NEEDS_INFORMATION"
    store.block("g_total", "kernel NEEDS_INFORMATION: sum fact missing",
                provenance="kernel_typed_halt")
    store.progress("g_total",
                   "self-model routed the need to the tool board",
                   provenance="self_model",
                   artifact=f"self_model_digest:{model.model_digest}")

    digest = store.save(os.path.join(workdir, STORE))
    result = {"language_answer": language["answer"],
              "tools_routing": route_tools["verdict"],
              "vision_routing": route_vision["verdict"],
              "goal_status": store.goals["g_total"]["status"],
              "store_digest": digest}
    _write_log(workdir, "episode1", result)
    return result


# ----------------------------------------------------------------------
def episode2(workdir: str) -> Dict:
    from goals.store import GoalStore
    from toolboard.toolboard import CCB_T1
    from toolboard.tools import default_registry

    store = GoalStore.load(os.path.join(workdir, STORE))
    store.begin_episode()
    store.start("g_total", provenance="episode2_resumption")

    # TOOLS + EXACT MATH: the calculator serves the missing sum
    problem = json.load(open(TOOL_PROBLEM_PATH, encoding="utf-8"))
    result = CCB_T1(problem, registry=default_registry()).run()
    assert result["terminal_status"] == "CONCLUDED"
    record = result["tool_records"][0]
    store.progress("g_total",
                   "exact sum served: 2/3 + 3/4 = 17/12, gt 1",
                   provenance="ccb_t1",
                   artifact=f"tool_record_digest:{record['digest']}")

    # COMPLETION IS EARNED: the kernel proves the condition from the
    # tool-augmented facts and the problem's own rules
    base = json.load(open(TOOL_PROBLEM_PATH, encoding="utf-8"))
    facts = list(base["propositions"]) + list(record["result"]["add_facts"])
    rules = base["rules"]
    completion = store.complete("g_total", facts, rules,
                                provenance="kernel_proof")
    digest = store.save(os.path.join(workdir, STORE))
    payload = {"tool_status": result["terminal_status"],
               "completion": completion,
               "store_digest": digest}
    _write_log(workdir, "episode2", payload)
    return payload


# ----------------------------------------------------------------------
def episode3(workdir: str) -> Dict:
    from cas_math.discovery import discover
    from goals.store import GoalStore
    from rlp.fixture_loader import load_package
    from rlp.rlp import CAS_RLP
    from rlp.strategies import StrategyMemory

    store = GoalStore.load(os.path.join(workdir, STORE))
    store.begin_episode()
    store.start("g_discover", provenance="episode3_resumption")

    # LEARNING: the remembered class strategy repairs under budget
    memory = StrategyMemory()
    memory.add_provisional("overgeneral_rule", ["gt", "eq", "lt"],
                           provenance="prior_proof")
    memory.promote("overgeneral_rule")
    repair = CAS_RLP(load_package("r1_heavier_structural")).improve(
        strategy_memory=memory, max_evaluations=1)
    assert any(d["verdict"] == "PROMOTED" for d in repair["decisions"])
    store.progress("g_discover",
                   "learning leg: strategy-driven repair in 1 evaluation",
                   provenance="cas_rlp",
                   artifact=f"cycle_digest:{repair['cycle_digest']}")

    # DISCOVERY: machine-novel theorems proved by the trusted checker
    packet = discover()
    assert packet["theorems"], "no theorems discovered"
    # DIRECT FACT, disclosed (audit boundary): the theorem_proved
    # fact is constructed here from the sealed discovery packet - the
    # kernel check is a fact-echo; the EVIDENCE is the discovery
    # digest; allow_direct_fact=True acknowledges exactly that.
    completion = store.complete(
        "g_discover",
        facts=[{"pred": "theorem_proved",
                "args": [packet["discovery_digest"]]}],
        rules=[], provenance="discovery_sealed_evidence",
        allow_direct_fact=True)

    digest = store.save(os.path.join(workdir, STORE))
    payload = {"repair_promoted": True,
               "theorems": len(packet["theorems"]),
               "discovery_digest": packet["discovery_digest"],
               "completion": completion,
               "store_digest": digest}
    _write_log(workdir, "episode3", payload)
    return payload
