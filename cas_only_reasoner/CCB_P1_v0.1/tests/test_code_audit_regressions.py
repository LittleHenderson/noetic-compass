"""Regression locks for the CCB-P1 adversarial audit (workflow
wf_feca63ef, 2026-08-29): every confirmed sandbox/authority finding
gets the test that would have caught it."""

import os

from codeboard import ProcedureStore, algorithm_battery, run, static_gate
from codeboard.spec import SPECS, memorization_defects
from codeboard.tracer import trace_run


# audit 1 (CARDINAL): the generator frame-walk escape to __import__
def test_generator_frame_walk_escape_refused_before_execution():
    escape = ("def f():\n"
              "    box = {}\n"
              "    def gen():\n"
              "        yield box['frame'].f_back.f_builtins"
              "['__import__']\n"
              "    g = gen()\n"
              "    box['frame'] = g.gi_frame\n"
              "    return list(g)[0]('os')\n")
    defects = static_gate(escape)
    assert defects  # refused statically
    assert run(escape, "f", [])["status"] in ("FORBIDDEN_EFFECT",)


def test_all_attribute_access_and_dunder_literals_blocked():
    assert static_gate("def f(x):\n    return x.gi_frame\n")
    assert static_gate("def f(x):\n    return x.f_builtins\n")
    assert static_gate('def f(x):\n    return "{0.__class__}"'
                       '.format(x)\n')
    assert static_gate("def f():\n    return __builtins__\n")
    assert static_gate('def f(d):\n    return d["__import__"]\n')
    assert static_gate("def f():\n    yield 1\n")
    assert static_gate("def f():\n    g = lambda: 1\n    return g()\n")


# audit 8/9 (major): single-line memory/CPU bombs
def test_memory_and_compute_bombs_refused():
    assert run("def f():\n    return len([0] * 5000000)\n",
               "f", [])["status"] == "FORBIDDEN_EFFECT"
    assert static_gate("def f():\n    return 2 ** 100000000\n")
    assert static_gate("def f():\n    return 'a' * 999999999\n")


# audit 10 (major): the tracer enforces the same budget across frames
def test_tracer_budgets_runaway_helper_frames():
    # a loop bound WITHIN the int-literal cap, but a tiny budget: the
    # STEP BUDGET (not the static cap) must fire inside the HELPER
    # frame - the tracer no longer scopes budgeting to the target
    # function only
    code = ("def helper():\n"
            "    x = 0\n"
            "    while x < 900000:\n"
            "        x = x + 1\n"
            "    return x\n"
            "def f():\n"
            "    return helper()\n")
    assert run(code, "f", [], step_budget=5000)["status"] \
        == "STEP_BUDGET_EXCEEDED"
    result = trace_run(code, "f", [], step_budget=5000)
    assert result["status"] == "TRACE_BUDGET"   # no longer hangs


# audit 6 (cardinal): a memorizing lookup table is refused
def test_memorizing_lookup_table_refused():
    table = ("def sum_list(xs):\n"
             "    table = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50,\n"
             "             6: 60, 7: 70, 8: 80, 9: 90, 10: 100,\n"
             "             11: 110, 12: 120, 13: 130, 14: 140,\n"
             "             15: 150, 16: 160, 17: 170, 18: 180,\n"
             "             19: 190, 20: 200, 21: 210, 22: 220}\n"
             "    return table.get(len(xs), 0)\n")
    assert memorization_defects(table)
    literal_compare = ("def f(xs):\n"
                       "    if xs == [1, 2, 3, 4]:\n"
                       "        return 99\n"
                       "    return 0\n")
    assert memorization_defects(literal_compare)
    # a genuine algorithm is NOT flagged
    real = ProcedureStore.load(
        os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))),
            "fixtures", "code_procedures.json"))
    if real.get("sum_list"):
        assert not memorization_defects(
            real.get("sum_list")["formal"]["code"])


# audit: the taught functions still pass under the hardened gate
def test_hardened_gate_admits_the_taught_procedures():
    store = ProcedureStore.load(
        os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))),
            "fixtures", "code_procedures.json"))
    for skill_id in ("sum_list", "reverse_string", "max_list",
                     "count_matching"):
        record = store.get(skill_id)
        if record is None:
            continue
        code = record["formal"]["code"]
        assert not static_gate(code), \
            f"{skill_id} rejected by hardened gate: {static_gate(code)}"
        ok, _ = algorithm_battery(skill_id, code, SPECS[skill_id])
        assert ok
