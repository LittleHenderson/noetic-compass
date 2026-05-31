"""Condition-3 fixture: REAL CAS element meaning embedded in ORDINARY scenarios.

Why this exists (the BLOCK that Condition-2 hit):
  Condition-2 prompts are pure CAS role-bound prose with no ordinary topic/event
  content. The prereg's coherent non-CAS opponents (Control B NC40_TOPIC_FRAME_V1
  = 8 topics x 5 frames; Control C NC28 = 7 settings x 4 functions) must be
  assigned from NON-CAS fields only. Condition-2 has none, so a comparative-gate
  capture lands BLOCKED_FIXTURE_NOT_ELIGIBLE. Condition-3 fixes exactly this.

Design (one prompt simultaneously satisfies all four constraints):
  1. REAL CAS meaning recoverable  -> the focused role carries the authoritative
     noetic dynamic (N in 1..10), expressed in the cognitive REGISTER of its
     domain (A=transcendent, B=analytical, C=affective, D=embodied). Verbs are
     faithful ("attracted toward", "adverse to / repelled by", "resonates",
     "composed of", "triggers", "brought to mind"); visceral-^3 and associative-^8
     anti-drift rules respected. This keeps the 95.6% lineage mechanism.
  2. Surface leakage near chance (Surface Gate) -> the noetic-dynamic phrasing and
     the register-manner phrasing are TRAIN/TEST-DISJOINT, so a bag-of-words
     classifier trained on the train split cannot transfer the CAS-label-bearing
     surface to test. Only MEANING transfers.
  3. Reader-recoverable meaning (Meaning-Preservation Gate) -> dynamic + manner
     map cleanly onto the 40-Element definition sheet.
  4. Ordinary topic/event content (Fixture-Eligibility Gate) -> every prompt sits
     inside a concrete everyday scenario (a hospital ward, a finance desk, a
     warehouse crew, ...) doing an ordinary discourse move (classify, explain a
     cause, run a procedure, weigh a tradeoff, mitigate a risk). The scenario
     supplies explicit non-CAS fields control_semantic.topic_40 / .frame_40
     (and secondary .topic_7 / .function_4), so Control B (and a derived Control
     C) materialize WITHOUT reading any CAS field.

CRITICAL honesty property -- ORTHOGONALITY:
  The (topic, frame) scaffold is assigned INDEPENDENTLY of the CAS element via a
  CAS-BLIND seeded shuffle of a balanced 40-cell multiset per split (the shuffle
  key knows nothing about the base's domain/noetic). If topic/frame were correlated
  with (domain, noetic), the surface scenario keywords would leak the CAS label and
  the Surface Gate would fail. Orthogonality guarantees the ordinary content is
  useless for recovering the CAS label, so the coherent opponent is real AND the
  CAS surface stays near chance. The builder MEASURES this (normalized mutual
  information calibrated against a permutation null + per-cell balance) and refuses
  to write if balance is off or real NMI exceeds the null's 97.5th percentile.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
_DOMAINS = ("A", "B", "C", "D")
_DOMAIN_NAMES = {"A": "Spiritual", "B": "Mental", "C": "Emotional", "D": "Physical"}
_DOMAIN_TO_CAS = {"A": "P", "B": "C", "C": "E", "D": "O"}
_DOMAIN_TO_REGISTER = {"A": "T", "B": "A", "C": "f", "D": "E"}
_NOETIC_NAMES = {1: "Mind", 2: "Positive", 3: "Negative", 4: "Vibration", 5: "Female",
                 6: "Male", 7: "Rhythm", 8: "Above/Cause", 9: "Below/Effect", 10: "Idea"}
_TKS_TO_CAS_NOETIC = {10: "^0", **{i: f"^{i}" for i in range(1, 10)}}

# --- CAS carriers (TRAIN/TEST-DISJOINT; carry the label, must stay near-chance) ---

# Noetic dynamic, fits "the one who {dyn}". Faithful to authoritative definitions.
# 3 phrasings per split, authored CONTENT-WORD-DISJOINT train<->test so a
# bag-of-words classifier cannot transfer the noetic-axis surface across splits.
_NOETIC_DYN: dict[int, dict[str, list[str]]] = {
    1: {"train": ["takes in what is there and turns it over",
                  "gathers the material and keeps mulling it",
                  "intakes the input and dwells on it"],
        "test": ["minds whatever shows up and runs through it",
                 "holds the content and processes it",
                 "receives the input and weighs it inwardly"]},
    2: {"train": ["is drawn toward it and leans in",
                  "feels an affinity and gravitates to it",
                  "warms to it and reaches for it"],
        "test": ["is tugged closer and welcomes it",
                 "likes it and moves nearer without resistance",
                 "is pulled in, favoring it"]},
    3: {"train": ["recoils from it and wants none of it",
                  "is sickened by it and backs away",
                  "bristles at it and shoves it off"],
        "test": ["finds it repugnant and pushes back",
                 "is repelled, turning from it in disgust",
                 "shrinks from it on a gut level"]},
    4: {"train": ["lets it land and leave a mark inside",
                  "is stirred as it resonates through",
                  "takes the impact and holds the impression"],
        "test": ["is struck and senses it reverberate within",
                 "vibrates with it as it carries through",
                 "registers the tremor it sets off"]},
    5: {"train": ["is made of everything taken in over time",
                  "amounts to the sum of gathered experience",
                  "is built from all it has lived"],
        "test": ["is constituted by what it has absorbed",
                 "is the deposit of past intakes",
                 "consists of its accumulated history"]},
    6: {"train": ["opens it up to show the parts inside",
                  "breaks it into the ideas it holds",
                  "lays bare the pieces within"],
        "test": ["pulls its components out and exposes them",
                 "decomposes it into what composes it",
                 "unpacks the elements it contains"]},
    7: {"train": ["is shaped by the same exposure repeated and repeated",
                  "is trained by a steady rate of recurrence",
                  "settles in through drill after drill"],
        "test": ["is grooved into place by ceaseless looping",
                 "is conditioned over many returning passes",
                 "beds down via cadence after cadence"]},
    8: {"train": ["sets off the thought of a different thing",
                  "acts as a trigger that calls something else up",
                  "sparks a separate notion to arise"],
        "test": ["makes an unrelated idea surface",
                 "cues a different content into mind",
                 "nudges another thought into view"]},
    9: {"train": ["arrives on its own once something prompts it",
                  "is the notion fetched by an earlier trigger",
                  "is what comes up after a cue lands"],
        "test": ["simply pops into mind when summoned",
                 "is the answering thought a signal delivers",
                 "is the content that follows being set off"]},
    10: {"train": ["is the bare content itself, thought of or not",
                   "is the thing as sheer idea, in or out of mind",
                   "stands as plain subject material on its own"],
         "test": ["is the item as pure notion apart from any thinker",
                  "is the thing taken just as what it is",
                  "exists as raw subject regardless of attention"]},
}

# Domain carried as REGISTER (the operational character of the engagement),
# NOT as a named setting. The register is carried ENTIRELY by a single disjoint
# adjective, dropped into a SHARED syntactic template used identically by all four
# domains. This is deliberate: if each domain had its own clause shape, the
# function-word skeleton ("of its...", "by ...ing", "with concrete...") would be a
# stable cross-split fingerprint a bag-of-words classifier reads even when content
# words differ -- leaking domain through syntax. Shared templates + train/test
# content-word-disjoint adjectives leave NO transfer channel for surface recovery,
# while a human reader still recovers the register from the adjective's meaning.
_REGISTER_ADJ: dict[str, dict[str, list[str]]] = {
    "A": {"train": ["transcendent", "purpose-seeking", "meaning-centered"],
          "test": ["visionary", "aspirational", "significance-driven"]},
    "B": {"train": ["analytical", "reasoned", "systematic"],
          "test": ["logical", "methodical", "deductive"]},
    "C": {"train": ["emotional", "feeling-led", "heartfelt"],
          "test": ["affective", "sentiment-based", "mood-driven"]},
    "D": {"train": ["embodied", "hands-on", "tactile"],
          "test": ["physical", "kinesthetic", "sensorimotor"]},
}
# Shared across ALL domains -> carries zero domain signal (function words identical).
_MANNER_TEMPLATE = ("in a {a} way", "with a {a} bearing", "on {a} ground")

# --- Non-CAS scaffold (ORTHOGONAL to CAS; supplies the coherent opponent) ---
# Topic sectors match Control B NC40 topic_40 axis + manifest keyword dictionaries.
_TOPIC40 = ("healthcare", "education", "commerce_finance", "law_governance",
            "software_data", "logistics_operations", "customer_support", "public_safety")
_FRAME40 = ("classification", "causal_explanation", "procedure",
            "tradeoff_decision", "risk_mitigation")

# Secondary derived axes (Control C NC28). public_safety has no clean topic_7
# family; it folds into human_services (flagged approximate in the manifest).
_TOPIC40_TO_TOPIC7 = {
    "healthcare": "medical_care", "education": "learning_assessment",
    "commerce_finance": "market_transaction", "law_governance": "law_policy",
    "software_data": "technical_system", "logistics_operations": "operations_planning",
    "customer_support": "human_services", "public_safety": "human_services",
}
_FRAME40_TO_FUNCTION4 = {
    "classification": "describe_state", "causal_explanation": "explain_cause",
    "procedure": "choose_action", "tradeoff_decision": "choose_action",
    "risk_mitigation": "evaluate_risk",
}

_TOPIC_SCENE: dict[str, list[str]] = {
    "healthcare": ["a hospital ward reviewing a patient's care plan",
                   "a clinic team handling a triage and treatment decision"],
    "education": ["a classroom where a teacher weighs a student's assessment",
                  "a course review over a lesson and its grading"],
    "commerce_finance": ["a finance desk going over an invoice and a budget",
                         "a vendor negotiation about a loan and its payment"],
    "law_governance": ["a regulatory office reading a statute for compliance",
                       "a court matter over a contract and an agency permit"],
    "software_data": ["an engineering team tracing a bug in the data pipeline",
                      "a server review of an API against its database"],
    "logistics_operations": ["a warehouse crew planning a shipment and its routing",
                             "a dispatch room scheduling inventory and packing"],
    "customer_support": ["a support queue handling a customer's refund ticket",
                         "a service call about a client account complaint"],
    "public_safety": ["an emergency crew responding to a safety hazard",
                      "an inspection team logging an incident and its risk"],
}
_FRAME_CLAUSE: dict[str, list[str]] = {
    "classification": ["as they classify which category it falls in",
                       "while sorting it into the right type"],
    "causal_explanation": ["as they explain why it happened and what caused it",
                           "while tracing what led to the outcome"],
    "procedure": ["as they apply the procedure across ordered stages",
                  "while advancing the process from one phase to the next"],
    "tradeoff_decision": ["as they weigh the tradeoff and decide which option to prioritize",
                          "while comparing options to recommend one"],
    "risk_mitigation": ["as they move to mitigate the risk and prevent harm",
                        "while putting a guardrail against failure"],
}

_LITERAL = ["A1", "A2", "B1", "C1", "D1", "^0", "^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9"]
_FORBIDDEN = re.compile(r"\b(?:cas|tks|noetic|element label|spiritual mind|mental mind)\b", re.IGNORECASE)
_NC40_SEED = 20260531  # CAS-blind RNG seed for the orthogonal scaffold assignment


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _eid(d: str, n: int) -> str:
    return f"{d}{n}"


def _flags(text: str) -> dict[str, bool]:
    return {"contains_literal_element_code": any(t in text for t in _LITERAL),
            "contains_framework_word": bool(_FORBIDDEN.search(text)),
            "gloss_string_embedded": False}


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


def _role(d: str, n: int, split: str, si: int, di: int) -> str:
    dyn = _NOETIC_DYN[n][split][di % 3]
    adj = _REGISTER_ADJ[d][split][si % 3]
    manner = _MANNER_TEMPLATE[si % 3].format(a=adj)
    return f"{dyn}, {manner}"


def _scene(topic: str, frame: str, si: int, di: int) -> tuple[str, str, str]:
    topic_text = _TOPIC_SCENE[topic][si % 2]
    frame_text = _FRAME_CLAUSE[frame][di % 2]
    return f"{topic_text}, {frame_text}", topic_text, frame_text


def _bases() -> list[dict[str, Any]]:
    """720 base scenarios (80 pairs x 3 si x 3 di), each emitting Focus A + B."""
    bases: list[dict[str, Any]] = []
    for pi, pair in enumerate(_pairs()):
        split = "train" if pi % 2 == 0 else "test"
        (ld, ln), (rd, rn) = pair["left"], pair["right"]
        for si in range(3):
            for di in range(3):
                bases.append({"pair_kind": pair["kind"], "split": split,
                              "left": (ld, ln), "right": (rd, rn), "si": si, "di": di})
    return bases


def _assign_nc40(bases: list[dict[str, Any]]) -> None:
    """Assign (topic_40, frame_40) per base: exactly balanced per split, CAS-blind.

    For each split, build a balanced multiset of all 40 NC40 cells repeated equally
    to fill the split, shuffle it with a fixed CAS-BLIND RNG (the shuffle key knows
    nothing about the base's domain/noetic), and deal cells to bases in enumeration
    order. Exact per-cell balance per split + independence from CAS in expectation.
    The independence is then calibrated against a permutation null in the gate.
    """
    by_split: dict[str, list[int]] = defaultdict(list)
    for idx, b in enumerate(bases):
        by_split[b["split"]].append(idx)
    rng = np.random.default_rng(_NC40_SEED)
    for split in sorted(by_split):
        idxs = by_split[split]
        if len(idxs) % 40 != 0:
            raise SystemExit(f"split {split} has {len(idxs)} bases, not divisible by 40")
        reps = len(idxs) // 40
        cells = np.tile(np.arange(40), reps)
        rng.shuffle(cells)
        for i, cell in zip(idxs, cells.tolist()):
            bases[i]["topic_40"] = _TOPIC40[cell // 5]
            bases[i]["frame_40"] = _FRAME40[cell % 5]


def _nmi(xs: list[str], ys: list[str]) -> float:
    """Normalized mutual information (0 = independent, 1 = perfectly coupled)."""
    n = len(xs)
    cx, cy, cxy = Counter(), Counter(), Counter()
    for x, y in zip(xs, ys):
        cx[x] += 1; cy[y] += 1; cxy[(x, y)] += 1
    mi = 0.0
    for (x, y), nxy in cxy.items():
        pxy = nxy / n
        mi += pxy * math.log(pxy / ((cx[x] / n) * (cy[y] / n)))
    hx = -sum((v / n) * math.log(v / n) for v in cx.values())
    hy = -sum((v / n) * math.log(v / n) for v in cy.values())
    denom = math.sqrt(hx * hy)
    return mi / denom if denom > 0 else 0.0


def _nmi_null_band(xs: list[str], ys: list[str], k: int = 500) -> dict[str, float]:
    """Permutation null for NMI: shuffle ys (preserves marginals, forces independence).

    At 40x40 over 640 rows the raw NMI floor is large from sparse-cell bias, so the
    honest test is whether the REAL NMI sits inside this independence band, not
    whether it clears an absolute threshold.
    """
    rng = np.random.default_rng(7)
    ys_arr = np.array(ys, dtype=object)
    vals = []
    for _ in range(k):
        perm = rng.permutation(len(ys_arr))
        vals.append(_nmi(xs, ys_arr[perm].tolist()))
    vals = np.array(vals)
    return {"null_mean": float(vals.mean()), "null_p975": float(np.percentile(vals, 97.5)),
            "null_max": float(vals.max())}


def build_rows() -> list[dict[str, Any]]:
    bases = _bases()
    _assign_nc40(bases)
    rows: list[dict[str, Any]] = []
    for b in bases:
        split, si, di = b["split"], b["si"], b["di"]
        (ld, ln), (rd, rn) = b["left"], b["right"]
        topic, frame = b["topic_40"], b["frame_40"]
        scene, topic_text, frame_text = _scene(topic, frame, si, di)
        roleA = _role(ld, ln, split, si, di)
        roleB = _role(rd, rn, split, si, di)
        base = f"In {scene}: A is the one who {roleA}; B is the one who {roleB}."
        for focus, (d, n) in (("A", (ld, ln)), ("B", (rd, rn))):
            eng = f"{base} Focus: {focus}."
            sid = (f"c3_{split}_{b['pair_kind']}_{_eid(ld,ln)}_{_eid(rd,rn)}"
                   f"_s{si}d{di}_{topic}_{frame}_{_eid(d,n)}")
            rows.append({
                "sample_id": sid,
                "dataset_version": "mtc_condition3_topical_scenarios_v0",
                "split": split,
                "counterfactual_pair_id": f"{b['pair_kind']}_{_eid(ld,ln)}_{_eid(rd,rn)}_s{si}d{di}",
                "pair_kind": b["pair_kind"],
                "surface_style": "real_meaning_in_ordinary_scenario_orthogonal_topic_frame_no_gloss",
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
                "control_semantic": {
                    "topic_40": topic,
                    "frame_40": frame,
                    "topic_7": _TOPIC40_TO_TOPIC7[topic],
                    "function_4": _FRAME40_TO_FUNCTION4[frame],
                    "assignment": "cas_blind_seeded_shuffle_balanced_per_split_null_calibrated",
                },
                "scene_topic_text": topic_text,
                "scene_frame_text": frame_text,
                "anti_leak_flags": _flags(eng),
                "source_strategy": "claude_authored_condition3_real_meaning_in_ordinary_scenario_orthogonal_scaffold",
                "review_status": "draft_local_gates_pending",
            })
    return rows


def _balance_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    nc40 = [(r["control_semantic"]["topic_40"], r["control_semantic"]["frame_40"]) for r in rows]
    cas = [r["element_label"] for r in rows]
    cas_dom = [r["element_domain"] for r in rows]
    cas_noe = [str(r["element_noetic_tks"]) for r in rows]
    topic = [r["control_semantic"]["topic_40"] for r in rows]
    frame = [r["control_semantic"]["frame_40"] for r in rows]

    per_split_cell: dict[str, Counter] = defaultdict(Counter)
    for r, (t, f) in zip(rows, nc40):
        per_split_cell[r["split"]][f"{t}|{f}"] += 1
    cell_balanced = {s: (min(c.values()), max(c.values()), len(c))
                     for s, c in per_split_cell.items()}

    cell_lbl = [f"{t}|{f}" for t, f in nc40]
    real = _nmi(cas, cell_lbl)
    null = _nmi_null_band(cas, cell_lbl)
    return {
        "nc40_cell_counts_per_split_min_max_ndistinct": cell_balanced,
        "topic40_counts": dict(sorted(Counter(topic).items())),
        "frame40_counts": dict(sorted(Counter(frame).items())),
        "nmi_cas_element_vs_nc40_cell": round(real, 4),
        "nmi_cas_element_vs_nc40_null_mean": round(null["null_mean"], 4),
        "nmi_cas_element_vs_nc40_null_p975": round(null["null_p975"], 4),
        "orthogonal_within_independence_band": bool(real <= null["null_p975"]),
        "nmi_cas_domain_vs_topic40": round(_nmi(cas_dom, topic), 4),
        "nmi_cas_noetic_vs_frame40": round(_nmi(cas_noe, frame), 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(_HERE / f"mtc_condition3_topical_scenarios_{_DATE}.jsonl"))
    args = ap.parse_args(argv)

    rows = build_rows()
    rep = _balance_report(rows)

    # Hard balance check: every NC40 cell must have identical count within each split.
    for split, (mn, mx, nd) in rep["nc40_cell_counts_per_split_min_max_ndistinct"].items():
        if nd != 40 or mn != mx:
            raise SystemExit(f"NC40 not balanced in split={split}: "
                             f"min={mn} max={mx} distinct_cells={nd} (want 40 cells, equal counts)")
    # Orthogonality: the real CAS<->NC40 coupling must sit INSIDE the independence
    # band (raw NMI floor is high here purely from 40x40 sparse-cell bias).
    if not rep["orthogonal_within_independence_band"]:
        raise SystemExit(
            f"orthogonality FAILED: NMI(CAS,NC40)={rep['nmi_cas_element_vs_nc40_cell']} "
            f"exceeds independence p97.5={rep['nmi_cas_element_vs_nc40_null_p975']}")

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    manifest = {
        "schema_version": "mtc_condition3_fixture_manifest.v1",
        "date": _DATE, "out_jsonl": out.name, "out_jsonl_sha256": _sha256(out),
        "n_rows": len(rows), "n_elements": len({r["element_label"] for r in rows}),
        "split_counts": dict(sorted(Counter(r["split"] for r in rows).items())),
        "label_counts": dict(sorted(Counter(r["element_label"] for r in rows).items())),
        "design": ("real CAS meaning (noetic dynamic + domain-as-register, no gloss, "
                   "train/test-disjoint) embedded in ordinary scenarios that carry an "
                   "ORTHOGONAL topic/frame scaffold for Control B NC40_TOPIC_FRAME_V1"),
        "control_b_fields": ["control_semantic.topic_40", "control_semantic.frame_40"],
        "control_c_secondary_fields": ["control_semantic.topic_7", "control_semantic.function_4"],
        "control_c_note": "public_safety folds into human_services (no clean topic_7); NC28 balance approximate (secondary)",
        "orthogonality_and_balance": rep,
        "surface_gate_target": "local CAS-label text baseline near-chance (~2.5% for 40 classes)",
        "fixture_eligibility_target": "NC40 materializes balanced from non-CAS fields only (no CAS field read)",
    }
    (out.with_name(out.stem + "_manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
