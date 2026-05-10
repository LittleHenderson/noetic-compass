"""rpm_chain decoder-seeding diagnostic patch (Option A).

Per the user's call (2026-05-09): treat decoder-seeding as a diagnostic
that answers one question, not as the final architecture.

  > If we force the valid RPM answer to start as a valid RPM
  > explanation, can the model continue correctly?

  - If yes: model has the RPM content somewhere; the opening/silhouette
    is collapsing into the invalid path. Task-control is the issue.
    Schedule Option C (retrain with [VALID]/[INVALID] task tokens).
  - If no: model does not actually know how to fill valid RPM chains
    reliably. Need training data / task tokens, not just decoder seeding.

This script reruns ONLY the 3 rpm_chain records from the v1 PREFIX128
5ep 24-record audit (records 19, 20, 21 in the grading template) with
``seed_rpm_silhouette=True``, and emits a side-by-side diagnostic
report: prior unseeded gen, new seeded gen, target reply.

Grading is the human's job. This script never grades its own output.
"""
from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD_ROOT = REPO_ROOT / "noetic-compass-scaffold" / "noetic-compass"
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(SCAFFOLD_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(SCAFFOLD_ROOT))

import torch
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.nl_generation_head import (
    NLGenerationHead,
    NLGenerationHeadConfig,
)
from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.inference.routed_generate import routed_generate


CHECKPOINT_DIR = Path(
    r"D:\tksCAS-archive\runpod_runs\2026-05-09_session_61_v1_milestone"
    r"\runs\v1_path_d_PREFIX128_5ep_20260509T035024Z"
)
PRIOR_EVAL_PATH = REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "v1_eval_pack_24records_20260509T174012Z.jsonl"
OUT_DIR = REPO_ROOT / "cas-synthetic" / "data" / "path_d"


def _utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_checkpoint():
    print(f"loading checkpoint from {CHECKPOINT_DIR}")
    tokenizer = HybridCASTokenizer.load(CHECKPOINT_DIR / "tokenizer.json")
    bpe = CHECKPOINT_DIR / "english_bpe.json"
    if bpe.exists():
        tokenizer = tokenizer.with_english_bpe(bpe)
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
        CHECKPOINT_DIR / "model_final.pt",
        map_location=device,
        weights_only=False,
    )
    model.load_state_dict(state["model"])
    model.eval()
    return model, tokenizer, device


