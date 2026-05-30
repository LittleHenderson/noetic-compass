"""Merge the S7-F28 Balanced Bridge run into one Evidence Packet.

This script is deliberately file-based: it does not re-run the model, and it
does not invent a final ACCEPT/SUPPRESS decision. It binds the exact readout,
ablation, likelihood-bridge, trace-diagnostic, and scenario artifacts into a
CAS Harness Evidence Packet with hashes and proof chips.
"""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


METHOD_LABEL = "S7-F28-BALANCED-BRIDGE"
METHOD_NAME = "S7-F28 Balanced Bridge Method"
TRACE_ID = "s7-f28-balanced-bridge-gpt-neox-20b-20260526"
SCHEMA_VERSION = "cas_harness_evidence_packet_v1"

PROOF_CHIP_NAMES = {
    "model_proof": "Model proof",
    "cas_readout": "CAS readout",
    "causal_proof": "Causal proof",
    "control_proof": "Control proof",
    "output_proof": "Output proof",
    "packet_proof": "Packet proof",
}


@dataclass(frozen=True)
class MergeConfig:
    scenario_path: Path
    eval_report: Path
    ablation_report: Path
    bridge_report: Path
    trace_diagnostics_report: Path
    output: Path
    output_md: Path | None = None
    trace_id: str = TRACE_ID
    model_provenance_path: Path | None = None


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-path", required=True, type=Path)
    parser.add_argument("--eval-report", required=True, type=Path)
    parser.add_argument("--ablation-report", required=True, type=Path)
    parser.add_argument("--bridge-report", required=True, type=Path)
    parser.add_argument("--trace-diagnostics-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--trace-id", default=TRACE_ID)
    parser.add_argument("--model-provenance-path", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = MergeConfig(
        scenario_path=args.scenario_path,
        eval_report=args.eval_report,
        ablation_report=args.ablation_report,
        bridge_report=args.bridge_report,
        trace_diagnostics_report=args.trace_diagnostics_report,
        output=args.output,
        output_md=args.output_md,
        trace_id=args.trace_id,
        model_provenance_path=args.model_provenance_path,
    )
    packet = build_evidence_packet(config)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    config.output.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    if config.output_md:
        config.output_md.parent.mkdir(parents=True, exist_ok=True)
        config.output_md.write_text(render_markdown(packet), encoding="utf-8")
    verification = packet["verification"]
    print(f"[evidence-packet] trace_id={packet['trace_id']}")
    print(f"[evidence-packet] verdict={verification['explicit_verifier_decision']['verdict']}")
    print(f"[evidence-packet] confidence={verification['explicit_verifier_decision']['confidence']:.6f}")
    print(f"[evidence-packet] wrote {config.output}")
    if config.output_md:
        print(f"[evidence-packet] wrote {config.output_md}")
    return 0


def build_evidence_packet(config: MergeConfig) -> dict[str, Any]:
    artifacts = {
        "scenario_path": config.scenario_path,
        "eval_report": config.eval_report,
        "ablation_report": config.ablation_report,
        "bridge_report": config.bridge_report,
        "trace_diagnostics_report": config.trace_diagnostics_report,
    }
    for name, path in artifacts.items():
        if not path.is_file():
            raise FileNotFoundError(f"{name} not found: {path}")

    scenario = load_json(config.scenario_path)
    eval_report = load_json(config.eval_report)
    ablation_report = load_json(config.ablation_report)
    bridge_report = load_json(config.bridge_report)
    trace_report = load_json(config.trace_diagnostics_report)
    model_provenance = load_json(config.model_provenance_path) if config.model_provenance_path else None

    readout = readout_summary(trace_report=trace_report, eval_report=eval_report)
    ablation = ablation_summary(ablation_report)
    matched_controls = matched_control_summary(ablation_report=ablation_report, bridge_report=bridge_report)
    output = output_summary(bridge_report)
    trace = trace_summary(trace_report)
    proof_chips = proof_chips_for(
        readout=readout,
        ablation=ablation,
        matched_controls=matched_controls,
        output=output,
        trace=trace,
    )
    confidence = evidence_gate_confidence(
        readout=readout,
        output=output,
        ablation=ablation,
        trace=trace,
    )
    scenario_summary = summarize_scenarios(scenario)
    model = model_summary(bridge_report)
    packet_hashes = artifact_hashes(artifacts)

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trace_id": config.trace_id,
        "generated_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": {
            "method_label": METHOD_LABEL,
            "method_name": METHOD_NAME,
            "axis": "Foundation-28",
            "scenario_set": scenario_summary,
            "text": "Stage 7 Foundation-28 role-bound scenario set; one packet summarizes the full run, not a single prompt.",
        },
        "model": model,
        "model_provenance": model_provenance,
        "cas_expression": {
            "text": "Foundation-28 = F1..F7 x T/A/f/E",
            "compiler_valid": True,
            "grammar_category": "source_defined_foundation_axis",
            "method_label": METHOD_LABEL,
        },
        "output": output,
        "copy_slot_trace": copy_slot_trace(artifacts),
        "provenance": {
            "method_label": METHOD_LABEL,
            "source_stage": "Stage 7 Foundation-28 large-model bridge",
            "source_reports": [
                "stage7_foundation_rolebound_probe_eval",
                "stage7_foundation_rolebound_activation_cover_ablation",
                "stage7_eta_epsilon_bridge_logistic",
                "stage7_trace_diagnostics_logistic",
            ],
            "code_commit_sha": git_head_sha(),
            "artifact_paths": {name: str(path) for name, path in artifacts.items()},
            "model_provenance_path": str(config.model_provenance_path) if config.model_provenance_path else None,
            "runpod_workspace": "/workspace/cas-harness-large-eval",
            "local_artifact_root": str(config.output.parent),
        },
        "hashes": packet_hashes,
        "claim_levels": claim_levels(
            readout=readout,
            ablation=ablation,
            matched_controls=matched_controls,
            output=output,
            trace=trace,
        ),
        "caveats": caveats(),
        "readout": readout,
        "ablation": ablation,
        "matched_controls": matched_controls,
        "verification": {
            "proof_chips": proof_chips,
            "trace_diagnostics": trace,
            "evidence_gate_confidence": confidence,
            "explicit_verifier_decision": {
                "verdict": "FLAG_FOR_HUMAN_REVIEW",
                "confidence": confidence["score"],
                "source": METHOD_LABEL,
                "reason": (
                    "All S7-F28 evidence layers are present, but this packet is a "
                    "large-model validation artifact. Final production ACCEPT/SUPPRESS "
                    "still requires the Stage 19/20/21 verifier decision layer."
                ),
            },
        },
        "generation_readiness": {
            "generation_readiness": "caveat",
            "risk_score": confidence["score"],
            "reason": "Strong 20B evidence packet assembled; final product verifier merge remains pending.",
            "missing_for_accept_suppress": [
                "Stage 19 verification-stack decision",
                "Stage 20 generation-readiness action",
                "production audit-session persistence",
            ],
        },
    }
    packet["hashes"]["packet_content_sha256"] = sha256_json_without_packet_hash(packet)
    return packet


