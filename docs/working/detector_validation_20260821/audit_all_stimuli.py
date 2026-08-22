"""AUDIT THE REST (v2 -- structural rule BUGFIX: genuine multi-class, not one-vs-rest) -- does the v19 template flaw also invalidate valence / Operator-10 / ^8-^9?

v19 lesson: a stimulus set can pass the char-ngram control while a SHORT HAND-WRITTEN RULE solves
it perfectly. Rather than hand-crafting regexes (subjective, and biased by my knowing the answer),
this searches AUTOMATICALLY for the shortest rule, which is an objective upper bound on how much
of each result is 'just a template':

  RULE FAMILY 1 -- best single WORD presence (one word per class, greedy, chosen on the SAME items)
  RULE FAMILY 2 -- best structural feature (internal period / comma count / char length threshold)

Reported per stimulus set alongside the published activation and char-ngram numbers. If a trivial
rule matches or beats the model, that result carries no evidence about representation.
$0, no model, no GPU -- pure text analysis.
"""
import re, json, hashlib, pathlib, itertools
from collections import Counter

SP = pathlib.Path(__file__).resolve().parent

# ---------------- stimulus sets whose results are STILL STANDING ----------------
# v10/v16 valence: TEST set = implicit-valence scenarios (the set the 0.938 was scored on)
VAL_POS=["She opened the letter and saw she had been accepted","After years of trying they finally held their newborn","He crossed the finish line as the crowd rose to their feet","The test came back clear and the doctor smiled","They were reunited at the gate after the long deployment","Her name was the first one called for the prize","The jury foreman read the single word they had hoped for","The last payment cleared and the house was finally theirs"]
VAL_NEG=["She opened the letter and saw she had been rejected","After years of trying the treatment had failed once more","He collapsed before the finish line as the crowd fell silent","The test came back and the doctor looked away","They stood at the gate but no one came off the plane","Her name was the only one missing from the list","The jury foreman read the word they had feared","The final notice cleared out what little they had saved"]
# v14 Operator-10: TEST set = FRESH non-colloquial phrasings (the set the 0.800 was scored on)
OP_TEST={
 "^0":["Democracy is not a thing you could ever hold in your hand","Seven has no colour, weight, or place; it lives only in thought"],
 "^1":["Every small sound in the room registered with her at once","He held the whole problem in view without letting any part slip"],
 "^2":["From the first glance she wanted the little blue house","He kept finding excuses to return to that one quiet cafe"],
 "^3":["After a single bite he quietly pushed the bowl aside","She found reasons to leave whenever that subject arose"],
 "^4":["The film sat with him, unshakeable, for a week afterward","Long after she spoke, her sentence kept returning to him"],
 "^5":["Every hardship she had survived was now folded into who she was","A lifetime at the workbench had become the man himself"],
 "^6":["He examined each assumption the whole theory was resting on","She separated the proposal into the smaller claims it was made of"],
 "^7":["By the thousandth time, his hands moved without a single thought","Morning after morning of it wore the habit smooth and automatic"],
 "^8":["The scent of pine tar pulled a whole childhood winter back up","One look at the old photo and his father was suddenly present again"],
 "^9":["With no warning at all, the finished solution was simply there","The forgotten name arrived on its own, asked for by nothing"]}
# v14 ^8/^9 construct-correct TEST set (the 0.917 was scored on)
CE_TEST={
 "^8":["The worn leather seat carried him straight back to his grandfather's garage","A few bars of that old tune and the whole summer stood in front of her again","The scent of chalk dust set a classroom from thirty years ago alight for him","One taste of the broth and her mother's kitchen rose up around her","The creak of that gate swung open his entire childhood","A stranger's cologne on the train and his first love was there once more"],
 "^9":["Halfway through dinner, the missing word was simply there","In the small hours the whole answer lay finished in her thoughts","Without her reaching for it, the man's name settled into place","The solution he had chased for weeks was suddenly, quietly present","Between one step and the next, the plan assembled itself complete","The forgotten address rose up on its own, wanted by nothing"]}
# v19 domain grid (KNOWN FAIL -- positive control for the audit itself)
DOM_TEST={
 "P":["The captain reported the cracked windscreen instead of flying on to stay on schedule","The carpenter turned the job down rather than build with timber he knew was rotten","The teller flagged the odd transfer even though it slowed the line behind her","The teacher reported the leaked exam rather than let the result stand"],
 "C":["A jet engine pushes air backward to drive the aircraft forward","Oak is denser and heavier than pine of the same size","A savings account pays interest on the money that is held in it","The alphabet used to write English is made up of twenty six letters"],
 "E":["The crew handled the storm in a way that put every passenger at ease","The finish on that cabinet is a pleasure to run your hand across","Working with that advisor left the family feeling genuinely looked after","Her class was the part of the day the children looked forward to"],
 "O":["Lower the landing gear. Line up with the runway. Ease back on the throttle.","Measure the plank twice. Cut along the marked line. Sand the edge smooth.","Enter the amount. Confirm the account number. Approve the transfer.","Hand out the worksheets. Read the instructions aloud. Collect the answers at the end."]}

def words(s): return set(re.findall(r"[a-z']+", s.lower()))

