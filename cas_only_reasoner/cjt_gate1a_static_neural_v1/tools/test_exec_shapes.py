"""test_exec_shapes.py -- CPU-only synthetic-tensor proofs of the frozen exec code.

Owner-authorized CPU use (audit 2026-08-31 section 2): "Use synthetic tensors and
tiny CPU-only shape tests to prove" the declared properties. NO model is loaded;
no real activation exists; nothing here is claim-bearing. Proves:

  1. every arm produces the declared shapes (variable Ideas + candidates, masked)
  2. every arm's trainable parameter count is within +/-1% of S3's
  3. S6 is structurally IDENTICAL to S3 except the profile input
  4. S7 has the IDENTICAL coupler structure
  5. corrupted-label arms cannot read gold at runtime (assembled examples carry
     no gold class labels; S4 differs from gold on 100% of Ideas; S5 on ~75%)
  6. candidate masks and variable candidate counts work (-inf at pads)
  7. no protected data path reaches assembly or training
  8. GPU_REQUIRED fires at every guarded neural entry BEFORE anything else
     (provable on this box precisely because it has no CUDA)
plus span mapping, candidate encoding, schedule, layer selection, budget gate,
and receipt-field laws.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

import torch  # noqa: E402

from exec.arms import (ARM_IDS, ARM_STRUCT, CAPACITY_TOLERANCE,  # noqa: E402
                       build_arm_head, matched_heads, trainable_param_count)
from exec.dataset_assembly import ProtectedPathError, assemble_examples  # noqa: E402
from exec.gpu_guard import GpuRequiredError  # noqa: E402
from exec.labels import one_hot, profile_vectors, s7_taxonomy_label  # noqa: E402
from exec.layer_select import select_layer  # noqa: E402
from exec.spans import (SpanMappingFailure, build_input_text,  # noqa: E402
                        clause_char_spans, token_spans)
from exec.candidate_encoding import encode_candidates  # noqa: E402
from exec.train_loop import lr_lambda, run_training  # noqa: E402
from exec.launcher import campaign_budget_gate  # noqa: E402
from exec.receipts import build_receipt  # noqa: E402

REGISTERED_VERBS = ["drawn", "pulled", "felt", "captured", "withdrew", "repelled",
                    "recoiled", "backed", "broke", "lay", "split", "made",
                    "brought", "thought", "reminded", "summoned"]


def load_records(n=60):
    lines = (PKG / "data" / "candidate" / "train.jsonl").read_text(
        encoding="utf-8").splitlines()[:n]
    return [json.loads(x) for x in lines]


def test_capacity_and_shapes():
    heads = matched_heads()
    ref = heads["S3"][2]
    print(f"  S3 reference trainable parameters: {ref}")
    for arm, (head, w, count) in heads.items():
        rel = abs(count - ref) / ref
        assert rel <= CAPACITY_TOLERANCE, f"{arm}: {count} vs {ref} ({rel:.4f})"
        print(f"  {arm}: params={count} widen_w={w} rel_diff={rel:.5f}")
    torch.manual_seed(0)
    B, N, C = 3, 6, 9
    h = torch.randn(B, N, 896)
    g = torch.randn(B, 896)
    p = torch.randn(B, N, 4).softmax(-1)
    idea_mask = torch.tensor([[1] * 3 + [0] * 3, [1] * 4 + [0] * 2, [1] * 6]).bool()
    cand_enc = torch.randn(B, C, 896)
    cand_mask = torch.tensor([[1] * 5 + [0] * 4, [1] * 9, [1] * 7 + [0] * 2]).bool()
    for arm, (head, w, _) in heads.items():
        logits = head(h, g, p if ARM_STRUCT[arm]["profiles"] else None,
                      idea_mask, cand_enc, cand_mask)
        assert logits.shape == (B, C), f"{arm}: {logits.shape}"
        assert (logits[0, 5:] == torch.finfo(logits.dtype).min).all(), \
            f"{arm}: masked candidates not at the mask floor"
        assert int(logits[0].argmax()) < 5, f"{arm}: argmax escaped the mask"
        assert torch.isfinite(logits[cand_mask]).all(), f"{arm}: nonfinite valid logits"
    print("PASS capacity matched within 1% + declared shapes + candidate masks")


def test_structural_identity():
    s3 = build_arm_head("S3", 0)
    for arm in ("S4", "S5", "S6", "S7"):
        m = build_arm_head(arm, 0)
        k3 = {k: tuple(v.shape) for k, v in s3.state_dict().items()}
        km = {k: tuple(v.shape) for k, v in m.state_dict().items()}
        assert k3 == km, f"{arm} structure differs from S3"
    k0 = {k: tuple(v.shape) for k, v in build_arm_head("S0", 0).state_dict().items()}
    assert k0 != {k: tuple(v.shape) for k, v in s3.state_dict().items()}
    print("PASS S4/S5/S6/S7 structurally identical to S3; S0 differs (sanity)")


def test_labels_cannot_read_gold():
    records = load_records()
    verb_to_class = {v: i % 4 for i, v in enumerate(REGISTERED_VERBS)}
    total = s4_diff = s5_diff = 0
    for arm in ARM_IDS:
        exs = assemble_examples(records, arm, verb_to_class=verb_to_class)
        for ex in exs:
            assert "idea_labels" not in ex and "seed_trace" not in ex, \
                f"{arm}: gold labels leaked into the assembled example"
    for rec in records:
        gold = [one_hot(c) for c in rec["idea_labels"]]
        p4 = profile_vectors("S4", rec)
        p5 = profile_vectors("S5", rec)
        p6 = profile_vectors("S6", rec)
        for i in range(len(gold)):
            total += 1
            s4_diff += int(p4[i] != gold[i])
            s5_diff += int(p5[i] != gold[i])
            assert p6[i] == [0.25, 0.25, 0.25, 0.25]
    assert s4_diff == total, f"S4 must differ from gold on 100%: {s4_diff}/{total}"
    assert 0.60 <= s5_diff / total <= 0.90, f"S5 differ rate {s5_diff / total:.3f}"
    assert profile_vectors("S4", records[0]) == profile_vectors("S4", records[0])
    print(f"PASS gold isolation: S4 differs {s4_diff}/{total} (100%), "
          f"S5 differs {s5_diff / total:.1%} (~75% expected), S6 uniform, "
          "no gold fields in any assembled example")


def test_s7_reads_surface_only():
    verb_to_class = {v: i % 4 for i, v in enumerate(REGISTERED_VERBS)}
    assert s7_taxonomy_label("mira withdrew from jazz.", verb_to_class) \
        == verb_to_class["withdrew"]
    try:
        s7_taxonomy_label("mira ignored jazz.", verb_to_class)
        raise AssertionError("unregistered clause must fail closed")
    except ValueError as exc:
        assert "TAXONOMY_LOOKUP_FAILURE" in str(exc)
    print("PASS S7 labels come from the clause surface; unregistered verbs fail closed")


def test_protected_path_refused():
    rec = load_records(1)[0]
    fake = dict(rec, split="protected")
    try:
        assemble_examples([fake], "S3")
        raise AssertionError("protected record reached assembly")
    except ProtectedPathError:
        pass
    exs = assemble_examples([fake], "S3", allow_protected=True)   # evaluator-only path
    assert exs[0]["split"] == "protected"
    print("PASS protected records refused at assembly (evaluator-only override works)")


def test_gpu_required_fires_first():
    assert not torch.cuda.is_available(), "this proof needs a CUDA-less box"
    for name, call in [
        ("run_training", lambda: run_training("S3", 11, 0, [], [])),
    ]:
        try:
            call()
            raise AssertionError(f"{name} ran without a GPU")
        except GpuRequiredError as exc:
            assert "GPU_REQUIRED" in str(exc)
    from exec.protected_eval import run_protected_evaluation
    try:
        run_protected_evaluation(PKG, [], None, None, None, Path("x"))
        raise AssertionError("protected evaluation ran without a GPU")
    except GpuRequiredError as exc:
        assert "GPU_REQUIRED" in str(exc)
    print("PASS GPU_REQUIRED fires before any work at every guarded neural entry")


def test_spans_and_encoding():
    rec = load_records(1)[0]
    text = build_input_text(rec)
    spans, qspan = clause_char_spans(rec)
    for (s0, s1), cl in zip(spans, rec["clauses"]):
        assert text[s0:s1] == cl["text"]
    assert text[qspan[0]:qspan[1]] == rec["question"]
    om = [(i, i + 1) for i in range(len(text))]          # 1 char = 1 token synthetic
    idea_toks, q_toks = token_spans(spans, qspan, om)
    assert idea_toks[0][0] == 0 and q_toks[-1] == len(text) - 1
    try:
        token_spans([(5, 5)], qspan, om)                 # empty span -> zero tokens
        raise AssertionError("zero-token clause must abort")
    except SpanMappingFailure:
        pass
    emb = torch.randn(50, 8)
    enc = encode_candidates(["ab", "c"], lambda s: [ord(c) % 50 for c in s],
                            lambda ids: emb[torch.tensor(ids)])
    assert enc.shape == (2, 8)
    try:
        encode_candidates(["x"], lambda s: [], lambda ids: emb[torch.tensor(ids)])
        raise AssertionError("0-token candidate must fail")
    except ValueError:
        pass
    print("PASS span mapping (incl. SPAN_MAPPING_FAILURE) + context-free encoding")


def test_schedule_and_selection_and_policy():
    assert lr_lambda(0) < 0.01 and abs(lr_lambda(149) - 1.0) < 0.01
    assert lr_lambda(2999) < 0.001
    assert select_layer({6: 0.5, 12: 0.7, 18: 0.7, 24: 0.6}) == 12  # tie -> lowest
    try:
        select_layer({6: 0.5})
        raise AssertionError("wrong layer set must fail")
    except ValueError:
        pass
    try:
        campaign_budget_gate(115.0, 2.0, 5.0, 120.0)
        raise AssertionError("budget gate must refuse")
    except RuntimeError as exc:
        assert "COST_CEILING_REFUSAL" in str(exc)
    campaign_budget_gate(100.0, 2.0, 5.0, 120.0)         # 110 <= 120: allowed
    try:
        build_receipt(job_id="x")
        raise AssertionError("thin receipt must fail")
    except ValueError as exc:
        assert "RECEIPT_INVALID" in str(exc)
    print("PASS warmup/cosine schedule + layer selection + budget gate + receipt law")


def main():
    test_capacity_and_shapes()
    test_structural_identity()
    test_labels_cannot_read_gold()
    test_s7_reads_surface_only()
    test_protected_path_refused()
    test_gpu_required_fires_first()
    test_spans_and_encoding()
    test_schedule_and_selection_and_policy()
    print("ALL EXEC SHAPE TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
