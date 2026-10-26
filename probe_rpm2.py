import sys, traceback
sys.path.insert(0, r"C:\Users\wakil\Documents\Codex\2026-10-16")
from rpm_council import engine as rpm
S, E, B = rpm.Stage, rpm.Evidence, rpm.Blocker


def cond(gid, stmt, d=None, w=None, p=None, a0=1.0, prereqs=()):
    c = rpm.Condition(id=gid, statement=stmt)
    c.scores = {S.ASPIRATION: a0, S.DRIVE: 1.0 if d is None else d,
                S.WILL: 1.0 if w is None else w, S.PROFICIENCY: 1.0 if p is None else p}
    c.prerequisites = list(prereqs)
    c.status = E.ESTABLISHED
    return c


def graph_of(*cs):
    g = rpm.Graph()
    for c in cs:
        g.add(c)
    return g


print("=" * 70)
print("R1  full report() text for a circular graph (a<->b)")
g = graph_of(cond("a", "a", d=0.0, prereqs=("b",)), cond("b", "b", d=0.0, prereqs=("a",)))
d = rpm.diagnose(g, "a", 0.5)
print(rpm.report(d))
print("--- where the word CIRCULAR appears: ---")
for i, ln in enumerate(rpm.report(d).splitlines()):
    if "CIRCULAR" in ln.upper():
        print("   line %d: %s" % (i, ln))

print()
print("=" * 70)
print("R2  which recursion blows up on a deep ACYCLIC chain?")
g = rpm.Graph()
prev = None
for i in range(3000):
    c = cond("c%d" % i, "lvl %d" % i, d=0.0 if i == 0 else 1.0)
    if prev:
        c.prerequisites = [prev]
    g.add(c)
    prev = c.id
try:
    rpm.diagnose(g, prev, 0.5)
except RecursionError:
    tb = traceback.format_exc().splitlines()
    frames = [l.strip() for l in tb if "engine.py" in l]
    print("   deep frames:", len(frames))
    for l in frames[-3:]:
        print("     ", l)
    print("   repeat line:", [l for l in tb if "line" in l][-1].strip())
except Exception as ex:
    print("  ", type(ex).__name__, ex)

print()
print("=" * 70)
print("R3  find_graph_cycles on the same deep chain, alone")
try:
    rpm.find_graph_cycles(g)
    print("   ok")
except RecursionError:
    print("   RecursionError from find_graph_cycles on an ACYCLIC graph")

print()
print("=" * 70)
print("R4  can the section-law assertion inside make_stage_state ever fire?")
import inspect
print("   ", inspect.getsource(rpm.make_stage_state).splitlines()[-8:])
print("   SectionLawViolation at construction is unreachable: embed() sets component[0]")
print("   to float(score); realize() returns component[0].")

print()
print("=" * 70)
print("R5  ASSUMED: does the 'fail closed on assumed' test pass for its stated reason?")
g = graph_of(cond("a", "assumed thing", d=0.0), cond("child", "child", prereqs=("a",)))
g.add_edge("a", rpm.Graph.ASSUMED, "child")
st = rpm.evaluate_condition("child", g, 0.5)
print("   with assumed node scoring d=0.0 -> child satisfied:", st[-1].satisfied,
      "(test asserts False and passes)")
g2 = graph_of(cond("a2", "assumed thing", d=1.0), cond("child2", "child", prereqs=("a2",)))
g2.add_edge("a2", rpm.Graph.ASSUMED, "child2")
st2 = rpm.evaluate_condition("child2", g2, 0.5)
print("   with assumed node scoring d=1.0 -> child satisfied:", st2[-1].satisfied,
      " <- ASSUMED satisfies the gate")
print("   same graph, diagnosed:", rpm.diagnose(g2, "child2", 0.5).blocker.value)

print()
print("=" * 70)
print("R6  test_gating_is_one_directional compares a graph with NO downstream node")
ga = graph_of(cond("x", "x", d=0.3, w=0.9, p=0.9))
gb = graph_of(cond("x", "x", d=0.3, w=0.1, p=0.1))
print("   graph A nodes:", list(ga.conditions), " graph B nodes:", list(gb.conditions))
print("   A/B identical in structure: only x's own scores differ -> the assertion compares")
print("   nothing with a downstream effect.")
