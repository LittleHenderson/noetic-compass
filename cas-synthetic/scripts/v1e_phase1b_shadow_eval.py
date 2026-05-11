"""v1e Phase 1B shadow-mode eval driver (Task #135).

Runs the 42-record eval suite
(``cas-synthetic/data/path_d/v1e_phase1b_eval_suite.jsonl``: 35
stratified fractals + 7 non-fractal negative controls) against the
archived v0 checkpoint under FIVE config combinations:

  - A: control       — apply_fractal_decoder=False (= v0 baseline)
  - B: smoke         — apply_fractal_decoder=True, no levers
  - C: eos_bias_only — apply_fractal_decoder=True, fractal_decoder_eos_bias=3.0
  - D: first_n_only  — apply_fractal_decoder=True, fractal_decoder_first_n_mode=True
  - E: both          — apply_fractal_decoder=True, eos_bias=3.0 + first_n_mode=True

Per the user's promotion gate (2026-05-10):
  - Exact k-sequence improves materially on fractal suite (B/C/D/E vs A).
  - Record 14 ``Φ<3:7>`` (low-k canonical) does not lose prose quality.
  - No non-fractal drift (B/C/D/E byte-match A on the 7 negatives).
  - v0 canary stays PASS (run separately via v0_canary.py --check).
  - No hard notation / jargon / truncation regression vs A.

Outputs (under ``cas-synthetic/data/path_d/``):
  - ``v1e_phase1b_shadow_eval_<timestamp>.jsonl`` — per-record per-config
    raw results with full fractal_decoder_log + verifier
  - ``v1e_phase1b_shadow_eval_<timestamp>_summary.md`` — promotion-gate
    analysis: aggregate counters per config, sequence_match flips,
    fail-closed selection rates, non-fractal drift report, record-14
    delta, regression watch table

Determinism: greedy decoding + fixed checkpoint = byte-identical
output across runs on the same machine. The eval is re-runnable.
"""
from __future__ import annotations

import json
import os
import sys
import types
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
DATA_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"
SUITE_PATH = DATA_DIR / "v1e_phase1b_eval_suite.jsonl"

# Archived v0 checkpoint (per V0_RELEASE_CANDIDATE.md §2).
ARCHIVE_DIR = Path(r"D:\tksCAS-archive\v0_rc1\v1c_VALIDTOK_5ep")

# Bootstrap cas_native importable from scaffold root.
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules.setdefault("cas_native", pkg)
sys.path.insert(0, str(SCAFFOLD_ROOT))

import torch  # noqa: E402
from cas_native.inference.routed_generate import routed_generate  # noqa: E402
from cas_native.model.cas_native_model import (  # noqa: E402
    CASNativeConfig, CASNativeModel,
)
from cas_native.model.nl_generation_head import (  # noqa: E402
    NLGenerationHead, NLGenerationHeadConfig,
)
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402


# v0 flag profile (matches V0_RELEASE_CANDIDATE.md §3). The shadow eval
# always uses these v0 defaults; the four constrained configs only
# toggle ``apply_fractal_decoder`` + lever kwargs.
V0_FLAGS = {
    "use_v1c_task_tokens": True,
    "use_v1c_rpm_seed": True,
    "use_v1c_rpm_retry": False,
}

# Selected EOS bias strength. Conservative starting point — strong
# enough to materially raise EOS log-prob over the typical post-slot
# prose token (greedy decoder) but not so high that the model
# truncates on a single slot.
EOS_BIAS_STRENGTH = 3.0


