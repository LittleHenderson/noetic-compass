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
from cas_native.inference.constrained_sampling import (  # noqa: E402
    CandidateTrieConstraint,
    build_candidate_expressions,
    build_dataset_candidate_expressions,
    candidate_matches_slot_policy,
    candidate_matches_slots,
    candidate_matches_required_terms,
    expression_product_operands,
    expression_slots,
    expression_families,
    filter_candidates_for_prompt,
    infer_prompt_families,
    infer_prompt_slot_policies,
    infer_prompt_slots,
    infer_prompt_required_terms,
)
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
    p.add_argument("--min-new-tokens", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--task",
        choices=("expr", "raw"),
        default="expr",
        help="Prompt formatting. expr uses [TASK_EXPR] [PROMPT] ... [RESPONSE].",
    )
    p.add_argument(
        "--causal-lm",
        dest="causal_lm",
        action="store_true",
        default=None,
        help="Force causal LM mode even if the checkpoint has no model_config.",
    )
    p.add_argument(
        "--no-causal-lm",
        dest="causal_lm",
        action="store_false",
        help="Force bidirectional mode for legacy checkpoints.",
    )
    p.add_argument(
        "--tokenizer",
        type=Path,
        default=None,
        help="Path to tokenizer.json. Defaults to the checkpoint run directory when present.",
    )
    p.add_argument(
        "--decode-mode",
        choices=("free", "grammar", "rerank"),
        default="free",
        help="free samples raw tokens; grammar masks next tokens; rerank scores compiler-valid candidates.",
    )
    p.add_argument(
        "--constraint-max-candidates",
        type=int,
        default=5000,
        help="Maximum compiler-valid candidates to build per bucket for grammar-constrained decoding.",
    )
    p.add_argument(
        "--candidate-source",
        choices=("builtin", "dataset", "hybrid"),
        default="builtin",
        help="Candidate source for grammar/rerank modes. hybrid uses dataset candidates plus builtins.",
    )
    p.add_argument(
        "--rerank-max-candidates",
        type=int,
        default=2000,
        help="Maximum candidates per bucket to score in rerank mode.",
    )
    p.add_argument(
        "--rerank-batch-size",
        type=int,
        default=64,
        help="Number of candidate expressions scored per model forward pass in rerank mode.",
    )
    p.add_argument(
        "--family-filter",
        choices=("none", "prompt"),
        default="none",
        help="prompt filters candidate banks by inferred structural family before grammar/rerank decoding.",
    )
    p.add_argument(
        "--family-filter-min-candidates",
        type=int,
        default=1,
        help="Minimum candidates required after a prompt-family filter before falling back.",
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
    blocked_ids: set[int] | None = None,
    allowed_token_ids: set[int] | None = None,
) -> int:
    """Top-p nucleus sampling with invalid-token masking."""
    logits = logits.float().clone()
    if logits.numel() > tokenizer.vocab_size:
        logits[tokenizer.vocab_size:] = float("-inf")
    if allowed_token_ids is not None:
        allowed = torch.zeros_like(logits, dtype=torch.bool)
        for token_id in allowed_token_ids:
            if 0 <= token_id < logits.numel():
                allowed[token_id] = True
        logits = logits.masked_fill(~allowed, float("-inf"))
    for token_id in tokenizer.disallowed_generation_ids():
        if 0 <= token_id < logits.numel():
            logits[token_id] = float("-inf")
    for token_id in blocked_ids or set():
        if 0 <= token_id < logits.numel():
            logits[token_id] = float("-inf")
    if not torch.isfinite(logits).any():
        raise RuntimeError("no finite logits remain after sampling masks")
    logits = logits / max(temperature, 1e-6)

    sorted_logits, sorted_idx = torch.sort(logits, descending=True)
    probs = torch.softmax(sorted_logits, dim=-1)
    cumprobs = torch.cumsum(probs, dim=-1)
    mask = cumprobs <= top_p
    mask[..., 0] = True
    over_threshold = torch.nonzero(cumprobs > top_p, as_tuple=False)
    if over_threshold.numel() > 0:
        mask[over_threshold[0].item()] = True
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
    min_new_tokens: int,
    temperature: float,
    top_p: float,
    device: torch.device,
    constraint: CandidateTrieConstraint | None = None,
) -> tuple[str, list[int], dict]:
    encoded = tokenizer.encode(prompt, max_length=512)
    if encoded and encoded[-1] == tokenizer.EOS_ID:
        encoded = encoded[:-1]
    input_ids = torch.tensor([encoded], dtype=torch.long, device=device)

    new_token_ids: list[int] = []
    diagnostics = {
        "decode_mode": "grammar" if constraint is not None else "free",
        "candidate_count": constraint.candidate_count if constraint is not None else 0,
        "dead_end_count": 0,
        "allowed_token_counts": [],
        "termination_reason": "max_new_tokens",
    }
    model.eval()
    with torch.no_grad():
        for _ in range(max_new_tokens):
            out = model(input_ids)
            last_logits = out["logits"][0, -1, :]
            blocked_ids = set()
            allowed_token_ids = None
            if constraint is not None:
                decision = constraint.decision(new_token_ids)
                diagnostics["allowed_token_counts"].append(len(decision.allowed_token_ids) + int(decision.allow_eos))
                if not decision.valid_prefix:
                    diagnostics["dead_end_count"] += 1
                    diagnostics["termination_reason"] = "constraint_dead_end"
                    break
                allowed_token_ids = set(decision.allowed_token_ids)
                if decision.allow_eos:
                    allowed_token_ids.add(tokenizer.EOS_ID)
                if not allowed_token_ids:
                    diagnostics["termination_reason"] = "constraint_no_legal_tokens"
                    break
            elif len(new_token_ids) < min_new_tokens:
                blocked_ids.add(tokenizer.EOS_ID)
            tok = sample_token(
                last_logits,
                temperature,
                top_p,
                tokenizer=tokenizer,
                blocked_ids=blocked_ids,
                allowed_token_ids=allowed_token_ids,
            )
            if tok == tokenizer.EOS_ID:
                diagnostics["termination_reason"] = "eos"
                break
            new_token_ids.append(tok)
            next_tensor = torch.tensor([[tok]], dtype=torch.long, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)
            if input_ids.shape[1] >= 512:
                diagnostics["termination_reason"] = "context_limit"
                break

    return decode_ids(tokenizer, new_token_ids), new_token_ids, diagnostics


