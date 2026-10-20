"""Merge the census shards (counts only out). Applies, on the candidate rows: DESIGNER_SEEN slice (Id mod 25 = 0),
PERSONAL_DATA (X-REAL filter), DUPLICATE_TEXT (X-REAL normalize), LEAKAGE (CTT rule: equal after normalising, or a
shared 8-word run with any train.jsonl input; c45 train.jsonl). Writes census_c1_custody/CENSUS_C1.json (counts +
id/hash lists; no text) and prints the counts. Run: python -B -I -X utf8 merge_c1.py"""
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

USE1 = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\use1")
OUT = USE1 / "census_c1_custody"
TRAIN = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\cas_token_transformer\run_c45_ctt1_20261020\a1_unpacked"
             r"\c45_out\ctt_out\data\train.jsonl")
LEAK = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\cas_token_transformer\HELM_CTT_20261019\ctt_build\leakage.py")

sys.path.insert(0, str(LEAK.parent))
import leakage as L  # noqa: E402  (the CTT rule, unchanged)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


counts, shards = {}, []
for p in sorted(glob.glob(str(OUT / "shard_*.json"))):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    assert d["status"] == "COMPLETE", p
    shards.append(Path(p).name)
    for k, v in d["counts"].items():
        counts[k] = counts.get(k, 0) + v
assert len(shards) == 16, shards

excl = {}
frame, u4b_stub = [], []  # U4b rows are abundant: keep only (id, cand, personal, norm_sha256) to stay under 300 MiB
for p in sorted(glob.glob(str(OUT / "rows_*.jsonl"))):
    with open(p, encoding="utf-8") as fh:
        for x in fh:
            if not x.strip():
                continue
            r = json.loads(x)
            if r["group"] != "FRAME":
                continue
            if r["cand"] == "U4b":
                u4b_stub.append({"id": r["id"], "cand": "U4b", "personal": r["personal"],
                                 "norm_sha256": r["norm_sha256"], "would_ask": r["would_ask"]})
            else:
                frame.append(r)
frame += u4b_stub
del u4b_stub


def drop(r, why):
    excl.setdefault(r["cand"], {}).setdefault(why, 0)
    excl[r["cand"]][why] += 1


# leakage index over the non-U4b candidates (U4b is abundant; reported before leakage)
check = [r for r in frame if r["cand"] in ("U1", "U3", "U4a")]
idx = L.exam_index(r["text"] for r in check)
leaked_norm, leaked_grams = set(), set()
n_train = 0
with open(TRAIN, encoding="utf-8") as fh:
    for line in fh:
        t = json.loads(line).get("text") or ""
        n_train += 1
        nt = L.norm(t)
        if nt in idx["exact"]:
            leaked_norm.add(nt)
        g = L.grams(t) & idx["grams"]
        if g:
            leaked_grams |= g

seen, elig = set(), {}
for r in sorted(frame, key=lambda r: r["id"]):
    c = r["cand"]
    if r["personal"]:
        drop(r, "PERSONAL_DATA")
        continue
    if r["norm_sha256"] in seen:
        drop(r, "DUPLICATE_TEXT")
        continue
    seen.add(r["norm_sha256"])
    if c in ("U1", "U3", "U4a") and (L.norm(r["text"]) in leaked_norm or (L.grams(r["text"]) & leaked_grams)):
        drop(r, "LEAKAGE")
        continue
    elig.setdefault(c, []).append(r)

u1 = elig.get("U1", [])
u2 = [r for r in u1 if r["would_ask"]]
S = counts.get("FRAME_sentences", 0) + counts.get("SLICE_sentences", 0)
per10k = lambda n, d=S: round(10000 * n / d, 3) if d else None  # noqa: E731

