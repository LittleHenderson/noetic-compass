"""Does the dilution diagnosis predict the observed per-kind outcome?

Joins, from saved bytes only:
  - the answer alphabet of each field (recorded in the per-update loss records)
  - the number of slots each kind declares (recorded in the frozen contract)
  - the observed exact-answer outcome per kind (recorded scoring rows)

and tests one prediction: a kind fails when its answer requires discriminating
among ~64 world symbols through a mean-pooled packet, and succeeds when its answer
is a small structural choice.
"""

import collections
import json
import pathlib

REC = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
    r"\records\typed_matched_001"
)
ART = REC / "receipt_20260919_m" / "collected" / "results" / "artifacts"

# Field -> kind, from the frozen contract's slot counts and the task groupings
# recorded in the per-update loss records (each training task is one kind).
FIELD_OF_KIND = {
    "definition": ("whole", "kind_ref", "function_ref"),
    "context": ("participants", "setting_ref"),
    "analogy": ("world_id",),
    "correspondence": ("correspondence",),
    "parts": ("nodes",),
    "edge_account": ("edges",),
    "role_set": ("roles",),
    "reach": ("reach",),
}
SLOTS = {"role_set": 6, "definition": 3, "context": "1+nodes", "analogy": 1,
         "correspondence": "1+nodes", "parts": "nodes", "edge_account": "nodes^2",
         "reach": 1}


def main():
    # alphabet sizes, from the recorded per-update loss records
    alpha = collections.defaultdict(set)
    n_tasks = collections.Counter()
    for p in sorted(ART.glob("main_*_update.json")):
        u = json.loads(p.read_text(encoding="utf-8"))
        for t in u["tasks"]:
            fields = tuple(sorted(f["field"] for f in t["fields"]))
            n_tasks[fields] += 1
            for f in t["fields"]:
                alpha[f["field"]].add(f["public_alphabet_size"])

    kind_of_fields = {v: k for k, v in FIELD_OF_KIND.items()}

    # observed outcome per kind across the whole matched study (both arms, 3 seeds)
    acc = collections.defaultdict(lambda: {"before": 0, "after": 0, "n": 0})
    for seed in (20260917, 20260918, 20260919):
        for arm in ("a", "m"):
            base = REC / f"receipt_{seed}_{arm}" / "collected" / "results" / "artifacts"
            for phase, key in (("initial_scoring.json", "before"),
                               ("final_scoring.json", "after")):
                for r in json.loads((base / phase).read_text(encoding="utf-8"))["rows"]:
                    acc[r["kind"]][key] += 1 if r["correct"] else 0
                    if key == "before":
                        acc[r["kind"]]["n"] += 1

    print("=" * 104)
    print("PREDICTION TEST: kind -> answer alphabet -> observed outcome")
    print("=" * 104)
    print()
    print(f"  {'kind':14s} {'slots':>8s} {'field alphabets':>22s} {'max alpha':>10s} "
          f"{'before':>9s} {'after':>9s} {'outcome':>10s}")
    print("  " + "-" * 100)
    rows = []
    for fields, count in n_tasks.most_common():
        kind = kind_of_fields.get(fields, "?")
        alphas = {a for f in fields for a in alpha[f]}
        mx = max(alphas) if alphas else 0
        a = acc[kind]
        pct = 100 * a["after"] / a["n"] if a["n"] else 0
        before = 100 * a["before"] / a["n"] if a["n"] else 0
        outcome = "LEARNED" if pct > 20 else ("weak" if pct > 5 else "FAILED")
        rows.append((kind, SLOTS.get(kind, "?"), sorted(alphas), mx, before, pct, outcome))
    for kind, slots, alphas, mx, before, pct, outcome in sorted(rows, key=lambda r: -r[5]):
        print(f"  {kind:14s} {str(slots):>8s} {str(alphas):>22s} {mx:10d} "
              f"{before:8.2f}% {pct:8.2f}% {outcome:>10s}")

    print()
    print("=" * 104)
    print("HYPOTHESIS: a kind fails when its answer requires naming one of ~64 worlds")
    print("=" * 104)
    print()
    names_world = [r for r in rows if r[3] >= 64]
    no_world = [r for r in rows if r[3] < 64]
    print("  kinds whose answer needs a 64/65-way world symbol:")
    for kind, slots, alphas, mx, before, pct, outcome in sorted(names_world, key=lambda r: -r[5]):
        print(f"    {kind:14s} max alphabet {mx:3d}   after {pct:6.2f}%   {outcome}")
    print()
    print("  kinds whose answer does not:")
    for kind, slots, alphas, mx, before, pct, outcome in sorted(no_world, key=lambda r: -r[5]):
        print(f"    {kind:14s} max alphabet {mx:3d}   after {pct:6.2f}%   {outcome}")
    print()
    w = [r[5] for r in names_world]
    n = [r[5] for r in no_world]
    print(f"  mean after-accuracy, world-naming kinds : {sum(w)/len(w):.2f}%  (n={len(w)})")
    print(f"  mean after-accuracy, other kinds        : {sum(n)/len(n):.2f}%  (n={len(n)})")
    print()
    lo = max(w)
    hi = min(n)
    if lo < hi:
        print(f"  SEPARATION: every world-naming kind scores at most {lo:.2f}% and every")
        print(f"  other kind scores at least {hi:.2f}%. The split is clean.")
    else:
        print("  No clean separation; the hypothesis is not sufficient on its own.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
