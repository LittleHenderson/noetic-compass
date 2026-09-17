import math, pickle, pathlib, struct, sys
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION")); sys.path.insert(0, str(HOME))
from cas_meta2.typed_teaching import binding, course, slots, worker_contract
SEED=20260916; D=64
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
HEAD=["START","FORMAT","BINDINGS","ALIASES","POLICY","SOURCE","RECORD","QUERY","END"]; Q=HEAD.index("QUERY")
def unit(v):
    n=math.sqrt(sum(x*x for x in v)); return [x/n for x in v] if n else v
def rv(dom): return list(struct.unpack("<64f", binding.row_bytes(dom, seed=SEED, d_model=D)))
feats=pickle.loads(CACHE.read_bytes())
frozen,_t,_s = worker_contract.load_material(HOME)
# the FROZEN readout rows for W0..W63, exactly as the learner uses them
readout = {f"W{i}": rv(["readout", f"W{i}"]) for i in range(64)}
print("rebuilt the frozen readout rows for W0..W63")
# rebuild the REAL slot encodings (same construction as the learner)
by_id={r["record_id"]:f for r,f in zip(frozen["registry"],feats)}
enc=[]; y=[]
for row in frozen["registry"]:
    f = by_id.get(row["record_id"])
    if f is None: continue
    packet = course.model_packet(frozen, row["record_id"])
    plan = slots.compile_slots(packet); validated = slots.validate_plan(packet, plan)
    spec = binding._query_spec(validated, plan["slots"][0])
    s = rv(["query", spec])
    flat=f["cat_head"]; qrow=flat[Q*64:(Q+1)*64]
    mean=f["mean"]
    enc.append((f["focus"], unit([(a+b)/math.sqrt(2) for a,b in zip(mean,s)]),
                            unit([(a+b)/math.sqrt(2) for a,b in zip(qrow,s)])))
print(f"encodings: {len(enc)}")
print()
print("="*92)
print("THE LEARNER'S ACTUAL READOUT: argmax over the FROZEN readout rows (no training)")
print("chance = 1/64 = 1.5625%")
print("="*92)
for label, idx in (("current slot encoding (mean+slot)", 1), ("proposed (query+slot)", 2)):
    hits=0
    for focus, a, b in enc:
        v = a if idx==1 else b
        scores = {k: sum(p*q for p,q in zip(v, r)) for k,r in readout.items()}
        best = max(scores, key=scores.get)
        if int(best[1:]) == focus: hits+=1
    print(f"  {label:38s} {hits:4d}/{len(enc):<4d} = {100*hits/len(enc):6.2f}%  "
          f"{hits/len(enc)*64:5.1f}x chance")