def best_single_word_rule(classes):
    """Greedy: pick one discriminative word per class; unmatched -> residue class. Returns (acc, rule)."""
    labels=list(classes)
    vocab=set()
    for c in labels:
        for s in classes[c]: vocab |= words(s)
    # score each (word,class): present in-class, absent out-of-class
    picks={}
    for c in labels:
        best=(-1,None)
        for w in vocab:
            inn=sum(1 for s in classes[c] if w in words(s))
            out=sum(1 for c2 in labels if c2!=c for s in classes[c2] if w in words(s))
            score=inn-2*out    # penalise leakage
            if score>best[0]: best=(score,w)
        picks[c]=best[1]
    # evaluate: first class whose word matches wins; ties/none -> residue = largest class w/o unique word
    def predict(s):
        ws=words(s); hits=[c for c in labels if picks[c] in ws]
        return hits[0] if hits else None
    ok=tot=0; unresolved=0
    for c in labels:
        for s in classes[c]:
            p=predict(s); tot+=1
            if p is None: unresolved+=1
            ok += (p==c)
    # residue assignment: give unresolved to the class that would gain most
    resid_best=0
    for cand in labels:
        gain=sum(1 for c in labels for s in classes[c] if predict(s) is None and c==cand)
        resid_best=max(resid_best,gain)
    return (ok+resid_best)/tot, picks

def best_structural_rule(classes):
    """Best structural rule as a GENUINE MULTI-CLASS predictor (not one-vs-rest).

    BUGFIX 2026-08-21: the first version scored structural features one-vs-rest, so on a 10-class
    set the degenerate rule "nothing is ^8" scored 18/20 = 0.90 and looked like it beat a 10-way
    0.800 model. That is not a comparable statistic. A structural rule must predict a CLASS for
    every item, exactly like the model does.
    """
    labels=list(classes); items=[(s,c) for c in labels for s in classes[c]]; tot=len(items)
    K=len(labels)
    best=(0.0,"none")
    def score_map(featfn, bins):
        # assign each bin to its majority class (fit on the same items = maximally generous)
        buckets={}
        for s,c in items: buckets.setdefault(bins(featfn(s)),[]).append(c)
        amap={b:max(set(cs),key=cs.count) for b,cs in buckets.items()}
        ok=sum(1 for s,c in items if amap.get(bins(featfn(s)))==c)
        return ok/tot
    # length quantile bins (K bins)
    lens=sorted(len(s) for s,_ in items)
    cuts=[lens[int(len(lens)*i/K)] for i in range(1,K)]
    def lenbin(v):
        b=0
        for c in cuts:
            if v>=c: b+=1
        return b
    a=score_map(len,lenbin); 
    if a>best[0]: best=(a,f"length-quantile bins ({K} bins, majority-mapped)")
    # comma count bins
    a=score_map(lambda s:s.count(','), lambda v:min(v,K-1))
    if a>best[0]: best=(a,"comma-count bins (majority-mapped)")
    # internal-period (2 bins) -- the v19 O tell
    a=score_map(lambda s:1 if __import__('re').search(r"\.\s",s) else 0, lambda v:v)
    if a>best[0]: best=(a,"internal-period present/absent (majority-mapped)")
    # word-count bins
    a=score_map(lambda s:len(s.split()), lenbin)
    if a>best[0]: best=(a,"word-count bins (majority-mapped)")
    return best

SETS={
 "valence ^2/^3 (v10/v16 test set)": ({"pos":VAL_POS,"neg":VAL_NEG}, 0.500, 0.938, 0.500),
 "Operator-10 fresh (v14 test set)": (OP_TEST, 0.100, 0.800, 0.550),
 "^8/^9 construct-correct (v14 test)": (CE_TEST, 0.500, 0.917, 0.833),
 "Domain-4 framing-stripped (v19 -- KNOWN FAIL, positive control)": (DOM_TEST, 0.250, 0.963, 0.688),
}
GATE=0.35   # rule accuracy above chance+gate margin => template-confounded
out={"gate_note":"a stimulus set FAILS if a trivial auto-found rule matches or approaches the published activation",
     "sets":{}}
print("==== AUTOMATED SHORTEST-RULE AUDIT (no model, $0) ====\n")
for name,(classes,chance,published_act,published_surf) in SETS.items():
    wacc,picks=best_single_word_rule(classes)
    sacc,sdesc=best_structural_rule(classes)
    rule_acc=max(wacc,sacc)
    verdict=("TEMPLATE-CONFOUNDED (rule >= published activation)" if rule_acc>=published_act
             else ("SUSPECT (rule beats char-ngram surface)" if rule_acc>published_surf
                   else "SURVIVES (rule below surface baseline)"))
    out["sets"][name]={"chance":chance,"published_activation":published_act,"published_char_ngram":published_surf,
        "best_word_rule_acc":round(wacc,3),"word_rule":{k:v for k,v in picks.items()},
        "best_structural_rule_acc":round(sacc,3),"structural_rule":sdesc,
        "shortest_rule_acc":round(rule_acc,3),"verdict":verdict}
    print(f"{name}")
    print(f"   chance {chance}   published activation {published_act}   char-ngram {published_surf}")
    print(f"   best single-word rule : {wacc:.3f}   picks={picks}")
    print(f"   best structural rule  : {sacc:.3f}   ({sdesc})")
    print(f"   SHORTEST RULE         : {rule_acc:.3f}  -> {verdict}\n")
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"audit_all_stimuli_results.json").write_bytes(raw)
print("sha256="+hashlib.sha256(raw).hexdigest()[:16])