def candidate_expressions_for_bucket(
    records: list[dict],
    bucket: str,
    *,
    source: str,
    max_candidates: int,
) -> tuple[str, ...]:
    if source == "builtin":
        return build_candidate_expressions(bucket, max_candidates)
    if source == "dataset":
        return build_dataset_candidate_expressions(
            records,
            bucket,
            max_candidates=max_candidates,
            include_builtin=False,
        )
    return build_dataset_candidate_expressions(
        records,
        bucket,
        max_candidates=max_candidates,
        include_builtin=True,
    )


def score_candidate_batch(
    model: CASNativeModel,
    tokenizer: HybridCASTokenizer,
    prompt: str,
    candidates: list[str],
    device: torch.device,
) -> list[dict]:
    """Teacher-force score candidates by prompt-conditioned mean log-prob."""
    prompt_ids = tokenizer.encode(prompt, max_length=512)
    if prompt_ids and prompt_ids[-1] == tokenizer.EOS_ID:
        prompt_ids = prompt_ids[:-1]
    if not prompt_ids:
        raise ValueError("prompt encoded to no tokens")

    encoded_candidates: list[tuple[str, list[int], list[int], list[bool]]] = []
    max_len = 0
    for candidate in candidates:
        candidate_ids = tokenizer.encode(candidate, max_length=512, add_special=False)
        if not candidate_ids:
            continue
        full = prompt_ids + candidate_ids + [tokenizer.EOS_ID]
        if len(full) < 2 or len(full) > 512:
            continue
        input_ids = full[:-1]
        target_ids = full[1:]
        # The logit at position len(prompt_ids)-1 predicts the first candidate
        # token. Everything before that belongs to the prompt and is ignored.
        target_mask = [idx >= len(prompt_ids) - 1 for idx in range(len(target_ids))]
        encoded_candidates.append((candidate, input_ids, target_ids, target_mask))
        max_len = max(max_len, len(input_ids))

    if not encoded_candidates:
        return []

    pad_id = tokenizer.pad_id()
    input_tensor = torch.full((len(encoded_candidates), max_len), pad_id, dtype=torch.long, device=device)
    target_tensor = torch.full((len(encoded_candidates), max_len), pad_id, dtype=torch.long, device=device)
    mask_tensor = torch.zeros((len(encoded_candidates), max_len), dtype=torch.bool, device=device)

    for row, (_, input_ids, target_ids, target_mask) in enumerate(encoded_candidates):
        seq_len = len(input_ids)
        input_tensor[row, :seq_len] = torch.tensor(input_ids, dtype=torch.long, device=device)
        target_tensor[row, :seq_len] = torch.tensor(target_ids, dtype=torch.long, device=device)
        mask_tensor[row, :seq_len] = torch.tensor(target_mask, dtype=torch.bool, device=device)

    out = model(input_tensor)
    log_probs = torch.log_softmax(out["logits"], dim=-1)
    gathered = log_probs.gather(-1, target_tensor.unsqueeze(-1)).squeeze(-1)
    gathered = gathered.masked_fill(~mask_tensor, 0.0)
    token_counts = mask_tensor.sum(dim=1).clamp(min=1)
    sum_logprobs = gathered.sum(dim=1)
    mean_logprobs = sum_logprobs / token_counts

    scored = []
    for row, (candidate, candidate_input, _, _) in enumerate(encoded_candidates):
        scored.append(
            {
                "candidate": candidate,
                "token_count": int(token_counts[row].item()),
                "candidate_token_count": max(len(candidate_input) - len(prompt_ids), 0),
                "sum_logprob": float(sum_logprobs[row].item()),
                "mean_logprob": float(mean_logprobs[row].item()),
            }
        )
    return scored


