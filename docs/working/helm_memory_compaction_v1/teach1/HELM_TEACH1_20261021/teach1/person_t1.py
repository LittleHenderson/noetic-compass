"""The scripted person of TEACH-1 (pre-code 4.5): answers HELM's refresh questions from the key only.

Right value with probability 0.75, "I don't remember." with probability 0.25, at the PERSON seed; never a wrong value
in v1 (OPEN_QUESTIONS Q9 a). A question about an unknown-to-the-person fact or about a small-talk turn is always
answered "I don't remember." Every draw is recorded (I11: the answers come from the key file and nothing else).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from . import common_t1 as C

DONT_REMEMBER = "I don't remember."


class ScriptedPerson:
    def __init__(self, world: Dict[str, Any], turns: List[Dict[str, Any]], seed) -> None:
        self.world = world
        self.by_turn = {t["turn_index"]: t for t in turns}
        self.facts = {f["id"]: f for f in world["facts"]}
        self.rng = random.Random(f"{seed}:person:{world['world_id']}")
        self.draws: List[Dict[str, Any]] = []

    def fact_for_turns(self, turn_ids: List[int]) -> Optional[Dict[str, Any]]:
        """The keyed fact behind a capsule's turns: the first keyed turn among them (a FIX turn names its fact)."""
        for tid in turn_ids:
            t = self.by_turn.get(tid)
            if t and t.get("fact_id"):
                return self.facts.get(t["fact_id"])
        return None

    def answer(self, turn_ids: List[int], capsule_id: str) -> Dict[str, Any]:
        f = self.fact_for_turns(turn_ids)
        u = self.rng.random()
        if f is None:
            text, kind = DONT_REMEMBER, "NOT_A_FACT"
        elif f.get("unknown"):
            text, kind = DONT_REMEMBER, "KEY_UNKNOWN"
        elif u < C.PERSON_RIGHT_SHARE:
            text, kind = "Yes. " + f["statement"], "RIGHT"
        else:
            text, kind = DONT_REMEMBER, "DONT_REMEMBER"
        row = {"capsule_id": capsule_id, "turn_ids": list(turn_ids), "fact_id": f["id"] if f else None, "draw": u,
               "kind": kind, "text": text}
        self.draws.append(row)
        return row
