"""Probes for the CO-3 negative read of rpm_council/engine.py. Read-only w.r.t. the engine."""
import sys, io, traceback, linecache

sys.path.insert(0, r"C:\Users\wakil\Documents\Codex\2026-10-16")
from rpm_council import engine as rpm

S, E, B = rpm.Stage, rpm.Evidence, rpm.Blocker


def cond(gid, statement, d=None, w=None, p=None, a0=1.0, ev=None, prereqs=(), status=None):
    c = rpm.Condition(id=gid, statement=statement)
    c.scores = {S.ASPIRATION: a0, S.DRIVE: 1.0 if d is None else d,
                S.WILL: 1.0 if w is None else w, S.PROFICIENCY: 1.0 if p is None else p}
    if ev:
        c.evidence = ev
    c.prerequisites = list(prereqs)
    c.status = E.ESTABLISHED if status is None else status
    return c


def graph_of(*cs):
    g = rpm.Graph()
    for c in cs:
        g.add(c)
    return g


print("=" * 70)
print("P1  BUG 2 -- undefined prerequisite: does KeyError still escape?")
g = graph_of(cond("target", "the outcome", prereqs=("never_defined",)))
try:
    d = rpm.diagnose(g, "target", 0.5)
    print("   returned:", d.blocker)
except Exception:
    tb = traceback.format_exc()
    print("   ESCAPED:")
    for ln in tb.strip().splitlines()[-8:]:
        print("     " + ln)

print()
print("=" * 70)
print("P1b  where is the unguarded dereference?  (known_requires_of vs requires_of)")
for name in ("known_requires_of", "requires_of"):
    print("   %-20s exists=%s" % (name, hasattr(rpm.Graph, name)))
import inspect
src = inspect.getsource(rpm._diagnose)
for i, ln in enumerate(src.splitlines(), start=1):
    if "requires_of" in ln or "evaluate_condition" in ln:
        print("   _diagnose%s -> %s" % ("/loop", ln.strip()))

print()
print("=" * 70)
print("P2  cycle branch reachability: how many times does line 429 execute?")
ENG = rpm.__file__
hits = {"cycle_branch": 0, "eval_calls": 0}


def tracer(frame, event, arg):
    if frame.f_code.co_filename != ENG:
        return None
    if event == "call" and frame.f_code.co_name == "evaluate_condition":
        hits["eval_calls"] += 1
    if event == "line" and frame.f_lineno == 429:
        hits["cycle_branch"] += 1
    return tracer


def run_case(label, g, target):
    hits["cycle_branch"] = hits["eval_calls"] = 0
    sys.settrace(tracer)
    try:
        d = rpm.diagnose(g, target, 0.5)
        out = "blocker=%s cycles=%s" % (d.blocker.value, getattr(d, "graph_cycles"))
    except Exception as ex:
        out = "RAISED %s: %s" % (type(ex).__name__, ex)
    finally:
        sys.settrace(None)
    print("   %-28s eval_calls=%d fabricated_chain_hits=%d  |  %s"
          % (label, hits["eval_calls"], hits["cycle_branch"], out))


run_case("two-node cycle a<->b",
         graph_of(cond("a", "a", d=0.0, prereqs=("b",)), cond("b", "b", d=0.0, prereqs=("a",))), "a")
run_case("self loop",
         graph_of(cond("self", "requires itself", d=0.0, prereqs=("self",))), "self")
run_case("3-chain cyclic tail",
         graph_of(cond("t", "t", prereqs=("m",)), cond("m", "m", prereqs=("t",))), "t")
print("   -> if fabricated_chain_hits is 0 on every cycle case, the invented-chain")
print("      branch never runs; something else is what stops the recursion.")

