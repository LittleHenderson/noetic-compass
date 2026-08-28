"""Authoring a brand-new problem: a family-relation syllogism.

The battery has no grandparent task. This file builds one from scratch
and runs it - that is the interaction surface: the machine is ONE generic
reasoner; problems are CAS-encoded data. Nothing in cas_rr/ knows about
grandparents.

    python examples/custom_kinship.py

Expected output:

    CONCLUDED -> grandparent(ada,cy)
    proof: grandparent(ada,cy) rules: ['r_grandparent']
           premises: ['parent(ada,bo)', 'parent(bo,cy)']
"""

import os
import sys

# Runnable from any directory: put the package root on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cas_rr.foundations import GoalFrame
from cas_rr.runtime import CASRuntime, Problem, default_constitution
from cas_rr.terms import Atom, Rule


def A(pred, *args):
    return Atom(pred, tuple(args))


facts = [A("parent", "ada", "bo"), A("parent", "bo", "cy")]
rules = [
    Rule("r_grandparent",
         [A("parent", "?X", "?Y"), A("parent", "?Y", "?Z")],
         A("grandparent", "?X", "?Z"), "example", "two-step kinship"),
]
goal = GoalFrame(
    goal_id="g_kinship",
    foundation_ref="TF4b",          # social cognition channel
    desired_outcome=A("grandparent", "ada", "cy"),
    kind="question",
)
problem = Problem(
    "custom_kinship_01",
    "Is ada a grandparent of cy? (authored example)",
    facts, rules,
    [A("grandparent", "ada", "cy"), A("grandparent", "cy", "ada")],
    goal,
)

packet = CASRuntime(default_constitution(), problem).run()
print(packet["terminal_status"], "->", packet["output"]["conclusion"])
for rec in packet["inferences"].values():
    if rec["success"]:
        print("proof:", rec["conclusion"],
              "rules:", rec["rules_used"],
              "premises:", rec["premises_used"])
