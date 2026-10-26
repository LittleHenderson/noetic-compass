import json, re, sys
sys.dont_write_bytecode = True
G = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1"
sys.path.insert(0, G + "/tools")
import check_labels_v22 as c21
from pathlib import Path
t = Path(G + "/02_LABELING_GUIDE_v2_2.md").read_text(encoding="utf-8")
# passages X1..X11, P00
ps = {}
for m in re.finditer(r'^Passage (X\d+|P00)[^:]*: "(.*)"\s*$', t, re.M):
    ps[m.group(1)] = m.group(2)
blocks = re.findall(r"```json\n(.*?)```", t, re.S)
recs = []
for b in blocks:
    b = b.strip()
    try:
        recs.append(json.loads(b))
    except Exception:
        # E blocks are entry lines
        pass
for r in recs:
    pid = r.get("passage_id")
    if pid in ps:
        msgs = c21.check_record(r, ps[pid], pid)
        print(pid, "passes" if not msgs else msgs)
# E examples: compare the entries shown in the guide with the records file
W = json.load(open(G + "/label_v22_draft/worked_examples_records.json", encoding="utf-8"))
WP = {p["id"]: p["text"] for p in json.load(open(G + "/label_v22_draft/worked_examples_passages.json", encoding="utf-8"))}
shown = []
for b in blocks:
    lines = [l for l in b.strip().splitlines() if l.startswith('{"noetic"')]
    for l in lines:
        shown.append(json.loads(l))
allw = [e for r in W for e in r["entries"]]
miss = [e for e in shown if e not in allw]
print("E entries shown in guide:", len(shown), "not in records file:", len(miss))
# check that guide's quoted W passages equal the passages file
for pid, txt in WP.items():
    print(pid, "passage text in guide:", txt in t)
