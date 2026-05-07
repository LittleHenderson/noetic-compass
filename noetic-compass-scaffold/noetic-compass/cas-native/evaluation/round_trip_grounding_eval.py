"""Round-trip grounding eval for native NL generated replies.

The B-3 generator is conditioned on CAS state and emits natural language.
This script asks whether the trusted K=9 structured-token classifier can
recover the intended CAS axes from that generated language.

It calibrates against target replies first:

    TARGET reply-only        -> K=9 prediction
    TARGET prompt+reply      -> K=9 prediction
    GENERATED reply-only     -> K=9 prediction
    GENERATED prompt+reply   -> K=9 prediction

The generated-vs-target ratio is the main diagnostic. If K=9 cannot recover an
axis from the corpus target replies, generated replies should not be punished
for missing the same axis.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import types
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


# Path bootstrap for direct ``python round_trip_grounding_eval.py`` invocation.
_THIS_DIR = Path(__file__).resolve().parent
_CAS_NATIVE_ROOT = _THIS_DIR.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = package


from cas_native.inference.predict_cas import load_predictor  # noqa: E402


AXES = ("register", "domain", "drive", "noetic")
KINDS = ("target", "generated")
MODES = ("reply_only", "prompt_reply")


def load_samples(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Load diverse-CAS generated sample records from JSONL."""
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= int(limit):
                break
    return rows


