"""Meaning-Preservation Gate packet for the Condition-3 fixture.

Companion to the Condition-2 packet builder. The Surface Gate showed a word
counter recovers only 6.25% of the 40-element label from Condition-3 prompts
(2.5x chance). This gate asks the complementary question: can a reader, using ONLY
the 40-Element definition sheet, still recover the element from the prompt's
marked role? If yes (well above the 2.5% chance floor) while the text baseline is
near chance, the meaning is present WITHOUT being a copyable surface shortcut --
the condition under which a hidden-vs-text + matched-taxonomy capture reads as real
specificity.

The Condition-3 role carries BOTH the noetic dynamic (the verb phrase after "the
one who ...") and the domain-as-register (the adjective in the shared manner
template "in a {adj} way" / "with a {adj} bearing" / "on {adj} ground"). The
surrounding everyday scenario (topic + frame) is ORTHOGONAL scaffold and must be
ignored when choosing the element.

Outputs (rater fills the CSV; key + scorer stay private until rated):
  - condition3_mp_rater_sheet_<date>.csv  : item_id, prompt, chosen_label[, conf]
  - condition3_mp_answer_key_<date>.json   : item_id -> true element_label
  - condition3_mp_protocol_<date>.md       : instructions + gate threshold

Definition sheet the rater uses (label -> definition):
  docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md
"""
from __future__ import annotations
import argparse, csv, json, random
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
FIX = _HERE / "mtc_condition3_topical_scenarios_20260531.jsonl"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-element", type=int, default=1)
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
    rng.shuffle(picked)  # break element grouping so order leaks nothing

    sheet = _HERE / f"condition3_mp_rater_sheet_{_DATE}.csv"
    with sheet.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "prompt", "chosen_label", "confidence_1to5"])
        for r in picked:
            w.writerow([r["sample_id"], r["english"], "", ""])

    key = {r["sample_id"]: r["element_label"] for r in picked}
    (_HERE / f"condition3_mp_answer_key_{_DATE}.json").write_text(
        json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    n = len(picked)
    chance = 1.0 / len({r["element_label"] for r in picked})
    protocol = f"""# Condition-3 Meaning-Preservation Gate -- protocol ({_DATE})

## Task
For each row in `condition3_mp_rater_sheet_{_DATE}.csv`, read the `prompt` and
choose the single 40-Element label (A1..D10) whose definition best matches the
role marked by `Focus: A` or `Focus: B`. Put it in `chosen_label`. Optional:
`confidence_1to5`.

Use ONLY the definition sheet:
`docs/working/lsa_artifacts_20260530/lsa_definition_sheet_40e_v0_1.md`
(A=Spiritual, B=Mental, C=Emotional, D=Physical; 1..10 = the noetic dynamic).

The role carries the noetic dynamic (verb phrase after "the one who ...") AND the
domain-as-register (the adjective in "in a {{adj}} way" / "with a {{adj}} bearing"
/ "on {{adj}} ground"). IGNORE the everyday scenario (topic + frame) -- it is
orthogonal scaffold and does not determine the element. The prompt never shows the
label or a canonical gloss string.

## Items
{n} items, {args.per_element} per element x 40 elements, {args.split} split.
Order is shuffled. Chance = {chance:.4f} (2.5%).

## Gate
PASS if reader recovery is well above chance (target: overall >= ~50%, and clearly
> the 6.25% Surface-Gate text baseline). PASS + near-chance text baseline => meaning
is present without a surface shortcut => Condition-3 carries real CAS meaning.
FAIL (recovery near chance) => the instantiations no longer carry the element
meaning; revise before any capture.

## Scoring
`python score_condition3_meaning_preservation.py --filled <rater_sheet.csv>`
compares against the private answer key and reports overall / per-domain /
per-noetic recovery vs chance and vs the 6.25% text baseline.
"""
    (_HERE / f"condition3_mp_protocol_{_DATE}.md").write_text(protocol, encoding="utf-8")

    print(f"items={n} per_element={args.per_element} chance={chance:.4f}")
    print(f"wrote {sheet.name}, condition3_mp_answer_key_{_DATE}.json, "
          f"condition3_mp_protocol_{_DATE}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
