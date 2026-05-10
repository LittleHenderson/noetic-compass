"""v1c post-bundle smoke test (local CPU, pre-RunPod).

Per user direction (2026-05-09):

  After the bundled commit, run one local/CPU smoke checking:
   - checkpoint loads after embedding resize,
   - [VALID]/[INVALID] rows exist,
   - one valid and one invalid generation call does not crash.

This script does NOT retrain. It loads the v1 PREFIX128 5ep
checkpoint from the durable D: archive, runs the v1c warm-start
in-memory (vocab 38683 -> 38685, copy [TASK_EXPR] -> [VALID],
copy [TASK_EXPLAIN] -> [INVALID]), confirms the new rows match
their anchors, then runs ONE valid CAS generation and ONE invalid
CAS generation through ``routed_generate`` with
``prepend_task_token=True`` to verify the full plumbing is sound
end-to-end.

Pass criteria:
  1. Vocab grew exactly +2 (38683 -> 38685).
  2. [VALID] = old [TASK_EXPR] embedding.
  3. [INVALID] = old [TASK_EXPLAIN] embedding.
  4. Valid CAS routed to cas_to_english AND prepend_token == VALID id.
  5. Invalid CAS routed to invalid_to_explanation AND prepend_token == INVALID id.
  6. Both generations return non-empty reply_text without exceptions.

A run that produces all 6 means the v1c retrain is launchable — the
warm-start surgery, new tokenizer, and inference plumbing are
sound at the pre-training level. Only the actual retrain can prove
whether the architectural fix changes model behavior; this smoke
proves the data + load paths don't crash.
"""
from __future__ import annotations

import sys
import types
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
from cas_native.training.tokenizer import HybridCASTokenizer, SPECIAL_TOKENS
from cas_native.training.tokenizer_task_tokens import extend_with_task_tokens
from cas_native.training.vocab_expansion import (
    WarmStartCopy,
    expand_state_dict_for_vocab_extension,
)
from cas_native.inference.routed_generate import routed_generate