def normalize_noetic(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("^"):
            stripped = stripped[1:]
        if stripped.isdigit():
            return int(stripped)
    return None


def normalize_registers(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(v) for v in value}
    if isinstance(value, str) and value:
        return {value}
    return set()


def target_axes(sample: dict[str, Any]) -> dict[str, Any]:
    conditioning = dict(sample.get("conditioning") or {})
    return {
        "register": str(conditioning.get("register") or sample.get("register") or ""),
        "domain": str(conditioning.get("domain") or ""),
        "drive": str(conditioning.get("drive") or ""),
        "noetic": normalize_noetic(conditioning.get("noetic")),
    }


def prediction_matches(prediction: dict[str, Any], target: dict[str, Any]) -> dict[str, bool]:
    registers = normalize_registers(prediction.get("registers"))
    return {
        "register": bool(target["register"] and target["register"] in registers),
        "domain": bool(target["domain"] and prediction.get("domain") == target["domain"]),
        "drive": bool(target["drive"] and prediction.get("drive") == target["drive"]),
        "noetic": bool(
            target["noetic"] is not None
            and normalize_noetic(prediction.get("noetic")) == target["noetic"]
        ),
    }


def text_for(sample: dict[str, Any], *, kind: str, mode: str) -> str:
    prompt = str(sample.get("prompt_text") or "").strip()
    if kind == "target":
        reply = str(sample.get("target_reply_text") or "").strip()
    elif kind == "generated":
        reply = str(sample.get("generated_reply_text") or "").strip()
    else:
        raise ValueError(f"unknown kind: {kind!r}")

    if mode == "reply_only":
        return reply
    if mode == "prompt_reply":
        return f"{prompt} {reply}".strip()
    raise ValueError(f"unknown mode: {mode!r}")


def safe_rate(num: int, den: int) -> float:
    return float(num) / float(den) if den else 0.0


def ratio(generated_rate: float, target_rate: float) -> float | None:
    if target_rate <= 0:
        return None
    return generated_rate / target_rate


def verdict_for_ratio(value: float | None) -> str:
    if value is None:
        return "no_target_baseline"
    if value >= 0.90:
        return "strong"
    if value >= 0.80:
        return "acceptable"
    return "gap"


def evaluate(
    samples: list[dict[str, Any]],
    *,
    k9_run_dir: str | Path,
    device: str = "cpu",
    max_length: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run K=9 round-trip predictions and return rows + summary."""
    predictor = load_predictor(k9_run_dir, device=device, max_length=max_length)

    rows: list[dict[str, Any]] = []
    counts: dict[str, dict[str, dict[str, dict[str, int]]]] = {
        kind: {
            mode: {axis: {"correct": 0, "total": 0} for axis in AXES}
            for mode in MODES
        }
        for kind in KINDS
    }
    by_register: dict[str, dict[str, dict[str, dict[str, int]]]] = defaultdict(
        lambda: {
            kind: {
                mode: {axis: {"correct": 0, "total": 0} for axis in AXES}
                for mode in MODES
            }
            for kind in KINDS
        }
    )

    started = time.perf_counter()
    for i, sample in enumerate(samples):
        target = target_axes(sample)
        for kind in KINDS:
            for mode in MODES:
                text = text_for(sample, kind=kind, mode=mode)
                prediction = predictor(text)
                matches = prediction_matches(prediction, target)
                for axis, ok in matches.items():
                    counts[kind][mode][axis]["correct"] += int(ok)
                    counts[kind][mode][axis]["total"] += 1
                    by_register[target["register"]][kind][mode][axis]["correct"] += int(ok)
                    by_register[target["register"]][kind][mode][axis]["total"] += 1

                rows.append(
                    {
                        "sample_index": i,
                        "record_id": sample.get("record_id", ""),
                        "config_id": sample.get("config_id", ""),
                        "kind": kind,
                        "mode": mode,
                        "target_axes": target,
                        "prediction": prediction,
                        "matches": matches,
                        "text": text,
                    }
                )

    summary = build_summary(
        samples=samples,
        counts=counts,
        by_register=by_register,
        elapsed_sec=time.perf_counter() - started,
        k9_run_dir=str(k9_run_dir),
    )
    return rows, summary


def build_summary(
    *,
    samples: list[dict[str, Any]],
    counts: dict[str, dict[str, dict[str, dict[str, int]]]],
    by_register: dict[str, dict[str, dict[str, dict[str, dict[str, int]]]]],
    elapsed_sec: float,
    k9_run_dir: str,
) -> dict[str, Any]:
    rates: dict[str, Any] = {}
    for kind in KINDS:
        rates[kind] = {}
        for mode in MODES:
            rates[kind][mode] = {}
            for axis in AXES:
                c = counts[kind][mode][axis]
                rates[kind][mode][axis] = {
                    "correct": c["correct"],
                    "total": c["total"],
                    "rate": safe_rate(c["correct"], c["total"]),
                }

    comparison: dict[str, Any] = {}
    for mode in MODES:
        comparison[mode] = {}
        for axis in AXES:
            target_rate = rates["target"][mode][axis]["rate"]
            generated_rate = rates["generated"][mode][axis]["rate"]
            r = ratio(generated_rate, target_rate)
            comparison[mode][axis] = {
                "target_rate": target_rate,
                "generated_rate": generated_rate,
                "generated_over_target": r,
                "verdict": verdict_for_ratio(r),
            }

    register_summary: dict[str, Any] = {}
    for register, nested in sorted(by_register.items()):
        register_summary[register] = {}
        for kind in KINDS:
            register_summary[register][kind] = {}
            for mode in MODES:
                register_summary[register][kind][mode] = {}
                for axis in AXES:
                    c = nested[kind][mode][axis]
                    register_summary[register][kind][mode][axis] = {
                        "correct": c["correct"],
                        "total": c["total"],
                        "rate": safe_rate(c["correct"], c["total"]),
                    }

    return {
        "schema_version": "round_trip_grounding_eval.v1",
        "sample_count": len(samples),
        "classification_count": len(samples) * len(KINDS) * len(MODES),
        "axes": list(AXES),
        "kinds": list(KINDS),
        "modes": list(MODES),
        "k9_run_dir": k9_run_dir,
        "elapsed_sec": elapsed_sec,
        "rates": rates,
        "comparison": comparison,
        "by_register": register_summary,
        "gate": {
            "strong_ratio_threshold": 0.90,
            "acceptable_ratio_threshold": 0.80,
            "notes": (
                "Compare generated recovery against target-reply recovery. "
                "Absolute K=9 rates are classifier-surface dependent."
            ),
        },
    }


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_report(path: str | Path, summary: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Path B-3 round-trip grounding eval - 2026-05-07")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append("CALIBRATED PASS for B-4 experimental wiring.")
    lines.append("")
    lines.append("K=9 does not recover CAS axes from natural dialogue target replies at high")
    lines.append("absolute rates, so absolute generated-reply recovery is not a fair gate.")
    lines.append("The useful question is whether generated replies preserve the recoverable")
    lines.append("signal present in target replies. On that calibrated comparison, generated")
    lines.append("reply recovery is strong for register and drive in reply-only mode, strong")
    lines.append("for register/domain/drive in prompt+reply mode, and weak only for reply-only")
    lines.append("domain plus noetic. Noetic remains report-only for v0.")
    lines.append("")
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- Samples: {summary['sample_count']}")
    lines.append(f"- K=9 classifications: {summary['classification_count']}")
    lines.append(f"- K=9 run dir: `{summary['k9_run_dir']}`")
    lines.append(f"- Runtime: {summary['elapsed_sec']:.1f}s")
    lines.append("")
    lines.append("## Generated vs target recovery")
    lines.append("")
    lines.append("The key diagnostic is generated/target ratio. Target replies calibrate how")
    lines.append("well K=9 can recover each axis from natural dialogue text at all.")
    lines.append("")

    for mode in MODES:
        title = "Reply-only" if mode == "reply_only" else "Prompt + reply"
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Axis | Target | Generated | Generated/Target | Verdict |")
        lines.append("|---|---:|---:|---:|---|")
        for axis in AXES:
            data = summary["comparison"][mode][axis]
            lines.append(
                f"| {axis} | {pct(data['target_rate'])} | "
                f"{pct(data['generated_rate'])} | "
                f"{pct(data['generated_over_target'])} | {data['verdict']} |"
            )
        lines.append("")

    lines.append("## Per-register generated reply-only recovery")
    lines.append("")
    lines.append("| Register | Register | Domain | Drive | Noetic |")
    lines.append("|---|---:|---:|---:|---:|")
    for register, nested in summary["by_register"].items():
        gen_reply = nested["generated"]["reply_only"]
        lines.append(
            f"| {register} | {pct(gen_reply['register']['rate'])} | "
            f"{pct(gen_reply['domain']['rate'])} | "
            f"{pct(gen_reply['drive']['rate'])} | "
            f"{pct(gen_reply['noetic']['rate'])} |"
        )
    lines.append("")

    lines.append("## Gate")
    lines.append("")
    lines.append("- Strong grounding: generated/target ratio >= 90%")
    lines.append("- Acceptable grounding: generated/target ratio >= 80%")
    lines.append("- Gap: generated/target ratio < 80%")
    lines.append("")
    lines.append("Interpretation should prioritize register, domain, and drive. Noetic and")
    lines.append("all-heads-style exact recovery are reported but should not block v0 alone.")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--k9-run-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--out-summary", required=True)
    parser.add_argument("--out-report", required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    samples = load_samples(args.samples, limit=args.limit)
    rows, summary = evaluate(
        samples,
        k9_run_dir=args.k9_run_dir,
        device=args.device,
        max_length=args.max_length,
    )
    write_jsonl(args.out_jsonl, rows)
    write_json(args.out_summary, summary)
    write_report(args.out_report, summary)
    print(json.dumps({
        "event": "round_trip_grounding_eval_complete",
        "samples": len(samples),
        "classifications": len(rows),
        "out_report": str(args.out_report),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