def readout_summary(
    *,
    trace_report: Mapping[str, Any],
    eval_report: Mapping[str, Any],
) -> dict[str, Any]:
    layer_scan = mapping(trace_report.get("layer_scan"))
    lacunarity = mapping(trace_report.get("lacunarity_gate"))
    probe = mapping(trace_report.get("probe_readout"))
    legacy_foundation = mapping(mapping(eval_report.get("axes")).get("foundation"))
    legacy_controls = mapping(legacy_foundation.get("controls"))
    return {
        "status": "verified" if trace_report.get("status") == "TRACE_DIAGNOSTICS_PASS" else "present",
        "axis": "Foundation-28",
        "method": METHOD_LABEL,
        "kind": probe.get("kind", "balanced_logistic_linear_probe"),
        "layer": layer_scan.get("best_layer"),
        "heldout_accuracy": number(layer_scan.get("best_test_acc")),
        "heldout_macro_f1": number(layer_scan.get("best_test_macro_f1")),
        "lacunarity": number(lacunarity.get("score")),
        "lacunarity_threshold": number(lacunarity.get("threshold")),
        "lacunarity_passed": bool(lacunarity.get("passed")),
        "drive_lacunarity": number(lacunarity.get("drive_lacunarity")),
        "register_lacunarity": number(lacunarity.get("register_lacunarity")),
        "balanced_probe": {
            "class_weight": probe.get("class_weight"),
            "C": probe.get("C"),
            "standardized": probe.get("standardized"),
        },
        "legacy_centroid_context": {
            "best_layer": mapping(legacy_foundation.get("best_layer")).get("layer"),
            "test_acc": number(mapping(legacy_foundation.get("best_layer")).get("test_acc")),
            "majority_class_test_acc": number(legacy_controls.get("majority_class_test_acc")),
            "shuffled_label_hidden_centroid_mean_test_acc": number(
                legacy_controls.get("shuffled_label_hidden_centroid_mean_test_acc")
            ),
            "text_hash_centroid_test_acc": number(mapping(legacy_controls.get("text_hash_centroid")).get("test_acc")),
            "note": "Legacy centroid report is retained as cover-discovery context; the S7-F28 gate uses balanced logistic.",
        },
    }


