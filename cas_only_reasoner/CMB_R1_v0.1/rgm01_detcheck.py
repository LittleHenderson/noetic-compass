# rgm01_detcheck.py — canonical determinism check. The initial 2-pass hash included volatile
# fields (wall_s, tracemalloc peak) — a hashing bug, not content nondeterminism. This reruns
# pass 2 and compares the two passes on content only, then repairs the receipt.
import json, hashlib, copy
import run_rgm01 as R

def canon(worlds):
    w2 = copy.deepcopy(worlds)
    for w in w2:
        for k, v in w["eff"].items():
            if isinstance(v, dict):
                v.pop("wall_s", None)
        w["eff"].pop("peak_mem_prop_bytes", None)
    return w2

d = json.load(open("RGM01_RECEIPT.json"))
h1 = hashlib.sha256(json.dumps(canon(d["worlds_pass1"]), sort_keys=True).encode()).hexdigest()
p2 = [R.run_world(w) for w in range(R.WORLDS)]
h2 = hashlib.sha256(json.dumps(canon(p2), sort_keys=True).encode()).hexdigest()
d["determinism"] = {"canonical_hash_pass1": h1, "canonical_hash_pass2": h2,
                    "identical": h1 == h2,
                    "note": "hash excludes wall-clock and tracemalloc peak (volatile); both passes on identical seeds; initial non-canonical hash (a5e8352d...) voided by this check"}
d["worlds_pass2"] = p2
json.dump(d, open("RGM01_RECEIPT.json", "w"), indent=1, sort_keys=True)
print("DET_CANONICAL:", h1 == h2, h1[:16], h2[:16])
