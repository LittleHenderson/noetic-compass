"""Meaning-Preservation Gate packet for the Condition-2 fixture.

The Surface Gate already showed a word-counter recovers only 6.9% of the
40-element label from Condition-2 prompts. The Meaning-Preservation Gate asks
the complementary question: can a HUMAN, reading the prompt and using the
40-Element definition sheet, still recover the element? If yes (well above the
2.5% chance floor) while the text baseline is near chance, the meaning is
present in the prompt WITHOUT being a copyable surface shortcut — the exact
condition under which a hidden-vs-text + matched-taxonomy capture is
interpretable as real specificity.

Outputs (rater fills the CSV; key + scorer stay private until rated):
  - condition2_mp_rater_sheet_<date>.csv   : item_id, prompt, chosen_label[, confidence]
  - condition2_mp_answer_key_<date>.json    : item_id -> true element_label
  - condition2_mp_protocol_<date>.md        : instructions + gate threshold

Definition sheet the rater uses (label -> definition):
  docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md
"""
from __future__ import annotations
import argparse, csv, json, random
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
FIX = _HERE / "mtc_condition2_meaning_instantiated_20260531.jsonl"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-element", type=int, default=2)
    ap.add_argument("--split", default="test")
    ap.add_argument("--seed", type=int, default=20260531)
    args = ap.parse_args(argv)

    rows = [json.loads(l) for l in FIX.open(encoding="utf-8")]
    rows = [r for r in rows if r["split"] == args.split]
    by_elem: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_elem[r["element_label"]].append(r)

    rng = random.Random(args.seed)
    picked: list[dict] = []
    for elem in sorted(by_elem):
        pool = sorted(by_elem[elem], key=lambda r: r["sample_id"])
        rng.shuffle(pool)
        picked.extend(pool[: args.per_element])
    rng.shuffle(picked)  # break element grouping so raters cannot infer by order

    sheet = _HERE / f"condition2_mp_rater_sheet_{_DATE}.csv"
    with sheet.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "prompt", "chosen_label", "confidence_1to5"])
        for r in picked:
            w.writerow([r["sample_id"], r["english"], "", ""])

    key = {r["sample_id"]: r["element_label"] for r in picked}
    (_HERE / f"condition2_mp_answer_key_{_DATE}.json").write_text(
        json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    n = len(picked)
    chance = 1.0 / len({r["element_label"] for r in picked})
    protocol = f"""# Condition-2 Meaning-Preservation Gate — protocol ({_DATE})

## Task
For each row in `condition2_mp_rater_sheet_{_DATE}.csv`, read the `prompt` and
choose the single 40-Element label (A1..D10) whose definition best matches the
role marked by `Focus: A` or `Focus: B`. Put it in `chosen_label`. Optional:
`confidence_1to5`.

Use ONLY the definition sheet:
`docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md`
(A=Spiritual, B=Mental, C=Emotional, D=Physical; 1..10 = the noetic dynamic).
The prompt never shows the label or the canonical gloss string.

## Items
{n} items, {args.per_element} per element x 40 elements, {args.split} split.
Order is shuffled. Chance = {chance:.4f} (2.5%).

## Gate
PASS if human recovery is well above chance (target: macro recovery >= ~50%,
and clearly > the 6.9% Surface-Gate text baseline). PASS + near-chance text
baseline => meaning is present without being a surface shortcut => Condition-2
is eligible for GPU capture (hidden-vs-text + matched-taxonomy comparator).
FAIL (recovery near chance) => the prompts no longer carry the element meaning;
revise instantiations before any capture.

## Scoring
`python score_condition2_meaning_preservation.py --filled <rater_sheet.csv>`
compares against the private answer key and reports overall / per-domain /
per-noetic recovery vs chance.
"""
    (_HERE / f"condition2_mp_protocol_{_DATE}.md").write_text(protocol, encoding="utf-8")

    print(f"items={n} per_element={args.per_element} chance={chance:.4f}")
    print(f"wrote {sheet.name}, condition2_mp_answer_key_{_DATE}.json, "
          f"condition2_mp_protocol_{_DATE}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