CONFIGS = [
    {
        "id": "A_control",
        "label": "control (apply_fractal_decoder=False)",
        "kwargs": dict(apply_fractal_decoder=False),
    },
    {
        "id": "B_smoke",
        "label": "smoke (decoder on, no levers)",
        "kwargs": dict(apply_fractal_decoder=True),
    },
    {
        "id": "C_eos_bias",
        "label": f"eos_bias_only (eos_bias={EOS_BIAS_STRENGTH})",
        "kwargs": dict(
            apply_fractal_decoder=True,
            fractal_decoder_eos_bias=EOS_BIAS_STRENGTH,
        ),
    },
    {
        "id": "D_first_n",
        "label": "first_n_only (first_n_mode=True)",
        "kwargs": dict(
            apply_fractal_decoder=True,
            fractal_decoder_first_n_mode=True,
        ),
    },
    {
        "id": "E_both",
        "label": f"both (eos_bias={EOS_BIAS_STRENGTH} + first_n_mode=True)",
        "kwargs": dict(
            apply_fractal_decoder=True,
            fractal_decoder_eos_bias=EOS_BIAS_STRENGTH,
            fractal_decoder_first_n_mode=True,
        ),
    },
]


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_checkpoint():
    """Load v1c_VALIDTOK_5ep — same as v1_eval_pack_24records.py."""
    print(f"loading checkpoint from {ARCHIVE_DIR}")
    tokenizer = HybridCASTokenizer.load(ARCHIVE_DIR / "tokenizer.json")
    bpe = ARCHIVE_DIR / "english_bpe.json"
    if bpe.exists():
        tokenizer = tokenizer.with_english_bpe(bpe)
    # v1c VALIDTOK task tokens.
    from cas_native.training.tokenizer_task_tokens import extend_with_task_tokens
    tokenizer = extend_with_task_tokens(tokenizer)
    vocab_size = int(tokenizer.vocab_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  device={device}, vocab_size={vocab_size}")
    enc_cfg = CASNativeConfig(
        d_model=512, n_layers=6, n_heads=8, vocab_size=vocab_size,
    )
    model = CASNativeModel(enc_cfg).to(device)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=vocab_size, d_model=512, n_heads=8, n_layers=6,
    )
    head = NLGenerationHead(head_cfg).to(device)
    model.attach_nl_gen_head(head)
    state = torch.load(
        ARCHIVE_DIR / "model_final.pt", map_location=device, weights_only=False,
    )
    model.load_state_dict(state["model"])
    model.eval()
    return model, tokenizer, device


def load_suite() -> list[dict]:
    rows: list[dict] = []
    with SUITE_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def run_one(
    *, model: Any, tokenizer: Any, device: Any, record: dict, config: dict,
) -> dict:
    """Run ``routed_generate`` once for a (record, config). Returns a
    JSONL-serializable dict."""
    cas = record["cas_expression"]
    with torch.no_grad():
        r = routed_generate(
            model=model, tokenizer=tokenizer,
            source_cas=cas,
            register="T",
            apply_repair=True,
            sampling="greedy",
            use_cas_prefix=True,
            device=device,
            prepend_task_token=V0_FLAGS["use_v1c_task_tokens"],
            seed_rpm_silhouette=V0_FLAGS["use_v1c_rpm_seed"],
            apply_rpm_retry=V0_FLAGS["use_v1c_rpm_retry"],
            **config["kwargs"],
        )
    pp = r.postprocess_result
    return {
        "record_id": record["record_id"],
        "config_id": config["id"],
        "category": record["category"],
        "subcategory": record["subcategory"],
        "cas_expression": cas,
        "expected_k_values": record.get("expected_k_values"),
        "final_text": r.final_text,
        "raw_text": r.raw_text,
        "task_routed": r.task_type,
        "compiled": r.routing.compiled,
        "truncated": r.truncated,
        "quality_passed": pp.quality_passed,
        "quality_failures": pp.quality_failures,
        "hard_notation_count": pp.hard_notation_count,
        "jargon_count": pp.jargon_count,
        "n_steps": r.generation_metadata.get("n_steps"),
        "rpm_seed_fired": r.seed_decoder_text is not None,
        "fractal_repair_log": (
            pp.fractal_repair_log.to_dict()
            if pp.fractal_repair_log is not None else None
        ),
        "fractal_decoder_log": (
            r.fractal_decoder_log.to_dict()
            if r.fractal_decoder_log is not None else None
        ),
    }


