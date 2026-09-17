"""Quantify the two-level mean and the unweighted row mean, on real packets.

Pure Python, project's pure modules only. No torch, no GPU.
"""

import collections
import json
import pathlib
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, worker_contract  # noqa: E402

SEED = 20260916


def main():
    frozen, tok, _ = worker_contract.load_material(HOME)
    reg = frozen["registry"]
    step = max(1, len(reg) // 10)
    sample = reg[::step][:10]

    per_family = collections.defaultdict(lambda: {"rows": 0, "tokens": 0})
    total_rows = total_tokens = 0
    for row in sample:
        p = course.model_packet(frozen, row["record_id"])
        plan = binding.compile_packet(p, tok, seed=SEED, d_model=64)
        for r in plan["rows"]:
            f = r["scope"][0]
            per_family[f]["rows"] += 1
            per_family[f]["tokens"] += r["count"]
        total_rows += len(plan["rows"])
        total_tokens += sum(r["count"] for r in plan["rows"])

    print("=" * 100)
    print(f"WEIGHT vs INFORMATION, {len(sample)} REAL PACKETS")
    print("=" * 100)
    print("  packet = unit_l2( sum of unit row vectors ), so EVERY row carries weight")
    print("  1/n_rows regardless of how many tokens it holds.")
    print()
    print(f"  {'scope family':14s} {'rows/pkt':>9s} {'weight':>9s} {'tokens/pkt':>11s} "
          f"{'token share':>12s} {'mismatch':>10s}")
    print("  " + "-" * 92)
    rows_sorted = sorted(per_family.items(), key=lambda kv: -kv[1]["tokens"])
    for fam, d in rows_sorted:
        rpp = d["rows"] / len(sample)
        tpp = d["tokens"] / len(sample)
        weight = rpp / (total_rows / len(sample))
        share = tpp / (total_tokens / len(sample))
        print(f"  {fam:14s} {rpp:9.2f} {100*weight:8.2f}% {tpp:11.0f} "
              f"{100*share:11.2f}% {share/weight:9.1f}x")
    print("  " + "-" * 92)
    print(f"  {'TOTAL':14s} {total_rows/len(sample):9.2f} {100.0:8.2f}% "
          f"{total_tokens/len(sample):11.0f} {100.0:11.2f}%")
    print()
    print("  'mismatch' is token share divided by weight: how many times more")
    print("  information a family carries than the influence it is given, or less.")

    print()
    print("=" * 100)
    print("THE THREE COMPOUNDING DEFECTS")
    print("=" * 100)
    q = per_family["QUERY"]
    al = per_family["ALIASES"]
    st = per_family["START"]
    n_rows = total_rows / len(sample)
    n_tok = total_tokens / len(sample)
    print(f"  1. WITHIN-ROW MEAN. Each row is unit_l2(sum of its own tokens), so a")
    print(f"     token is diluted by its row's length. The QUERY row holds the whole")
    print(f"     question in {q['tokens']/len(sample):.0f} tokens, so a focus-world token is")
    print(f"     one part in ~{q['tokens']/len(sample):.0f} of that row before row pooling begins.")
    print()
    print(f"  2. UNWEIGHTED ROW MEAN. Every one of the {n_rows:.0f} rows is given weight")
    print(f"     1/{n_rows:.0f} = {100/n_rows:.2f}%, whatever it contains. Measured:")
    print(f"       ALIASES  {al['rows']/len(sample):5.0f} row(s)  {100*(al['rows']/len(sample))/n_rows:6.2f}% weight  "
          f"{al['tokens']/len(sample):7.0f} tokens  {100*(al['tokens']/len(sample))/n_tok:6.2f}% of the tokens")
    print(f"       QUERY    {q['rows']/len(sample):5.0f} row(s)  {100*(q['rows']/len(sample))/n_rows:6.2f}% weight  "
          f"{q['tokens']/len(sample):7.0f} tokens  {100*(q['tokens']/len(sample))/n_tok:6.2f}% of the tokens")
    print(f"       START    {st['rows']/len(sample):5.0f} row(s)  {100*(st['rows']/len(sample))/n_rows:6.2f}% weight  "
          f"{st['tokens']/len(sample):7.0f} token   {100*(st['tokens']/len(sample))/n_tok:6.3f}% of the tokens")
    print()
    print(f"     A one-token START marker and the entire {al['tokens']/len(sample):.0f}-token alias table")
    print(f"     receive identical influence. The question itself receives")
    print(f"     {100/n_rows:.2f}% of the packet.")
    print()
    print("  3. NO CONTENT ADDRESSING. The aggregation is a fixed unweighted sum,")
    print("     identical in form for every question. Nothing in it depends on what")
    print("     is being asked, so no amount of training can make it selective.")

    out = {
        "schema": "cncm.encoder-mean-defects/0.1",
        "packets": len(sample),
        "rows_per_packet": total_rows / len(sample),
        "tokens_per_packet": total_tokens / len(sample),
        "per_family": {k: {"rows_per_packet": v["rows"] / len(sample),
                           "tokens_per_packet": v["tokens"] / len(sample)}
                       for k, v in per_family.items()},
        "row_weight": 1.0 / n_rows,
    }
    pathlib.Path(__file__).with_name("mean_defects.json").write_text(
        json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print()
    print("  wrote mean_defects.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
