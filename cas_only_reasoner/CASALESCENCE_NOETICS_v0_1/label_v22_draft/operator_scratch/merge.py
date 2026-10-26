import sys, json
import lab
import p1, p2, p3, p4, p5, p6, p7, p8


def all_records():
    out = []
    for m in (p1, p2, p3, p4, p5, p6, p7, p8):
        out.extend(m.build())
    return out


def order_ok(recs):
    ids = [r["passage_id"] for r in recs]
    want = [p for p in sorted(lab.PASSAGES)]
    return ids == want, ids, want


if __name__ == "__main__":
    recs = all_records()
    ok, ids, want = order_ok(recs)
    print("order/coverage ok:", ok, len(ids))
    probs = lab.check(recs)
    hard = [x for x in probs if "SOFT" not in x[1]]
    soft = [x for x in probs if "SOFT" in x[1]]
    print("hard problems:", len(hard))
    for x in hard:
        print("  ", x)
    print("soft warnings:", len(soft))
    for x in soft:
        print("  ", x)
    if len(sys.argv) > 1 and sys.argv[1] == "write":
        if hard or not ok:
            print("NOT WRITING: problems present")
        else:
            with open(lab.WORK, "w", encoding="ascii") as f:
                json.dump(recs, f, indent=1, ensure_ascii=True)
            print("wrote", lab.WORK)
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        lo, hi = sys.argv[2], sys.argv[3]
        for r in recs:
            if lo <= r["passage_id"] <= hi:
                print("=" * 70)
                print(r["passage_id"], "none" if r["none_of_these"] else "", lab.PASSAGES[r["passage_id"]].encode("ascii", "backslashreplace").decode())
                for e in r["entries"]:
                    s = "  %s [%s%s] label=%r | mind=%r | rel=%r | say=%r%s" % (
                        e["noetic"], e["certainty"], ("/" + e["other_candidate"]) if "other_candidate" in e else "",
                        e["label"], e["mind"], e["relative_to"], e["saying"],
                        " | REASONING" if e.get("reached_by") else "")
                    print(s.encode("ascii", "backslashreplace").decode())
                for n in r["not_enough_information"]:
                    print("  NOTE:", n)
