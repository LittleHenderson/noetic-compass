"""Tests for the fully-native CAS NL generation eval harness.

Verifies:

* CAS-grounding rate hits 1.0 when the classifier perfectly recovers the
  conditioning expression on every record.
* CAS-grounding rate detects per-axis mismatches.
* Fluency perplexity returns a finite number on a tiny val set.
* Diversity distinct-2 = 1.0 when every bigram is unique.
* Diversity distinct-2 -> 0 when all generations are identical (collapse).
* EvalResult carries every load-bearing provenance field.
* Per-bucket breakdown covers all 10×4×7×4 axes (empty buckets allowed).
* Markdown report renders without raising.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
import torch.nn as nn

from cas_native.evaluation import native_nl_generation_eval as ev


# ---------------------------------------------------------------------------
# 1. CAS-grounding: perfect-match case scores 1.0
# ---------------------------------------------------------------------------


def test_cas_grounding_perfect_match_scores_one():
    records = [
        {
            "cas": {
                "noetic": 3,
                "domain": "P",
                "drive": "F2",
                "registers": ["A"],
            },
            "prompt": "Walk me through your reasoning.",
        },
        {
            "cas": {
                "noetic": 2,
                "domain": "C",
                "drive": "F4",
                "registers": ["f"],
            },
            "prompt": "Why is this resonant?",
        },
    ]

    def gen_fn(_model, rec):
        return "echo: " + rec["prompt"]

    def classify_fn(_clf, _text):
        # Perfect oracle.
        return {"noetic": _peek["cas"]["noetic"], "domain": _peek["cas"]["domain"],
                "drive": _peek["cas"]["drive"], "registers": list(_peek["cas"]["registers"])}

    # Inject a closure pointer so classify_fn knows what to return per call.
    # Use a monkeypatch-style closure by overriding gen_fn to also stash the
    # current record under `_peek`.
    _peek: dict = {}

    def gen_fn_(_model, rec):
        _peek.update({"cas": rec["cas"]})
        return "echo: " + rec["prompt"]

    result = ev.evaluate_cas_grounding_rate(
        model=nn.Linear(2, 2),
        eval_records=records,
        checkpoint_id="ckpt-perfect",
        eval_dataset_id="ds-perfect",
        classifier=nn.Linear(1, 1),
        classify_fn=classify_fn,
        generate_fn=gen_fn_,
    )
    assert result.value == pytest.approx(1.0)
    assert result.metric_name == "cas_grounding_rate"


# ---------------------------------------------------------------------------
# 2. CAS-grounding: axis mismatch detected
# ---------------------------------------------------------------------------


def test_cas_grounding_detects_axis_mismatch():
    records = [
        {"cas": {"noetic": 3, "domain": "P", "drive": "F2", "registers": ["A"]},
         "prompt": "test"},
    ]

    def gen_fn(_m, _r):
        return "stub reply"

    def classify_fn(_clf, _text):
        # Wrong noetic -> mismatch on the noetic axis.
        return {"noetic": 7, "domain": "P", "drive": "F2", "registers": ["A"]}

    result = ev.evaluate_cas_grounding_rate(
        model=nn.Linear(1, 1),
        eval_records=records,
        checkpoint_id="ckpt-mismatch",
        eval_dataset_id="ds-mismatch",
        classifier=nn.Linear(1, 1),
        classify_fn=classify_fn,
        generate_fn=gen_fn,
    )
    assert result.value == pytest.approx(0.0)
    # The "3" bucket (the conditioning noetic) had a record but no match.
    assert result.per_bucket_breakdown["noetic"]["3"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 3. Fluency: returns finite perplexity on tiny val set
# ---------------------------------------------------------------------------


class _TinyLM(nn.Module):
    def __init__(self, vocab: int = 16) -> None:
        super().__init__()
        self.vocab = vocab
        self.embed = nn.Embedding(vocab, 8)
        self.lm_head = nn.Linear(8, vocab)

    def forward(self, input_ids, target_ids=None, **_kwargs):
        out = self.embed(input_ids)
        logits = self.lm_head(out)
        return {"logits": logits}


def test_fluency_perplexity_returns_finite():
    model = _TinyLM(vocab=16)
    batch_a = {
        "input_ids": torch.randint(0, 16, (2, 4)),
        "target_ids": torch.randint(0, 16, (2, 4)),
    }
    batch_b = {
        "input_ids": torch.randint(0, 16, (2, 4)),
        "target_ids": torch.randint(0, 16, (2, 4)),
    }
    result = ev.evaluate_fluency_perplexity(
        model,
        [batch_a, batch_b],
        checkpoint_id="ckpt-ppl",
        eval_dataset_id="ds-ppl",
        eval_dataset_hash="hash-ppl",
    )
    assert result.metric_name == "fluency_perplexity"
    assert result.value > 0.0
    assert result.value != float("inf")


# ---------------------------------------------------------------------------
# 4. Diversity distinct-2 = 1.0 on 100% unique bigrams
# ---------------------------------------------------------------------------


def test_diversity_distinct2_all_unique_bigrams():
    gens = ["a b c d e f", "g h i j k l", "m n o p q r"]
    result = ev.evaluate_diversity_distinct2(
        gens,
        checkpoint_id="ckpt-div",
        eval_dataset_id="ds-div",
    )
    assert result.value == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 5. Diversity distinct-2 -> low when generations identical
# ---------------------------------------------------------------------------


def test_diversity_distinct2_collapses_on_identical_generations():
    gens = ["the same thing again", "the same thing again", "the same thing again"]
    result = ev.evaluate_diversity_distinct2(
        gens,
        checkpoint_id="ckpt-div",
        eval_dataset_id="ds-div-collapse",
    )
    # 3 unique bigrams over 9 total = 0.333...
    assert result.value == pytest.approx(1.0 / 3.0, abs=1e-6)
    # Empty input -> 0.0
    empty = ev.evaluate_diversity_distinct2(
        [],
        checkpoint_id="c",
        eval_dataset_id="d",
    )
    assert empty.value == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 6. EvalResult has all provenance fields
# ---------------------------------------------------------------------------


def test_eval_result_has_all_provenance_fields():
    result = ev.EvalResult(
        eval_id="ev-1",
        checkpoint_id="ckpt-1",
        eval_dataset_id="ds-1",
        eval_dataset_hash="abc",
        metric_name="cas_grounding_rate",
        value=0.5,
    )
    d = result.to_dict()
    required = {
        "eval_id",
        "checkpoint_id",
        "eval_dataset_id",
        "eval_dataset_hash",
        "metric_name",
        "value",
        "per_bucket_breakdown",
        "timestamp",
        "schema_version",
        "metadata",
    }
    missing = required - set(d.keys())
    assert not missing, f"EvalResult missing fields: {missing}"
    assert d["schema_version"] == "eval_result.v1"


# ---------------------------------------------------------------------------
# 7. Per-bucket breakdown covers all 10x4x7x4 axes (empty allowed)
# ---------------------------------------------------------------------------


def test_per_bucket_breakdown_covers_all_axes():
    # Empty eval records still yields a structurally-complete bucket map.
    result = ev.evaluate_cas_grounding_rate(
        model=nn.Linear(1, 1),
        eval_records=[],
        checkpoint_id="empty",
        eval_dataset_id="empty",
        classifier=None,
        classify_fn=None,
    )
    breakdown = result.per_bucket_breakdown
    assert set(breakdown.keys()) == {"noetic", "domain", "drive", "register"}
    assert len(breakdown["noetic"]) == 10, "must cover all 10 noetics"
    assert len(breakdown["domain"]) == 4, "must cover P/C/E/O"
    assert len(breakdown["drive"]) == 7, "must cover F1..F7"
    assert len(breakdown["register"]) == 4, "must cover T/A/f/E"


# ---------------------------------------------------------------------------
# 8. Markdown report renders
# ---------------------------------------------------------------------------


def test_markdown_report_renders(tmp_path):
    results = [
        ev.EvalResult(
            eval_id="ev-md-1",
            checkpoint_id="ckpt-md",
            eval_dataset_id="ds-md",
            eval_dataset_hash="hash-md",
            metric_name="cas_grounding_rate",
            value=0.42,
            per_bucket_breakdown={
                "noetic": {str(i): (0.5 if i == 3 else 0.0) for i in range(10)},
                "domain": {d: 0.0 for d in ev.DOMAIN_LABELS},
                "drive": {d: 0.0 for d in ev.DRIVE_LABELS},
                "register": {r: 0.0 for r in ev.REGISTER_LABELS},
            },
            timestamp="2026-05-04T00:00:00Z",
        ),
        ev.EvalResult(
            eval_id="ev-md-2",
            checkpoint_id="ckpt-md",
            eval_dataset_id="ds-md",
            eval_dataset_hash="hash-md",
            metric_name="diversity_distinct_2",
            value=0.91,
            timestamp="2026-05-04T00:00:00Z",
        ),
    ]
    md = ev.render_eval_report_markdown(results)
    assert "CAS-Native NL Generation Eval Report" in md
    assert "cas_grounding_rate" in md
    assert "diversity_distinct_2" in md
    # write_eval_artifacts persists JSON + markdown.
    written = ev.write_eval_artifacts(results, tmp_path)
    assert "report" in written
    assert Path(written["report"]).exists()


# ---------------------------------------------------------------------------
# 9. hash_dataset_bytes is deterministic
# ---------------------------------------------------------------------------


def test_hash_dataset_bytes_deterministic():
    rec = [{"a": 1}, {"b": 2}]
    h1 = ev.hash_dataset_bytes(rec)
    h2 = ev.hash_dataset_bytes(rec)
    assert h1 == h2
    assert ev.hash_dataset_bytes([{"a": 1}, {"b": 3}]) != h1
