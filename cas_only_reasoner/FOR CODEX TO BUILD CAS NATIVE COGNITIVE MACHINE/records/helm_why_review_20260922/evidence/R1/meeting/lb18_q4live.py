"""LB18 — analogy: what the correct answer set actually depends on."""
import sys
from collections import Counter
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


tally = Counter()
detail = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "analogy":
        continue
    wmap = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = wmap[q["focus_world_id"]]
    tgt = checker.derive_target(p["source"], q)
    good = [a["value"]["world_id"] for a in tgt["admissible_answers"]]
    good = [g for g in good if g]
    canon = {wid: checker._isomorphisms(focus, w)[0] for wid, w in wmap.items()}
    other_domain = {wid for wid, w in wmap.items() if w["declarations"]["domain"] != focus["declarations"]["domain"]}
    iso_and_other = {wid for wid in wmap if wid != focus["world_id"] and canon[wid] and wid in other_domain}
    iso_any = {wid for wid in wmap if wid != focus["world_id"] and canon[wid]}
    s = side(rid)
    tally[(s, "records")] += 1
    tally[(s, "good_is_exactly_iso_and_other_domain")] += int(set(good) == iso_and_other)
    tally[(s, "good_is_exactly_iso")] += int(set(good) == iso_any)
    tally[(s, "answers")] += len(good)
    # what a shape-only rule (pooled world vector) would do: every other same-shape world
    shape_peers = {w for w in iso_any}
    tally[(s, "shape_only_extra_candidates")] += len(shape_peers - set(good))
    detail.append((s, rid[-12:], len(good), len(iso_any), len(iso_any - set(good)), len(other_domain)))

for s in ("held", "trained", "excluded"):
    if not tally[(s, "records")]:
        continue
    print("%-9s records %d answers %d | correct set == (isomorphic AND different domain) in %d records |"
          " correct set == (isomorphic) in %d | alternative isomorphic candidates the shape test alone cannot reject: %d"
          % (s, tally[(s, "records")], tally[(s, "answers")], tally[(s, "good_is_exactly_iso_and_other_domain")],
             tally[(s, "good_is_exactly_iso")], tally[(s, "shape_only_extra_candidates")]))
print()
print("held detail (side, rid, correct answers, isomorphic others, isomorphic-but-rejected, non-domain candidates):")
for row in detail:
    if row[0] == "held":
        print("   ", row)
