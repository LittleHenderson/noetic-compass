#!/usr/bin/env python3
"""Stage 21A: export canonical CAS Harness EvidencePacket v1 samples."""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
CAS_NATIVE_ROOT = ROOT / "cas-native"
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cas_native.model.generation_readiness_gate import (  # noqa: E402
    BALANCED,
    MAX_COVERAGE_TRIAGE,
    GenerationReadinessGate,
)
from evidence_packet import (  # noqa: E402
    SCHEMA_VERSION,
    validate_evidence_packet,
    write_evidence_packet,
)


STAGE19B = SCRIPT_DIR / "stage19b_cross_arch_foundation_verification_stack_20260519.json"
STAGE19C = SCRIPT_DIR / "stage19c_verification_mode_selector_20260519.json"
PRODUCT_PACKET = SCRIPT_DIR / "CAS_HARNESS_PRODUCT_EVIDENCE_PACKET_20260519.json"
OUT_DIR = SCRIPT_DIR / "evidence_packets"
OUT_JSON = SCRIPT_DIR / "stage21a_evidence_packet_export_20260519.json"
OUT_MD = SCRIPT_DIR / "STAGE21A_EVIDENCE_PACKET_EXPORT_20260519.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT.parents[1],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _manifest(model_report: dict[str, Any]) -> dict[str, Any]:
    path = SCRIPT_DIR / model_report["manifest_file"]
    return _read_json(path)


def _mode_profile(stage19c: dict[str, Any], model_key: str, mode: str) -> dict[str, Any]:
    profile = stage19c["modes"][mode]["models"][model_key]
    return {
        "accepted_accuracy": profile["accepted_accuracy"],
        "coverage": profile["coverage"],
        "silent_error_rate": profile["silent_error_rate"],
        "suppressed_rate": profile["suppressed_rate"],
        "source_component": profile["source_component"],
    }


def _cpl2(product_packet: dict[str, Any], model_name: str) -> dict[str, Any]:
    for row in product_packet["cross_model_cpl2"]:
        if row["model"] == model_name:
            return row
    return {}


