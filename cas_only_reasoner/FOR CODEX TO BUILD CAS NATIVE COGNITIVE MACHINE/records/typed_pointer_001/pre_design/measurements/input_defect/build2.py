"""Stage 1 (defect2): rebuild the frozen encoder (float64, pure Python) over ALL 564 course packets.

Gate: projection + readout sha256 must equal the published digests, else abort.
Caches per packet: row tags/keys/token counts, packet vector, per-category row sums; per slot: query spec,
query vector, 64-bit sign mask, label (PRESENT/ABSENT for the four per-bit kinds). Writes build2.pkl here only.
Run: python -B build2.py
"""
import sys
sys.dont_write_bytecode = True
import time, pickle, json
from enc_rebuild import *  # noqa: F401,F403  (verified vs encoder.py:154-164, 202-212)
from cas_meta2.typed_teaching import checker, slots as slotsmod

t0 = time.time()
frozen, tok, dev, held, trained, excluded, packets = load()
print("load s", round(time.time() - t0, 1), "held", len(held), "trained", len(trained), "excluded", len(excluded),
      "packets", len(packets), flush=True)
ok, hp, hr, projection, readout = gate(tok)
print("GATE", ok, "projection", hp, "readout", hr, flush=True)
if not ok:
    print("ABORT: frozen bytes do not reproduce"); sys.exit(1)
reg = {r["record_id"]: r for r in frozen["registry"]}
split_of = {**{k: "held" for k in held}, **{k: "trained" for k in trained}, **{k: "excluded" for k in excluded}}
assert len(split_of) == 564 == len(packets)
SET_FIELD = {"edge_account": "edge", "parts": "node", "role_set": "role", "context": "participant"}


def tag_of(scope):
    return scope[0]


out = {"gate": {"ok": ok, "projection": hp, "readout": hr}, "packets": {}, "slots": [], "rowvec": {}}
for n, (rid, packet) in enumerate(sorted(packets.items())):
    plan, rows = packet_rows(packet, tok, projection)
    rowinfo = []
    for r, v in rows:
        key = (r["ordinal"], tuple(r["scope"]), tuple(r["token_ids"]))
        out["rowvec"][key] = v
        rowinfo.append({"tag": tag_of(r["scope"]), "scope": tuple(r["scope"]), "ordinal": r["ordinal"],
                        "count": r["count"], "key": key})
    pv = packet_vector_from_rows([v for _, v in rows])
    rec = reg[rid]
    q = rec["query"]
    out["packets"][rid] = {"split": split_of[rid], "kind": q["kind"], "query_id": q["query_id"],
                           "focus": q["focus_world_id"], "source_world": rec["source_world_id"],
                           "n_supports": len(rec["supports"]), "rows": rowinfo, "pv": pv,
                           "n_worlds": len(packet["source"]["worlds"])}
    splan = slotsmod.compile_slots(packet)
    validated = slotsmod.validate_plan(packet, splan)
    labels = None
    if q["kind"] in SET_FIELD:
        target = checker.derive_target(packet["source"], q)
        value = target["admissible_answers"][0]["value"]
        kind = q["kind"]
        if kind == "edge_account":
            labels = {(e["source"], e["target"]) for e in value["edges"]}
        elif kind == "parts":
            labels = set(value["nodes"])
        elif kind == "role_set":
            labels = set(value["roles"])
        else:
            labels = set(value["participants"])
    for slot in splan["slots"]:
        spec, qv = query_vector(validated, slot)
        mask = 0
        for i, x in enumerate(qv):
            assert x in (0.125, -0.125)
            if x > 0:
                mask |= 1 << i
        label = None
        if labels is not None and slot["field"] == SET_FIELD[q["kind"]]:
            key = (slot["coordinates"][0], slot["coordinates"][1]) if q["kind"] == "edge_account" else slot["coordinates"][0]
            label = "PRESENT" if key in labels else "ABSENT"
        out["slots"].append({"record_id": rid, "split": split_of[rid], "kind": q["kind"], "query_id": q["query_id"],
                             "focus": q["focus_world_id"], "field": slot["field"], "slot_id": slot["slot_id"],
                             "scope_alias": slot["scope_alias"], "scope_world": slot["scope_world_id"],
                             "coordinates": list(slot["coordinates"]),
                             "spec_c": json.dumps(spec, sort_keys=True, separators=(",", ":")),
                             "qv": qv, "mask": mask, "label": label})
    if n % 50 == 0:
        print(n, rid[:24], "rows", len(rows), "slots so far", len(out["slots"]), round(time.time() - t0, 1), flush=True)

out["held_worlds"] = list(c.HELD_WORLDS)
out["held"], out["trained"], out["excluded"] = held, trained, excluded
with open(SCRATCH / "build2.pkl", "wb") as fh:
    pickle.dump(out, fh)
print("done s", round(time.time() - t0, 1), "slots", len(out["slots"]), "distinct rows", len(out["rowvec"]))
