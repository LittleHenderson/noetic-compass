#!/usr/bin/env python3
"""Demographic-robustness evaluation gate for CAS-Native (Task #69).

Loads a structured-token-prediction checkpoint, runs the held-out eval set
stratified across demographic profiles + tonal registers (produced by Task
#68's expansion script), computes per-stratum ``all_heads_exact`` rate,
compares each stratum to the population mean, and FAILS the build (exit 1)
if any stratum is more than ``tolerance_pp`` percentage points below the mean.

Exit codes
----------
* ``0`` — gate PASSED (all strata within tolerance, or no gateable strata).
* ``1`` — gate FAILED (one or more strata out of tolerance).

Stratification
--------------
* By ``demographic_profile`` only (e.g., P1..P8): all records with that profile.
* By ``tonal_register`` only (e.g., T1..T5): all records with that tone.
* Jointly by ``(profile, tone)``: requires both fields present on the record.

Strata with ``n < MIN_GATE_N`` (default 5) are reported but excluded from the
gate verdict (insufficient sample size for a stable rate).

Spec coupling
-------------
This module imports profile/tone identifiers from
``cas_synthetic.generator.demographic_tonal_axes`` (Task #68). If that module
has not landed yet, this gate falls back to a hardcoded ID-only stub
(``_FALLBACK_PROFILE_IDS`` / ``_FALLBACK_TONE_IDS``) and emits a warning. The
fallback IDs match the task spec exactly: P1..P8, T1..T5.

CLI
---
    python -m cas_native.evaluation.demographic_robustness_eval \\
        --checkpoint runs/<run>/best_structured_token_model.pt \\
        --eval-input <eval>.jsonl \\
        --tolerance-pp 10 \\
        --out-json runs/<run>/demographic_robustness_report.json \\
        --out-markdown runs/<run>/demographic_robustness_report.md \\
        --device cuda
"""

from __future__ import annotations

import argparse
import json
import sys
import types
import warnings
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

# UTF-8 stdout/stderr for Windows shells when run as a script.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, OSError):
    pass

# Make the cas_native package importable when invoked as a script.
_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if "cas_native" not in sys.modules:
    _package = types.ModuleType("cas_native")
    _package.__file__ = str(_CAS_NATIVE_ROOT / "__init__.py")
    _package.__path__ = [str(_CAS_NATIVE_ROOT)]
    sys.modules["cas_native"] = _package


# ---------------------------------------------------------------------------
# Task #68 spec coupling — profile/tone identifiers
# ---------------------------------------------------------------------------
# When Task #68 lands, this import resolves to the canonical profile + tone
# definitions. Until then, the stub IDs below are used. Either path produces
# the same gate behavior because the gate only stratifies by ID strings.

_FALLBACK_PROFILE_IDS: tuple[str, ...] = (
    "P1",  # young_professional_technical
    "P2",  # senior_academic_humanities
    "P3",  # mid_career_clinician_direct
    "P4",  # global_english_indirect
    "P5",  # lay_casual
    "P6",  # skeptical_analyst
    "P7",  # anxious_first_timer
    "P8",  # confident_veteran
)
_FALLBACK_TONE_IDS: tuple[str, ...] = (
    "T1",  # neutral
    "T2",  # anxious
    "T3",  # frustrated
    "T4",  # excited
    "T5",  # reflective
)
_FALLBACK_PROFILE_LABELS: dict[str, str] = {
    "P1": "young_professional_technical",
    "P2": "senior_academic_humanities",
    "P3": "mid_career_clinician_direct",
    "P4": "global_english_indirect",
    "P5": "lay_casual",
    "P6": "skeptical_analyst",
    "P7": "anxious_first_timer",
    "P8": "confident_veteran",
}
_FALLBACK_TONE_LABELS: dict[str, str] = {
    "T1": "neutral",
    "T2": "anxious",
    "T3": "frustrated",
    "T4": "excited",
    "T5": "reflective",
}

try:
    from cas_synthetic.generator.demographic_tonal_axes import (  # type: ignore
        PROFILES,
        TONES,
    )

    PROFILE_IDS: tuple[str, ...] = tuple(getattr(p, "id", str(p)) for p in PROFILES)
    TONE_IDS: tuple[str, ...] = tuple(getattr(t, "id", str(t)) for t in TONES)
    PROFILE_LABELS: dict[str, str] = {
        getattr(p, "id", str(p)): getattr(p, "label", getattr(p, "id", str(p)))
        for p in PROFILES
    }
    TONE_LABELS: dict[str, str] = {
        getattr(t, "id", str(t)): getattr(t, "label", getattr(t, "id", str(t)))
        for t in TONES
    }
    _TASK_68_AVAILABLE = True