def _readout_from_row(model_report: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    selected = model_report["selected_layers"]["foundation"]["focus_token"]
    votes = row.get("foundation_votes") or row.get("votes") or {}
    return {
        "axis": "foundation",
        "layer": int(selected["layer_position"]),
        "position": "focus_token",
        "label": row.get("prediction") or row.get("foundation") or "suppressed",
        "confidence": None,
        "confidence_source": "verification_stack_tier",
        "votes": votes,
        "stable_agree": row.get("stable_agree", []),
    }


def _verification(
    *,
    mode: str,
    mode_profile: dict[str, Any],
    accepted: bool,
    row: dict[str, Any],
) -> dict[str, Any]:
    reason = row.get("reason")
    suppression_reasons = [part for part in str(reason).split("+") if part] if reason else []
    return {
        "mode": mode,
        "accepted": accepted,
        "confidence_tier": row.get("confidence_tier", "suppressed" if not accepted else "high"),
        "mode_profile": mode_profile,
        "suppression_reasons": suppression_reasons,
    }


def _readiness(
    gate: GenerationReadinessGate,
    verification: dict[str, Any],
) -> dict[str, Any]:
    gate_verification: dict[str, Any]
    if verification["accepted"]:
        gate_verification = {
            "accepted": True,
            "decision_tier": verification["confidence_tier"],
        }
    else:
        gate_verification = {
            "accepted": False,
            "suppression_reasons": verification["suppression_reasons"],
        }
    return gate(
        verification=gate_verification,
        mode=verification["mode"],
    ).as_dict()


def _find(rows: list[dict[str, Any]], predicate, label: str) -> dict[str, Any]:
    for row in rows:
        if predicate(row):
            return row
    raise RuntimeError(f"Could not find canonical row for {label}")


def _packet(
    *,
    trace_id: str,
    model_key: str,
    model_report: dict[str, Any],
    manifest: dict[str, Any],
    product_packet: dict[str, Any],
    stage19c: dict[str, Any],
    row: dict[str, Any],
    accepted: bool,
    mode: str,
    code_commit: str,
    label: str,
) -> dict[str, Any]:
    mode_profile = _mode_profile(stage19c, model_key, mode)
    verification = _verification(
        mode=mode,
        mode_profile=mode_profile,
        accepted=accepted,
        row=row,
    )
    readiness = _readiness(GenerationReadinessGate(), verification)
    cpl2 = _cpl2(product_packet, manifest["model_name"])
    caveats = [
        "EvidencePacket v1 is an export artifact over locked Stage 19/20B reports; it does not rerun hidden-state inference.",
        "Readiness policy is generated from Verification Stack status in this export; neural lacunarity-head values are not present in the Stage 19 reports.",
        "Likelihood conditioning is supported by CPL2; exact sentence forcing in free-form decoding is not claimed.",
    ]
    if readiness["generation_readiness"] == "caveat":
        caveats.append("The readout was accepted at medium confidence, so downstream generation should disclose that caveat.")
    if readiness["generation_readiness"] in {"constrain", "suppress"}:
        caveats.append("The Verification Stack rejected this row; do not present it as a high-confidence accepted readout.")

    return {
        "schema_version": SCHEMA_VERSION,
        "trace_id": trace_id,
        "created_at": "2026-05-19",
        "model": {
            "name": manifest["model_name"],
            "family": "Qwen" if model_key == "qwen15b" else "OLMo",
            "model_key": model_key,
            "revision": manifest["model_revision"],
        },
        "provenance": {
            "code_commit": code_commit,
            "fixture_sha256": manifest["input_sha256"],
            "activation_sha256": manifest["output_sha256"],
            "activation_file": manifest["output_file"],
            "source_reports": [
                STAGE19B.name,
                STAGE19C.name,
                "stage20b_generation_readiness_packets_20260519.json",
            ],
            "source_stage": model_report["source_stage"],
        },
        "readout": _readout_from_row(model_report, row),
        "diagnostics": {
            "lacunarity": None,
            "blindspot_flags": verification["suppression_reasons"],
            "note": "Per-example LacunarityHead values are not present in Stage 19 reports.",
        },
        "verification": verification,
        "generation_readiness": readiness,
        "controls": {
            "text_baseline": None,
            "metadata_baseline": None,
            "random_ablation": "random null controls are reported in the source claims matrices",
            "raw_symbol_delta": cpl2.get("raw_symbol_delta"),
        },
        "conditioning": {
            "probe_readable_delta": cpl2.get("delta_vs_none"),
            "partner_margin": cpl2.get("margin_over_partner"),
            "p_value": cpl2.get("p_value"),
            "positive_cases": cpl2.get("positive_cases"),
        },
        "claim_badges": [
            "provenance",
            "readout",
            "verification_stack",
            "generation_readiness",
            "harness_conditioning",
        ],
        "caveats": caveats,
        "rejected_claims": product_packet["rejected_claims"],
        "boundary": (
            "This packet shows a bounded CAS Harness readout and readiness "
            "decision for one locked example. It does not claim raw CAS-symbol "
            "understanding, exact sentence forcing, or a complete neuron-by-neuron map."
        ),
        "export_label": label,
    }


def build_packets() -> list[dict[str, Any]]:
    stage19b = _read_json(STAGE19B)
    stage19c = _read_json(STAGE19C)
    product_packet = _read_json(PRODUCT_PACKET)
    code_commit = _git_commit()
    gate_models = stage19b["models"]

    olmo = gate_models["olmo1b"]
    qwen = gate_models["qwen15b"]
    olmo_manifest = _manifest(olmo)
    qwen_manifest = _manifest(qwen)

    qwen_allow = _find(
        qwen["accepted_examples_sample"],
        lambda r: r.get("confidence_tier") == "high",
        "qwen allow",
    )
    olmo_caveat = _find(
        olmo["accepted_examples_sample"],
        lambda r: r.get("confidence_tier") == "medium",
        "olmo caveat",
    )
    olmo_factor_conflict = _find(
        olmo["suppressed_examples_sample"],
        lambda r: r.get("reason") == "factor_conflicted",
        "olmo factor conflict",
    )

    return [
        _packet(
            trace_id="stage21a_allow_qwen15b_000",
            model_key="qwen15b",
            model_report=qwen,
            manifest=qwen_manifest,
            product_packet=product_packet,
            stage19c=stage19c,
            row=qwen_allow,
            accepted=True,
            mode=BALANCED,
            code_commit=code_commit,
            label="allow: clean accepted Qwen readout",
        ),
        _packet(
            trace_id="stage21a_caveat_olmo1b_009",
            model_key="olmo1b",
            model_report=olmo,
            manifest=olmo_manifest,
            product_packet=product_packet,
            stage19c=stage19c,
            row=olmo_caveat,
            accepted=True,
            mode=BALANCED,
            code_commit=code_commit,
            label="caveat: medium-confidence OLMo readout",
        ),
        _packet(
            trace_id="stage21a_suppress_olmo1b_054",
            model_key="olmo1b",
            model_report=olmo,
            manifest=olmo_manifest,
            product_packet=product_packet,
            stage19c=stage19c,
            row=olmo_factor_conflict,
            accepted=False,
            mode=BALANCED,
            code_commit=code_commit,
            label="suppress: factor-conflicted OLMo row in BALANCED",
        ),
        _packet(
            trace_id="stage21a_constrain_olmo1b_054",
            model_key="olmo1b",
            model_report=olmo,
            manifest=olmo_manifest,
            product_packet=product_packet,
            stage19c=stage19c,
            row=olmo_factor_conflict,
            accepted=False,
            mode=MAX_COVERAGE_TRIAGE,
            code_commit=code_commit,
            label="constrain: same OLMo row in MAX_COVERAGE_TRIAGE",
        ),
    ]


def _write_summary(packets: list[dict[str, Any]], written: list[dict[str, str]]) -> None:
    summary = {
        "schema_version": "stage21a_evidence_packet_export_v1",
        "date": "2026-05-19",
        "status": "EVIDENCE_PACKET_EXPORT_READY",
        "packet_schema_version": SCHEMA_VERSION,
        "packet_count": len(packets),
        "packets": [
            {
                "trace_id": packet["trace_id"],
                "model": packet["model"]["name"],
                "mode": packet["verification"]["mode"],
                "accepted": packet["verification"]["accepted"],
                "generation_readiness": packet["generation_readiness"]["generation_readiness"],
                "json": files["json"],
                "markdown": files["markdown"],
            }
            for packet, files in zip(packets, written)
        ],
        "boundary": (
            "Stage 21A exports canonical packet artifacts from locked Stage "
            "19/20B reports. It is product packaging, not a new model run."
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Stage 21A EvidencePacket Export",
        "",
        "Date: 2026-05-19",
        "",
        "Status: `EVIDENCE_PACKET_EXPORT_READY`",
        "",
        "## Boundary",
        "",
        summary["boundary"],
        "",
        "## Canonical Packets",
        "",
        "| Trace ID | Model | Mode | Accepted | Readiness | JSON | Markdown |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in summary["packets"]:
        lines.append(
            "| {trace_id} | {model} | `{mode}` | `{accepted}` | `{readiness}` | `{json}` | `{markdown}` |".format(
                trace_id=row["trace_id"],
                model=row["model"],
                mode=row["mode"],
                accepted=row["accepted"],
                readiness=row["generation_readiness"],
                json=row["json"],
                markdown=row["markdown"],
            )
        )
    lines.extend([
        "",
        "## Product Read",
        "",
        "Stage 21A turns the report stack into the customer-facing artifact:",
        "one packet per trace, each with provenance, readout, verification mode,",
        "generation readiness, controls, conditioning metrics, caveats, and",
        "rejected claims.",
        "",
    ])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    packets = build_packets()
    written: list[dict[str, str]] = []
    for packet in packets:
        validate_evidence_packet(packet)
        json_path, md_path = write_evidence_packet(packet, OUT_DIR)
        written.append({
            "json": json_path.relative_to(SCRIPT_DIR).as_posix(),
            "markdown": md_path.relative_to(SCRIPT_DIR).as_posix(),
        })
    _write_summary(packets, written)
    print(json.dumps({"status": "EVIDENCE_PACKET_EXPORT_READY", "packet_count": len(packets)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
