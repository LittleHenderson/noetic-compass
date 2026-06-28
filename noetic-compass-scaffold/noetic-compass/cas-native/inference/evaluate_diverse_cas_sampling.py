"""B-3.5 evaluation: diverse-CAS sampling + EOS/settings sweep.

Tests two things on a trained native-NL generation checkpoint:

1. **Diverse-CAS grounding** (Layer 4 of the 5-layer eval): does the model
   produce different, register-appropriate replies for different CAS
   conditioning? This is the load-bearing test for "CAS-Native vs LM with
   fancy corpus." We sample held-out records covering all 4 registers
   (T/A/f/E) plus varied Noetic/Domain/Drive combinations.

2. **EOS/settings sweep**: the B-3 full 50K run hit max_new_tokens=100 on
   29/29 sample replies (zero EOS). Sweep three inference configs to see
   if EOS fires under top-p / lower temperature:

       a) temperature=0.8 (current default)
       b) top_p=0.9, temperature=0.8
       c) top_p=0.85, temperature=0.7

For each (record × config), generate and report: reply text, EOS, length,
leakage, Jaccard novelty vs target.

Usage::

    python -m cas_native.inference.evaluate_diverse_cas_sampling \
        --checkpoint /workspace/.../runs/b3_full_50k_prodshape_20260507/model_final.pt \
        --tokenizer /workspace/.../runs/b3_full_50k_prodshape_20260507/tokenizer.json \
        --bpe /workspace/.../runs/b3_full_50k_prodshape_20260507/english_bpe.json \
        --corpus /workspace/.../v1_dialogue_50k_claude_20260507_full.jsonl \
        --out /workspace/.../runs/b3_full_50k_prodshape_20260507/diverse_cas_eval.jsonl \
        --n-records 24 --device cuda
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import types
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


# Path bootstrap — same pattern as train_native_nl_gen.py
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


import torch  # noqa: E402

from cas_native.inference.native_nl_generate import generate_reply  # noqa: E402
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEAKAGE_PATTERNS = {
    "literal_CAS": re.compile(r"\bCAS\b"),
    "noetic": re.compile(r"\bnoetic[s]?\b", re.I),
    "domain": re.compile(r"\bdomain[s]?\b", re.I),
    "drive": re.compile(r"\bdrive[s]?\b", re.I),
    "register": re.compile(r"\bregister[s]?\b", re.I),
    "caret_state": re.compile(r"\^[0-9]"),
    "F1F7": re.compile(r"\bF[1-7]\b"),
}

DEFAULT_SAMPLING_CONFIGS = [
    {"id": "temp_0.8", "sampling": "temperature", "temperature": 0.8, "top_p": 0.9},
    {"id": "top_p_0.9_temp_0.8", "sampling": "top_p", "temperature": 0.8, "top_p": 0.9},
    {"id": "top_p_0.85_temp_0.7", "sampling": "top_p", "temperature": 0.7, "top_p": 0.85},
]

REGISTERS = ("T", "A", "f", "E")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_set(text: str) -> set[str]:
    """Lowercased, punctuation-stripped word set for Jaccard scoring."""
    cleaned = re.sub(r"[^\w\s]", " ", (text or "").lower())
    return {w for w in cleaned.split() if len(w) >= 2}


def jaccard_novelty(generated: str, target: str) -> float:
    """1 - Jaccard(generated, target). 1.0 = totally novel; 0.0 = identical token sets."""
    g = _word_set(generated)
    t = _word_set(target)
    if not g or not t:
        return 1.0
    inter = g & t
    union = g | t
    if not union:
        return 1.0
    return 1.0 - (len(inter) / len(union))


def leakage_check(text: str) -> dict[str, int]:
    """Count which leakage patterns hit. Empty dict = clean."""
    hits = {}
    for label, pat in LEAKAGE_PATTERNS.items():
        if pat.search(text or ""):
            hits[label] = 1
    return hits


def deterministic_split_records(records: list[dict], val_fraction: float, seed: int) -> tuple[list[dict], list[dict]]:
    """Mirror the trainer's deterministic_split exactly so val records match training."""
    import random as _rand
    rng = _rand.Random(int(seed))
    indices = list(range(len(records)))
    rng.shuffle(indices)
    n_val = max(1, int(round(len(records) * float(val_fraction)))) if records else 0
    val_idx = set(indices[:n_val])
    train = [records[i] for i in range(len(records)) if i not in val_idx]
    val = [records[i] for i in range(len(records)) if i in val_idx]
    return train, val


