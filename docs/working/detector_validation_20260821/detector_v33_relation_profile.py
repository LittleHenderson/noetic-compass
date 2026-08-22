"""V33 -- RELATION LEGIBILITY PROFILE: is CAS ^8/^9 special, or one relation among many? ($0)

The CAS-specificity question is GREY. v32 gave a hint: CAS ^8/^9 (0.8033) beat temporal order
(0.7367) with non-overlapping CIs on the same model, same method, same pinned construction.
That is one comparison. This widens it to SIX relations under the identical pinned-pair design,
so the answer is a PROFILE, not a single contrast.

The point: if ^8/^9 sits at the top, that is evidence CAS names something the model encodes
unusually strongly. If it sits mid-pack, that is evidence AGAINST specificity -- CAS would be
naming an ordinary relation, which is exactly the skeptic's objection. EITHER OUTCOME IS
INFORMATIVE and is pre-registered here before the run.

Relations tested (each 60 pairs = 3 frames x 20 items):
  cas_8_9        trigger vs arrival        <- the CAS relation
  temporal       before vs after           <- ordinary time
  agent_patient  who did it to whom        <- the prompt-injection-adjacent one
  causal_vs_corr caused vs merely accompanied
  part_whole     contains vs contained-by
  speaker        who said what             <- the known-weak floor

Construction is unchanged and non-negotiable: identical word multisets AND identical char-ngram
bags (both baselines FORCED to 0.500), position counterbalanced, leave-one-PAIR-out, verdicts on
the selection-free mean over ALL layers, bootstrap 95% CI on per-pair scores.

BLOCKING pre-flight gate runs on every pair before the model loads; ANY failure aborts at $0.
Real pythia-160m through the attested engine.
"""
import sys, json, hashlib, pathlib, re
from collections import Counter
import numpy as np

REPO = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
WORKER = REPO / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker"
sys.path.insert(0, str(WORKER))
SP = pathlib.Path(__file__).resolve().parent
STORE = SP / "models" / "alias--pythia-160m-reserialized"
REV = "d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97"

NOUNS = [("scent of tar","memory of childhood"),("sound of the bell","winter of her youth"),
 ("taste of burnt sugar","kitchen of his mother"),("smell of wet chalk","classroom of that year"),
 ("creak of the gate","summer of his boyhood"),("colour of the dress","evening of the party"),
 ("weight of the coat","shape of his father"),("hum of the engine","drive along the coast"),
 ("grain of the wood","hands of her grandfather"),("chill of the water","morning she had lost"),
 ("shape of the writing","years of her schooling"),("rhythm of the train","town they had left"),
 ("glare of the lamp","office of his first job"),("scrape of the chair","hall of that school"),
 ("drift of the smoke","camp beside the river"),("weight of the key","door of the old house"),
 ("hiss of the kettle","flat above the bakery"),("crack of the ice","lake behind the farm"),
 ("dust of the road","walk home from market"),("chime of the clock","room where she waited")]
PEOPLE = [("nurse","patient"),("teacher","pupil"),("captain","engineer"),("lawyer","client"),
 ("driver","courier"),("farmer","neighbour"),("banker","auditor"),("chemist","student"),
 ("editor","author"),("ranger","climber"),("plumber","tenant"),("coach","striker"),
 ("curator","donor"),("pilot","mechanic"),("baker","supplier"),("nanny","toddler"),
 ("dentist","patient"),("porter","guest"),("tailor","actor"),("vet","owner")]
INSTR = [("follow the rules","ignore the rules"),("keep the secret","leak the secret"),
 ("verify the sender","trust the sender"),("refuse the request","accept the request"),
 ("check the signature","skip the signature"),("log every action","hide every action"),
 ("ask for approval","waive the approval"),("protect the record","delete the record"),
 ("report the error","conceal the error"),("limit the access","widen the access"),
 ("confirm the amount","raise the amount"),("respect the policy","override the policy"),
 ("encrypt the backup","expose the backup"),("review the change","deploy the change"),
 ("quarantine the file","execute the file"),("mask the identifier","reveal the identifier"),
 ("throttle the caller","promote the caller"),("archive the message","forward the message"),
 ("validate the token","reuse the token"),("escalate the alert","silence the alert")]

def frames3(a_verb, b_verb):
    """three frames swapping which slot gets a_verb vs b_verb; ' : ' keeps junctions identical"""
    return [
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; done", f"the {x} : {b_verb} ; the {y} : {a_verb} ; done"),
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; end",  f"the {x} : {b_verb} ; the {y} : {a_verb} ; end"),
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; stop", f"the {x} : {b_verb} ; the {y} : {a_verb} ; stop"),
    ]