def rerank_generate(
    model: CASNativeModel,
    tokenizer: HybridCASTokenizer,
    prompt: str,
    candidates: tuple[str, ...],
    device: torch.device,
    *,
    batch_size: int,
) -> tuple[str, list[int], dict]:
    """Choose the highest-probability compiler-valid candidate."""
    scored: list[dict] = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(candidates), batch_size):
            scored.extend(
                score_candidate_batch(
                    model,
                    tokenizer,
                    prompt,
                    list(candidates[start : start + batch_size]),
                    device,
                )
            )
    if not scored:
        return "", [], {
            "decode_mode": "rerank",
            "candidate_count": len(candidates),
            "scored_candidate_count": 0,
            "termination_reason": "no_scoreable_candidates",
        }

    scored.sort(key=lambda item: (item["mean_logprob"], item["sum_logprob"]), reverse=True)
    best = scored[0]
    generated = str(best["candidate"])
    token_ids = tokenizer.encode(generated, max_length=512, add_special=False)
    return generated, token_ids, {
        "decode_mode": "rerank",
        "candidate_count": len(candidates),
        "scored_candidate_count": len(scored),
        "termination_reason": "reranked_candidate",
        "best_mean_logprob": best["mean_logprob"],
        "best_sum_logprob": best["sum_logprob"],
        "best_token_count": best["token_count"],
        "top_candidates": scored[:5],
    }


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
    "meta_logic": re.compile(r"NoeticCluster|StateCluster|StateVariantCluster|RelationCluster|Product|Coordinate|CASCoordinate|Pullback|CoverOf|PartitionOf|∈|⊆|⊂|∪|∩|∖"),
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

    whole_attempt = _attempt("whole", text.strip())
    out["compile_attempts"].append(whole_attempt)
    for frag in extract_cas_fragments(text)[:3]:
        out["compile_attempts"].append(_attempt("fragment", frag))

    out["whole_valid"] = bool(whole_attempt["valid"])
    out["whole_error"] = whole_attempt["error"]
    out["any_valid"] = any(a["valid"] for a in out["compile_attempts"])
    out["fragment_valid"] = any(a["valid"] for a in out["compile_attempts"] if a["label"] == "fragment")
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
    checkpoint_config = dict(ckpt.get("model_config") or {})
    if args.causal_lm is not None:
        causal_lm = bool(args.causal_lm)
    else:
        causal_lm = bool(checkpoint_config.get("causal_lm", args.task == "expr"))
    model = CASNativeModel(CASNativeConfig(
        vocab_size=model_vocab_size,
        causal_lm=causal_lm,
    ))
    print(f"      causal_lm = {causal_lm}")

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

    candidate_banks: dict[str, tuple[str, ...]] = {}
    constraints: dict[str, CandidateTrieConstraint] = {}
    if args.decode_mode in {"grammar", "rerank"}:
        print("[4b/5] Building candidate banks...")
        for b in BUCKETS:
            max_candidates = args.rerank_max_candidates if args.decode_mode == "rerank" else args.constraint_max_candidates
            candidates = candidate_expressions_for_bucket(
                records,
                b,
                source=args.candidate_source,
                max_candidates=max_candidates,
            )
            candidate_banks[b] = candidates
            print(f"      {b}: {len(candidates)} compiler-valid candidates ({args.candidate_source})")
            if args.decode_mode == "grammar":
                constraints[b] = CandidateTrieConstraint(tokenizer, b, candidates=candidates)

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
            base_candidates = candidate_banks.get(bucket, ())
            filter_diagnostics = {
                "family_filter": args.family_filter,
                "prompt_families": list(infer_prompt_families(prompt, bucket)),
                "prompt_required_terms": list(infer_prompt_required_terms(prompt)),
                "prompt_slots": {key: list(value) for key, value in infer_prompt_slots(prompt, bucket).items()},
                "prompt_slot_policies": {key: list(value) for key, value in infer_prompt_slot_policies(prompt, bucket).items()},
                "pre_filter_candidate_count": len(base_candidates),
                "post_filter_candidate_count": len(base_candidates),
                "family_filter_fallback": False,
                "term_filter_fallback": False,
                "slot_filter_fallback": False,
                "policy_filter_fallback": False,
            }
            sample_candidates = base_candidates
            if args.decode_mode in {"grammar", "rerank"} and args.family_filter == "prompt":
                sample_candidates, filter_diagnostics = filter_candidates_for_prompt(
                    base_candidates,
                    prompt,
                    bucket,
                    min_candidates=args.family_filter_min_candidates,
                )
            constraint = constraints.get(bucket)
            if args.decode_mode == "grammar" and args.family_filter == "prompt":
                constraint = CandidateTrieConstraint(tokenizer, bucket, candidates=sample_candidates)
            try:
                if args.decode_mode == "rerank":
                    generated, token_ids, decode_diagnostics = rerank_generate(
                        model,
                        tokenizer,
                        generation_prompt,
                        sample_candidates,
                        device,
                        batch_size=args.rerank_batch_size,
                    )
                else:
                    generated, token_ids, decode_diagnostics = generate(
                        model,
                        tokenizer,
                        generation_prompt,
                        max_new_tokens=args.max_new_tokens,
                        min_new_tokens=args.min_new_tokens,
                        temperature=args.temperature,
                        top_p=args.top_p,
                        device=device,
                        constraint=constraint,
                    )
            except Exception as exc:
                print(f"  [{bucket} #{i}] generation FAILED: {type(exc).__name__}: {exc}")
                generated = ""
                token_ids = []
                decode_diagnostics = {
                    "decode_mode": args.decode_mode,
                    "candidate_count": constraint.candidate_count if constraint is not None else 0,
                    "dead_end_count": 1 if constraint is not None else 0,
                    "allowed_token_counts": [],
                    "termination_reason": f"error:{type(exc).__name__}",
                }
            decode_diagnostics.update(filter_diagnostics)
            compile_result = try_compile(generated, bucket)
            ground_truth = str(rec.get("cas_expression", "") or "").strip()
            generated_families = sorted(expression_families(generated))
            prompt_families = filter_diagnostics.get("prompt_families", [])
            prompt_required_terms = filter_diagnostics.get("prompt_required_terms", [])
            prompt_slots = filter_diagnostics.get("prompt_slots", {})
            prompt_slot_policies = filter_diagnostics.get("prompt_slot_policies", {})
            family_match = not prompt_families or bool(set(prompt_families) & set(generated_families))
            required_terms_applicable = bool(prompt_required_terms)
            required_terms_match = candidate_matches_required_terms(generated, prompt_required_terms)
            generated_slots = expression_slots(generated)
            slot_match_applicable = any(prompt_slots.values())
            slot_match = candidate_matches_slots(generated, prompt_slots)
            slot_policy_match_applicable = any(prompt_slot_policies.values())
            slot_policy_match = candidate_matches_slot_policy(generated, prompt_slots, prompt_slot_policies)
            sample = {
                "bucket": bucket,
                "sample_idx": i,
                "prompt": prompt,
                "generation_prompt": generation_prompt,
                "ground_truth_response": rec.get("response") or rec.get("assistant_response") or "",
                "ground_truth_cas_expression": ground_truth,
                "generated_response": generated,
                "generated_token_ids": token_ids,
                "decode_mode": args.decode_mode,
                "decode_diagnostics": decode_diagnostics,
                "exact_match": generated.strip() == ground_truth,
                "generated_families": generated_families,
                "prompt_families": prompt_families,
                "family_match": family_match,
                "prompt_required_terms": prompt_required_terms,
                "required_terms_applicable": required_terms_applicable,
                "required_terms_match": required_terms_match,
                "generated_slots": {key: list(value) for key, value in generated_slots.items()},
                "generated_product_operands": list(expression_product_operands(generated)),
                "prompt_slots": prompt_slots,
                "slot_match_applicable": slot_match_applicable,
                "slot_match": slot_match,
                "prompt_slot_policies": prompt_slot_policies,
                "slot_policy_match_applicable": slot_policy_match_applicable,
                "slot_policy_match": slot_policy_match,
                "whole_compile_valid": compile_result["whole_valid"],
                "compile_valid_anywhere": compile_result["any_valid"],
                "fragment_compile_valid": compile_result["fragment_valid"],
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
                f"family={family_match} terms={required_terms_match} slots={slot_match} policy={slot_policy_match} "
                f"prompt='{prompt[:60]}...' generated='{generated[:60]}...'"
            )

        required_terms_applicable_count = sum(1 for s in bucket_results if s["required_terms_applicable"])
        required_terms_match_count = sum(
            1 for s in bucket_results if s["required_terms_applicable"] and s["required_terms_match"]
        )
        slot_match_applicable_count = sum(1 for s in bucket_results if s["slot_match_applicable"])
        slot_match_count = sum(1 for s in bucket_results if s["slot_match_applicable"] and s["slot_match"])
        slot_policy_match_applicable_count = sum(1 for s in bucket_results if s["slot_policy_match_applicable"])
        slot_policy_match_count = sum(1 for s in bucket_results if s["slot_policy_match_applicable"] and s["slot_policy_match"])
        bucket_summary[bucket] = {
            "n_total": len(bucket_results),
            "n_exact_match": sum(1 for s in bucket_results if s["exact_match"]),
            "exact_match_rate": sum(1 for s in bucket_results if s["exact_match"]) / max(len(bucket_results), 1),
            "n_family_match": sum(1 for s in bucket_results if s["family_match"]),
            "family_match_rate": sum(1 for s in bucket_results if s["family_match"]) / max(len(bucket_results), 1),
            "n_required_terms_applicable": required_terms_applicable_count,
            "n_required_terms_match": required_terms_match_count,
            "required_terms_match_rate": required_terms_match_count / max(required_terms_applicable_count, 1),
            "n_slot_match_applicable": slot_match_applicable_count,
            "n_slot_match": slot_match_count,
            "slot_match_rate": slot_match_count / max(slot_match_applicable_count, 1),
            "n_slot_policy_match_applicable": slot_policy_match_applicable_count,
            "n_slot_policy_match": slot_policy_match_count,
            "slot_policy_match_rate": slot_policy_match_count / max(slot_policy_match_applicable_count, 1),
            "n_whole_valid": sum(1 for s in bucket_results if s["whole_compile_valid"]),
            "whole_valid_rate": sum(1 for s in bucket_results if s["whole_compile_valid"]) / max(len(bucket_results), 1),
            "n_valid": sum(1 for s in bucket_results if s["compile_valid_anywhere"]),
            "valid_rate": sum(1 for s in bucket_results if s["compile_valid_anywhere"]) / max(len(bucket_results), 1),
            "n_fragment_valid": sum(1 for s in bucket_results if s["fragment_compile_valid"]),
            "fragment_valid_rate": sum(1 for s in bucket_results if s["fragment_compile_valid"]) / max(len(bucket_results), 1),
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
    required_terms_applicable_count = sum(1 for s in all_samples if s["required_terms_applicable"])
    required_terms_match_count = sum(1 for s in all_samples if s["required_terms_applicable"] and s["required_terms_match"])
    slot_match_applicable_count = sum(1 for s in all_samples if s["slot_match_applicable"])
    slot_match_count = sum(1 for s in all_samples if s["slot_match_applicable"] and s["slot_match"])
    slot_policy_match_applicable_count = sum(1 for s in all_samples if s["slot_policy_match_applicable"])
    slot_policy_match_count = sum(1 for s in all_samples if s["slot_policy_match_applicable"] and s["slot_policy_match"])
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "checkpoint": str(args.checkpoint),
                "dataset": str(args.dataset),
                "samples_per_bucket": args.samples_per_bucket,
                "max_new_tokens": args.max_new_tokens,
                "min_new_tokens": args.min_new_tokens,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "seed": args.seed,
                "task": args.task,
                "decode_mode": args.decode_mode,
                "candidate_source": args.candidate_source,
                "family_filter": args.family_filter,
                "family_filter_min_candidates": args.family_filter_min_candidates,
                "constraint_max_candidates": args.constraint_max_candidates,
                "rerank_max_candidates": args.rerank_max_candidates,
                "rerank_batch_size": args.rerank_batch_size,
                "causal_lm": causal_lm,
                "tokenizer": tokenizer.metadata(),
                "tokenizer_path": str(tokenizer_path) if tokenizer_path is not None else None,
                "overall_exact_match_rate": sum(1 for s in all_samples if s["exact_match"]) / max(len(all_samples), 1),
                "overall_family_match_rate": sum(1 for s in all_samples if s["family_match"]) / max(len(all_samples), 1),
                "overall_required_terms_applicable": required_terms_applicable_count,
                "overall_required_terms_match_rate": required_terms_match_count / max(required_terms_applicable_count, 1),
                "overall_slot_match_applicable": slot_match_applicable_count,
                "overall_slot_match_rate": slot_match_count / max(slot_match_applicable_count, 1),
                "overall_slot_policy_match_applicable": slot_policy_match_applicable_count,
                "overall_slot_policy_match_rate": slot_policy_match_count / max(slot_policy_match_applicable_count, 1),
                "overall_whole_valid_rate": sum(1 for s in all_samples if s["whole_compile_valid"]) / max(len(all_samples), 1),
                "overall_valid_rate": sum(1 for s in all_samples if s["compile_valid_anywhere"]) / max(len(all_samples), 1),
                "overall_fragment_valid_rate": sum(1 for s in all_samples if s["fragment_compile_valid"]) / max(len(all_samples), 1),
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