def summarize(rows: list[dict], suite: list[dict]) -> str:
    """Build the promotion-gate analysis markdown."""
    by_config_record: dict[tuple[str, str], dict] = {
        (r["config_id"], r["record_id"]): r for r in rows
    }
    fractal_ids = [r["record_id"] for r in suite if r["category"] == "fractal"]
    negative_ids = [r["record_id"] for r in suite if r["category"] == "negative"]
    control_id = "A_control"

    out: list[str] = []
    out.append(f"# v1e Phase 1B Shadow Eval — Promotion-Gate Analysis")
    out.append("")
    out.append(f"- suite size: {len(suite)} records ({len(fractal_ids)} fractal + {len(negative_ids)} negative)")
    out.append(f"- configs: {[c['id'] for c in CONFIGS]}")
    out.append("")
    out.append(f"Per-config aggregate (over the {len(fractal_ids)} fractal records):")
    out.append("")
    out.append("| config | sequence_match | cardinality_match | constrained_selected | hard_notation | jargon | truncated |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")

    summary_per_config: dict[str, dict] = {}
    for cfg in CONFIGS:
        cid = cfg["id"]
        seq = card = sel = hard_n = jarg = trunc = 0
        for rid in fractal_ids:
            r = by_config_record.get((cid, rid))
            if r is None:
                continue
            fr = r.get("fractal_repair_log") or {}
            fd = r.get("fractal_decoder_log") or {}
            if fr.get("sequence_matches"):
                seq += 1
            if fr.get("cardinality_matches"):
                card += 1
            if fd.get("selected") == "constrained":
                sel += 1
            if r.get("hard_notation_count", 0) > 0:
                hard_n += 1
            if r.get("jargon_count", 0) > 0:
                jarg += 1
            if r.get("truncated"):
                trunc += 1
        summary_per_config[cid] = dict(
            seq=seq, card=card, sel=sel,
            hard_n=hard_n, jarg=jarg, trunc=trunc,
        )
        out.append(
            f"| {cid} | {seq}/{len(fractal_ids)} | "
            f"{card}/{len(fractal_ids)} | {sel}/{len(fractal_ids)} | "
            f"{hard_n} | {jarg} | {trunc} |"
        )

    out.append("")
    out.append("## Non-fractal drift (negative controls — must byte-match A)")
    out.append("")
    out.append("| record_id | subcategory | B_smoke=A? | C_eos=A? | D_firstn=A? | E_both=A? |")
    out.append("|---|---|---|---|---|---|")
    neg_drift_count_per_cfg: dict[str, int] = defaultdict(int)
    for rid in negative_ids:
        a = by_config_record.get(("A_control", rid))
        if a is None:
            continue
        a_text = a.get("final_text", "")
        cells = []
        for cfg in CONFIGS[1:]:
            other = by_config_record.get((cfg["id"], rid))
            other_text = other.get("final_text", "") if other else None
            match = (other_text == a_text)
            cells.append("✓" if match else "✗ DRIFT")
            if not match:
                neg_drift_count_per_cfg[cfg["id"]] += 1
        subcat = a.get("subcategory", "?")
        out.append(f"| {rid} | {subcat} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} |")
    out.append("")

    out.append("## Record 14 prose-quality watch (k=2 `Φ<3:7>`)")
    out.append("")
    out.append("Per the audit: 'Record 14 does not lose prose quality.' "
               "Below is the final_text + verifier for Record 14 under each config.")
    out.append("")
    # The k=2 diverse record with k_values (3,7) is the Record-14 analog.
    record14_id = next(
        (r["record_id"] for r in suite
         if r["category"] == "fractal"
         and r["subcategory"] == "diverse"
         and r["expected_k_values"] == [3, 7]),
        None,
    )
    if record14_id:
        for cfg in CONFIGS:
            r = by_config_record.get((cfg["id"], record14_id))
            if r is None:
                continue
            fr = r.get("fractal_repair_log") or {}
            out.append(
                f"- **{cfg['id']}**: "
                f"seq_match={fr.get('sequence_matches')} "
                f"found={fr.get('found_k_sequence')} "
                f"text={r.get('final_text', '')[:140]!r}"
            )
    else:
        out.append("- record-14 analog not found in suite")
    out.append("")

    out.append("## Lever-individual safety (each lever vs B_smoke)")
    out.append("")
    b = summary_per_config["B_smoke"]
    for cid in ("C_eos_bias", "D_first_n", "E_both"):
        s = summary_per_config[cid]
        seq_delta = s["seq"] - b["seq"]
        card_delta = s["card"] - b["card"]
        sel_delta = s["sel"] - b["sel"]
        hard_delta = s["hard_n"] - b["hard_n"]
        jarg_delta = s["jarg"] - b["jarg"]
        trunc_delta = s["trunc"] - b["trunc"]
        out.append(
            f"- **{cid}** vs B_smoke: "
            f"seq Δ={seq_delta:+d}, card Δ={card_delta:+d}, "
            f"selected_constrained Δ={sel_delta:+d}, "
            f"hard_notation Δ={hard_delta:+d}, jargon Δ={jarg_delta:+d}, "
            f"truncated Δ={trunc_delta:+d}"
        )
    out.append("")

    out.append("## Promotion-gate verdict")
    out.append("")
    a_summary = summary_per_config["A_control"]
    promote_checks = []
    for cid in ("B_smoke", "C_eos_bias", "D_first_n", "E_both"):
        s = summary_per_config[cid]
        seq_lift = s["seq"] - a_summary["seq"]
        non_fractal_drift = neg_drift_count_per_cfg.get(cid, 0)
        hard_n_regress = s["hard_n"] - a_summary["hard_n"]
        jarg_regress = s["jarg"] - a_summary["jarg"]
        trunc_regress = s["trunc"] - a_summary["trunc"]
        notes = []
        if seq_lift > 0:
            notes.append(f"+{seq_lift} sequence_match lift")
        elif seq_lift < 0:
            notes.append(f"{seq_lift} sequence_match REGRESSION")
        else:
            notes.append("0 sequence_match delta")
        if non_fractal_drift > 0:
            notes.append(f"⚠ {non_fractal_drift} negative drift")
        if hard_n_regress > 0:
            notes.append(f"⚠ +{hard_n_regress} hard_notation regression")
        if jarg_regress > 0:
            notes.append(f"⚠ +{jarg_regress} jargon regression")
        if trunc_regress > 0:
            notes.append(f"⚠ +{trunc_regress} truncation regression")
        verdict = (
            "PASS" if seq_lift > 0
            and non_fractal_drift == 0
            and hard_n_regress <= 0
            and jarg_regress <= 0
            and trunc_regress <= 0
            else "REVIEW"
        )
        promote_checks.append((cid, verdict, ", ".join(notes)))
    out.append("| config | verdict | notes |")
    out.append("|---|---|---|")
    for cid, verdict, notes in promote_checks:
        out.append(f"| {cid} | {verdict} | {notes} |")
    out.append("")
    out.append("**Note:** \"PASS\" is a HEURISTIC label, not a hard promotion gate. "
               "Per audit 2026-05-10, α/β/γ paths surface to user with empirical "
               "data; promotion is a USER decision.")
    return "\n".join(out)


