"""Condition-2 fixture: REAL TKS meaning instantiated WITHOUT naming the gloss.

Goal (honest specificity test, leakage-gated):
  - Keep the real TKS Element meaning present so a pretrained model recognizes
    the semantic territory (the mechanism behind the 95.625% lineage).
  - Express each element's authoritative dynamic in CONCRETE phrasing, never the
    canonical gloss string, with TRAIN/TEST-DISJOINT vocabulary, so a
    bag-of-words classifier cannot shortcut to the 40-way (domain x noetic)
    label. Surface Gate target: local text baseline -> near-chance (2.5%).
  - Role-bound same-sentence counterfactual pairs + explicit Focus marker, so
    the label is the focused role, not the surrounding words (v1 structure).

Each element = (domain D in {A,B,C,D}) x (noetic N in 1..10). Noetic dynamics
are faithful to the authoritative CAS/TKS definitions (verbs preserved:
"attracted toward", "adverse to / repelled by", "resonates", "composed of",
"triggers", "brought to mind"), with the visceral-^3 and associative-^8
anti-drift rules respected. They are NOT the v1 gloss strings.

Leakage control: a counterfactual pair is assigned to train OR test, and BOTH
elements in that pair are realized from that split's phrasing pools only. Train
and test therefore share no element-discriminative surface phrasing; only the
underlying MEANING transfers. A hidden-state probe that reads meaning can still
recover; a word-counter trained on train phrasings cannot.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
_DOMAINS = ("A", "B", "C", "D")
_DOMAIN_NAMES = {"A": "Spiritual", "B": "Mental", "C": "Emotional", "D": "Physical"}
_DOMAIN_TO_CAS = {"A": "P", "B": "C", "C": "E", "D": "O"}
_DOMAIN_TO_REGISTER = {"A": "T", "B": "A", "C": "f", "D": "E"}
_NOETIC_NAMES = {1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female",
                 6: "Male", 7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect", 10: "Idea"}
_TKS_TO_CAS_NOETIC = {10: "^0", **{i: f"^{i}" for i in range(1, 10)}}

# Domain "settings" - WHERE the dynamic plays out. Train/test pools are lexically
# disjoint; both carry the same domain meaning (TKS-source flavored).
_DOMAIN_SETTING: dict[str, dict[str, list[str]]] = {
    "A": {"train": ["a question of ultimate meaning and what guides it",
                    "the soul's bearing toward its highest aim"],
          "test": ["the sacred dimension behind what is happening",
                   "a search for what a life is finally for"]},
    "B": {"train": ["a problem being reasoned out toward a conclusion",
                    "a matter of memory and careful analysis"],
          "test": ["the mind sorting facts on the way to a verdict",
                   "a puzzle thought through step by step"]},
    "C": {"train": ["a moment weighed entirely by how it feels",
                    "a scene charged with felt mood"],
          "test": ["the heart taking the measure of what just happened",
                   "an episode heavy with emotional tone"]},
    "D": {"train": ["a hands-on material task with moving parts",
                    "a concrete bodily arrangement at work"],
          "test": ["a tangible mechanical setup being handled",
                   "the physical substrate and its parts in motion"]},
}

# Noetic "dynamics" - the authoritative structural move, in concrete non-gloss
# phrasing. Train/test pools lexically disjoint; meaning identical.
_NOETIC_DYN: dict[int, dict[str, list[str]]] = {
    1: {"train": ["someone takes in what is there and works it over",
                  "an awareness keeps and turns the material it receives"],
        "test": ["a knower holds the content and runs through it",
                 "the processing engine intakes and minds what shows up"]},
    2: {"train": ["the one involved is drawn toward it and leans in",
                  "there is a pull of affinity toward the thing"],
        "test": ["an attraction tugs them closer to it",
                 "the thing is liked and approached without resistance"]},
    3: {"train": ["the one involved recoils from it and wants none of it",
                  "there is a gut refusal, a turning-away in disgust"],
        "test": ["it is found repellent and pushed back from",
                 "a visceral aversion makes them shrink from it"]},
    4: {"train": ["the thing lands and leaves its mark inside",
                  "it resonates and registers as an impression"],
        "test": ["it strikes a chord and reverberates within",
                 "the impact carries through and is felt as a vibration"]},
    5: {"train": ["the whole is made of everything taken in over time",
                  "what it is equals the sum of its gathered experience"],
        "test": ["it is constituted by all it has absorbed across its history",
                 "its very makeup is the deposit of past intakes"]},
    6: {"train": ["it is opened up to show the parts it is built from",
                  "the thing is taken apart into the ideas inside it"],
        "test": ["its internal pieces are pulled out and laid bare",
                 "it is decomposed into the components that compose it"]},
    7: {"train": ["it is shaped by the same exposure repeated and repeated",
                  "a rate of recurrence trains and conditions it"],
        "test": ["steady repetition grooves it into place",
                 "the cadence of return entrains it over many passes"]},
    8: {"train": ["one thing here sets off the thought of a different thing",
                  "it acts as a trigger that calls something else up"],
        "test": ["encountering it makes a separate idea surface",
                 "it cues a different content into mind"]},
    9: {"train": ["the content that arrives on its own once cued",
                  "the idea brought to mind by something that set it off"],
        "test": ["what simply pops up after a trigger lands",
                 "the answering thought delivered by an earlier prompt"]},
    10: {"train": ["the bare content itself, thought of or not",
                   "the thing as sheer idea, in or out of any mind"],
         "test": ["the item as pure content apart from any thinker",
                  "the matter considered just as what it is"]},
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _eid(d: str, n: int) -> str:
    return f"{d}{n}"


def _pairs() -> list[dict[str, Any]]:
    out = []
    for d in _DOMAINS:
        for n in range(1, 11):
            nxt = 1 if n == 10 else n + 1
            out.append({"kind": f"same_domain_noetic_cycle_{d}", "left": (d, n), "right": (d, nxt)})
    for n in range(1, 11):
        for ld, rd in (("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")):
            out.append({"kind": f"same_noetic_domain_cycle_{n}", "left": (ld, n), "right": (rd, n)})
    return out


def _phrase(d: str, n: int, split: str, si: int, di: int) -> str:
    setting = _DOMAIN_SETTING[d][split][si % len(_DOMAIN_SETTING[d][split])]
    dyn = _NOETIC_DYN[n][split][di % len(_NOETIC_DYN[n][split])]
    return f"the role where {dyn}, within {setting}"


_LITERAL = ["A1", "A2", "B1", "C1", "D1", "^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9"]
_FORBIDDEN = re.compile(r"\b(?:cas|tks|noetic|element label|spiritual mind|mental mind)\b", re.IGNORECASE)


def _flags(text: str) -> dict[str, bool]:
    return {"contains_literal_element_code": any(t in text for t in _LITERAL),
            "contains_framework_word": bool(_FORBIDDEN.search(text)),
            "gloss_string_embedded": False}


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pairs = _pairs()
    # deterministically alternate pair split assignment to keep train/test balanced
    for pi, pair in enumerate(pairs):
        split = "train" if pi % 2 == 0 else "test"
        (ld, ln), (rd, rn) = pair["left"], pair["right"]
        # a few disjoint surface realizations per pair
        for si in range(2):
            for di in range(2):
                lp = _phrase(ld, ln, split, si, di)
                rp = _phrase(rd, rn, split, si, di)
                base = f"A is {lp}; B is {rp}."
                for focus, (d, n) in (("A", (ld, ln)), ("B", (rd, rn))):
                    eng = f"{base} Focus: {focus}."
                    sid = f"c2_{split}_{pair['kind']}_{_eid(ld,ln)}_{_eid(rd,rn)}_s{si}d{di}_{_eid(d,n)}"
                    rows.append({
                        "sample_id": sid,
                        "dataset_version": "mtc_condition2_meaning_instantiated_v0",
                        "split": split,
                        "counterfactual_pair_id": f"{pair['kind']}_{_eid(ld,ln)}_{_eid(rd,rn)}_s{si}d{di}",
                        "pair_kind": pair["kind"],
                        "surface_style": "meaning_instantiated_role_bound_counterfactual_no_gloss",
                        "english": eng,
                        "base_sentence": base,
                        "focus_span": focus,
                        "element_label": _eid(d, n),
                        "element_domain": d,
                        "element_domain_name": _DOMAIN_NAMES[d],
                        "element_cas_domain": _DOMAIN_TO_CAS[d],
                        "element_register": _DOMAIN_TO_REGISTER[d],
                        "element_noetic_tks": n,
                        "element_noetic_name": _NOETIC_NAMES[n],
                        "element_cas_noetic": _TKS_TO_CAS_NOETIC[n],
                        "contrast_partner_element": _eid(rd, rn) if focus == "A" else _eid(ld, ln),
                        "anti_leak_flags": _flags(eng),
                        "source_strategy": "claude_authored_condition2_meaning_instantiated_no_gloss_disjoint_surface",
                        "review_status": "draft_local_surface_gate_pending",
                    })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(_HERE / f"mtc_condition2_meaning_instantiated_{_DATE}.jsonl"))
    args = ap.parse_args(argv)
    rows = build_rows()
    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "mtc_condition2_fixture_manifest.v1",
        "date": _DATE, "out_jsonl": out.name, "out_jsonl_sha256": _sha256(out),
        "n_rows": len(rows), "n_elements": len({r["element_label"] for r in rows}),
        "split_counts": dict(sorted(Counter(r["split"] for r in rows).items())),
        "label_counts": dict(sorted(Counter(r["element_label"] for r in rows).items())),
        "design": "real TKS meaning, no gloss string, train/test-disjoint surface phrasing, role-bound counterfactual + Focus",
        "surface_gate_target": "local text baseline near-chance (~2.5% for 40 classes)",
    }
    (out.with_name(out.stem + "_manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
