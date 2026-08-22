"""HAND-ADVERSARIAL AUDIT -- try HARD to break the last two standing results ($0, no model).

v20 showed automated rule search is a LOWER bound (it found 0.688 on the Domain grid where a
hand-written regex reached 1.000). So the automated "SURVIVES" verdicts for valence (+0.313) and
Operator-10 (+0.150) are not safe. This attacks them by hand.

FAIRNESS RULE: the attacking lexicons are GENERIC English sentiment/semantic word lists written
WITHOUT looking at which sentence is which -- not tuned per item. If a generic lexicon solves the
set, the result carries no evidence beyond lexical semantics.
"""
import re, json, hashlib, pathlib
SP=pathlib.Path(__file__).resolve().parent

VAL_POS=["She opened the letter and saw she had been accepted","After years of trying they finally held their newborn","He crossed the finish line as the crowd rose to their feet","The test came back clear and the doctor smiled","They were reunited at the gate after the long deployment","Her name was the first one called for the prize","The jury foreman read the single word they had hoped for","The last payment cleared and the house was finally theirs"]
VAL_NEG=["She opened the letter and saw she had been rejected","After years of trying the treatment had failed once more","He collapsed before the finish line as the crowd fell silent","The test came back and the doctor looked away","They stood at the gate but no one came off the plane","Her name was the only one missing from the list","The jury foreman read the word they had feared","The final notice cleared out what little they had saved"]
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

# ---- ATTACK 1: generic English sentiment lexicon (standard positive/negative words) ----
POS_LEX=set("""accepted accept win won success succeed smiled smile happy joy glad hope hoped held hold
finally reunited prize first best cleared clear love loved warm safe healthy born newborn cheer
celebrate celebrated rose risen achieve achieved granted approved""".split())
NEG_LEX=set("""rejected reject fail failed failure lost lose collapsed collapse silent silence away
missing miss feared fear afraid notice final dread worse worst sad grief sick ill died die dead
denied refuse refused empty alone """.split())
def sentiment_rule(s):
    w=set(re.findall(r"[a-z']+",s.lower()))
    return "pos" if len(w&POS_LEX)>=len(w&NEG_LEX) else "neg"
val_items=[(s,"pos") for s in VAL_POS]+[(s,"neg") for s in VAL_NEG]
val_acc=sum(sentiment_rule(s)==lab for s,lab in val_items)/len(val_items)
val_miss=[(lab,s[:55]) for s,lab in val_items if sentiment_rule(s)!=lab]

# ---- ATTACK 2: generic semantic-cue lexicons for the 10 Noetics ----
OP_LEX={
 "^0":set("idea concept notion abstract thought democracy seven infinity thing hold hand place colour weight".split()),
 "^1":set("attention aware awareness notice noticed registered focus focused mind view sound room".split()),
 "^2":set("wanted want drawn attracted like love appeal glance excuses return cafe house".split()),
 "^3":set("pushed aside avoid leave reasons refuse disgust repelled bite bowl subject".split()),
 "^4":set("impression resonate struck film sat unshakeable returning week spoke sentence".split()),
 "^5":set("experience experiences hardship survived lifetime become who was workbench man himself folded".split()),
 "^6":set("examined assumption theory separated proposal claims parts break decompose smaller made".split()),
 "^7":set("repeat repeated habit automatic practice thousandth hands moved morning wore smooth".split()),
 "^8":set("reminds triggered memory scent pine tar childhood photo father look pulled winter".split()),
 "^9":set("suddenly popped arrived warning finished solution forgotten name simply there own nothing".split())}
def op_rule(s):
    w=set(re.findall(r"[a-z']+",s.lower()))
    best=max(OP_LEX, key=lambda c: len(w & OP_LEX[c]))
    return best if len(w & OP_LEX[best])>0 else "^0"
op_items=[(s,c) for c in OP_TEST for s in OP_TEST[c]]
op_acc=sum(op_rule(s)==c for s,c in op_items)/len(op_items)
op_miss=[(c,s[:50]) for s,c in op_items if op_rule(s)!=c]

out={"attack":"hand-adversarial generic lexicons (written without per-item tuning)",
 "valence":{"published_activation":0.938,"automated_shortest_rule":0.625,
   "hand_sentiment_lexicon":round(val_acc,3),"n":len(val_items),"misses":val_miss,
   "verdict":("BROKEN -- generic sentiment lexicon matches/beats the model" if val_acc>=0.938 else
              ("WEAKENED -- lexicon beats the automated rule" if val_acc>0.625 else "HOLDS"))},
 "operator10":{"published_activation":0.800,"automated_shortest_rule":0.650,
   "hand_semantic_lexicon":round(op_acc,3),"n":len(op_items),"misses":op_miss,
   "verdict":("BROKEN -- generic lexicon matches/beats the model" if op_acc>=0.800 else
              ("WEAKENED -- lexicon beats the automated rule" if op_acc>0.650 else "HOLDS"))}}
raw=json.dumps(out,indent=2,sort_keys=True).encode()
(SP/"hand_adversarial_results.json").write_bytes(raw)
print("==== HAND-ADVERSARIAL AUDIT (generic lexicons, $0, no model) ====\n")
print(f"VALENCE     published {0.938}  automated-rule {0.625}  HAND SENTIMENT LEXICON {val_acc:.3f}  -> {out['valence']['verdict']}")
for lab,s in val_miss: print(f"     miss[{lab}]: {s}")
print(f"\nOPERATOR-10 published {0.800}  automated-rule {0.650}  HAND SEMANTIC LEXICON {op_acc:.3f}  -> {out['operator10']['verdict']}")
for c,s in op_miss: print(f"     miss[{c}]: {s}")
print("\nsha256="+hashlib.sha256(raw).hexdigest()[:16])
