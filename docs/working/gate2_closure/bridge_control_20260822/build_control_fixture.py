# -*- coding: utf-8 -*-
"""Build the 80-case bridge stance-control fixture from the FROZEN originals.

Inputs (all sha256-verified against the May 2026 run record):
  - original result JSON  (80 selected cases: labels + scenario_ids + condition scores)
  - scenario fixture JSON (prompts)
  - the attested bridge script's gloss templates (imported, not copied)

Emits bridge_control_fixture_20260822.json with, per case: prompt, gold/partner/predicted
labels, CAS readable/raw prefixes, CONTROL (non-CAS stance-matched) prefixes, continuations.
"""
import json, hashlib, pathlib, sys

R2 = pathlib.Path(r"C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\cas_interpretability_successor_20260820")
SCRIPTS = R2 / "noetic-compass-scaffold" / "noetic-compass" / "live-trace-worker" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from run_stage9_40e_eta_epsilon_bridge import (  # noqa: E402
    readable_prefix, raw_prefix, element_phrase, base_prompt, parse_element_label,
)

ARCH = pathlib.Path(r"D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_bridge_proof_20260528")
CLOSURE = pathlib.Path(r"D:\tksCAS-archive\gpt_neox_20b_stage9_original_40e_closure_20260527")
SP = pathlib.Path(__file__).resolve().parent

RESULT_JSON = ARCH / "gpt_neox_20b_stage9_original_40e_eta_epsilon_bridge_per2_20260528T0455Z.json"
SCENARIO_JSON = CLOSURE / "stage9_original_40e_scenarios_20260527.json"
OUT = SP / "bridge_control_fixture_20260822.json"

def ctrl_prefix(label: str) -> str:
    """Deterministic non-CAS stance-matched control (prereg 4.2, pinned verbatim)."""
    op, dom = parse_element_label(label)
    op_name, dom_name, op_gloss, dom_gloss = _gloss_of(label)
    return (
        "Plain-English context for the focused role:\n"
        f"- What it is about: {op_name.lower()} - {op_gloss}\n"
        f"- The sense in play: {dom_name.lower()} - {dom_gloss}\n"
        f"- In short: {element_phrase(label)}\n"
        "Use this context as background for the next sentence.\n\n"
    )

def _gloss_of(label: str):
    from run_stage9_40e_eta_epsilon_bridge import OPERATOR_GLOSSES, DOMAIN_GLOSSES
    op, dom = parse_element_label(label)
    oi, di = OPERATOR_GLOSSES[op], DOMAIN_GLOSSES[dom]
    return oi["name"], di["name"], oi["gloss"], di["gloss"]

def main() -> None:
    result = json.loads(RESULT_JSON.read_text(encoding="utf-8"))
    scenarios = json.loads(SCENARIO_JSON.read_text(encoding="utf-8"))
    if isinstance(scenarios, dict):
        scenarios = scenarios.get("scenarios") or scenarios.get("items") or []
    meta = {str(it["id"]): it for it in scenarios}
    cases_out = []
    ratios = []
    for case in result["cases"]:
        sid = str(case["scenario_id"])
        if sid not in meta:
            raise RuntimeError(f"scenario missing: {sid}")
        gold, partner, predicted = case["gold_label"], case["partner_label"], case["predicted_label"]
        cas_probe = readable_prefix(predicted)
        ctrl_probe = ctrl_prefix(predicted)
        cas_gold = readable_prefix(gold)
        ctrl_gold = ctrl_prefix(gold)
        cas_raw = raw_prefix(predicted)
        ratios.append(len(ctrl_probe) / max(1, len(cas_probe)))
        cases_out.append({
            "scenario_id": sid,
            "prompt": str(meta[sid]["prompt"]),
            "gold_label": gold, "partner_label": partner, "predicted_label": predicted,
            "base_prompt": base_prompt(str(meta[sid]["prompt"])),
            "correct_continuation": f" {element_phrase(gold)}.",
            "partner_continuation": f" {element_phrase(partner)}.",
            "prefixes": {
                "cas_probe": cas_probe, "ctrl_probe": ctrl_probe,
                "cas_gold": cas_gold, "ctrl_gold": ctrl_gold,
                "cas_raw": cas_raw,
            },
        })
    payload = {
        "schema": "bridge_stance_control_fixture.v1",
        "created_by": "build_control_fixture.py",
        "source_result_json": str(RESULT_JSON.name),
        "source_result_json_sha256": "9363F54B89122B5F2EB20954FFBE56C4447D69F68D2E8A9E1CC2E7F42F27EE2B",
        "source_scenario_json_sha256": "b2ad0481daaa1e5597a445a7ad8a9f2a4d108ead213818edd2ffb665af55b537",
        "n_cases": len(cases_out),
        "case_scenario_ids_equal_original": [c["scenario_id"] for c in cases_out] == [c["scenario_id"] for c in result["cases"]],
        "ctrl_over_cas_length_ratio": {
            "mean": round(sum(ratios) / len(ratios), 6), "min": round(min(ratios), 6), "max": round(max(ratios), 6),
        },
        "cases": cases_out,
    }
    raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    OUT.write_bytes(raw)
    print("n_cases:", len(cases_out))
    print("ids match original:", payload["case_scenario_ids_equal_original"])
    print("length ratio mean/min/max:", payload["ctrl_over_cas_length_ratio"])
    print("fixture sha256:", hashlib.sha256(raw).hexdigest())

if __name__ == "__main__":
    main()
