"""Qualitative-assessment sample generator for CAS-Native v2 checkpoints.

Loads a trained checkpoint plus the persisted tokenizer artifact from its run
directory, then generates samples per bucket conditioned on dataset prompts.
Generated text is checked with the compiler and with a stricter structured-CAS
gate so bare fragments like ``^7`` no longer count as success.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import types
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
pkg = types.ModuleType("cas_native")
pkg.__path__ = [str(REPO_ROOT / "cas-native")]
sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

import torch  # noqa: E402

from api.notation import compile_expression  # noqa: E402
from cas_native.model import CASNativeConfig, CASNativeModel  # noqa: E402
from cas_native.training.data_pipeline import load_cas_data  # noqa: E402
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402


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
    p.add_argument(
        "--task",
        choices=("expr", "raw"),
        default="expr",
        help="Prompt formatting. expr uses [TASK_EXPR] [PROMPT] ... [RESPONSE].",
    )
    p.add_argument(
        "--tokenizer",
        type=Path,
        default=None,
        help="Path to tokenizer.json. Defaults to the checkpoint run directory when present.",
    )
    return p.parse_args()


def find_tokenizer_path(checkpoint: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    for candidate in (
        checkpoint.parent.parent / "tokenizer.json",
        checkpoint.parent / "tokenizer.json",
    ):
        if candidate.exists():
            return candidate
    return None


def load_or_build_tokenizer(
    records: list[dict],
    checkpoint: Path,
    explicit: Path | None,
) -> tuple[HybridCASTokenizer, Path | None]:
    tokenizer_path = find_tokenizer_path(checkpoint, explicit)
    if tokenizer_path is not None:
        return HybridCASTokenizer.load(tokenizer_path), tokenizer_path
    # Compatibility fallback for pre-redesign checkpoints. New production runs
    # should always persist and pass tokenizer.json.
    return HybridCASTokenizer.from_records(records, freeze=True), None


def decode_ids(tokenizer: HybridCASTokenizer, ids: list[int]) -> str:
    return tokenizer.decode(ids)


def sample_token(
    logits: torch.Tensor,
    temperature: float,
    top_p: float,
    *,
    tokenizer: HybridCASTokenizer,
) -> int:
    """Top-p nucleus sampling with invalid-token masking."""
    logits = logits.float().clone()
    if logits.numel() > tokenizer.vocab_size:
        logits[tokenizer.vocab_size:] = float("-inf")
    for token_id in tokenizer.disallowed_generation_ids():
        if 0 <= token_id < logits.numel():
            logits[token_id] = float("-inf")
    logits = logits / max(temperature, 1e-6)

    sorted_logits, sorted_idx = torch.sort(logits, descending=True)
    probs = torch.softmax(sorted_logits, dim=-1)
    cumprobs = torch.cumsum(probs, dim=-1)
    mask = cumprobs <= top_p
    mask[..., 0] = True
    sorted_logits = sorted_logits.masked_fill(~mask, float("-inf"))

    kept_logits = torch.full_like(logits, float("-inf"))
    kept_logits.scatter_(0, sorted_idx, sorted_logits)
    probs = torch.softmax(kept_logits, dim=-1)
    return int(torch.multinomial(probs, num_samples=1).item())


def generate(
    model: CASNativeModel,
    tokenizer: HybridCASTokenizer,
    prompt: str,
    max_new_tokens: int,
    temperature: float,
    top_p: float,
    device: torch.device,
) -> tuple[str, list[int]]:
    encoded = tokenizer.encode(prompt, max_length=512)
    if encoded and encoded[-1] == tokenizer.EOS_ID:
        encoded = encoded[:-1]
    input_ids = torch.tensor([encoded], dtype=torch.long, device=device)

    new_token_ids: list[int] = []
    model.eval()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            out = model(input_ids)
            last_logits = out["logits"][0, -1, :]
            tok = sample_token(
                last_logits,
                temperature,
                top_p,
                tokenizer=tokenizer,
            )
            if tok == tokenizer.EOS_ID:
                break
            new_token_ids.append(tok)
            next_tensor = torch.tensor([[tok]], dtype=torch.long, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)
            if input_ids.shape[1] >= 512:
                break

    return decode_ids(tokenizer, new_token_ids), new_token_ids


def format_generation_prompt(prompt: str, task: str) -> str:
    if task == "expr":
        # Training uses "[RESPONSE] {cas_expression}", so keep the trailing
        # space token in the inference prefix. Without it the model often
        # predicts EOS immediately after the response sentinel.
        return f"[TASK_EXPR] [PROMPT] {prompt} [RESPONSE] "
    return prompt


_CAS_FRAGMENT_RE = re.compile(
    r"(?:"
    r"Θ\(Ω_\w+\)\s*=[^→]*→\s*Ω_\w+"
    r"|\([^)]*×[^)]*\)\s*=\s*\^\d+(?:\^[PCEO])?\|Ω_\w+"
    r"|NoeticCluster\{[^}]*\}|StateCluster\{[^}]*\}|StateVariantCluster\{[^}]*\}|RelationCluster\{[^}]*\}"
    r"|(?:Product|Pullback|CoverOf|PartitionOf|Union|Intersection|Difference)\([^)]*\)"
    r"|\^\d+\^[PCEO]_\{F_?\d+\}\|[TAfE]"
    r"|\^\d+\^[PCEO]_\{F_?\d+\}"
    r"|Φ<[^>]*>"
    r"|RPM\(F_?\d+\)"
    r"|CO-\d+"
    r"|\^\d+"
    r")"
)

_STRUCTURED_BY_BUCKET = {
    "v74_baseline": re.compile(r"\^\d+\^[PCEO]_\{F_?\d+\}|Φ<[^>]*>|RPM\(F_?\d+\)"),
    "v75_register": re.compile(r"\^\d+\^[PCEO]_\{F_?\d+\}\|[TAfE]|\|⟨[^⟩]+⟩|\|<[TAfE,]+>"),
    "v77_rule_four": re.compile(r"\([^)]*(?:×|\+)[^)]*\)\s*=\s*(?:\^\d+(?:\^[PCEO])?\|)?Ω_\w+|(?:×|\+)"),
    "v77_omega": re.compile(r"\([^)]*×[^)]*\)\s*=\s*\^\d+(?:\^[PCEO])?\|Ω_\w+"),
    "v76_production": re.compile(r"Θ\(Ω_\w+\)\s*=[^→]+→\s*Ω_\w+"),
    "meta_logic": re.compile(r"NoeticCluster|StateCluster|StateVariantCluster|RelationCluster|Product|Pullback|CoverOf|PartitionOf|∈|⊆|⊂|∪|∩|∖"),
}


def extract_cas_fragments(text: str) -> list[str]:
    """Pull candidate CAS-shaped substrings from a free-form generation."""
    return list(dict.fromkeys(_CAS_FRAGMENT_RE.findall(text)))


def is_structured_candidate(candidate: str, bucket: str) -> bool:
    stripped = candidate.strip()
    if not stripped or "[UNK]" in stripped:
        return False
    if re.fullmatch(r"(?:CO-)?\^?\d+", stripped):
        return False
    pattern = _STRUCTURED_BY_BUCKET.get(bucket)
    return bool(pattern.search(stripped)) if pattern is not None else True


def try_compile(text: str, bucket: str) -> dict:
    """Compile the whole generation, then CAS-shaped fragments."""
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
            return {
                "label": label,
                "candidate": candidate,
                "valid": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    out["compile_attempts"].append(_attempt("whole", text.strip()))
    for frag in extract_cas_fragments(text)[:3]:
        out["compile_attempts"].append(_attempt("fragment", frag))

    out["any_valid"] = any(a["valid"] for a in out["compile_attempts"])
    out["valid_candidates"] = [a["candidate"] for a in out["compile_attempts"] if a["valid"]]
    out["structured_valid_candidates"] = [
        a["candidate"]
        for a in out["compile_attempts"]
        if a["valid"] and is_structured_candidate(a["candidate"], bucket)
    ]
    out["structured_valid"] = bool(out["structured_valid_candidates"])
    return out


def checkpoint_vocab_size(model_state: dict[str, torch.Tensor]) -> int | None:
    weight = model_state.get("token_embedding.weight")
    if weight is None:
        return None
    return int(weight.shape[0])


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[setup] dataset = {args.dataset}")
    print(f"[setup] checkpoint = {args.checkpoint}")
    print(f"[setup] out_dir = {args.out_dir}")

    print("[1/5] Loading dataset records...")
    records = load_cas_data(str(args.dataset))
    print(f"      {len(records)} records loaded")

    print("[2/5] Loading tokenizer artifact...")
    tokenizer, tokenizer_path = load_or_build_tokenizer(records, args.checkpoint, args.tokenizer)
    print(f"      tokenizer path: {tokenizer_path or 'built fallback from dataset'}")
    print(f"      tokenizer meta: {tokenizer.metadata()}")

    print("[3/5] Loading model + checkpoint...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(str(args.checkpoint), map_location=device, weights_only=False)
    model_state = ckpt.get("model_state_dict", ckpt)
    model_vocab_size = checkpoint_vocab_size(model_state) or tokenizer.vocab_size
    model = CASNativeModel(CASNativeConfig(vocab_size=model_vocab_size))

    own_state = model.state_dict()
    own_keys = set(own_state.keys())
    filtered_state = {
        k: v
        for k, v in model_state.items()
        if k in own_keys and tuple(v.shape) == tuple(own_state[k].shape)
    }
    missing = own_keys - set(filtered_state.keys())
    unexpected = set(model_state.keys()) - set(filtered_state.keys())
    if missing:
        print(f"      WARN: {len(missing)} model keys missing from checkpoint; using fresh init for those")
    if unexpected:
        print(f"      INFO: {len(unexpected)} checkpoint keys ignored for inference")
    if tokenizer.vocab_size != model_vocab_size:
        print(
            f"      WARN: tokenizer vocab {tokenizer.vocab_size} != model vocab {model_vocab_size}; "
            "generation masks IDs outside tokenizer vocab"
        )
    model.load_state_dict(filtered_state, strict=False)
    model.to(device).eval()
    print(f"      params: {sum(p.numel() for p in model.parameters()):,}")
    print(f"      model vocab size: {model_vocab_size}")
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
            print(f"  [{bucket}] only {len(bucket_records)} records; skipping")
            continue
        chosen = rng.sample(bucket_records, args.samples_per_bucket)
        bucket_results = []
        for i, rec in enumerate(chosen):
            prompt = rec.get("prompt") or rec.get("user_prompt") or ""
            generation_prompt = format_generation_prompt(prompt, args.task)
            try:
                generated, token_ids = generate(
                    model,
                    tokenizer,
                    generation_prompt,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    device=device,
                )
            except Exception as exc:
                print(f"  [{bucket} #{i}] generation FAILED: {type(exc).__name__}: {exc}")
                generated = ""
                token_ids = []
            compile_result = try_compile(generated, bucket)
            sample = {
                "bucket": bucket,
                "sample_idx": i,
                "prompt": prompt,
                "generation_prompt": generation_prompt,
                "ground_truth_response": rec.get("response") or rec.get("assistant_response") or "",
                "ground_truth_cas_expression": rec.get("cas_expression", ""),
                "generated_response": generated,
                "generated_token_ids": token_ids,
                "compile_valid_anywhere": compile_result["any_valid"],
                "structured_cas_valid": compile_result["structured_valid"],
                "compile_valid_candidates": compile_result["valid_candidates"],
                "structured_valid_candidates": compile_result["structured_valid_candidates"],
                "compile_attempts": compile_result["compile_attempts"],
            }
            all_samples.append(sample)
            bucket_results.append(sample)
            print(
                f"  [{bucket} #{i}] valid={compile_result['any_valid']} "
                f"structured={compile_result['structured_valid']} "
                f"prompt='{prompt[:60]}...' generated='{generated[:60]}...'"
            )

        bucket_summary[bucket] = {
            "n_total": len(bucket_results),
            "n_valid": sum(1 for s in bucket_results if s["compile_valid_anywhere"]),
            "valid_rate": sum(1 for s in bucket_results if s["compile_valid_anywhere"]) / max(len(bucket_results), 1),
            "n_structured_valid": sum(1 for s in bucket_results if s["structured_cas_valid"]),
            "structured_valid_rate": sum(1 for s in bucket_results if s["structured_cas_valid"]) / max(len(bucket_results), 1),
            "ground_truth_examples": [r.get("cas_expression", "") for r in bucket_records[:3]],
        }

    samples_path = args.out_dir / "samples.jsonl"
    with open(samples_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(all_samples)} samples to {samples_path}")

    summary_path = args.out_dir / "bucket_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "checkpoint": str(args.checkpoint),
                "dataset": str(args.dataset),
                "samples_per_bucket": args.samples_per_bucket,
                "max_new_tokens": args.max_new_tokens,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "seed": args.seed,
                "task": args.task,
                "tokenizer": tokenizer.metadata(),
                "tokenizer_path": str(tokenizer_path) if tokenizer_path is not None else None,
                "overall_valid_rate": sum(1 for s in all_samples if s["compile_valid_anywhere"]) / max(len(all_samples), 1),
                "overall_structured_valid_rate": sum(1 for s in all_samples if s["structured_cas_valid"]) / max(len(all_samples), 1),
                "buckets": bucket_summary,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Wrote bucket summary to {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