def main() -> int:
    timestamp = _utc_compact()
    print(f"v1 rpm_chain decoder-seeding diagnostic — {timestamp}")
    print()

    # Load the prior eval's records to reuse the same CAS expressions
    # and target replies. Filtering to rpm_chain only.
    prior_records: list[dict] = []
    with PRIOR_EVAL_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line.strip())
            if r["grammar_category"] == "rpm_chain":
                prior_records.append(r)
    print(f"loaded {len(prior_records)} rpm_chain records from prior eval")
    if not prior_records:
        print("  ERROR: no rpm_chain records found in prior eval")
        return 1

    model, tokenizer, device = load_checkpoint()
    print()

    # Rerun each record TWICE: with seeding off (control) and on
    # (treatment). Greedy decoding for both = deterministic.
    results: list[dict] = []
    for i, prior in enumerate(prior_records, start=1):
        cas = prior["cas_expression"]
        print(f"  [{i}/{len(prior_records)}] {prior['record_id']}")

        with torch.no_grad():
            unseeded = routed_generate(
                model=model, tokenizer=tokenizer,
                source_cas=cas, register="T",
                apply_repair=True, sampling="greedy",
                use_cas_prefix=True, device=device,
                seed_rpm_silhouette=False,
            )
            seeded = routed_generate(
                model=model, tokenizer=tokenizer,
                source_cas=cas, register="T",
                apply_repair=True, sampling="greedy",
                use_cas_prefix=True, device=device,
                seed_rpm_silhouette=True,
            )

        results.append({
            "record_id": prior["record_id"],
            "cas_expression": cas,
            "target": prior["target"],
            "prior_unseeded_gen": prior["final_text"],
            "control_gen_no_seed": unseeded.final_text,
            "treatment_gen_with_seed": seeded.final_text,
            "seed_decoder_text": seeded.seed_decoder_text,
            "control_n_steps": unseeded.generation_metadata.get("n_steps"),
            "treatment_n_steps": seeded.generation_metadata.get("n_steps"),
            "seed_token_count": seeded.generation_metadata.get("seed_token_count", 0),
            "control_truncated": unseeded.truncated,
            "treatment_truncated": seeded.truncated,
        })

    # Render side-by-side report
    out: list[str] = []
    out.append(f"# rpm_chain decoder-seeding diagnostic — {timestamp}")
    out.append("")
    out.append(
        "Diagnostic question (per user 2026-05-09): if we force the valid"
        " RPM answer to start as a valid RPM explanation, can the model"
        " continue correctly?"
    )
    out.append("")
    out.append(
        "Setup: same v1 PREFIX128 5ep checkpoint, same 3 rpm_chain val"
        " records the 24-record audit graded `wrong`. Greedy decoding both"
        " runs. Control = no seed. Treatment = `seed_rpm_silhouette=True`"
        " (decoder primed with `\"Let <first_var_name> name \"`)."
    )
    out.append("")
    out.append("Grades remain the human's call. Per-record human grading is")
    out.append("the truth source.")
    out.append("")
    out.append("---")
    out.append("")

    for i, r in enumerate(results, start=1):
        out.append(f"## Record {i}/3 — `{r['record_id']}`")
        out.append("")
        out.append(f"**source CAS:** `{r['cas_expression']}`")
        out.append("")
        out.append("**target reply:**")
        out.append("> " + r["target"].replace("\n", "\n> "))
        out.append("")
        out.append("**control gen (no seed):**")
        out.append("> " + r["control_gen_no_seed"].replace("\n", "\n> "))
        out.append(
            f"  *(n_steps={r['control_n_steps']}, "
            f"truncated={r['control_truncated']})*"
        )
        out.append("")
        out.append(f"**seed text used (treatment):** `{r['seed_decoder_text']}`")
        out.append("")
        out.append("**treatment gen (with seed):**")
        out.append("> " + r["treatment_gen_with_seed"].replace("\n", "\n> "))
        out.append(
            f"  *(seed_tokens={r['seed_token_count']}, "
            f"new_n_steps={r['treatment_n_steps']}, "
            f"truncated={r['treatment_truncated']})*"
        )
        out.append("")
        out.append("**human grading (fill in):**")
        out.append("")
        out.append("| | grade | one-line note |")
        out.append("|---|---|---|")
        out.append("| control gen | _____ | |")
        out.append("| treatment gen | _____ | |")
        out.append("| **diagnostic verdict** | _____ | improved / unchanged / worse / mixed |")
        out.append("")
        out.append("---")
        out.append("")

    out.append("## Diagnostic interpretation guide")
    out.append("")
    out.append("- **All three improved (treatment >= control by ≥1 grade band):**")
    out.append("  Model has rpm_chain content but the silhouette opening collapses")
    out.append("  into invalid-explanation language. Task-control is the issue.")
    out.append("  → schedule Option C (retrain with [VALID]/[INVALID] task tokens).")
    out.append("")
    out.append("- **Treatment unchanged or worse:**")
    out.append("  Model doesn't actually know how to fill valid RPM chains")
    out.append("  reliably. Decoder-seeding only forces the opening; if the")
    out.append("  continuation is still wrong, the issue is training data /")
    out.append("  task tokens, not silhouette routing.")
    out.append("  → Option A is insufficient; need more rpm_chain training")
    out.append("  data, [VALID]/[INVALID] tokens, or both.")
    out.append("")
    out.append("- **Mixed (some improved, some not):**")
    out.append("  Partial signal. Probe with 10-20 more rpm_chain records before")
    out.append("  committing to direction.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / f"v1_rpm_seed_diagnostic_{timestamp}.md"
    jsonl_path = OUT_DIR / f"v1_rpm_seed_diagnostic_{timestamp}.jsonl"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(out))
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print()
    print(f"wrote diagnostic report: {md_path}")
    print(f"wrote structured raw:    {jsonl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
