"""Stage 1: parser check vs the 16 saved reference ASTs; family G train/dev statistics (visible files only)."""
import collections
import json
import math
from common import *

insp = json.loads((REC / "inspected_predictions.json").read_text(encoding="utf-8"))["cases"]
ok = sum(parse(c["input"]) == c["checker_reference_ast"] for c in insp)
print("PARSER_VS_SAVED_REFERENCE_AST exact:", ok, "/", len(insp))
tok_ok = sum(ast_to_tokens(parse(c["input"])) == ast_to_tokens(c["checker_reference_ast"]) for c in insp)
print("PARSER_TOKENS_VS_REFERENCE_TOKENS exact:", tok_ok, "/", len(insp))

train = read_jsonl(DATA / "visible_G_train.jsonl")
dev = read_jsonl(DATA / "visible_G_dev.jsonl")
print("rows train/dev:", len(train), len(dev))
tr = [parse(r["observation"]) for r in train]
dv = [parse(r["observation"]) for r in dev]
dv16 = dv[:16]
# check the 16 dev ids match the inspected cases
print("first16 dev ids == inspected ids:", [r["record_id"] for r in dev[:16]] == [c["record_id"] for c in insp])

for name, asts in (("train", tr), ("dev", dv), ("dev_first16", dv16)):
    print("\n==", name, "n =", len(asts))
    print(" depth:", dict(sorted(collections.Counter(depth(a) for a in asts).items())))
    tl = collections.Counter(len(ast_to_tokens(a)) for a in asts)
    print(" target token length:", dict(sorted(tl.items())))
    lens = [len(ast_to_tokens(a)) for a in asts]
    print(" token length mean:", sum(lens) / len(lens), "min", min(lens), "max", max(lens))
    nl = collections.Counter(len(leaves(a)) for a in asts)
    print(" leaves per tree:", dict(sorted(nl.items())))
    shp = collections.Counter(json.dumps(shape(a)) for a in asts)
    print(" distinct bare shapes:", len(shp))
    ib = [len(r["observation"].encode("utf-8")) for r in (train if name == "train" else dev[: len(asts)])]
    print(" input bytes mean/min/max:", sum(ib) / len(ib), min(ib), max(ib))

shapes_tr = {json.dumps(shape(a)) for a in tr}
shapes_dv = {json.dumps(shape(a)) for a in dv}
print("\nbare shapes train", len(shapes_tr), "dev", len(shapes_dv), "shared", len(shapes_tr & shapes_dv))
print("dev first16 bare shapes:", collections.Counter(json.dumps(shape(a)) for a in dv16).most_common())

# leaf-field frequencies over train leaves
L = [l for a in tr for l in leaves(a)]
print("\ntrain leaves:", len(L))
for f in ("operator", "domain", "drive"):
    c = collections.Counter(l[f] for l in L)
    print(" ", f, c.most_common())
c = collections.Counter(l.get("register", "ABSENT") for l in L)
print("  register", c.most_common())
st = collections.Counter(l["operator"] + "^" + l["domain"] for l in L)
print("  top 12 leaf states (noetic^domain):", st.most_common(12))
print("  bottom 5 leaf states:", st.most_common()[-5:])
print("  count ^7^E", st["^7^E"], "rank", [k for k, _ in st.most_common()].index("^7^E") + 1,
      "; ^7^C", st["^7^C"], "rank", [k for k, _ in st.most_common()].index("^7^C") + 1, "of", len(st))
full = collections.Counter(canon(l) for l in L)
bare7E = canon({"node": "StateLiteral", "operator": "^7", "domain": "E", "drive": None})
bare7C = canon({"node": "StateLiteral", "operator": "^7", "domain": "C", "drive": None})
print("  exact bare leaf ^7^E (no drive, no register):", full[bare7E], " ^7^C:", full[bare7C])
print("  distinct full leaf literals:", len(full), " top 8:", [(show(json.loads(k)), v) for k, v in full.most_common(8)])
ops = collections.Counter(s["op"] for a in tr for s in subtrees(a) if s["node"] == "BinaryExpr")
print("  binary ops:", ops.most_common())
rootop = collections.Counter(a["op"] for a in tr)
print("  root op:", rootop.most_common())

# whole trees and sub-trees
whole = collections.Counter(canon(a) for a in tr)
print("\ndistinct whole train trees:", len(whole), " max multiplicity:", whole.most_common(1)[0][1])
subs = collections.Counter(canon(s) for a in tr for s in subtrees(a) if s["node"] == "BinaryExpr")
print("distinct binary sub-trees:", len(subs), " top 5:", [(show(json.loads(k)), v) for k, v in subs.most_common(5)])
pred = {"left": {"domain": "E", "drive": None, "node": "StateLiteral", "operator": "^7"}, "node": "BinaryExpr", "op": "PLUS",
        "right": {"domain": "C", "drive": None, "node": "StateLiteral", "operator": "^7"}}
print("pred tree as whole train tree:", whole[canon(pred)], " as sub-tree:", subs[canon(pred)])
# looser: any binary node whose two children are leaves ^7^E and ^7^C (any drive/register, any op, either order)
def loose(s, a, b):
    if s["node"] != "BinaryExpr":
        return False
    l, r = s["left"], s["right"]
    if l["node"] != "StateLiteral" or r["node"] != "StateLiteral":
        return False
    return (l["operator"] + "^" + l["domain"], r["operator"] + "^" + r["domain"]) == (a, b)
print("loose sub-tree (^7^E op ^7^C), any drive/register/op:", sum(loose(s, "^7^E", "^7^C") for a in tr for s in subtrees(a)))
print("loose sub-tree (^7^C op ^7^E):", sum(loose(s, "^7^C", "^7^E") for a in tr for s in subtrees(a)))
print("string '^7^E + ^7^C' in train observations:", sum("^7^E + ^7^C" in r["observation"] for r in train))
# bare depth-1 PLUS shape with two bare leaves (no drive, no register) of any states
def bare_leaf(x):
    return x["node"] == "StateLiteral" and x["drive"] is None and "register" not in x
print("train whole trees = (bareleaf + bareleaf):", sum(a["op"] == "PLUS" and bare_leaf(a["left"]) and bare_leaf(a["right"]) for a in tr if a["node"] == "BinaryExpr" and depth(a) == 1))
print("train whole trees of depth 1:", sum(depth(a) == 1 for a in tr))
# position-specific: leaves directly under root-left/right in depth-1 trees
d1 = [a for a in tr if depth(a) == 1]
print("depth-1 root-left leaf domain:", collections.Counter(a["left"]["domain"] for a in d1).most_common(),
      " noetic:", collections.Counter(a["left"]["operator"] for a in d1).most_common(3))
print("depth-1 root-right leaf domain:", collections.Counter(a["right"]["domain"] for a in d1).most_common(),
      " noetic:", collections.Counter(a["right"]["operator"] for a in d1).most_common(3))