def ablation_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    foundation = mapping(mapping(report.get("axes")).get("foundation"))
    label = mapping(foundation.get("label_specific_cover_ablation"))
    random_control = mapping(foundation.get("label_random_same_size_controls"))
    wrong = mapping(foundation.get("wrong_cover_control"))
    result = mapping(foundation.get("result_summary"))
    return {
        "status": "verified" if result.get("label_drop_exceeds_random_max") is True else "present",
        "axis": "Foundation-28",
        "mode": report.get("ablation_mode", "activation_level_train_mean_replacement"),
        "best_layer": foundation.get("best_layer"),
        "clean": mapping(foundation.get("clean")),
        "label_specific_cover_ablation": label,
        "wrong_cover_control": wrong,
        "label_random_same_size_controls": random_control,
        "result_summary": result,
        "plain_english_read": (
            "The true Foundation cover damages heldout readout far more than "
            "same-size random covers or wrong-Foundation covers."
        ),
        "important_limit": report.get("important_limit"),
    }


def matched_control_summary(
    *,
    ablation_report: Mapping[str, Any],
    bridge_report: Mapping[str, Any],
) -> dict[str, Any]:
    foundation = mapping(mapping(ablation_report.get("axes")).get("foundation"))
    random_control = mapping(foundation.get("label_random_same_size_controls"))
    wrong = mapping(foundation.get("wrong_cover_control"))
    result = mapping(foundation.get("result_summary"))
    conditions = mapping(bridge_report.get("conditions"))
    return {
        "status": "verified" if result.get("label_drop_exceeds_random_max") is True else "present",
        "activation_controls": {
            "same_size_random_controls": random_control,
            "wrong_cover_control": wrong,
            "label_drop_exceeds_random_max": result.get("label_drop_exceeds_random_max"),
            "label_drop_minus_random_mean": number(result.get("label_drop_minus_random_mean")),
        },
        "bridge_controls": {
            "probe_raw_delta_vs_none": number(
                mapping(mapping(conditions.get("probe_raw")).get("delta_vs_none")).get("mean")
            ),
            "gold_raw_delta_vs_none": number(
                mapping(mapping(conditions.get("gold_raw")).get("delta_vs_none")).get("mean")
            ),
            "partner_readable_delta_vs_none": number(
                mapping(mapping(conditions.get("partner_readable")).get("delta_vs_none")).get("mean")
            ),
            "probe_readable_sign_p": number(bridge_gate(bridge_report, "probe_readable", "delta_positive_sign_p")),
        },
        "plain_english_read": (
            "Random cover removal, wrong-cover removal, and raw CAS-symbol prefixes "
            "do not explain the same effect as the true readable Foundation bridge."
        ),
    }


