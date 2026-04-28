"""Qualitative-assessment sample generator for CAS-Native v2 checkpoints.

Loads a trained checkpoint, rebuilds the SimpleTokenizer state by re-tokenizing
the training dataset (matches what training did), then generates N samples per
bucket conditioned on dataset prompts. Each generated response is compile-
validated against api/notation/compiler.py and the ground-truth CAS expression
from the source record is captured for side-by-side comparison.

Output: samples.jsonl + per-bucket prompts/completions + compile validity.
The companion comparison_report.md is authored separately by the calling agent
based on the contents of samples.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import types
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    # Local fallback for syntax check
    REPO_ROOT = Path(__file__).resolve().parents[1]
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

import torch  # noqa: E402

from cas_native.training.data_pipeline import (  # noqa: E402
    SimpleTokenizer,
    load_cas_data,
)
from cas_native.model import CASNativeModel, CASNativeConfig  # noqa: E402
from api.notation import compile_expression  # noqa: E402

BUCKETS = [
    "v74_baseline",
    "v75_register",
    "v77_rule_four",
    "v77_omega",
    "v76_production",
    "meta_logic",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--samples-per-bucket", type=int, default=5)
    p.add_argument("--max-new-tokens", type=int, default=80)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def build_tokenizer(records: list[dict]) -> SimpleTokenizer:
    """Recreate the tokenizer state by tokenizing every training record once.

    Matches what CASDataset does during training. Without this, vocab would
    be empty at inference and every word would map to UNK.
    """
    tokenizer = SimpleTokenizer()
    for r in records:
        prompt = r.get("prompt") or r.get("user_prompt") or r.get("text") or ""
        response = r.get("response") or r.get("assistant_response") or r.get("output") or ""
        combined = f"{prompt} {response}".strip()
        if combined:
            tokenizer.encode(combined, max_length=512)
    return tokenizer


def decode_ids(tokenizer: SimpleTokenizer, ids: list[int]) -> str:
    id2word = {v: k for k, v in tokenizer.word2id.items()}
    special = {tokenizer.PAD_ID, tokenizer.BOS_ID, tokenizer.EOS_ID, tokenizer.UNK_ID}
    return " ".join(id2word.get(i, "[UNK]") for i in ids if i not in special)


def sample_token(logits: torch.Tensor, temperature: float, top_p: float) -> int:
    """Top-p (nucleus) sampling at a given temperature. Returns an int token id."""
    logits = logits.float() / max(temperature, 1e-6)
    sorted_logits, sorted_idx = torch.sort(logits, descending=True)
    probs = torch.softmax(sorted_logits, dim=-1)
    cumprobs = torch.cumsum(probs, dim=-1)
    mask = cumprobs <= top_p
    mask[..., 0] = True  # always keep top token
    sorted_logits = sorted_logits.masked_fill(~mask, float("-inf"))
    # Scatter back to original order
    kept_logits = torch.full_like(logits, float("-inf"))
    kept_logits.scatter_(0, sorted_idx, sorted_logits)
    probs = torch.softmax(kept_logits, dim=-1)
    return int(torch.multinomial(probs, num_samples=1).item())


def generate(
    model: CASNativeModel,
    tokenizer: SimpleTokenizer,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    device: torch.device,
) -> tuple[str, list[int]]:
    encoded = tokenizer.encode(prompt, max_length=512)
    # Strip the trailing EOS that encode appends — we want the model to continue.
    if encoded and encoded[-1] == tokenizer.EOS_ID:
        encoded = encoded[:-1]
    input_ids = torch.tensor([encoded], dtype=torch.long, device=device)

    new_token_ids: list[int] = []
    model.eval()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            out = model(input_ids)
            last_logits = out["logits"][0, -1, :]
            tok = sample_token(last_logits, temperature, top_p)
            if tok == tokenizer.EOS_ID:
                break
            new_token_ids.append(tok)
            next_tensor = torch.tensor([[tok]], dtype=torch.long, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)
            if input_ids.shape[1] >= 512:
                break

    return decode_ids(tokenizer, new_token_ids), new_token_ids


_CAS_FRAGMENT_RE = re.compile(
    r"(?:CO-\d+|\^\d+(?:\^[PCEO])?(?:_\{F\d+\})?(?:\|[TAfE])?|"
    r"NoeticCluster\{[^}]*\}|StateCluster\{[^}]*\}|"
    r"\(\s*\^[^)]*\)\s*=\s*\^[^|]*\|Ω_\w+|"
    r"Θ\(Ω_\w+\)\s*=[^→]*→\s*Ω_\w+|"
    r"Φ<[^>]*>)"
)


def extract_cas_fragments(text: str) -> list[str]:
    """Pull out candidate CAS-shaped substrings from a free-form generation."""
    return list(dict.fromkeys(_CAS_FRAGMENT_RE.findall(text)))


def try_compile(text: str) -> dict:
    """Try compiling text as a whole, then any CAS-shaped fragments inside it."""
    out = {"compile_attempts": []}

    def _attempt(label: str, candidate: str) -> dict:
        try:
            artifact = compile_expression(candidate)
            return {
                "label": label,
                "candidate": candidate,
                "valid": bool(getattr(artifact, "valid", False)),
                "error": str(getattr(artifact, "error", "") or "") or None,
            }
        except Exception as exc:
            return {"label": label, "candidate": candidate, "valid": False, "error": f"{type(exc).__name__}: {exc}"}

    out["compile_attempts"].append(_attempt("whole", text.strip()))
    for frag in extract_cas_fragments(text)[:3]:
        out["compile_attempts"].append(_attempt("fragment", frag))

    out["any_valid"] = any(a["valid"] for a in out["compile_attempts"])
    out["valid_candidates"] = [a["candidate"] for a in out["compile_attempts"] if a["valid"]]
    return out


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[setup] dataset = {args.dataset}")
    print(f"[setup] checkpoint = {args.checkpoint}")
    print(f"[setup] out_dir = {args.out_dir}")

    print("[1/5] Loading dataset records...")
    records = load_cas_data(str(args.dataset))
    print(f"      {len(records)} records loaded")

    print("[2/5] Rebuilding tokenizer state...")
    tokenizer = build_tokenizer(records)
    print(f"      vocab size: {len(tokenizer.word2id)}")

    print("[3/5] Loading model + checkpoint...")
    cfg = CASNativeConfig()
    model = CASNativeModel(cfg)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(str(args.checkpoint), map_location=device, weights_only=False)
    model_state = ckpt.get("model_state_dict", ckpt)
    # Strip v2_components keys we don't need for inference (they may differ from
    # the bare model architecture if the v2 flag was on during training).
    own_keys = set(model.state_dict().keys())
    filtered_state = {k: v for k, v in model_state.items() if k in own_keys}
    missing = own_keys - set(filtered_state.keys())
    unexpected = set(model_state.keys()) - own_keys
    if missing:
        print(f"      WARN: {len(missing)} model keys missing from checkpoint; using fresh init for those")
    if unexpected:
        print(f"      INFO: {len(unexpected)} v2-component keys ignored for inference")
    model.load_state_dict(filtered_state, strict=False)
    model.to(device).eval()
    print(f"      params: {sum(p.numel() for p in model.parameters()):,}")
    print(f"      device: {device}")

    print("[4/5] Grouping records by bucket...")
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        bucket = r.get("_meta", {}).get("bucket", "unknown")
        by_bucket[bucket].append(r)
    for b in BUCKETS:
        print(f"      {b}: {len(by_bucket.get(b, []))} records")

    print("[5/5] Generating samples...")
    rng = random.Random(args.seed)
    all_samples: list[dict] = []
    bucket_summary: dict[str, dict] = {}

    for bucket in BUCKETS:
        bucket_records = by_bucket.get(bucket, [])
        if len(bucket_records) < args.samples_per_bucket:
            print(f"  [{bucket}] only {len(bucket_records)} records — skipping")
            continue
        chosen = rng.sample(bucket_records, args.samples_per_bucket)
        bucket_results = []
        for i, rec in enumerate(chosen):
            prompt = rec.get("prompt") or rec.get("user_prompt") or ""
            try:
                generated, _ = generate(
                    model, tokenizer, prompt,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    device=device,
                )
            except Exception as exc:
                print(f"  [{bucket} #{i}] generation FAILED: {type(exc).__name__}: {exc}")
                generated = ""
            compile_result = try_compile(generated)
            sample = {
                "bucket": bucket,
                "sample_idx": i,
                "prompt": prompt,
                "ground_truth_response": rec.get("response") or rec.get("assistant_response") or "",
                "ground_truth_cas_expression": rec.get("cas_expression", ""),
                "generated_response": generated,
                "compile_valid_anywhere": compile_result["any_valid"],
                "compile_valid_candidates": compile_result["valid_candidates"],
                "compile_attempts": compile_result["compile_attempts"],
            }
            all_samples.append(sample)
            bucket_results.append(sample)
            print(f"  [{bucket} #{i}] valid={compile_result['any_valid']}  "
                  f"prompt='{prompt[:60]}...'  generated='{generated[:60]}...'")

        bucket_summary[bucket] = {
            "n_total": len(bucket_results),
            "n_valid": sum(1 for s in bucket_results if s["compile_valid_anywhere"]),
            "valid_rate": sum(1 for s in bucket_results if s["compile_valid_anywhere"]) / max(len(bucket_results), 1),
            "ground_truth_examples": [r.get("cas_expression", "") for r in bucket_records[:3]],
        }

    samples_path = args.out_dir / "samples.jsonl"
    with open(samples_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(all_samples)} samples to {samples_path}")

    summary_path = args.out_dir / "bucket_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "checkpoint": str(args.checkpoint),
            "dataset": str(args.dataset),
            "samples_per_bucket": args.samples_per_bucket,
            "max_new_tokens": args.max_new_tokens,
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
            "overall_valid_rate": sum(1 for s in all_samples if s["compile_valid_anywhere"]) / max(len(all_samples), 1),
            "buckets": bucket_summary,
        }, f, indent=2, ensure_ascii=False)
    print(f"Wrote bucket summary to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
