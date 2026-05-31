"""Scorer for the Condition-3 Meaning-Preservation Gate.

Reads a rater-filled CSV (item_id, prompt, chosen_label[, confidence_1to5]) and
compares each chosen_label against the private answer key written by
`build_condition3_meaning_preservation_packet.py`. Reports recovery overall and
per-domain (A/B/C/D) and per-noetic (1..10) against the 2.5% chance floor and the
6.25% Surface-Gate text baseline.

Gate verdict:
  PASS  if overall recovery is well above chance (target >= ~50%) and clearly
        above the 6.25% text baseline => meaning present without surface shortcut.
  FAIL  if recovery is near chance / text baseline => meaning not preserved.

Usage:
  python score_condition3_meaning_preservation.py --filled condition3_mp_rater_sheet_20260531.csv
  python score_condition3_meaning_preservation.py --filled <sheet> --smoke-perfect  # validate scorer
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
_CHANCE = 0.025
_TEXT_BASELINE = 0.0625


def _domain_of(label: str) -> str:
    return label[0]


def _noetic_of(label: str) -> str:
    return label[1:]


def _load_filled(path: Path, key: dict[str, str], smoke_perfect: bool) -> dict[str, str]:
    chosen: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            iid = (row.get("item_id") or "").strip()
            if not iid:
                continue
            chosen[iid] = key.get(iid, "") if smoke_perfect else (row.get("chosen_label") or "").strip()
    return chosen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--filled", default=f"condition3_mp_rater_sheet_{_DATE}.csv")
    ap.add_argument("--key", default=f"condition3_mp_answer_key_{_DATE}.json")
    ap.add_argument("--smoke-perfect", action="store_true",
                    help="ignore chosen_label; fill from key to validate the scorer")
    args = ap.parse_args(argv)

    key_path = _HERE / args.key if not Path(args.key).is_absolute() else Path(args.key)
    filled_path = _HERE / args.filled if not Path(args.filled).is_absolute() else Path(args.filled)

    key = json.loads(key_path.read_text(encoding="utf-8"))
    chosen = _load_filled(filled_path, key, args.smoke_perfect)

    scored = [iid for iid in key if chosen.get(iid)]
    blank = [iid for iid in key if not chosen.get(iid)]
    missing = [iid for iid in chosen if iid not in key]

    correct = sum(1 for iid in scored if chosen[iid] == key[iid])
    n = len(scored)
    overall = correct / n if n else 0.0
    # domain-only and noetic-only partial credit (diagnostic)
    dom_ok = sum(1 for iid in scored if chosen[iid][:1] == key[iid][:1])
    noe_ok = sum(1 for iid in scored if chosen[iid][1:] == key[iid][1:])

    by_dom_tot: dict[str, int] = defaultdict(int)
    by_dom_ok: dict[str, int] = defaultdict(int)
    by_noe_tot: dict[str, int] = defaultdict(int)
    by_noe_ok: dict[str, int] = defaultdict(int)
    for iid in scored:
        true = key[iid]
        ok = 1 if chosen[iid] == true else 0
        by_dom_tot[_domain_of(true)] += 1
        by_dom_ok[_domain_of(true)] += ok
        by_noe_tot[_noetic_of(true)] += 1
        by_noe_ok[_noetic_of(true)] += ok

    print(f"=== Condition-3 Meaning-Preservation Gate -- score ({_DATE}) ===")
    print(f"filled : {filled_path.name}{'  [SMOKE: perfect fill]' if args.smoke_perfect else ''}")
    print(f"key    : {key_path.name}")
    print(f"scored : {n}/{len(key)} items  (blank={len(blank)}, unknown_item_id={len(missing)})")
    print(f"chance : {_CHANCE:.4f} (2.5%)   text-baseline : {_TEXT_BASELINE:.4f} (6.25%)")
    print()
    print(f"OVERALL recovery : {overall:.4f}  ({correct}/{n})"
          f"   vs chance x{overall/_CHANCE:.1f}   vs text x{overall/_TEXT_BASELINE:.1f}")
    print(f"  domain-only correct : {dom_ok/n:.4f} ({dom_ok}/{n}, chance 0.25)")
    print(f"  noetic-only correct : {noe_ok/n:.4f} ({noe_ok}/{n}, chance 0.10)")
    print()
    print("Per-domain (true label A/B/C/D):")
    for d in sorted(by_dom_tot):
        t, o = by_dom_tot[d], by_dom_ok[d]
        print(f"  {d}: {o/t:.4f}  ({o}/{t})")
    print()
    print("Per-noetic (true label 1..10):")
    for no in sorted(by_noe_tot, key=lambda x: int(x)):
        t, o = by_noe_tot[no], by_noe_ok[no]
        print(f"  ^{no}: {o/t:.4f}  ({o}/{t})")
    print()

    if blank:
        print(f"NOTE: {len(blank)} item(s) left blank -- gate cannot pass until all are rated.")
    well_above = overall >= 0.50 and overall > _TEXT_BASELINE * 2
    if not blank and well_above:
        verdict, reason = "PASS", ("recovery well above chance and clearly above the 6.25% "
                                   "text baseline => meaning present without surface shortcut")
    elif not blank and overall <= _TEXT_BASELINE * 1.5:
        verdict, reason = "FAIL", "recovery near the text baseline / chance => meaning not preserved"
    else:
        verdict, reason = "INCONCLUSIVE", ("above text baseline but below the >=50% target, or "
                                           "items still unrated => tighten or complete before deciding")
    print(f"GATE: {verdict} -- {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
