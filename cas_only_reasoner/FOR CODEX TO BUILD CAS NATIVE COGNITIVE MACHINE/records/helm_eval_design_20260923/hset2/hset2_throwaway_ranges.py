"""HSET-2 expected ranges over THROWAWAY salts (CLAUDE_BUILT_CLAUDE_CHECKED). Never a real salt: every salt here is
derived from a public string by `hset2_build.resolve_salts`'s throwaway rule, so no sealed TEST can be reproduced.

What it runs: the builder's own `load_stage0` and `derive` (the same splits, eligibility and items as the sealed build),
the builder's own comparator functions and cell summaries. What it skips: packet validation, Helm's reader and checker v2.
Each comparator is compared DIRECTLY with the independent gold (the reach rules re-implemented; for analogy the planted
partner, for correspondence an edge check). The real build requires, on every packet, that checker v2's verdict equals
exactly this direct comparison (`comparator_scoring_consistent`), so the two paths give the same cell numbers; the
builder report shows them agreeing on the same salt.

    python -B hset2_throwaway_ranges.py --package-root DIR --seeds tiny-9,tiny-10 [--only correspondence] --out FILE
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))


def throwaway_salts(H, seed):
    derive = lambda which: hashlib.sha256((H.THROWAWAY_PREFIX + seed + "|" + which).encode()).hexdigest()  # noqa: E731
    return derive("hset1a"), derive("hset2")


def fast_rows(H, items):
    """{item_id: row} with the fields the builder's cell summaries read, graded against the independent gold."""
    W = H._W
    hw, A, source, oracle, S0 = W["hw"], W["A"], W["source"], W["oracle"], W["S0"]
    rows = {}
    for item in items:
        if "world" in item:
            focus = hw.world_from_spec(source, item["world"])
            refs = hw.node_refs(focus, item["world"])
            arguments = {"whole": refs[item["whole"]]} if item.get("whole") is not None else {}
            if item.get("part") is not None:
                arguments["part"] = refs[item["part"]]
            query = {"arguments": arguments, "rule": item["rule"]}
            gold = A._independent_gold(hw, item, refs)
            payloads, aux = A._comparators(item["kind"], focus, query)
            if item["kind"] == "reach":
                payloads.update(H.extra_reach_payloads(focus, query, payloads))
            flags = {}
            if item["kind"] == "reach" and gold["state"] == "VIA":
                flags = {"GOLD_VIA_IS_PARTICIPANT_2": gold["via"] == aux["p2"],
                         "GOLD_VIA_IS_LOWEST_RANK_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][0],
                         "GOLD_VIA_IS_RANK_LAST_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][-1]}
            rows[item["item_id"]] = {"comparators": {n: hw.canon(p) == hw.canon(gold) for n, p in payloads.items()},
                                     "flags": flags, "gold": gold}
            continue
        worlds = [hw.world_from_spec(source, spec) for spec in item["worlds"]]
        members = {worlds[i]["world_id"]: worlds[i] for i in item["bank"]}
        members[worlds[item["focus"]]["world_id"]] = worlds[item["focus"]]
        public = {"worlds": [members[k] for k in sorted(members)],
                  "bank": {"world_ids": sorted(worlds[i]["world_id"] for i in item["bank"])}}
        focus_id = worlds[item["focus"]]["world_id"]
        ids = sorted(members)
        alias = {}
        if item["kind"] == "analogy":
            payloads = H.analogy_payloads(public, focus_id, W["trained_shapes"],
                                          lambda shape: S0.class_key(oracle.canonical_form(*shape)))
            gold = worlds[item["roles"].index("PARTNER")]["world_id"] if item["status"] == "MATCH" else None
            right = lambda p: p["world_id"] == gold                                        # noqa: E731
            for role in ("PARTNER", "DISTRACTOR"):
                if role in item["roles"]:
                    alias[role] = "W%d" % ids.index(worlds[item["roles"].index(role)]["world_id"])
        else:
            target = worlds[item["target"]]
            payloads = H.correspondence_payloads(public, focus_id, target["world_id"])
            fn, fe, frefs = H.world_graph(worlds[item["focus"]])
            tn, te, trefs = H.world_graph(target)
            tindex = {r: i for i, r in enumerate(trefs)}

            def right(p, fe=fe, te=te, frefs=frefs, tindex=tindex, status=item["status"]):
                if p["status"] == "NO_MATCH":
                    return status == "NO_MATCH"
                m = {frefs.index(q["source"]): tindex[q["target"]] for q in p["pairs"]}
                return status == "MAPPING" and {(m[a], m[b]) for a, b in fe} == set(te)
            alias["TARGET"] = "W%d" % ids.index(target["world_id"])
        rows[item["item_id"]] = {"item_id": item["item_id"], "comparators": {n: right(p) for n, p in payloads.items()},
                                 "role_alias": alias}
    return rows


def cells(H, D, rows, salt2, splits=None):
    import hset_worlds as hw
    import hset1a_build as A
    import hset2_stage0_public as S0
    out = {}
    items_by_cluster = collections.defaultdict(list)
    for item in D["items"]:
        items_by_cluster[item["cluster_id"]].append(item)
    for split, seed in (("DEV_NEW_6", S0.DEV_SEED), ("TEST_NEW_6", salt2)):
        if splits and split not in splits:
            continue
        for cell in ("REACH_FIRST_DIRECT", "REACH_BFS"):
            members = [c for c in D["single_clusters"] if c["split"] == split and c["cell"] == cell]
            if members:
                out["%s/%s" % (split, cell)] = H.summarise_reach_cell(hw, A, cell, members, rows, items_by_cluster, seed, "-")
    for name, members in D["bank_clusters"].items():
        if splits and name.split("/")[0] not in splits:
            continue
        kind = "analogy" if name.split("/")[1].startswith("ANALOGY") else "correspondence"
        out[name] = H.summarise_bank_cell(A, name, kind, members, rows, "-")
    return out


def views(block):
    """Codex A2.4's per-view numbers of one cell or claim (counts only)."""
    v = block["a2_views"]
    return {"units": v["units"], "sizes": v["size_distributions"],
            "binding_by_view": {k: [b["comparator"], b["W"]] for k, b in v["binding_by_view"].items()},
            "W_by_comparator_by_view": v["W_by_comparator_by_view"],
            "a2_4_floors_met": v["floors"]["meets_every_floor"], "a2_4_reasons": v["floors"]["not_testable_reasons"],
            "exact_power": {view: {k: ex[k] for k in ("state", "bar", "uniform_model_accuracy",
                                                      "never_loses_where_bar_is_right_wins_fraction") if k in ex}
                            for view, ex in v["exact_power_under_hset1a_model"].items() if ex},
            **({"computed_not_registered_W_by_view": v["computed_not_registered_W_by_view"]}
               if "computed_not_registered_W_by_view" in v else {})}


def headline(summaries, D):
    """The numbers the review gave ranges for, per cell, with Codex A2.2's views."""
    h = {"test_new_6_draws": D["test_draws"], "eligible_full": D["eligible_full_counts"]}
    for name, s in summaries.items():
        if "claims" in s:
            h[name] = {"primary_by_state": s["primary_by_state"],
                       **{claim: {"binding_W": b["binding_W"], "binding": b["binding_comparator"],
                                  "distinct_shapes_behind_W": b["distinct_shapes_behind_binding_W"],
                                  "can_carry": b["can_carry_a_claim"], "W_by_comparator": b["W_by_comparator"],
                                  "views": views(b)}
                          for claim, b in s["claims"].items()}}
        else:
            h[name] = {"clusters": s["clusters"], "binding_W": s["binding_W"], "binding": s["binding_comparator"],
                       "distinct_degree_groups": s["distinct_degree_groups"], "can_carry": s["can_carry_a_claim"],
                       "W_by_comparator": s["W_by_comparator"],
                       "tuned_diagnostic": s.get("tuned_on_this_cell_diagnostic_not_a_bar"),
                       "flag_image": s["flag_image_rates"], "diagnostics": s["printed_diagnostics_never_bars"],
                       "views": views(s)}
            if "distractor_split_diagnostic" in s:
                h[name]["distractor_split_binding_W"] = {k: v["binding_W"] for k, v in s["distractor_split_diagnostic"].items()}
    return h


VIEWS = ("original_cluster", "degree_group", "shared_shape_component")
CLAIM_CELLS = {"ANALOGY_BEYOND_DEGREE_6": ("TEST_NEW_6/ANALOGY", None),
               "CORRESPONDENCE_BEYOND_DEGREE_6": ("TEST_NEW_6/CORRESPONDENCE", None),
               "CORRESPONDENCE_BEYOND_DEGREE_5": ("TEST_NEW_5/CORRESPONDENCE", None)}


def _mmm(values):
    values = [v for v in values if v is not None]
    return [min(values), round(sum(values) / len(values), 1), max(values)] if values else None


def summarize(results):
    """Ranges over seeds, counts only (min / mean / max), for the pre-salt manifest (A2.7: "complete throwaway
    feasibility ranges including groups/components"). A claim is counted testable in a seed when every one of its cells
    meets the original floor (can_carry); REPAIR_IMPROVES_ANALOGY_6 also needs every A2.4 floor (A2.3, A2.4, A2.7 D4)."""
    done = {s: r for s, r in results.items() if "refused" not in r}
    out = {"seeds_measured": sorted(done), "seeds_refused": {s: r["refused"] for s, r in results.items() if "refused" in r},
           "claims": {}}
    cells = sorted({c for r in done.values() for c in r if "/" in c})
    for cell in cells:
        rows = [r[cell] for r in done.values() if cell in r]
        blocks = ([(claim, [row[claim] for row in rows]) for claim in rows[0] if claim != "primary_by_state"]
                  if "primary_by_state" in rows[0] else [(None, rows)])
        for claim, bs in blocks:
            key = cell if claim is None else "%s [%s]" % (cell, claim)
            entry = {"seeds": len(bs),
                     "original_binding_W": _mmm([b["binding_W"] for b in bs]),
                     "original_floor_met": sum(1 for b in bs if b["can_carry"]),
                     "binding_bar_counts": dict(collections.Counter(b["binding"] for b in bs)),
                     "units_by_view": {v: _mmm([b["views"]["units"][v] for b in bs]) for v in VIEWS},
                     "binding_W_by_view": {v: _mmm([b["views"]["binding_by_view"][v][1] for b in bs]) for v in VIEWS},
                     "binding_bar_by_view_counts": {v: dict(collections.Counter(b["views"]["binding_by_view"][v][0]
                                                                                 for b in bs)) for v in VIEWS},
                     "a2_4_floors_met": sum(1 for b in bs if b["views"]["a2_4_floors_met"]),
                     "original_and_a2_4_floors_met": sum(1 for b in bs if b["can_carry"] and b["views"]["a2_4_floors_met"])}
            if claim is None and "clusters" in bs[0]:
                entry["clusters"] = _mmm([b["clusters"] for b in bs])
                entry["degree_groups"] = _mmm([b["distinct_degree_groups"] for b in bs])
            out[key] = entry
    # claims (both reach cells must carry for a reach claim)
    for claim, (cell, _) in CLAIM_CELLS.items():
        if cell in cells:
            n = [r[cell] for r in done.values() if cell in r]
            out["claims"][claim] = {"seeds": len(n), "testable": sum(1 for b in n if b["can_carry"])}
    if "TEST_NEW_6/ANALOGY" in cells:
        n = [r["TEST_NEW_6/ANALOGY"] for r in done.values() if "TEST_NEW_6/ANALOGY" in r]
        out["per_seed_TEST_NEW_6_ANALOGY_binding_W_original_group_component"] = {
            seed: [r["TEST_NEW_6/ANALOGY"]["views"]["binding_by_view"][v][1] for v in VIEWS]
            for seed, r in sorted(done.items()) if "TEST_NEW_6/ANALOGY" in r}
        out["claims"]["REPAIR_IMPROVES_ANALOGY_6"] = {
            "seeds": len(n), "testable_original_and_every_A2_4_floor": sum(1 for b in n if b["can_carry"] and
                                                                          b["views"]["a2_4_floors_met"])}
    reach_cells = ("TEST_NEW_6/REACH_FIRST_DIRECT", "TEST_NEW_6/REACH_BFS")
    if all(c in cells for c in reach_cells):
        both = [r for r in done.values() if all(c in r for c in reach_cells)]
        for claim in [k for k in both[0][reach_cells[0]] if k != "primary_by_state"]:
            out["claims"][claim] = {"seeds": len(both),
                                    "testable": sum(1 for r in both if all(r[c][claim]["can_carry"] for c in reach_cells))}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root")
    parser.add_argument("--seeds", help="comma-separated public strings; each gives two throwaway salts")
    parser.add_argument("--only", choices=("reach", "analogy", "correspondence"), default=None)
    parser.add_argument("--splits", default=None,
                        help="comma-separated splits to evaluate (for example TEST_NEW_6); default every split")
    parser.add_argument("--out", required=True)
    parser.add_argument("--summarize", nargs="+", default=None,
                        help="merge earlier --out files (counts only) into one ranges summary written to --out")
    args = parser.parse_args()
    if args.summarize:
        merged, sources = {}, {}
        for f in args.summarize:                           # one file per family or seed batch: merge cells per seed
            doc = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            sources[pathlib.Path(f).name] = {"only": doc.get("only"), "seeds": sorted(doc["results"])}
            for seed, r in doc["results"].items():
                merged.setdefault(seed, {}).update(r)
        pathlib.Path(args.out).write_text(json.dumps({"schema": "claude.hset2-throwaway-ranges-summary/0.1",
                                                      "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
                                                      "state": "THROWAWAY: throwaway salts; development estimates, "
                                                               "not the A2.4 table and never a result",
                                                      "runs": sources, "summary": summarize(merged)},
                                                     indent=1, sort_keys=True),
                                          encoding="utf-8")
        return 0
    if not (args.package_root and args.seeds):
        raise SystemExit("REFUSED: --package-root and --seeds are required unless --summarize is given")
    splits = set(args.splits.split(",")) if args.splits else None
    if any((q / ".git").exists() for q in pathlib.Path(args.out).resolve().parents):
        raise SystemExit("REFUSED: throwaway range outputs may not be written inside a git work tree")
    import hset2_build as H
    H.check_d1()                                          # verifier note VN-4: refuse D1 or R1 option c or an unknown value
    root = pathlib.Path(args.package_root).resolve()
    H._paths(root)
    H._init(str(root))
    from cas_meta2.typed_teaching import source
    import hset_worlds as hw
    vocab, _ = hw.vocabulary(source)
    stage0 = H.load_stage0(root)
    facts5 = None
    results = {}
    for seed in args.seeds.split(","):
        t0 = time.monotonic()
        salt1a, salt2 = throwaway_salts(H, seed)
        try:
            D = H.derive(stage0, salt1a, salt2, vocab, source, only=args.only, facts5=facts5)
        except SystemExit as error:                       # a throwaway TEST_NEW_5 that holds a PUBLIC_EXCLUDED class
            results[seed] = {"refused": str(error).split(":")[0]}
            print(seed, results[seed], flush=True)
            continue
        facts5 = D["facts5"]
        rows = fast_rows(H, [i for i in D["items"] if not splits or i["split"] in splits])
        results[seed] = headline(cells(H, D, rows, salt2, splits), D)
        results[seed]["seconds"] = round(time.monotonic() - t0, 1)
        print(seed, "done in %.1f s" % results[seed]["seconds"], flush=True)
    pathlib.Path(args.out).write_text(json.dumps({"schema": "claude.hset2-throwaway-ranges/0.1", "only": args.only,
                                                  "results": results}, indent=1, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
