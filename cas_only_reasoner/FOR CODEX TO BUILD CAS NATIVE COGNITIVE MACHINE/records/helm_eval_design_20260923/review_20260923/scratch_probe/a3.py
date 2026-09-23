# Pure-Python replay of the probe's verdict arithmetic (analogy_wiring_probe.py:182-221) on synthetic
# "repairs" whose world scores are s(c) = a(focus_shape) + b(focus_shape) * h(c): no focus-to-candidate comparison.
import json, itertools, random, sys
sys.path.insert(0, "D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_eval_design_20260923/analogy_wiring_probe")
import analogy_wiring_probe as P   # top level imports stdlib only; torch is imported inside main()
C=json.load(open("D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json",encoding="utf-8"))
bank={w["world_id"]:w for w in C["bank"]["worlds"]}
alts=P.alternative_shapes(C["bank"]["worlds"])
def graph(w):
    refs=sorted(x["ref"] for x in w["nodes"]); i={r:k for k,r in enumerate(refs)}
    return len(refs),[(i[e["source"]],i[e["target"]]) for e in w["contains"]],i[w["declared_whole"]]
an=sorted((r for r in C["registry"] if r["query"]["kind"]=="analogy"), key=lambda r:r["record_id"])
rng=random.Random(7); h={k:rng.gauss(0,1) for k in bank}
def run(kind):
    ga={}; 
    def a(shape): return ga.setdefault(shape,(rng.gauss(0,1),abs(rng.gauss(1,0.3))))
    def scores(shape):
        off,sc=a(shape)
        if kind=="offset": return {k:h[k]+off for k in bank}
        return {k:sc*h[k]+off for k in bank}
    base={}; m3={}; top1=0; rankchg=0
    for r in an:
        f=r["source_world_id"]; n,E,whole=graph(bank[f]); own=P.canon_shape(n,E)
        s=scores(own); base[r["record_id"]]=(f,s); worst=0.0
        for shp,edges in alts.get(n,[]):
            if shp==own: continue
            ch=scores(shp)
            worst=max(worst,max(abs(ch[c]-s[c]) for c in s if c!=f))
            nf=[c for c in s if c!=f]
            if sorted(nf,key=s.get)!=sorted(nf,key=ch.get): rankchg+=1
            if max(ch,key=ch.get)!=max(s,key=s.get): top1+=1
        m3[r["record_id"]]=worst
    fa,sa=base[P.WITNESSES[0]]; fb,sb=base[P.WITNESSES[1]]
    m1=max(abs(sa[c]-sb[c]) for c in sa if c in sb and c not in (fa,fb))
    share=sum(v>P.TAU_PRESENT for v in m3.values())/len(m3)
    verdict="PRESENT" if (m1>P.TAU_PRESENT and share>=P.PRESENT_SHARE) else "not PRESENT"
    print(kind, "M1=%.4f"%m1, "M3_share=%.3f"%share, "verdict:",verdict, "| rewires changing non-focus RANKING:",rankchg, "| top1 changes:",top1)
run("offset"); run("affine")
