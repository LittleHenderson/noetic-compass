"""RT5 step 5 (descriptive): profile of the whole-argument and part-argument nodes, trained reach+parts vs dev
DIRECT/parts; and exact shares of participant-rank 0 rows. Pure JSON over rt5_inputs.json."""
import json, os
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "rt5_inputs.json"), encoding="utf-8"))
def prof(r, which):
    n = r[which]
    if n is None: return None
    x = r["worlds"][r["focus_world_id"]]["rows"][n]
    return (x["participant"], x["is_declared_whole"], x["in"], x["out"])
def direct_or_parts(r):
    if r["kind"] == "parts": return "PARTS"
    kids = {t for s, t in r["worlds"][r["focus_world_id"]]["edges"] if s == r["whole"]}
    return "DIRECT" if r["part"] in kids else "OTHER"
for name, rs, sel in (("trained reach+parts", d["trained"], lambda r: r["kind"] in ("reach", "parts")),
                      ("trained DIRECT+parts", d["trained"], lambda r: r["kind"] in ("reach", "parts") and direct_or_parts(r) != "OTHER"),
                      ("dev DIRECT+parts", d["dev"], lambda r: direct_or_parts(r) != "OTHER")):
    sub = [r for r in rs.values() if sel(r)]
    print("==", name, len(sub))
    print("   whole arg (participant, declared_whole, in, out):", dict(Counter(prof(r, "whole") for r in sub)))
    print("   part  arg (participant, declared_whole, in, out):", dict(Counter(prof(r, "part") for r in sub if r["part"] is not None)))
def p0(rs, sel, focus_only):
    z = t = 0
    for r in rs.values():
        if not sel(r): continue
        for wid, w in r["worlds"].items():
            if focus_only and wid != r["focus_world_id"]: continue
            for x in w["rows"]:
                t += 1; z += x["participant"] == 0
    return z, t, z / t
print("participant-rank 0 rows: trained reach+parts focus %s; trained all rows (WIDE) %s; dev focus %s" % (
    p0(d["trained"], lambda r: r["kind"] in ("reach", "parts"), True), p0(d["trained"], lambda r: True, False),
    p0(d["dev"], lambda r: True, True)))