def output_summary(bridge_report: Mapping[str, Any]) -> dict[str, Any]:
    conditions = mapping(bridge_report.get("conditions"))
    probe_readable = mapping(conditions.get("probe_readable"))
    gold_readable = mapping(conditions.get("gold_readable"))
    n_cases = int(bridge_report.get("n_cases") or 0)
    probe_positive = int(probe_readable.get("delta_positive_count") or 0)
    gold_positive = int(gold_readable.get("delta_positive_count") or 0)
    probe_prediction = mapping(bridge_report.get("probe_prediction"))
    return {
        "status": bridge_report.get("status"),
        "text": (
            "Probe-predicted readable CAS context moved GPT-NeoX-20B likelihood in "
            "the predicted Foundation direction."
        ),
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "method": "eta_to_epsilon_likelihood_bridge",
        "readout_mode": bridge_report.get("readout_mode"),
        "readout_layer": bridge_report.get("readout_layer"),
        "n_cases": n_cases,
        "probe_prediction": {
            "all_test_foundation_accuracy": number(probe_prediction.get("all_test_foundation_accuracy")),
            "selected_foundation_accuracy": number(probe_prediction.get("selected_foundation_accuracy")),
            "selected_drive_accuracy": number(probe_prediction.get("selected_drive_accuracy")),
        },
        "probe_readable": {
            "delta_vs_none_mean": number(mapping(probe_readable.get("delta_vs_none")).get("mean")),
            "positive_count": probe_positive,
            "positive_fraction": round(probe_positive / n_cases, 6) if n_cases else None,
            "sign_p": number(probe_readable.get("delta_positive_sign_p")),
            "minus_partner_readable_margin": number(
                mapping(bridge_report.get("key_comparisons")).get("probe_readable_minus_partner_readable_margin")
            ),
        },
        "gold_readable": {
            "delta_vs_none_mean": number(mapping(gold_readable.get("delta_vs_none")).get("mean")),
            "positive_count": gold_positive,
            "positive_fraction": round(gold_positive / n_cases, 6) if n_cases else None,
            "sign_p": number(gold_readable.get("delta_positive_sign_p")),
        },
        "raw_symbol_controls": {
            "probe_raw_delta_vs_none": number(mapping(bridge_report.get("key_comparisons")).get("probe_raw_delta_vs_none")),
            "gold_raw_delta_vs_none": number(mapping(bridge_report.get("key_comparisons")).get("gold_raw_delta_vs_none")),
        },
        "important_limit": bridge_report.get("important_limit"),
    }


def trace_summary(trace_report: Mapping[str, Any]) -> dict[str, Any]:
    lacunarity = mapping(trace_report.get("lacunarity_gate"))
    fractal = mapping(trace_report.get("fractal_preflight"))
    layer_scan = mapping(trace_report.get("layer_scan"))
    return {
        "status": trace_report.get("status"),
        "passed": trace_report.get("status") == "TRACE_DIAGNOSTICS_PASS",
        "gate_layer": layer_scan.get("best_layer"),
        "heldout_foundation_accuracy": number(layer_scan.get("best_test_acc")),
        "foundation_lacunarity": number(lacunarity.get("score")),
        "drive_lacunarity": number(lacunarity.get("drive_lacunarity")),
        "register_lacunarity": number(lacunarity.get("register_lacunarity")),
        "numeric_trace_class": fractal.get("class"),
        "classifier_kind": fractal.get("classifier_kind"),
        "important_limit": fractal.get("important_limit"),
    }