def pick_diverse(records: list[dict], n: int, *, seed: int = 42) -> list[dict]:
    """Pick n records spanning all 4 registers and varied (noetic, drive)."""
    import random as _rand
    rng = _rand.Random(int(seed))
    by_register: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        reg = r.get("register", "T")
        if reg in REGISTERS:
            by_register[reg].append(r)

    per_reg = max(1, n // len(REGISTERS))
    picked: list[dict] = []
    for reg in REGISTERS:
        pool = list(by_register.get(reg, []))
        if not pool:
            continue
        # Diversify by (noetic, drive) inside register
        seen_combos: set[tuple] = set()
        rng.shuffle(pool)
        register_picks: list[dict] = []
        for r in pool:
            combo = (str(r.get("noetic")), str(r.get("drive")))
            if combo in seen_combos:
                continue
            seen_combos.add(combo)
            register_picks.append(r)
            if len(register_picks) >= per_reg:
                break
        # If diversity exhausted before per_reg, pad from leftover pool
        if len(register_picks) < per_reg:
            for r in pool:
                if r in register_picks:
                    continue
                register_picks.append(r)
                if len(register_picks) >= per_reg:
                    break
        picked.extend(register_picks)

    return picked[:n]


def load_tokenizer(tokenizer_json: Path, bpe_artifact: Path | None) -> Any:
    base = HybridCASTokenizer.load(tokenizer_json)
    if bpe_artifact is not None and bpe_artifact.exists():
        return base.with_english_bpe(bpe_artifact)
    return base


def build_model_with_head(*, vocab_size: int, config: dict, device: torch.device) -> Any:
    """Build CASNativeModel + NLGenerationHead with the trained-run config."""
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    from cas_native.model.nl_generation_head import NLGenerationHead, NLGenerationHeadConfig

    enc_cfg = CASNativeConfig(
        d_model=config["d_model"],
        n_layers=config["encoder_n_layers"],
        n_heads=config["encoder_n_heads"],
        vocab_size=vocab_size,
    )
    encoder = CASNativeModel(enc_cfg).to(device)

    head_cfg = NLGenerationHeadConfig(
        vocab_size=vocab_size,
        d_model=config["d_model"],
        n_heads=config["head_n_heads"],
        n_layers=config["head_n_layers"],
    )
    head = NLGenerationHead(head_cfg).to(device)

    if encoder.config.d_model != head.config.d_model:
        raise ValueError(
            f"d_model mismatch: encoder={encoder.config.d_model} head={head.config.d_model}"
        )
    encoder.attach_nl_gen_head(head)
    return encoder


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True, help="Path to model_final.pt")
    p.add_argument("--tokenizer", type=Path, required=True, help="Path to tokenizer.json")
    p.add_argument("--bpe", type=Path, default=None, help="Path to english_bpe.json (optional)")
    p.add_argument("--corpus", type=Path, required=True, help="Full training corpus to derive the same val split")
    p.add_argument("--out", type=Path, required=True, help="Output JSONL of (record × config) results")
    p.add_argument("--n-records", type=int, default=24, help="Diverse held-out records to sample")
    p.add_argument("--max-new-tokens", type=int, default=120)
    p.add_argument("--seed", type=int, default=42, help="Must match the training run's --seed for val split parity")
    p.add_argument("--val-fraction", type=float, default=0.05)
    p.add_argument("--device", default="cuda")
    p.add_argument("--d-model", type=int, default=512)
    p.add_argument("--encoder-n-layers", type=int, default=6)
    p.add_argument("--encoder-n-heads", type=int, default=8)
    p.add_argument("--head-n-layers", type=int, default=6)
    p.add_argument("--head-n-heads", type=int, default=8)
    p.add_argument(
        "--use-cas-prefix",
        action="store_true",
        help="Pass cas_prefix_ids into generation. Default OFF (matches training).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        print(json.dumps({"event": "warn", "reason": "cuda_unavailable_using_cpu"}))
        args.device = "cpu"
    device = torch.device(args.device)

    # Load tokenizer
    tokenizer = load_tokenizer(args.tokenizer, args.bpe)
    vocab_size = int(tokenizer.vocab_size)
    print(json.dumps({"event": "tokenizer_loaded", "vocab_size": vocab_size,
                      "kind": type(tokenizer).__name__}))

    # Build model + head, load checkpoint
    model = build_model_with_head(
        vocab_size=vocab_size,
        config={
            "d_model": args.d_model,
            "encoder_n_layers": args.encoder_n_layers,
            "encoder_n_heads": args.encoder_n_heads,
            "head_n_layers": args.head_n_layers,
            "head_n_heads": args.head_n_heads,
        },
        device=device,
    )
    state = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(state["model"])
    model.eval()
    print(json.dumps({
        "event": "model_loaded",
        "checkpoint": str(args.checkpoint),
        "step": int(state.get("step", -1)),
        "epoch": int(state.get("epoch", -1)),
    }))

    # Load corpus + derive val split
    records: list[dict] = []
    with args.corpus.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    _train, val_records = deterministic_split_records(records, args.val_fraction, args.seed)
    print(json.dumps({"event": "corpus_split", "n_train": len(_train), "n_val": len(val_records)}))

    # Pick diverse held-out
    held_out = pick_diverse(val_records, n=args.n_records, seed=args.seed)
    print(json.dumps({
        "event": "held_out_picked",
        "n": len(held_out),
        "registers": dict(Counter(r.get("register") for r in held_out)),
        "noetics": dict(Counter(r.get("noetic") for r in held_out)),
        "drives": dict(Counter(r.get("drive") for r in held_out)),
    }))

    # Generate per (record × config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    with args.out.open("w", encoding="utf-8") as out_fh:
        for r_i, record in enumerate(held_out):
            prompt = record.get("prompt_text") or record.get("prompt", "")
            cas_expr = record.get("cas_expression", "")
            target = record.get("reply_text") or record.get("reply", "")
            register = record.get("register", "T")

            for cfg in DEFAULT_SAMPLING_CONFIGS:
                gen_out = generate_reply(
                    model=model,
                    tokenizer=tokenizer,
                    prompt_text=prompt,
                    cas_expression=cas_expr,
                    register=register,
                    max_new_tokens=int(args.max_new_tokens),
                    sampling=cfg["sampling"],
                    temperature=cfg["temperature"],
                    top_p=cfg["top_p"],
                    use_cas_prefix=bool(args.use_cas_prefix),
                    device=device,
                    return_trace=False,
                )
                generated_text = gen_out["reply_text"]
                row = {
                    "record_id": record.get("id"),
                    "register": register,
                    "config_id": cfg["id"],
                    "config": cfg,
                    "conditioning": {
                        "cas_expression": cas_expr,
                        "noetic": record.get("noetic"),
                        "domain": record.get("domain"),
                        "drive": record.get("drive"),
                        "register": register,
                    },
                    "prompt_text": prompt,
                    "target_reply_text": target,
                    "generated_reply_text": generated_text,
                    "n_tokens": int(gen_out["n_steps"]),
                    "stopped_on_eos": bool(gen_out["stopped_on_eos"]),
                    "novelty_jaccard": jaccard_novelty(generated_text, target),
                    "leakage_hits": leakage_check(generated_text),
                }
                results.append(row)
                out_fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                out_fh.flush()
            print(json.dumps({"event": "record_done", "record_idx": r_i, "register": register}))

    # Summary
    print()
    print("=" * 70)
    print("=== SUMMARY ===")
    print(f"Total samples: {len(results)} ({len(held_out)} records × {len(DEFAULT_SAMPLING_CONFIGS)} configs)")

    by_config: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_config[row["config_id"]].append(row)

    for cfg_id, rows in by_config.items():
        eos_rate = sum(1 for r in rows if r["stopped_on_eos"]) / max(1, len(rows))
        avg_tokens = mean(r["n_tokens"] for r in rows)
        med_tokens = median(r["n_tokens"] for r in rows)
        truncation_rate = sum(1 for r in rows if not r["stopped_on_eos"] and r["n_tokens"] >= int(args.max_new_tokens)) / max(1, len(rows))
        avg_novelty = mean(r["novelty_jaccard"] for r in rows)
        leak_count = sum(1 for r in rows if r["leakage_hits"])
        print()
        print(f"--- config {cfg_id} ---")
        print(f"  EOS rate:          {eos_rate:.2%}")
        print(f"  Avg tokens:        {avg_tokens:.1f}  (median {med_tokens:.0f})")
        print(f"  Truncation rate:   {truncation_rate:.2%}  (capped at {args.max_new_tokens})")
        print(f"  Avg novelty:       {avg_novelty:.3f}  (1.0 = no overlap with target; 0.0 = identical)")
        print(f"  Leakage records:   {leak_count}/{len(rows)}")

    by_register: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_register[row["register"]].append(row)

    print()
    print("--- per-register quality (default temp_0.8 config) ---")
    for reg in REGISTERS:
        reg_rows = [r for r in by_register[reg] if r["config_id"] == "temp_0.8"]
        if not reg_rows:
            continue
        eos = sum(1 for r in reg_rows if r["stopped_on_eos"]) / max(1, len(reg_rows))
        nov = mean(r["novelty_jaccard"] for r in reg_rows)
        leak = sum(1 for r in reg_rows if r["leakage_hits"])
        print(f"  register {reg}: n={len(reg_rows)}  eos={eos:.0%}  novelty={nov:.3f}  leakage={leak}")

    print()
    print(f"Results saved to: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
