"""RT6 M4: run every expected/invalid case of the five admitted operations through reference_ops.py.
The case 'in' is exactly the operand set a learned operation module would receive (plus the operation id)."""
import json, math, pathlib, sys
LAB = pathlib.Path(r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab")
sys.path.insert(0, str(LAB)); import reference_ops as ref
d = json.loads((LAB / "OPERATION_CONTRACTS.json").read_text(encoding="utf-8"))
def run(name, args):
    if name == "compose": return ref.compose(*args)
    if name == "involute": return ref.involute(*args)
    if name == "is_admissible": return ref.is_admissible(args[0], tuple(args[1]), tuple(args[2]))
    if name == "domain_descent_mask": return ref.may_attend(tuple(args[0]), tuple(args[1]))
    if name == "rpm_embed_realize":
        e = ref.rpm_embed(args[0]); return {"embed": list(e), "realize": ref.rpm_realize(e)}
tot_ok = tot = 0
for name, o in d["operations"].items():
    ok = 0
    for c in o["expected_cases"]:
        got = run(name, c["in"])
        want = {"embed": c["embed"], "realize": c["realize"]} if name == "rpm_embed_realize" else c["out"]
        ok += int(got == want)
    inv_ok = 0
    for c in o["invalid_cases"]:
        try: run(name, c); 
        except ref.InvalidInput: inv_ok += 1
    tot_ok += ok + inv_ok; tot += len(o["expected_cases"]) + len(o["invalid_cases"])
    print("%-20s expected %d/%d  invalid->INVALID_INPUT %d/%d" % (name, ok, len(o["expected_cases"]), inv_ok, len(o["invalid_cases"])))
print("all cases reproduced by reference_ops from the operands alone: %d/%d" % (tot_ok, tot))
