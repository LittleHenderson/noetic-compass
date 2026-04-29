"""Bucket-conditional prefix-primed sample generator for CAS-Native v2.

Difference from generate_samples.py: instead of free generation, we force the
model's response prefix to a bucket-canonical opening. The model's logit
distribution learned the rest of the structure during training (proven by
30/30 loose-valid in the 1500-step free-sampling pass) — it just couldn't
escape its own probability mass on simpler shapes during free decoding. This
script tests the "decoding-side intervention" hypothesis: forcing the
architectural opening should let the model finish well-formed expressions for
buckets that didn't break through structurally at 1500 steps.

Generated text is the primer + the model's continuation. Compile-validation
runs against the full string. Structured-valid is computed per-bucket.
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


# Per-bucket primers — 5 strategies per bucket from minimal opening to
# near-complete prefix. Each primer is appended after [RESPONSE] and the
# model fills in the rest. The hypothesis: model has learned structural
# completion conditional on prefix, even if it can't produce the structure
# from scratch in free sampling.
BUCKET_PRIMERS: dict[str, list[str]] = {
    "v74_baseline": [
        "^",                       # 1: minimal, model fills everything
        "^2^P",                    # 2: compound start; model fills drive+register
        "^5_{F",                   # 3: drive subscript open
        "^7^E_{F3}",               # 4: full state shell, model adds register if any
        "^9^O_{F",                 # 5: full opening
    ],
    "v75_register": [
        "^",                       # 1: minimal
        "^2^P_{F",                 # 2: drive open
        "^4^O_{F1}|f + ",          # 3: full first state + plus; model fills second
        "^7^E_{F2}|A + ^",         # 4: first state + start of second
        "^N^D_{F".replace("N", str(random.Random(42).randint(0,9))).replace("D", random.Random(43).choice("PCEO")),  # 5: random open
    ],
    "v77_rule_four": [
        "^3^P_{F2}|A × ",          # 1: first half + cross
        "(^5^O_{F3}|T × ^5^O_{F3}|f) = ^5^O|",  # 2: full Ω-emergent shell
        "^4^E_{F1}|A + ^4^E_{F1}|f + ",         # 3: + co-presence start
        "^N^D_{F",                 # 4: minimal compound start
        "^6^P_{F1}|A × ^6^P_{F1}|f × ",          # 5: 2-of-3 register cross
    ],
    "v77_omega": [
        "(^",                                                 # 1: open paren
        "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_",                # 2: full structure, just Ω name missing
        "(^4^E|A × ^4^E|f) = ^4^E|Ω_",                          # 3: 2-register variant
        "(^7^O_{F3}|A × ^7^O_{F3}|T) = ^7^O|",                  # 4: with drive subscripts
        "(^",                                                 # 5: minimal
    ],
    "v76_production": [
        "Θ(Ω_",                                                # 1: recipe head only
        "Θ(Ω_focused_refusal) = ",                             # 2: full target name + equals
        "Θ(Ω_pattern_entrainment_learning) = 1*",              # 3: target + first coefficient
        "Θ(Ω_grounded_creative_insight) = 0.7*^",              # 4: target + coeff + state start
        "Θ(Ω_",                                                # 5: minimal
    ],
    "meta_logic": [
        "NoeticCluster{^",                                     # 1: cluster opening
        "Pullback(NoeticCluster{^",                             # 2: pullback opening
        "StateCluster{^",                                       # 3: state-cluster opening
        "^2 ∈ Noetics",                                        # 4: typed-membership full assertion
        "CoverOf(SubFoundations, Foundation_",                 # 5: cover opening
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--max-new-tokens", type=int, default=80)
    p.add_argument("--temperature", type=float, default=0.4)
    p.add_argument("--top-p", type=float, default=0.9)
    p.add_argument("--min-new-tokens", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--tokenizer", type=Path, default=None)
    return p.parse_args()


def find_tokenizer_path(checkpoint: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit
    for c in (checkpoint.parent.parent / "tokenizer.json", checkpoint.parent / "tokenizer.json"):
        if c.exists():
            return c
    return None


def sample_token(logits: torch.Tensor, temperature: float, top_p: float, *, tokenizer: HybridCASTokenizer, blocked: set[int] | None = None) -> int:
    logits = logits.float().clone()
    if logits.numel() > tokenizer.vocab_size:
        logits[tokenizer.vocab_size:] = float("-inf")
    for tid in tokenizer.disallowed_generation_ids():
        if 0 <= tid < logits.numel():
            logits[tid] = float("-inf")
    for tid in blocked or set():
        if 0 <= tid < logits.numel():
            logits[tid] = float("-inf")
    logits = logits / max(temperature, 1e-6)

    sorted_logits, sorted_idx = torch.sort(logits, descending=True)
    probs = torch.softmax(sorted_logits, dim=-1)
    cumprobs = torch.cumsum(probs, dim=-1)
    mask = cumprobs <= top_p
    mask[..., 0] = True
    over = torch.nonzero(cumprobs > top_p, as_tuple=False)
    if over.numel() > 0:
        mask[over[0].item()] = True
    sorted_logits = sorted_logits.masked_fill(~mask, float("-inf"))
    kept = torch.full_like(logits, float("-inf"))
    kept.scatter_(0, sorted_idx, sorted_logits)
    probs = torch.softmax(kept, dim=-1)
    return int(torch.multinomial(probs, num_samples=1).item())


def generate_with_primer(
    model: CASNativeModel,
    tokenizer: HybridCASTokenizer,
    prompt: str,
    primer: str,
    max_new_tokens: int,
    min_new_tokens: int,
    temperature: float,
    top_p: float,
    device: torch.device,
) -> tuple[str, list[int]]:
    """Build full prefix and generate continuation."""
    full_prefix = f"[TASK_EXPR] [PROMPT] {prompt} [RESPONSE] {primer}"
    encoded = tokenizer.encode(full_prefix, max_length=512)
    if encoded and encoded[-1] == tokenizer.EOS_ID:
        encoded = encoded[:-1]
    input_ids = torch.tensor([encoded], dtype=torch.long, device=device)

    new_token_ids: list[int] = []
    model.eval()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            out = model(input_ids)
            last_logits = out["logits"][0, -1, :]
            blocked = set()
            if len(new_token_ids) < min_new_tokens:
                blocked.add(tokenizer.EOS_ID)
            tok = sample_token(last_logits, temperature, top_p, tokenizer=tokenizer, blocked=blocked)
            if tok == tokenizer.EOS_ID:
                break
            new_token_ids.append(tok)
            next_t = torch.tensor([[tok]], dtype=torch.long, device=device)
            input_ids = torch.cat([input_ids, next_t], dim=1)
            if input_ids.shape[1] >= 512:
                break

    continuation = tokenizer.decode(new_token_ids)
    full_response = (primer + continuation).strip()
    return full_response, new_token_ids


_STRUCTURED_BY_BUCKET = {
    "v74_baseline": re.compile(r"^\^\d\^[PCEO](?:_\{F_?\d+\})?(?:\|[TAfE])?(?:\s*[+*]\s*\^\d\^[PCEO](?:_\{F_?\d+\})?(?:\|[TAfE])?)*\s*$"),
    "v75_register": re.compile(r"^\^\d\^[PCEO]_\{F_?\d+\}\|[TAfE]\s*\+\s*\^\d\^[PCEO]_\{F_?\d+\}\|[TAfE]\s*$"),
    "v77_rule_four": re.compile(r"^\^\d\^[PCEO]_\{F_?\d+\}\|[TAfE](?:\s*[+×]\s*\^\d\^[PCEO]_\{F_?\d+\}\|[TAfE]){1,3}\s*(?:=\s*\^\d\^[PCEO]\|Ω_\w+)?\s*$"),
    "v77_omega": re.compile(r"^\(?\^\d\^[PCEO](?:_\{F_?\d+\})?\|[TAfE]\s*×\s*\^\d\^[PCEO](?:_\{F_?\d+\})?\|[TAfE](?:\s*×\s*\^\d\^[PCEO](?:_\{F_?\d+\})?\|[TAfE])?\)?\s*=\s*\^\d\^[PCEO]\|Ω_\w+\s*$"),
    "v76_production": re.compile(r"^Θ\(Ω_\w+\)\s*=\s*[\d.]+\*\^\d\^[PCEO](?:_\{F_?\d+\})?(?:\|[TAfE])?(?:\s*\+\s*[\d.]+\*\^\d\^[PCEO](?:_\{F_?\d+\})?(?:\|[TAfE])?)*\s*→\s*Ω_\w+\s*$"),
    "meta_logic": re.compile(r"^(?:NoeticCluster\{[\^\d,\s]+\}|StateCluster\{[\^\d\sPCEO,]+\}|Pullback\(NoeticCluster\{[^}]+\},\s*NoeticCluster\{[^}]+\}\)|CoverOf\([^)]+\)|PartitionOf\([^)]+\)|\^\d+\s*∈\s*Noetics|\^\d+\^[PCEO]\s*∈\s*States|NoeticCluster\{[^}]+\}\s*[∪∩∖]\s*NoeticCluster\{[^}]+\}|Coordinate\{[^}]+\}|Product\([^)]+\))\s*$"),
}


def is_structured_valid(text: str, bucket: str) -> bool:
    text = text.strip()
    if not text:
        return False
    pattern = _STRUCTURED_BY_BUCKET.get(bucket)
    if pattern is None:
        return False
    if not pattern.match(text):
        return False
    try:
        result = compile_expression(text)
        return bool(getattr(result, "valid", False))
    except Exception:
        return False


def try_compile_loose(text: str) -> bool:
    """Return True if any CAS-fragment in text compiles."""
    try:
        if compile_expression(text.strip()).valid:
            return True
    except Exception:
        pass
    # try the substring matching simpler shapes
    for frag in re.findall(r"(?:\^\d+\^[PCEO](?:_\{F_?\d+\})?(?:\|[TAfE])?|\^\d+|NoeticCluster\{[^}]+\}|Θ\(Ω_\w+\)[^→]*→\s*Ω_\w+)", text)[:5]:
        try:
            if compile_expression(frag).valid:
                return True
        except Exception:
            pass
    return False


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[setup] dataset = {args.dataset}")
    print(f"[setup] checkpoint = {args.checkpoint}")
    print(f"[setup] out_dir = {args.out_dir}")
    print(f"[setup] sampling: T={args.temperature} top_p={args.top_p} max_new={args.max_new_tokens}")

    print("[1/4] Loading dataset records + tokenizer...")
    records = load_cas_data(str(args.dataset))
    print(f"      {len(records)} records loaded")

    tok_path = find_tokenizer_path(args.checkpoint, args.tokenizer)
    if tok_path is None:
        print("ERROR: tokenizer.json not found; aborting")
        return 1
    tokenizer = HybridCASTokenizer.load(tok_path)
    print(f"      tokenizer: vocab_size={tokenizer.vocab_size}")

    print("[2/4] Loading model + checkpoint...")
    cfg = CASNativeConfig(vocab_size=tokenizer.vocab_size, causal_lm=True)
    model = CASNativeModel(cfg)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(str(args.checkpoint), map_location=device, weights_only=False)
    model_state = ckpt.get("model_state_dict", ckpt)
    own_keys = set(model.state_dict().keys())
    filtered = {k: v for k, v in model_state.items() if k in own_keys}
    model.load_state_dict(filtered, strict=False)
    model.to(device).eval()
    print(f"      params: {sum(p.numel() for p in model.parameters()):,}")

    print("[3/4] Grouping records by bucket...")
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_bucket[r.get("_meta", {}).get("bucket", "unknown")].append(r)

    print("[4/4] Generating primed samples (5 primers × 6 buckets = 30 total)...")
    rng = random.Random(args.seed)
    all_samples = []
    bucket_summary: dict[str, dict] = {}

    for bucket in BUCKETS:
        primers = BUCKET_PRIMERS.get(bucket, ["^"])
        bucket_records = by_bucket.get(bucket, [])
        if len(bucket_records) < len(primers):
            print(f"  [{bucket}] only {len(bucket_records)} records — skipping")
            continue
        prompts = rng.sample(bucket_records, len(primers))
        bucket_results = []
        for i, (primer, rec) in enumerate(zip(primers, prompts)):
            prompt = rec.get("prompt") or rec.get("user_prompt") or ""
            try:
                response, _ = generate_with_primer(
                    model, tokenizer, prompt, primer,
                    max_new_tokens=args.max_new_tokens,
                    min_new_tokens=args.min_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                    device=device,
                )
            except Exception as exc:
                print(f"  [{bucket} #{i}] FAIL: {type(exc).__name__}: {exc}")
                response = ""
            loose = try_compile_loose(response)
            structured = is_structured_valid(response, bucket)
            sample = {
                "bucket": bucket,
                "sample_idx": i,
                "primer": primer,
                "prompt": prompt,
                "ground_truth_cas_expression": rec.get("cas_expression", ""),
                "generated_response": response,
                "compile_valid_anywhere": loose,
                "structured_valid": structured,
            }
            all_samples.append(sample)
            bucket_results.append(sample)
            tag_l = "✓" if loose else " "
            tag_s = "★" if structured else " "
            print(f"  [{bucket} #{i}] L{tag_l} S{tag_s}  primer={primer!r}  -> {response!r}")

        bucket_summary[bucket] = {
            "n_total": len(bucket_results),
            "n_loose_valid": sum(1 for s in bucket_results if s["compile_valid_anywhere"]),
            "n_structured_valid": sum(1 for s in bucket_results if s["structured_valid"]),
        }

    samples_path = args.out_dir / "samples.jsonl"
    with open(samples_path, "w", encoding="utf-8") as f:
        for s in all_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(all_samples)} samples to {samples_path}")

    overall_loose = sum(1 for s in all_samples if s["compile_valid_anywhere"])
    overall_struct = sum(1 for s in all_samples if s["structured_valid"])
    summary = {
        "checkpoint": str(args.checkpoint),
        "primer_strategy": "bucket_conditional_prefix",
        "samples_per_bucket": 5,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "seed": args.seed,
        "overall_loose_valid": overall_loose,
        "overall_structured_valid": overall_struct,
        "buckets": bucket_summary,
    }
    summary_path = args.out_dir / "bucket_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n=== HEADLINE ===")
    print(f"loose-valid: {overall_loose}/{len(all_samples)}")
    print(f"structured-valid: {overall_struct}/{len(all_samples)}")
    for b, info in bucket_summary.items():
        print(f"  {b}: structured={info['n_structured_valid']}/{info['n_total']}, loose={info['n_loose_valid']}/{info['n_total']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