def main() -> int:
    timestamp = _utc_now_compact()
    print(f"v1e Phase 1B shadow eval — {timestamp}")
    print()
    if not SUITE_PATH.exists():
        print(f"[error] suite not found: {SUITE_PATH}", file=sys.stderr)
        print("  Run build_fractal_eval_suite.py first.", file=sys.stderr)
        return 2
    if not ARCHIVE_DIR.exists():
        print(f"[error] archive not found: {ARCHIVE_DIR}", file=sys.stderr)
        return 2

    suite = load_suite()
    print(f"loaded suite: {len(suite)} records "
          f"({sum(1 for r in suite if r['category']=='fractal')} fractal, "
          f"{sum(1 for r in suite if r['category']=='negative')} negative)")
    model, tokenizer, device = load_checkpoint()
    print()

    rows: list[dict] = []
    for cfg_idx, config in enumerate(CONFIGS, start=1):
        print(f"=== config {cfg_idx}/{len(CONFIGS)}: {config['id']} ({config['label']}) ===")
        for i, record in enumerate(suite, start=1):
            cas_preview = record["cas_expression"][:50]
            print(f"  [{i:>2}/{len(suite)}] {record['category']}/{record['subcategory']:<24}  {cas_preview}")
            try:
                row = run_one(
                    model=model, tokenizer=tokenizer, device=device,
                    record=record, config=config,
                )
                rows.append(row)
            except Exception as e:
                print(f"    [error] {type(e).__name__}: {e}")
                rows.append({
                    "record_id": record["record_id"],
                    "config_id": config["id"],
                    "category": record["category"],
                    "subcategory": record["subcategory"],
                    "cas_expression": record["cas_expression"],
                    "error": f"{type(e).__name__}: {e}",
                })
        print()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_path = DATA_DIR / f"v1e_phase1b_shadow_eval_{timestamp}.jsonl"
    md_path = DATA_DIR / f"v1e_phase1b_shadow_eval_{timestamp}_summary.md"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_md = summarize(rows, suite)
    with md_path.open("w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"\nwrote {jsonl_path}")
    print(f"wrote {md_path}\n")
    print("=" * 72)
    print(summary_md.split("## Promotion-gate verdict", 1)[1] if "## Promotion-gate verdict" in summary_md else summary_md[-2000:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