print()
print("=" * 70)
print("P3  what the human-readable report says about a circular graph")
g = graph_of(cond("a", "a", d=0.0, prereqs=("b",)), cond("b", "b", d=0.0, prereqs=("a",)))
d = rpm.diagnose(g, "a", 0.5)
txt = rpm.report(d)
print("   graph_cycles attribute  :", getattr(d, "graph_cycles"))
print("   'CIRCULAR' in report()  :", "CIRCULAR" in txt)
print("   'cycl' in report()      :", "cycl" in txt.lower())
print("   report() says           : blocker=%s  condition=%s" % (d.blocker.value, d.condition))
print("   graph_cycles in to_json :", rpm.to_json(d)["graph_cycles"])
print("   'graph_cycles' in report:", "graph_cycles" in txt)

print()
print("=" * 70)
print("P4  'trusting a self-report': CONTRASTED with an unexamined end")
g = graph_of(cond("a", "a"), cond("b", "b"))
g.add_edge("a", rpm.Graph.CONFLICTS, "b")
d = rpm.diagnose(g, "a", 0.5)
print("   contradiction reported:", getattr(d, "contradictions"))
print("   but b was never evaluated: all_states keys =", list(getattr(d, "all_states").keys()))
print("   -> both-ends-satisfied is computed only for nodes the diagnosis happened to touch,")
print("      and 'not looked at' is reported identically to 'not contradictory'.")

print()
print("=" * 70)
print("P5  section law: can verify_section_law ever fail?")
print("   realize(embed(s)) == float(s) by construction?")
for s in (0.0, 0.3, 0.5, 0.9999999, 1.0):
    e = rpm.embed(s)
    print("     s=%-10r linear==float(s): %s" % (s, e.components[0] == float(s)))
print("   embed() returns Embedded((float(score), ...)); realize() returns components[0].")
print("   so the law compares a value with itself through the same producer.")
try:
    rpm.verify_section_law(float("nan"))
    print("   nan accepted!")
except rpm.RpmError as ex:
    print("   nan refused by the RANGE check, not by the law check:", ex)

print()
print("=" * 70)
print("P6  ASSUMED edge to a node whose own scores are fine")
g = graph_of(cond("a", "something taken for granted"), cond("target", "the outcome"))
g.add_edge("a", rpm.Graph.ASSUMED, "target")
d = rpm.diagnose(g, "target", 0.5)
print("   blocker:", d.blocker.value, " (Graph docstring: 'an ASSUMED prerequisite does NOT")
print("                                   satisfy the gate')")
print("   safeguards:", d.safeguards_fired)
print("   the passing test uses an assumed node with d=0.0, so it fails closed for an")
print("   unrelated reason.")

print()
print("=" * 70)
print("P7  deep acyclic graph -- is there still a crash-shaped answer?")
for n in (100, 300, 900, 3000):
    g = rpm.Graph()
    prev = None
    for i in range(n):
        c = cond("c%d" % i, "lvl %d" % i, d=0.0 if i == 0 else 1.0)
        if prev:
            c.prerequisites = [prev]
        g.add(c)
        prev = c.id
    try:
        d = rpm.diagnose(g, prev, 0.5)
        out = "blocker=%s" % d.blocker.value
    except RecursionError as ex:
        out = "RecursionError (acyclic graph!)"
    except Exception as ex:
        out = "%s: %s" % (type(ex).__name__, ex)
    print("   chain length %5d -> %s" % (n, out))

print()
print("=" * 70)
print("P8  fail-closed on an ABSENT prerequisite, evaluated (not diagnosed) directly")
g = graph_of(cond("target", "the outcome", prereqs=("never_defined",)))
try:
    st = rpm.evaluate_condition("target", g, 0.5)
    print("   evaluate_condition -> satisfied:", [s.satisfied for s in st])
except Exception as ex:
    print("   RAISED:", type(ex).__name__, ex)
print("   but diagnose() on the same graph:", end=" ")
try:
    print(rpm.diagnose(g, "target", 0.5).blocker.value)
except Exception as ex:
    print("RAISED %s: %s" % (type(ex).__name__, ex))