except Exception:  # pragma: no cover - covered by stub path during dev
    PROFILE_IDS = _FALLBACK_PROFILE_IDS
    TONE_IDS = _FALLBACK_TONE_IDS
    PROFILE_LABELS = dict(_FALLBACK_PROFILE_LABELS)
    TONE_LABELS = dict(_FALLBACK_TONE_LABELS)
    _TASK_68_AVAILABLE = False


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

MIN_GATE_N: int = 5
"""Minimum stratum size to participate in the gate verdict.

Strata with ``n < MIN_GATE_N`` are reported with a ``low_n=True`` flag but
do not cause the gate to fail. This is to avoid noisy false positives on
small strata.
"""


@dataclass(frozen=True)
class StratumResult:
    """Per-stratum eval rollup."""

    profile: str | None  # "P1".."P8" or None for tone-only stratification
    tone: str | None  # "T1".."T5" or None for profile-only
    n: int
    all_heads_exact: int
    rate: float
    delta_vs_population_pp: float
    low_n: bool = False

    @property
    def stratum_label(self) -> str:
        if self.profile is not None and self.tone is not None:
            return f"{self.profile}_{self.tone}"
        if self.profile is not None:
            return self.profile
        if self.tone is not None:
            return self.tone
        return "<unknown>"


@dataclass(frozen=True)
class GateVerdict:
    """Top-level verdict returned to CI."""

    passed: bool
    population_mean_rate: float
    population_n: int
    profile_results: list[StratumResult]
    tone_results: list[StratumResult]
    joint_results: list[StratumResult]
    failing_strata: list[StratumResult]
    tolerance_pp: float
    task_68_available: bool = field(default=_TASK_68_AVAILABLE)

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize verdict to a JSON-safe dict."""
        return {
            "passed": self.passed,
            "population_mean_rate": self.population_mean_rate,
            "population_n": self.population_n,
            "tolerance_pp": self.tolerance_pp,
            "task_68_available": self.task_68_available,
            "min_gate_n": MIN_GATE_N,
            "profile_results": [_stratum_to_dict(s) for s in self.profile_results],
            "tone_results": [_stratum_to_dict(s) for s in self.tone_results],
            "joint_results": [_stratum_to_dict(s) for s in self.joint_results],
            "failing_strata": [_stratum_to_dict(s) for s in self.failing_strata],
        }


def _stratum_to_dict(s: StratumResult) -> dict[str, Any]:
    out = asdict(s)
    out["stratum_label"] = s.stratum_label
    return out


# ---------------------------------------------------------------------------
# Core stratification + gate logic (predictor-agnostic)
# ---------------------------------------------------------------------------

PredictionFn = Callable[[Mapping[str, Any]], dict[str, Any]]
"""A prediction function takes one eval record and returns a dict with at
least ``all_heads_exact: bool`` and optionally ``head_correct``,
``prediction``, ``target`` keys (mirroring ``_eval_manifest_from_outputs``)."""


def stratify_and_gate(
    records: Sequence[Mapping[str, Any]],
    predictor: PredictionFn,
    *,
    tolerance_pp: float = 10.0,
) -> GateVerdict:
    """Run the predictor over each record, stratify, and compute the gate.

    This is the pure logic core. It does not load checkpoints or touch
    PyTorch. Tests inject a mock ``predictor`` to validate behavior without
    requiring a real model.
    """

    if tolerance_pp < 0:
        raise ValueError(f"tolerance_pp must be >= 0, got {tolerance_pp}")

    population_correct = 0
    population_n = 0
    by_profile: dict[str, list[bool]] = defaultdict(list)
    by_tone: dict[str, list[bool]] = defaultdict(list)
    by_joint: dict[tuple[str, str], list[bool]] = defaultdict(list)

    for record in records:
        prediction = predictor(record)
        exact = bool(prediction.get("all_heads_exact", False))
        population_correct += int(exact)
        population_n += 1

        profile = record.get("demographic_profile")
        tone = record.get("tonal_register")

        if isinstance(profile, str) and profile:
            by_profile[profile].append(exact)
        if isinstance(tone, str) and tone:
            by_tone[tone].append(exact)
        if isinstance(profile, str) and profile and isinstance(tone, str) and tone:
            by_joint[(profile, tone)].append(exact)

    population_rate = (
        (population_correct / population_n) if population_n > 0 else 0.0
    )

    profile_results = [
        _stratum_from_outcomes(
            outcomes=by_profile[p],
            profile=p,
            tone=None,
            population_rate=population_rate,
        )
        for p in sorted(by_profile.keys())
    ]
    tone_results = [
        _stratum_from_outcomes(
            outcomes=by_tone[t],
            profile=None,
            tone=t,
            population_rate=population_rate,
        )
        for t in sorted(by_tone.keys())
    ]
    joint_results = [
        _stratum_from_outcomes(
            outcomes=by_joint[(p, t)],
            profile=p,
            tone=t,
            population_rate=population_rate,
        )
        for (p, t) in sorted(by_joint.keys())
    ]

    failing = _collect_failing(
        profile_results=profile_results,
        tone_results=tone_results,
        joint_results=joint_results,
        tolerance_pp=tolerance_pp,
    )

    return GateVerdict(
        passed=not failing,
        population_mean_rate=population_rate,
        population_n=population_n,
        profile_results=profile_results,
        tone_results=tone_results,
        joint_results=joint_results,
        failing_strata=failing,
        tolerance_pp=tolerance_pp,
    )


def _stratum_from_outcomes(
    *,
    outcomes: Sequence[bool],
    profile: str | None,
    tone: str | None,
    population_rate: float,
) -> StratumResult:
    n = len(outcomes)
    correct = sum(1 for o in outcomes if o)
    rate = (correct / n) if n > 0 else 0.0
    delta_pp = (rate - population_rate) * 100.0
    return StratumResult(
        profile=profile,
        tone=tone,
        n=n,
        all_heads_exact=correct,
        rate=rate,
        delta_vs_population_pp=delta_pp,
        low_n=(n < MIN_GATE_N),
    )


def _collect_failing(
    *,
    profile_results: Sequence[StratumResult],
    tone_results: Sequence[StratumResult],
    joint_results: Sequence[StratumResult],
    tolerance_pp: float,
) -> list[StratumResult]:
    """A stratum fails iff it is below the population mean by more than
    ``tolerance_pp`` AND has ``n >= MIN_GATE_N``."""

    out: list[StratumResult] = []
    for stratum in (
        list(profile_results) + list(tone_results) + list(joint_results)
    ):
        if stratum.low_n:
            continue
        if stratum.delta_vs_population_pp < -float(tolerance_pp):
            out.append(stratum)
    out.sort(key=lambda s: s.delta_vs_population_pp)
    return out


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_verdict_markdown(verdict: GateVerdict) -> str:
    """Render a human-readable Markdown report for the gate verdict."""

    verdict_label = "PASS" if verdict.passed else "FAIL"
    pop_pct = 100.0 * verdict.population_mean_rate

    lines: list[str] = []
    lines.append("# Demographic Robustness Eval — Gate Report")
    lines.append("")
    lines.append(f"**Verdict:** `{verdict_label}`  ")
    lines.append(f"**Population mean rate:** {pop_pct:.2f}% (n = {verdict.population_n})  ")
    lines.append(f"**Tolerance:** {verdict.tolerance_pp:.1f} pp below population mean  ")
    lines.append(f"**Min gate n:** {MIN_GATE_N}  ")
    lines.append(
        f"**Task #68 module available:** "
        f"{'yes' if verdict.task_68_available else 'no (using fallback IDs)'}  "
    )
    lines.append("")

    lines.append("## Failing Strata")
    lines.append("")
    if verdict.failing_strata:
        lines.append("| Stratum | n | rate | Δ vs population (pp) |")
        lines.append("|---|---:|---:|---:|")
        for s in verdict.failing_strata:
            lines.append(
                f"| {s.stratum_label} | {s.n} | {100.0 * s.rate:.2f}% | "
                f"{s.delta_vs_population_pp:+.2f} |"
            )
    else:
        lines.append("_(none)_")
    lines.append("")

    lines.append("## Per-Profile Stratification")
    lines.append("")
    lines.append(_render_stratum_table(verdict.profile_results, axis="profile"))
    lines.append("")

    lines.append("## Per-Tone Stratification")
    lines.append("")
    lines.append(_render_stratum_table(verdict.tone_results, axis="tone"))
    lines.append("")

    lines.append("## Joint (Profile × Tone) Stratification")
    lines.append("")
    lines.append(_render_stratum_table(verdict.joint_results, axis="joint"))
    lines.append("")

    return "\n".join(lines)


def _render_stratum_table(
    strata: Sequence[StratumResult],
    *,
    axis: str,
) -> str:
    if not strata:
        return "_(no records carried this stratification axis)_"
    if axis == "joint":
        header = "| Profile | Tone | n | rate | Δ pp | low_n |"
    elif axis == "profile":
        header = "| Profile | label | n | rate | Δ pp | low_n |"
    else:
        header = "| Tone | label | n | rate | Δ pp | low_n |"

    rows = [header, "|---|---|---:|---:|---:|---|"]
    for s in strata:
        if axis == "joint":
            rows.append(
                f"| {s.profile} | {s.tone} | {s.n} | "
                f"{100.0 * s.rate:.2f}% | {s.delta_vs_population_pp:+.2f} | "
                f"{'yes' if s.low_n else 'no'} |"
            )
        elif axis == "profile":
            label = PROFILE_LABELS.get(s.profile or "", "")
            rows.append(
                f"| {s.profile} | {label} | {s.n} | "
                f"{100.0 * s.rate:.2f}% | {s.delta_vs_population_pp:+.2f} | "
                f"{'yes' if s.low_n else 'no'} |"
            )
        else:
            label = TONE_LABELS.get(s.tone or "", "")
            rows.append(
                f"| {s.tone} | {label} | {s.n} | "
                f"{100.0 * s.rate:.2f}% | {s.delta_vs_population_pp:+.2f} | "
                f"{'yes' if s.low_n else 'no'} |"
            )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Real model loading + record iteration
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"eval input not found: {path}")
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _build_real_predictor(
    *,
    checkpoint_path: Path,
    device: str,
) -> tuple[PredictionFn, dict[str, Any]]:
    """Construct a predictor closure that runs the trained model record-by-record.

    Mirrors the model construction from ``evaluate_structured_token_run.py``:
    embedding + structured-prediction head, with optional graph encoder /
    fusion when those modules exist (diagloop checkpoints). For checkpoints
    without graph state (K=9 baseline), the extra modules are skipped.
    """

    import torch  # local import keeps test path lightweight

    from cas_native.model.structured_prediction import StructuredPredictionHead
    from cas_native.model.structured_token_embedding import (
        StructuredTokenEmbedding,
        StructuredTokenStructuredPredictor,
    )
    from cas_native.tokenizer.vocabulary import StructuredTokenVocabulary
    from cas_native.training.structured_prediction_ingest import load_level3_jsonl
    from cas_native.training.train_structured_prediction import (
        evaluate_structured_token_prediction,
    )

    run_dir = checkpoint_path.parent
    manifest_path = run_dir / "manifest.json"
    cfg: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            cfg = dict(
                json.loads(manifest_path.read_text(encoding="utf-8")).get("config", {})
            )
        except Exception:
            cfg = {}

    d_model = int(cfg.get("d_model", 128))
    bottleneck_dim = int(cfg.get("bottleneck_dim", 64))
    max_length = int(cfg.get("max_length", 256))

    vocab_path = run_dir / "structured_token_vocab.json"
    if not vocab_path.exists():
        raise FileNotFoundError(
            f"structured-token vocabulary not found: {vocab_path}"
        )
    vocabulary = StructuredTokenVocabulary.load(vocab_path)
    embedding = StructuredTokenEmbedding(
        vocab_size=len(vocabulary), d_model=d_model
    )
    head = StructuredPredictionHead(d_model=d_model, bottleneck_dim=bottleneck_dim)

    # Defensive graph-encoder import — only available on diagloop branches.
    graph_components: dict[str, Any] = {}
    try:
        from cas_native.model.graph_encoder import (  # type: ignore
            EDGE_FEATURE_DIM,
            NODE_FEATURE_DIM,
            GraphEncoder,
        )
        from cas_native.model.graph_text_fusion import GraphTextFusion  # type: ignore

        graph_components = {
            "graph_encoder": GraphEncoder(
                NODE_FEATURE_DIM, EDGE_FEATURE_DIM, hidden_dim=64
            ),
            "graph_fusion": GraphTextFusion(d_text=d_model, d_graph=64),
        }
    except Exception:
        graph_components = {}

    if graph_components:
        try:
            model = StructuredTokenStructuredPredictor(
                embedding,
                head,
                graph_components["graph_encoder"],
                graph_components["graph_fusion"],
            )
        except TypeError:
            model = StructuredTokenStructuredPredictor(embedding, head)
    else:
        model = StructuredTokenStructuredPredictor(embedding, head)

    state = torch.load(checkpoint_path, map_location=device, weights_only=True)
    # Accept partial loads (e.g. graph keys missing on a baseline checkpoint).
    try:
        model.load_state_dict(state)
    except RuntimeError:
        model.load_state_dict(state, strict=False)
    model.to(torch.device(device))
    model.eval()

    def _predict_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records:
            return []
        manifest = evaluate_structured_token_prediction(
            model,
            records,
            vocabulary,
            device=device,
            batch_size=min(64, len(records)),
            max_length=max_length,
        )
        return list(manifest.get("samples", []))

    # Shape per-record predictor by deferring to a one-shot batch internally.
    state_box: dict[str, list[dict[str, Any]]] = {"pending": [], "cached": []}

    def predictor(record: Mapping[str, Any]) -> dict[str, Any]:
        # Collect-then-flush is not used here because the public surface is
        # per-record. We run a singleton batch per call. Acceptable for CI
        # gate cost (single CPU-friendly evaluation pass over a curated
        # demographic eval), and keeps the predictor signature clean.
        samples = _predict_batch([dict(record)])
        if not samples:
            return {"all_heads_exact": False}
        return samples[0]

    info = {
        "d_model": d_model,
        "bottleneck_dim": bottleneck_dim,
        "max_length": max_length,
        "vocab_size": len(vocabulary),
        "graph_components_loaded": bool(graph_components),
        "checkpoint": str(checkpoint_path),
        "run_dir": str(run_dir),
    }
    return predictor, info


def run_demographic_robustness_eval(
    checkpoint_path: Path,
    eval_jsonl: Path,
    *,
    tolerance_pp: float = 10.0,
    device: str = "cpu",
) -> GateVerdict:
    """End-to-end gate: load checkpoint, run eval, compute verdict.

    Use ``stratify_and_gate`` directly with a mock predictor for unit tests.
    """

    if not _TASK_68_AVAILABLE:
        warnings.warn(
            "cas_synthetic.generator.demographic_tonal_axes (Task #68) not "
            "available; using fallback profile/tone IDs. Eval gate will only "
            "run end-to-end after Task #68 lands.",
            stacklevel=2,
        )

    records = _load_jsonl(eval_jsonl)
    if not records:
        raise ValueError(f"no eval records found in {eval_jsonl}")

    predictor, _info = _build_real_predictor(
        checkpoint_path=checkpoint_path, device=device
    )

    return stratify_and_gate(
        records=records,
        predictor=predictor,
        tolerance_pp=tolerance_pp,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Demographic-robustness eval gate for CAS-Native (Task #69)."
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        required=True,
        help="Path to best_structured_token_model.pt (run dir is its parent).",
    )
    parser.add_argument(
        "--eval-input",
        type=Path,
        required=True,
        help="JSONL eval set with demographic_profile + tonal_register fields.",
    )
    parser.add_argument(
        "--tolerance-pp",
        type=float,
        default=10.0,
        help="Maximum allowed gap below population mean in percentage points.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Write the JSON gate report to this path.",
    )
    parser.add_argument(
        "--out-markdown",
        type=Path,
        default=None,
        help="Write the Markdown gate report to this path.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device for inference (cpu / cuda).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    verdict = run_demographic_robustness_eval(
        checkpoint_path=args.checkpoint,
        eval_jsonl=args.eval_input,
        tolerance_pp=args.tolerance_pp,
        device=args.device,
    )

    json_dict = verdict.to_json_dict()
    if args.out_json is not None:
        _write_json(args.out_json, json_dict)
    if args.out_markdown is not None:
        _write_text(args.out_markdown, render_verdict_markdown(verdict))

    # Stdout summary for CI logs.
    summary = {
        "passed": verdict.passed,
        "population_mean_rate": verdict.population_mean_rate,
        "population_n": verdict.population_n,
        "tolerance_pp": verdict.tolerance_pp,
        "n_failing_strata": len(verdict.failing_strata),
        "failing_strata": [s.stratum_label for s in verdict.failing_strata],
        "task_68_available": verdict.task_68_available,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    return 0 if verdict.passed else 1


__all__ = [
    "GateVerdict",
    "MIN_GATE_N",
    "PROFILE_IDS",
    "PROFILE_LABELS",
    "PredictionFn",
    "StratumResult",
    "TONE_IDS",
    "TONE_LABELS",
    "main",
    "render_verdict_markdown",
    "run_demographic_robustness_eval",
    "stratify_and_gate",
]


if __name__ == "__main__":
    raise SystemExit(main())