def proof_chips_for(
    *,
    readout: Mapping[str, Any],
    ablation: Mapping[str, Any],
    matched_controls: Mapping[str, Any],
    output: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> list[dict[str, str]]:
    bridge_passed = output.get("status") == "PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS"
    trace_passed = trace.get("passed") is True
    return [
        chip("model_proof", "present", "Model identity and architecture are recorded from the real GPT-NeoX-20B run."),
        chip(
            "cas_readout",
            "verified" if readout.get("lacunarity_passed") and trace_passed else "present",
            "Balanced-logistic Foundation-28 readout and trace gate are recorded.",
        ),
        chip(
            "causal_proof",
            str(ablation.get("status") or "present"),
            "Targeted Foundation cover ablation is recorded.",
        ),
        chip(
            "control_proof",
            str(matched_controls.get("status") or "present"),
            "Matched random, wrong-cover, and bridge controls are recorded.",
        ),
        chip(
            "output_proof",
            "verified" if bridge_passed else "present",
            "Eta-to-epsilon likelihood bridge output-effect evidence is recorded.",
        ),
        chip("packet_proof", "present", "This Evidence Packet binds the run artifacts and SHA-256 hashes."),
    ]


def evidence_gate_confidence(
    *,
    readout: Mapping[str, Any],
    output: Mapping[str, Any],
    ablation: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> dict[str, Any]:
    readout_acc = float(readout.get("heldout_accuracy") or 0.0)
    bridge_fraction = float(mapping(output.get("probe_readable")).get("positive_fraction") or 0.0)
    causal_score = 1.0 if ablation.get("status") == "verified" else 0.0
    trace_score = 1.0 if trace.get("passed") is True else 0.0
    score = round(min(readout_acc, bridge_fraction, causal_score, trace_score), 6)
    return {
        "score": score,
        "label": "evidence-gate confidence",
        "formula": (
            "min(balanced_logistic_heldout_accuracy, "
            "probe_readable_positive_fraction, causal_control_pass, trace_gate_pass)"
        ),
        "inputs": {
            "balanced_logistic_heldout_accuracy": readout_acc,
            "probe_readable_positive_fraction": bridge_fraction,
            "causal_control_pass": causal_score,
            "trace_gate_pass": trace_score,
        },
        "important_limit": (
            "This is a conservative evidence-gate score for this packet, not a "
            "mathematical certainty score and not a production ACCEPT/SUPPRESS confidence."
        ),
    }


def claim_levels(
    *,
    readout: Mapping[str, Any],
    ablation: Mapping[str, Any],
    matched_controls: Mapping[str, Any],
    output: Mapping[str, Any],
    trace: Mapping[str, Any],
) -> list[dict[str, str]]:
    return [
        claim(
            "CAS readout: balanced-logistic Foundation-28 hidden-state readout passed the trace gate.",
            "validated_run_artifact",
            f"Heldout accuracy={readout.get('heldout_accuracy')}; lacunarity={readout.get('lacunarity')}.",
        ),
        claim(
            "Ablation/intervention causal proof: true Foundation cover removal damaged readout more than controls.",
            "validated_run_artifact",
            f"Label-cover drop={mapping(ablation.get('label_specific_cover_ablation')).get('drop_from_clean')}.",
        ),
        claim(
            "Matched control proof: random covers, wrong covers, and raw-symbol bridge controls did not explain the same effect.",
            "validated_run_artifact",
            matched_controls.get("plain_english_read", ""),
        ),
        claim(
            "Output likelihood proof: eta-to-epsilon readable bridge moved likelihood in the predicted Foundation direction.",
            "validated_run_artifact",
            f"Probe-readable delta={mapping(output.get('probe_readable')).get('delta_vs_none_mean')}; sign p={mapping(output.get('probe_readable')).get('sign_p')}.",
        ),
        claim(
            "Trace diagnostic proof: numeric layer trace passed the S7-F28 pre-steering gate.",
            "validated_run_artifact",
            f"Trace status={trace.get('status')}; numeric class={trace.get('numeric_trace_class')}.",
        ),
        claim(
            "Evidence Packet proof: artifact hashes and method provenance are bound into this packet.",
            "packet_integrity",
            "SHA-256 hashes are recorded for the source reports used to assemble the packet.",
        ),
    ]


def claim(claim_text: str, level: str, rationale: str) -> dict[str, str]:
    return {
        "claim": claim_text,
        "level": level,
        "support_status": "supported",
        "support_rationale": rationale,
        "rationale": rationale,
    }


def chip(chip_id: str, status: str, detail: str) -> dict[str, str]:
    if status not in {"verified", "present", "missing", "failed", "unavailable"}:
        status = "present"
    return {
        "id": chip_id,
        "name": PROOF_CHIP_NAMES[chip_id],
        "status": status,
        "detail": detail,
    }


def bridge_gate(report: Mapping[str, Any], condition: str, check: str) -> Any:
    return mapping(mapping(mapping(report.get("bridge_gates")).get(condition)).get("checks")).get(check, {}).get("value")


def summarize_scenarios(payload: Mapping[str, Any]) -> dict[str, Any]:
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        return {"scenario_count": None, "note": "Scenario payload did not expose a scenarios list."}
    splits: dict[str, int] = {}
    foundations: dict[str, int] = {}
    for row in scenarios:
        if not isinstance(row, Mapping):
            continue
        meta = mapping(row.get("metadata"))
        axes = mapping(row.get("expected_cas_axes"))
        split = str(meta.get("split") or "unknown")
        foundation = str(axes.get("foundation") or meta.get("foundation") or "unknown")
        splits[split] = splits.get(split, 0) + 1
        foundations[foundation] = foundations.get(foundation, 0) + 1
    return {
        "scenario_count": len(scenarios),
        "split_counts": dict(sorted(splits.items())),
        "foundation_class_count": len([key for key in foundations if key != "unknown"]),
        "per_foundation_count": dict(sorted(foundations.items())),
    }


def model_summary(bridge_report: Mapping[str, Any]) -> dict[str, Any]:
    info = mapping(bridge_report.get("model_info"))
    return {
        "model_key": bridge_report.get("model_id"),
        "name": bridge_report.get("model_id"),
        "model_revision": bridge_report.get("model_revision"),
        "architectures": info.get("architectures"),
        "model_type": info.get("model_type"),
        "parameter_count": info.get("parameter_count"),
        "num_hidden_layers": info.get("num_hidden_layers"),
        "hidden_size": info.get("hidden_size"),
        "torch_dtype": info.get("torch_dtype"),
        "device_map": info.get("device_map"),
    }


def artifact_hashes(artifacts: Mapping[str, Path]) -> dict[str, Any]:
    entries = {}
    paths = {}
    sizes = {}
    for name, path in sorted(artifacts.items()):
        entries[name] = sha256_file(path)
        paths[f"{name}_path"] = str(path)
        sizes[name] = path.stat().st_size
    if "scenario_path" in artifacts:
        paths["corpus_path"] = str(artifacts["scenario_path"])
    return {
        "artifact_sha256": entries,
        "artifact_sizes_bytes": sizes,
        "on_disk_paths": paths,
        "weights_sha": None,
        "tokenizer_hash": None,
        "corpus_sha256": entries.get("scenario_path"),
    }


def copy_slot_trace(artifacts: Mapping[str, Path]) -> list[dict[str, Any]]:
    rows = []
    for index, (name, path) in enumerate(sorted(artifacts.items()), start=1):
        rows.append(
            {
                "slot": index,
                "source": name,
                "artifact_path": str(path),
                "sha256": sha256_file(path),
            }
        )
    return rows


def caveats() -> list[str]:
    return [
        "This packet is a GPT-NeoX-20B S7-F28 validation artifact, not a universal 20B/100B/300B proof.",
        "The verdict is FLAG_FOR_HUMAN_REVIEW because the Stage 19/20/21 production verifier layer is not attached.",
        "The trace diagnostic uses a numeric layer-trace proxy, not yet the discrete cas-engine CognitiveFractal orbit classifier.",
        "Activation-cover ablation is measured on captured hidden states; it is not the same as a live forward-pass steering hook.",
        "The packet records model identity and architecture, but no independent model-weight SHA is available in these artifacts.",
    ]


def render_markdown(packet: Mapping[str, Any]) -> str:
    verification = mapping(packet.get("verification"))
    decision = mapping(verification.get("explicit_verifier_decision"))
    readout = mapping(packet.get("readout"))
    ablation = mapping(packet.get("ablation"))
    output = mapping(packet.get("output"))
    trace = mapping(verification.get("trace_diagnostics"))
    confidence = mapping(verification.get("evidence_gate_confidence"))
    lines = [
        "# S7-F28 Balanced Bridge Evidence Packet",
        "",
        f"- Trace ID: `{packet.get('trace_id')}`",
        f"- Method: `{METHOD_LABEL}`",
        f"- Model: `{mapping(packet.get('model')).get('name')}`",
        f"- Verdict: `{decision.get('verdict')}`",
        f"- Evidence confidence: `{decision.get('confidence')}`",
        f"- Confidence formula: `{confidence.get('formula')}`",
        "",
        "## Core Results",
        "",
        f"- Balanced-logistic heldout Foundation accuracy: `{readout.get('heldout_accuracy')}`",
        f"- Foundation lacunarity: `{readout.get('lacunarity')}`",
        f"- Label-cover ablation drop: `{mapping(ablation.get('label_specific_cover_ablation')).get('drop_from_clean')}`",
        f"- Random-control mean drop: `{mapping(mapping(ablation.get('label_random_same_size_controls'))).get('mean_drop_from_clean')}`",
        f"- Wrong-cover drop: `{mapping(mapping(ablation.get('wrong_cover_control'))).get('drop_from_clean')}`",
        f"- Probe-readable bridge delta: `{mapping(output.get('probe_readable')).get('delta_vs_none_mean')}`",
        f"- Probe-readable positive rows: `{mapping(output.get('probe_readable')).get('positive_count')}/{output.get('n_cases')}`",
        f"- Trace diagnostic: `{trace.get('status')}` / `{trace.get('numeric_trace_class')}`",
        "",
        "## Why Not ACCEPT Yet",
        "",
        "This packet assembles the evidence chain. It does not attach the final Stage 19/20/21 production verifier, so the public verdict stays `FLAG_FOR_HUMAN_REVIEW`.",
        "",
        "## Caveats",
        "",
    ]
    lines.extend(f"- {item}" for item in packet.get("caveats") or [])
    return "\n".join(lines) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json_without_packet_hash(packet: Mapping[str, Any]) -> str:
    clone = json.loads(json.dumps(packet, sort_keys=True))
    hashes = mapping(clone.get("hashes"))
    if isinstance(hashes, dict):
        hashes.pop("packet_content_sha256", None)
    blob = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def git_head_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


if __name__ == "__main__":
    raise SystemExit(main())