def frames3_people(a_verb, b_verb):
    return [
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; done", f"the {x} : {b_verb} ; the {y} : {a_verb} ; done"),
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; end",  f"the {x} : {b_verb} ; the {y} : {a_verb} ; end"),
      lambda x,y: (f"the {x} : {a_verb} ; the {y} : {b_verb} ; stop", f"the {x} : {b_verb} ; the {y} : {a_verb} ; stop"),
    ]
SPK_FRAMES = [
 lambda p,q: (f"system said : {p} ; user said : {q} ; done", f"system said : {q} ; user said : {p} ; done"),
 lambda p,q: (f"from system : {p} ; from user : {q} ; end",  f"from system : {q} ; from user : {p} ; end"),
 lambda p,q: (f"per system : {p} ; per user : {q} ; stop",   f"per system : {q} ; per user : {p} ; stop"),
]

def build(frames, content):
    out=[]
    for fi,f in enumerate(frames):
        for a,b in content:
            A,B=f(a,b); out.append((A,B,fi))
    return out

RELATIONS = {
 "cas_8_9_trigger_arrival": build(frames3("triggered","arrived"), NOUNS),
 "temporal_before_after":   build(frames3("preceded","followed"), NOUNS),
 "agent_patient":           build(frames3_people("acted","waited"), PEOPLE),
 "causal_vs_correlate":     build(frames3("caused","accompanied"), NOUNS),
 "part_whole":              build(frames3("contained","entered"), NOUNS),
 "speaker_binding":         build(SPK_FRAMES, INSTR),
}

WORD=re.compile(r"[a-z']+")
def wm(x): return Counter(WORD.findall(x.lower()))
def ngm(x, ns=(2,3,4)):
    t=x.lower(); c=Counter()
    for n in ns:
        for i in range(len(t)-n+1): c[t[i:i+n]]+=1
    return c

print("=== BLOCKING PRE-FLIGHT GATE (before model load) ===", flush=True)
gate={}; abort=False
for name,pairs in RELATIONS.items():
    wbad=[i for i,(A,B,_) in enumerate(pairs) if wm(A)!=wm(B)]
    resid=[]
    for A,B,_ in pairs:
        ca,cb=ngm(A),ngm(B)
        resid.append((sum((ca-cb).values())+sum((cb-ca).values()))/(sum(ca.values())+sum(cb.values())))
    rmax=float(max(resid)); ok=(not wbad) and rmax<=0.001
    gate[name]={"n_pairs":len(pairs),"word_mismatches":len(wbad),"ngram_residual_max":round(rmax,6),"passed":ok}
    print(f"  {name:26} n={len(pairs):3} word_mismatch={len(wbad):2} residual={rmax:.6f} {'PASS' if ok else 'FAIL'}")
    if not ok:
        abort=True; bad=int(np.argmax(resid)); A,B,fi=pairs[bad]; ca,cb=ngm(A),ngm(B)
        print(f"     A-only={dict(ca-cb)} B-only={dict(cb-ca)}\n     A: {A}\n     B: {B}")
if abort:
    print("\n  GATE FAILED -> ABORT, $0 spent."); sys.exit(1)
print("  GATE PASSED -> both surface baselines FORCED to 0.500 on every relation.\n")

from app.runtime.open_weight.engine import (RuntimeLoadConfig, load_open_weight_runtime, capture_greedy_trajectory)
from app.runtime.open_weight.identity import LocalModelSnapshot
print("loading runtime (full attestation)...", flush=True)
rt = load_open_weight_runtime(RuntimeLoadConfig(
    snapshot=LocalModelSnapshot(model_id="pythia-160m-reserialized", revision=REV,
        snapshot_root=STORE/"snapshots"/REV, model_storage_root=STORE),
    adapter_source_path=WORKER.parent/"api"/"services"/"cas_harness_interpretability_adapter.py",
    entrypoint_source_path=pathlib.Path(__file__).resolve(), device="cpu", dtype="auto",
    minimum_available_memory_bytes=268435456, minimum_capture_available_bytes=134217728))
L=int(rt.layer_count); tok=rt.tokenizer
_cache={}
def rv(p):
    if p not in _cache:
        cap=capture_greedy_trajectory(rt, scenario_id="v33", prompt=p, max_new_tokens=1, seed=0)
        arr=cap.arrays if hasattr(cap,"arrays") else cap["arrays"]
        _cache[p]=np.asarray(arr["residual_states"])[0].astype(np.float64)
    return _cache[p]