food = counts.get("FRAME_food", 0)
agree = 1 - counts.get("FRAME_KS_disagree", 0) / food if food else None
ex = sorted(u1, key=lambda r: r["text_sha256"])[:10]
summary = {
    "schema": "use1.census_c1/1",
    "shards": shards,
    "train_rows_checked": n_train, "train_sha256": sha(TRAIN), "leakage_py_sha256": sha(LEAK),
    "totals": {
        "units": {k: v for k, v in counts.items() if k.startswith("units_")},
        "sentences_all": S, "sentences_frame": counts.get("FRAME_sentences", 0),
        "sentences_designer_slice": counts.get("SLICE_sentences", 0),
        "food_sentences_frame": food,
        "KS_frame": {k[9:]: v for k, v in counts.items() if k.startswith("FRAME_KS_")},
        "two_key_agreement_frame_food": round(agree, 4) if agree is not None else None,
        "KS_FACTS_frame_all": counts.get("FRAME_KS_FACTS", 0),
        "KS_FACTS_frame_R1_reader_gives_up": counts.get("FRAME_FACTS_R1", 0),
        "KS_FACTS_frame_R4_reader_reads": counts.get("FRAME_FACTS_R4", 0),
        "STOCK_FP_frame (FACTS + first-person shape, no recipe talk, no instruction)": counts.get("FRAME_STOCK_FP", 0),
        "STOCK_FP_frame_R1_reader_gives_up": counts.get("FRAME_STOCK_FP_R1_reader_gives_up", 0),
        "STOCK_FP_frame_R4_reader_reads": counts.get("FRAME_STOCK_FP_R4_reader_reads", 0),
        "made_any_first_person_frame (REPORTED only)": counts.get("FRAME_made_any", 0),
        "made_food_first_person_frame (REPORTED only)": counts.get("FRAME_made_food", 0),
        "made_food_KS": {k[len("FRAME_made_food_KS_"):]: v for k, v in counts.items()
                         if k.startswith("FRAME_made_food_KS_")},
        "slice_KS_FACTS": counts.get("SLICE_KS_FACTS", 0), "slice_STOCK_FP": counts.get("SLICE_STOCK_FP", 0),
    },
    "per_10000_sentences_all": {
        "KS_FACTS_frame_all": per10k(counts.get("FRAME_KS_FACTS", 0), counts.get("FRAME_sentences", 0)),
        "STOCK_FP_frame": per10k(counts.get("FRAME_STOCK_FP", 0), counts.get("FRAME_sentences", 0)),
        "STOCK_FP_frame_R1": per10k(counts.get("FRAME_STOCK_FP_R1_reader_gives_up", 0), counts.get("FRAME_sentences", 0)),
        "STOCK_FP_frame_R4": per10k(counts.get("FRAME_STOCK_FP_R4_reader_reads", 0), counts.get("FRAME_sentences", 0)),
        "made_food_frame": per10k(counts.get("FRAME_made_food", 0), counts.get("FRAME_sentences", 0)),
    },
    "exclusions_applied_by_candidate_class": excl,
    "eligible_after_exclusions": {
        "U1_stock (any reader)": len(u1), "U2_stock_reader_gives_up": len(u2),
        "U1_stock_reader_reads": len(u1) - len(u2),
        "U3_say_ask": len(elig.get("U3", [])), "U4a_instruction_trap": len(elig.get("U4a", [])),
        "U4b_fact_from_nothing (leakage not applied)": len(elig.get("U4b", [])),
        "MADE_REPORTED (not drawable)": len(elig.get("MADE_REPORTED", [])),
    },
    "not_applied_at_census": ["XREAL_USED / CTT_USED / RTR_USED / CTT2R_USED (spent draws: custodian, by id and text)",
                              "FORBIDDEN_TEXT (needs the forbidden list files: custodian)",
                              "POOL_OVERLAP (CTT-2R Part K pool: custodian)",
                              "SE precision check (DESIGN 3.1: non-builder reader; not done)"],
    "example_ids_hash_only": [{"id": r["id"], "text_sha256": r["text_sha256"], "reader": "gives_up" if r["would_ask"]
                               else "reads"} for r in ex],
    "all_U1_ids": sorted(r["id"] for r in u1),
}
(OUT / "CENSUS_C1.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print(json.dumps({k: summary[k] for k in ("totals", "per_10000_sentences_all", "exclusions_applied_by_candidate_class",
                                          "eligible_after_exclusions")}, indent=1))
print("CENSUS_C1.json sha256", sha(OUT / "CENSUS_C1.json"))
