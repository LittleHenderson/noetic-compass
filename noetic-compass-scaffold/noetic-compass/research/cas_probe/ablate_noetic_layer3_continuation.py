"""Stage 3.1 - continuation ablation of the layer-3 noetic subspace.

Stage 3 showed a narrow negative result: removing the layer-3 noetic
probe subspace did not change Pythia-160M's immediate next-token argmax
on the held-out prompts. Audit found that every baseline top token was
just a newline, so Stage 3 mostly tested "does ablation change newline?"

This script keeps the same ablation construction but forces a semantic
continuation before comparing baseline vs ablated generations.

Run:

    python noetic-compass-scaffold/noetic-compass/research/cas_probe/ablate_noetic_layer3_continuation.py

For a quick smoke:

    python .../ablate_noetic_layer3_continuation.py --limit 5

The script is research-only. It loads Pythia from the local Hugging Face
cache with ``local_files_only=True`` so this rerun does not silently pull
network state into the experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_TODAY = "20260515"

_ACTIVATIONS_PATH = _HERE / f"pythia_probe_activations_{_TODAY}.npz"
_PROBES_PATH = _HERE / f"pythia_noetic_probes_{_TODAY}.npz"
_PROBES_REPORT_PATH = _HERE / f"pythia_noetic_probes_report_{_TODAY}.json"
_LABELS_PATH = _HERE / f"pythia_probe_labels_{_TODAY}.jsonl"
_OUT_REPORT = _HERE / f"pythia_ablation_layer3_continuation_{_TODAY}.json"

_MODEL_NAME = "EleutherAI/pythia-160m"
_TARGET_LAYER_INDEX = 3
_HOOK_BLOCK_INDEX = _TARGET_LAYER_INDEX - 1

_PROMPT_TEMPLATES = [
    {
        "name": "in_other_words",
        "suffix": "\nIn other words,",
    },
    {
        "name": "this_concept_means",
        "suffix": "\nThis concept means",
    },
    {
        "name": "good_explanation",
        "suffix": "\nA good explanation is",
    },
]


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _first_divergence(a: list[int], b: list[int]) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def _token_match_rate(a: list[int], b: list[int]) -> float:
    if not a and not b:
        return 1.0
    denom = max(len(a), len(b), 1)
    n = min(len(a), len(b))
    matches = sum(1 for i in range(n) if a[i] == b[i])
    return matches / denom


def _softmax_kl(torch: Any, p_logits: Any, q_logits: Any) -> float:
    p = torch.softmax(p_logits.double(), dim=-1)
    q = torch.softmax(q_logits.double(), dim=-1)
    eps = 1e-30
    return float(
        torch.sum(
            p.clamp_min(eps)
            * (torch.log(p.clamp_min(eps)) - torch.log(q.clamp_min(eps)))
        ).item()
    )


def _build_projection(np: Any) -> dict[str, Any]:
    act = np.load(_ACTIVATIONS_PATH, allow_pickle=False)
    probes = np.load(_PROBES_PATH, allow_pickle=False)

    X = act["X"]
    y = act["y"]
    sample_ids = act["sample_ids"]
    coefs = probes["coefs"]
    intercepts = probes["intercepts"]
    scaler_mean = probes["scaler_mean"]
    scaler_scale = probes["scaler_scale"]
    idx_test = probes["idx_test"]

    with _PROBES_REPORT_PATH.open(encoding="utf-8") as fh:
        probes_report = json.load(fh)
    headline_layer = int(probes_report["headline_layer"]["layer"])
    if headline_layer != _TARGET_LAYER_INDEX:
        raise SystemExit(
            f"headline layer is {headline_layer}; this script ablates "
            f"layer {_TARGET_LAYER_INDEX}. Update constants before running."
        )

    layer = _TARGET_LAYER_INDEX
    w_std = coefs[layer]
    sigma = scaler_scale[layer]
    sigma_safe = np.where(sigma == 0, 1e-8, sigma)
    w_raw = w_std / sigma_safe[None, :]

    _U, S, Vh = np.linalg.svd(w_raw, full_matrices=False)
    threshold = S.max() * 1e-6
    basis_rows = Vh[S > threshold]
    P = basis_rows.T @ basis_rows

    # Same sanity gate as Stage 3: prove we removed what the probe reads.
    h_raw = X[:, layer, :]
    h_ablated_raw = h_raw - h_raw @ P
    mu = scaler_mean[layer]
    h_std = (h_raw - mu) / sigma_safe
    h_ablated_std = (h_ablated_raw - mu) / sigma_safe

    def probe_logits(h_std_input: Any) -> Any:
        return h_std_input @ w_std.T + intercepts[layer][None, :]

    preds_unablated = np.argmax(probe_logits(h_std), axis=1)
    preds_ablated = np.argmax(probe_logits(h_ablated_std), axis=1)
    acc_unablated = float(np.mean(preds_unablated[idx_test] == y[idx_test]))
    acc_ablated = float(np.mean(preds_ablated[idx_test] == y[idx_test]))

    return {
        "X": X,
        "y": y,
        "sample_ids": sample_ids,
        "idx_test": idx_test,
        "projection": P,
        "rank": int(basis_rows.shape[0]),
        "probe_accuracy_unablated": acc_unablated,
        "probe_accuracy_ablated": acc_ablated,
        "sanity_pass": bool(acc_ablated <= 0.20),
    }


def _load_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    with _LABELS_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels[row["sample_id"]] = row["english"]
    return labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of held-out records to run for a smoke test.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=24,
        help="Greedy continuation length per prompt.",
    )
    args = parser.parse_args()

    for p in (_ACTIVATIONS_PATH, _PROBES_PATH, _PROBES_REPORT_PATH, _LABELS_PATH):
        if not p.is_file():
            raise SystemExit(f"missing prerequisite: {p}")

    try:
        import numpy as np
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        print(
            f"missing dependency: {exc}\n"
            f"  pip install numpy torch transformers",
            file=sys.stderr,
        )
        return 2

    activations_sha = _sha256_of_file(_ACTIVATIONS_PATH)
    probes_sha = _sha256_of_file(_PROBES_PATH)
    print(f"activations sha256: {activations_sha}")
    print(f"probes sha256:      {probes_sha}")

    projection_info = _build_projection(np)
    print(f"noetic subspace rank: {projection_info['rank']}")
    print(
        "probe sanity: "
        f"{projection_info['probe_accuracy_unablated']:.3f} -> "
        f"{projection_info['probe_accuracy_ablated']:.3f} "
        f"(pass={projection_info['sanity_pass']})"
    )
    if not projection_info["sanity_pass"]:
        raise SystemExit("ablation sanity gate failed; refusing continuation test.")

    labels = _load_labels()
    idx_test = projection_info["idx_test"]
    sample_ids = [str(s) for s in projection_info["sample_ids"]]
    y = projection_info["y"]
    selected_indices = idx_test.tolist()
    if args.limit is not None:
        selected_indices = selected_indices[: args.limit]

    print(f"loading {_MODEL_NAME} from local cache only ...")
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=True)
    model.eval()
    device = torch.device("cpu")
    model.to(device)

    P_t = torch.tensor(
        projection_info["projection"], dtype=torch.float32, device=device
    )
    block = model.gpt_neox.layers[_HOOK_BLOCK_INDEX]

    def make_ablate_hook() -> Any:
        def hook(_module: Any, _input: Any, output: Any) -> Any:
            if isinstance(output, tuple):
                hs = output[0]
                hs_ablated = hs - hs @ P_t.to(hs.dtype)
                return (hs_ablated,) + output[1:]
            return output - output @ P_t.to(output.dtype)

        return hook

    def greedy_continuation(prompt: str, *, ablated: bool) -> dict[str, Any]:
        encoded = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        ).to(device)
        generated = encoded["input_ids"].clone()
        new_tokens: list[int] = []
        first_logits = None

        handle = block.register_forward_hook(make_ablate_hook()) if ablated else None
        try:
            with torch.no_grad():
                for step in range(args.max_new_tokens):
                    attention_mask = torch.ones_like(generated, device=device)
                    out = model(
                        input_ids=generated,
                        attention_mask=attention_mask,
                        use_cache=False,
                    )
                    logits = out.logits[0, -1, :]
                    if step == 0:
                        first_logits = logits.detach().cpu()
                    next_id = int(torch.argmax(logits).item())
                    new_tokens.append(next_id)
                    generated = torch.cat(
                        [
                            generated,
                            torch.tensor([[next_id]], dtype=generated.dtype, device=device),
                        ],
                        dim=1,
                    )
                    if tokenizer.eos_token_id is not None and next_id == tokenizer.eos_token_id:
                        break
        finally:
            if handle is not None:
                handle.remove()

        if first_logits is None:
            raise RuntimeError("no logits produced")
        return {
            "new_token_ids": new_tokens,
            "text": tokenizer.decode(new_tokens, skip_special_tokens=True),
            "first_logits": first_logits,
            "first_top1_id": new_tokens[0] if new_tokens else None,
            "first_top1_str": tokenizer.decode([new_tokens[0]]) if new_tokens else "",
        }

    per_case: list[dict[str, Any]] = []
    started = time.perf_counter()
    n_total = len(selected_indices) * len(_PROMPT_TEMPLATES)

    for rec_i, test_idx in enumerate(selected_indices):
        sid = sample_ids[test_idx]
        text = labels[sid].rstrip()
        true_y = int(y[test_idx])

        for template in _PROMPT_TEMPLATES:
            prompt = text + template["suffix"]
            baseline = greedy_continuation(prompt, ablated=False)
            ablated = greedy_continuation(prompt, ablated=True)

            base_ids = baseline["new_token_ids"]
            abl_ids = ablated["new_token_ids"]
            first_kl = _softmax_kl(
                torch, baseline["first_logits"], ablated["first_logits"]
            )
            divergence = _first_divergence(base_ids, abl_ids)
            exact_match = base_ids == abl_ids
            token_match = _token_match_rate(base_ids, abl_ids)

            per_case.append(
                {
                    "sample_id": sid,
                    "true_y": true_y,
                    "template": template["name"],
                    "prompt_suffix": template["suffix"],
                    "baseline_text": baseline["text"],
                    "ablated_text": ablated["text"],
                    "baseline_token_ids": base_ids,
                    "ablated_token_ids": abl_ids,
                    "exact_token_sequence_match": exact_match,
                    "token_match_rate": token_match,
                    "first_divergence_token_index": divergence,
                    "first_step_top1_match": baseline["first_top1_id"]
                    == ablated["first_top1_id"],
                    "first_step_kl_baseline_to_ablated": first_kl,
                    "baseline_first_top1_id": baseline["first_top1_id"],
                    "baseline_first_top1_str": baseline["first_top1_str"],
                    "ablated_first_top1_id": ablated["first_top1_id"],
                    "ablated_first_top1_str": ablated["first_top1_str"],
                }
            )

        done = (rec_i + 1) * len(_PROMPT_TEMPLATES)
        if done % 15 == 0 or done == n_total:
            elapsed = time.perf_counter() - started
            print(f"  [{done}/{n_total}] elapsed={elapsed:.1f}s")

    n_cases = len(per_case)
    n_exact = sum(1 for c in per_case if c["exact_token_sequence_match"])
    n_first_match = sum(1 for c in per_case if c["first_step_top1_match"])
    token_match_mean = sum(c["token_match_rate"] for c in per_case) / max(1, n_cases)
    first_kl_mean = (
        sum(c["first_step_kl_baseline_to_ablated"] for c in per_case)
        / max(1, n_cases)
    )
    first_kl_sorted = sorted(c["first_step_kl_baseline_to_ablated"] for c in per_case)
    first_kl_median = first_kl_sorted[len(first_kl_sorted) // 2] if first_kl_sorted else 0.0

    baseline_first_counter = Counter(
        repr(c["baseline_first_top1_str"]) for c in per_case
    )
    ablated_first_counter = Counter(repr(c["ablated_first_top1_str"]) for c in per_case)

    exact_rate = n_exact / max(1, n_cases)
    first_match_rate = n_first_match / max(1, n_cases)

    if first_match_rate >= 0.95 and exact_rate >= 0.95:
        verdict = "CONTINUATION_NO_CAUSAL_BITE"
    elif token_match_mean >= 0.80:
        verdict = "CONTINUATION_SMALL_CAUSAL_EFFECT"
    else:
        verdict = "CONTINUATION_CAUSAL_EFFECT_PRESENT"

    print()
    print("Stage 3.1 continuation effect:")
    print(f"  cases: {n_cases}")
    print(f"  first-step top1 match: {n_first_match}/{n_cases} ({first_match_rate:.3f})")
    print(f"  full continuation exact match: {n_exact}/{n_cases} ({exact_rate:.3f})")
    print(f"  mean token match rate: {token_match_mean:.3f}")
    print(f"  first-step KL mean: {first_kl_mean:.4f}")
    print(f"  first-step KL median: {first_kl_median:.4f}")
    print(f"  baseline first-token distribution: {dict(baseline_first_counter)}")
    print(f"  ablated first-token distribution: {dict(ablated_first_counter)}")
    print(f"VERDICT: {verdict}")

    out_path = _OUT_REPORT
    if args.limit is not None:
        out_path = _HERE / f"pythia_ablation_layer3_continuation_smoke_{_TODAY}.json"

    report = {
        "schema_version": "pythia_ablation_layer3_continuation_report.v1",
        "experiment": (
            "Stage 3.1 - semantic continuation ablation of layer-3 "
            "noetic subspace on Pythia-160M"
        ),
        "model_name": _MODEL_NAME,
        "local_files_only": True,
        "target_layer_index": _TARGET_LAYER_INDEX,
        "hook_block_index": _HOOK_BLOCK_INDEX,
        "activations_file": _ACTIVATIONS_PATH.name,
        "activations_sha256": activations_sha,
        "probes_file": _PROBES_PATH.name,
        "probes_sha256": probes_sha,
        "subspace_rank": int(projection_info["rank"]),
        "max_new_tokens": int(args.max_new_tokens),
        "prompt_templates": _PROMPT_TEMPLATES,
        "limit": args.limit,
        "probe_self_ablation_sanity_gate": {
            "probe_accuracy_unablated": projection_info["probe_accuracy_unablated"],
            "probe_accuracy_ablated": projection_info["probe_accuracy_ablated"],
            "pass_threshold": 0.20,
            "pass": bool(projection_info["sanity_pass"]),
        },
        "continuation_effect": {
            "records": int(len(selected_indices)),
            "cases": int(n_cases),
            "first_step_top1_match_count": int(n_first_match),
            "first_step_top1_match_rate": first_match_rate,
            "exact_continuation_match_count": int(n_exact),
            "exact_continuation_match_rate": exact_rate,
            "mean_token_match_rate": token_match_mean,
            "first_step_kl_baseline_to_ablated_mean": first_kl_mean,
            "first_step_kl_baseline_to_ablated_median": first_kl_median,
            "baseline_first_token_distribution": dict(baseline_first_counter),
            "ablated_first_token_distribution": dict(ablated_first_counter),
        },
        "decision_thresholds": {
            "no_causal_bite_requires_first_step_top1_match_rate_min": 0.95,
            "no_causal_bite_requires_exact_continuation_match_rate_min": 0.95,
            "small_causal_effect_token_match_rate_min": 0.80,
        },
        "verdict": verdict,
        "verdict_text": (
            "Continuation prompts force Pythia past the newline artifact. "
            "This report compares greedy baseline continuations against "
            "greedy continuations with the layer-3 noetic probe subspace "
            "removed. It measures token behavior only; semantic CAS "
            "interpretation still requires human audit of changed text."
        ),
        "per_case": per_case,
    }
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"report written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