def per_pair_matrix(RA, RB, L):
    n=len(RA); A=np.stack(RA); B=np.stack(RB); M=np.zeros((n,L))
    for li in range(L):
        a=A[:,li,:]; b=B[:,li,:]; sa=a.sum(0); sb=b.sum(0)
        for i in range(n):
            ca=(sa-a[i])/(n-1); cb=(sb-b[i])/(n-1)
            hit  = float(np.linalg.norm(a[i]-ca) < np.linalg.norm(a[i]-cb))
            hit += float(np.linalg.norm(b[i]-cb) < np.linalg.norm(b[i]-ca))
            M[i,li]=hit/2.0
    return M

res={"design":"relation legibility profile -- 6 relations, identical pinned-pair construction",
     "preregistered":"if cas_8_9 tops the profile that supports CAS naming an unusually strongly encoded relation; if it sits mid-pack that is evidence AGAINST specificity. Both outcomes are informative and are recorded before the run.",
     "model":"pythia-160m (reserialized, attested engine)","layers":L,"chance":0.5,
     "preflight_gate":gate,"relations":{}}
rng=np.random.default_rng(20260822)
for name,pairs in RELATIONS.items():
    print(f"capturing {name} ({2*len(pairs)} passes) ...", flush=True)
    A=[p[0] for p in pairs]; B=[p[1] for p in pairs]
    RA=[rv(s) for s in A]; RB=[rv(s) for s in B]
    lenbad=sum(1 for a,b in zip(A,B) if len(tok.encode(a))!=len(tok.encode(b)))
    M=per_pair_matrix(RA,RB,L)
    assert set(np.unique(M))<={0.0,0.5,1.0}
    per_layer={li:round(float(M[:,li].mean()),4) for li in range(L)}
    bl=max(per_layer,key=per_layer.get)
    ps=M.mean(axis=1); mean_all=float(ps.mean())
    boots=[float(ps[rng.integers(0,len(ps),len(ps))].mean()) for _ in range(2000)]
    lo,hi=np.percentile(boots,[2.5,97.5])
    res["relations"][name]={"n_pairs":len(pairs),"n_items":2*len(pairs),
      "token_length_mismatches":lenbad,"bag_of_words":0.5,"char_ngram":0.5,
      "activation_best":per_layer[bl],"activation_best_layer":bl,
      "mean_over_layers":round(mean_all,4),
      "bootstrap95":[round(float(lo),4),round(float(hi),4)],
      "excludes_chance":bool(lo>0.5)}
    print(f"   best {per_layer[bl]:.3f} (L{bl})  MEAN {mean_all:.4f}  95%CI [{lo:.4f},{hi:.4f}]  len {lenbad}", flush=True)

rank=sorted(res["relations"].items(), key=lambda kv: -kv[1]["mean_over_layers"])
res["ranking"]=[{"relation":k,"mean":v["mean_over_layers"],"ci":v["bootstrap95"]} for k,v in rank]
cas=res["relations"]["cas_8_9_trigger_arrival"]
others={k:v for k,v in res["relations"].items() if k!="cas_8_9_trigger_arrival"}
beaten=[k for k,v in others.items() if cas["bootstrap95"][0] > v["bootstrap95"][1]]
ties  =[k for k,v in others.items() if not (cas["bootstrap95"][0] > v["bootstrap95"][1] or v["bootstrap95"][0] > cas["bootstrap95"][1])]
above =[k for k,v in others.items() if v["bootstrap95"][0] > cas["bootstrap95"][1]]
res["cas_position"]={"rank":[k for k,_ in rank].index("cas_8_9_trigger_arrival")+1,
  "beats_with_nonoverlapping_ci":beaten,"ci_overlaps_with":ties,"beaten_by":above}
res["verdict"]=("CAS_TOPS_PROFILE" if not above and beaten else
                ("CAS_MID_PACK" if above else "CAS_TIED"))
raw=json.dumps(res,indent=2,sort_keys=True).encode()
(SP/"detector_v33_relation_profile_results.json").write_bytes(raw)
print("\n==== RELATION LEGIBILITY PROFILE (pythia-160m) ====")
for k,v in rank:
    ci=v["bootstrap95"]; star=" <-- CAS" if k=="cas_8_9_trigger_arrival" else ""
    print(f"  {k:26} {v['mean_over_layers']:.4f}  CI [{ci[0]:.4f},{ci[1]:.4f}]  best {v['activation_best']:.3f}{star}")
print(f"\n  CAS rank {res['cas_position']['rank']} of {len(rank)}")
print(f"  beats (non-overlapping CI): {beaten}")
print(f"  overlaps: {ties}")
print(f"  beaten by: {above}")
print(f"  VERDICT: {res['verdict']}")
print("sha256="+hashlib.sha256(raw).hexdigest()[:16])