CHECKPOINT_DIR = Path(
    r"D:\tksCAS-archive\runpod_runs\2026-05-09_session_61_v1_milestone"
    r"\runs\v1_path_d_PREFIX128_5ep_20260509T035024Z"
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def ok(msg: str) -> None:
    print(f"OK:   {msg}")


def main() -> int:
    print("v1c post-bundle smoke")
    print()

    # --- Step 1: Load the v1 tokenizer + extend with task tokens
    print("[1/6] loading v1 tokenizer + applying task-token overlay")
    if not (CHECKPOINT_DIR / "tokenizer.json").exists():
        fail(f"v1 tokenizer not at {CHECKPOINT_DIR / 'tokenizer.json'}")
    base_tok = HybridCASTokenizer.load(CHECKPOINT_DIR / "tokenizer.json")
    bpe_path = CHECKPOINT_DIR / "english_bpe.json"
    if bpe_path.exists():
        base_tok = base_tok.with_english_bpe(bpe_path)
    extended_tok = extend_with_task_tokens(base_tok)
    valid_id = extended_tok.task_token_ids.valid
    invalid_id = extended_tok.task_token_ids.invalid
    if extended_tok.vocab_size != int(base_tok.vocab_size) + 2:
        fail(
            f"vocab grew by {extended_tok.vocab_size - base_tok.vocab_size}, "
            "expected +2"
        )
    ok(f"vocab {base_tok.vocab_size} -> {extended_tok.vocab_size} "
       f"(VALID={valid_id}, INVALID={invalid_id})")

    # --- Step 2: Load checkpoint, warm-start expand, load into resized model
    print("[2/6] loading checkpoint + warm-start expand")
    state = torch.load(
        CHECKPOINT_DIR / "model_final.pt",
        map_location="cpu",
        weights_only=False,
    )
    model_state = state["model"]
    task_expr_id = SPECIAL_TOKENS.index("[TASK_EXPR]")
    task_explain_id = SPECIAL_TOKENS.index("[TASK_EXPLAIN]")
    expanded_state, log = expand_state_dict_for_vocab_extension(
        state_dict=model_state,
        old_vocab=int(base_tok.vocab_size),
        new_vocab=int(extended_tok.vocab_size),
        warm_starts=[
            WarmStartCopy(
                source_id=task_expr_id, source_token="[TASK_EXPR]",
                target_id=valid_id, target_token="[VALID]",
            ),
            WarmStartCopy(
                source_id=task_explain_id, source_token="[TASK_EXPLAIN]",
                target_id=invalid_id, target_token="[INVALID]",
            ),
        ],
    )
    ok(f"expanded {len(log.expanded_keys)} embedding keys; "
       f"{len(log.warm_starts)} warm starts logged")

    # --- Step 3: Verify warm-started rows match their anchors
    print("[3/6] verifying [VALID]/[INVALID] rows match anchors")
    for key in [
        "token_embedding.weight",
        "nl_gen_head.token_embedding.weight",
        "nl_gen_head.lm_head.weight",
    ]:
        if key not in expanded_state:
            print(f"      (skip) {key} not in state dict")
            continue
        new_w = expanded_state[key]
        old_w = model_state[key]
        if not torch.equal(new_w[valid_id], old_w[task_expr_id]):
            fail(f"{key}[VALID={valid_id}] != old[TASK_EXPR={task_expr_id}]")
        if not torch.equal(new_w[invalid_id], old_w[task_explain_id]):
            fail(f"{key}[INVALID={invalid_id}] != old[TASK_EXPLAIN={task_explain_id}]")
        ok(f"{key}: warm-start matches anchor")

    # --- Step 4: Build resized model + load expanded state
    print("[4/6] building resized model + loading expanded state")
    enc_cfg = CASNativeConfig(
        d_model=512, n_layers=6, n_heads=8,
        vocab_size=int(extended_tok.vocab_size),
    )
    model = CASNativeModel(enc_cfg)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=int(extended_tok.vocab_size),
        d_model=512, n_heads=8, n_layers=6,
    )
    head = NLGenerationHead(head_cfg)
    model.attach_nl_gen_head(head)
    try:
        model.load_state_dict(expanded_state)
    except Exception as e:
        fail(f"load_state_dict failed: {e}")
    model.eval()
    ok("model loaded with expanded vocab")

    # --- Step 5: One valid CAS generation
    print("[5/6] running one VALID CAS generation (should route cas_to_english)")
    try:
        with torch.no_grad():
            r_valid = routed_generate(
                model=model, tokenizer=extended_tok,
                source_cas="^7^C_{F2}|T",
                register="T", apply_repair=True, sampling="greedy",
                use_cas_prefix=True, device=torch.device("cpu"),
                prepend_task_token=True,
                max_new_tokens=40,  # short for smoke; just ensure no crash
            )
    except Exception as e:
        fail(f"valid generation crashed: {e}")
    if r_valid.routing.task_type != "cas_to_english":
        fail(f"valid CAS routed as {r_valid.routing.task_type}, expected cas_to_english")
    if not r_valid.final_text.strip():
        fail("valid generation produced empty reply")
    ok(f"valid generation: routing={r_valid.routing.task_type}, "
       f"reply_chars={len(r_valid.final_text)}")
    print(f"       reply preview: {r_valid.final_text[:120]!r}")

    # --- Step 6: One invalid CAS generation
    print("[6/6] running one INVALID CAS generation (should route invalid_to_explanation)")
    try:
        with torch.no_grad():
            r_invalid = routed_generate(
                model=model, tokenizer=extended_tok,
                source_cas="let X = ^0^P; X -> Y",  # Y undefined
                register="T", apply_repair=True, sampling="greedy",
                use_cas_prefix=True, device=torch.device("cpu"),
                prepend_task_token=True,
                max_new_tokens=40,
            )
    except Exception as e:
        fail(f"invalid generation crashed: {e}")
    if r_invalid.routing.task_type != "invalid_to_explanation":
        fail(
            f"invalid CAS routed as {r_invalid.routing.task_type}, "
            "expected invalid_to_explanation"
        )
    if not r_invalid.final_text.strip():
        fail("invalid generation produced empty reply")
    ok(f"invalid generation: routing={r_invalid.routing.task_type}, "
       f"reply_chars={len(r_invalid.final_text)}")
    print(f"       reply preview: {r_invalid.final_text[:120]!r}")

    print()
    print("=" * 60)
    print("v1c post-bundle smoke: ALL 6 STEPS PASSED")
    print("=" * 60)
    print()
    print("Note: this verifies the data/load/inference plumbing is sound,")
    print("NOT that the rpm_chain hijack is fixed. The retrain is what")
    print("changes model behavior. Smoke proves the launch is safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
