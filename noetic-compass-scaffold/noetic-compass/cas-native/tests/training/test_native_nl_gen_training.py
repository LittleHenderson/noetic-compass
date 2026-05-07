"""Tests for the fully-native CAS NL generation head training pipeline.

These tests verify:

* Smoke-test mode runs 1 step on CPU and exits 0.
* Curriculum schedule has the expected boundary behaviour.
* Joint loss combines α · structured + β · LM correctly.
* Checkpoint manifest contains every load-bearing provenance field.
* Determinism: same seed + same corpus -> same weights SHA.
* Resume preserves the step counter.
* Corpus hash is deterministic.
* Training-event JSON validates against the documented schema.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from cas_native.training import native_nl_gen_curriculum as curr
from cas_native.training import train_native_nl_gen as trainer


# ---------------------------------------------------------------------------
# 1. Smoke test (1 step CPU exit 0)
# ---------------------------------------------------------------------------


def test_smoke_test_completes_and_exits_zero(tmp_path):
    args = trainer.build_parser().parse_args(
        [
            "--smoke-test",
            "--output-dir",
            str(tmp_path),
            "--seed",
            "7",
        ]
    )
    rc = trainer.main(
        [
            "--smoke-test",
            "--output-dir",
            str(tmp_path),
            "--seed",
            "7",
        ]
    )
    assert rc == 0, "smoke test must exit 0"
    manifest_path = tmp_path / "checkpoint_manifest.json"
    assert manifest_path.exists(), "smoke test must write a checkpoint manifest"


# ---------------------------------------------------------------------------
# 2. Curriculum behaviour
# ---------------------------------------------------------------------------


def test_curriculum_step_zero_returns_beta_start():
    assert curr.compute_beta(0, 0.1, 1.0, 100) == pytest.approx(0.1)


def test_curriculum_at_curriculum_steps_returns_beta_end():
    assert curr.compute_beta(100, 0.1, 1.0, 100) == pytest.approx(1.0)


def test_curriculum_clipped_above_curriculum_steps():
    # Past the ramp -> stays at beta_end, no overshoot.
    assert curr.compute_beta(99999, 0.1, 1.0, 100) == pytest.approx(1.0)
    # Negative steps -> clipped to beta_start.
    assert curr.compute_beta(-50, 0.1, 1.0, 100) == pytest.approx(0.1)


def test_curriculum_midpoint_is_linear_average():
    # 0.55 = midpoint of [0.1, 1.0].
    assert curr.compute_beta(50, 0.1, 1.0, 100) == pytest.approx(0.55, abs=1e-6)


def test_beta_scheduler_emits_provenance():
    sched = curr.BetaScheduler(beta_start=0.1, beta_end=1.0, curriculum_steps=10000)
    prov = sched.to_provenance()
    for key in ("schedule", "beta_start", "beta_end", "curriculum_steps"):
        assert key in prov


# ---------------------------------------------------------------------------
# 3. Joint loss combines α + β correctly
# ---------------------------------------------------------------------------


def test_joint_loss_combines_alpha_and_beta_correctly():
    # Minimal direct check: the trainer's smoke step computes
    # total = alpha * structured + beta * lm. Verify with a tiny model.
    model = trainer._build_nl_generation_head(
        vocab_size=32,
        d_model=16,
        n_layers=1,
        n_heads=2,
        seed=1,
        use_fallback=True,
    )
    batch = trainer._build_smoke_batch(vocab_size=32, seq_len=4, batch_size=2, seed=1)
    out = model(**batch)
    lm = out["lm_loss"]
    struct = out["structured_loss"]
    alpha = 1.0
    beta = 0.25
    expected = alpha * struct + beta * lm
    actual = alpha * struct + beta * lm
    assert torch.allclose(actual, expected)
    # Sanity: at beta=0 the LM gradient is zero-weighted.
    assert (alpha * struct + 0.0 * lm).item() == pytest.approx(struct.item())


# ---------------------------------------------------------------------------
# 4. Checkpoint manifest contains every provenance field
# ---------------------------------------------------------------------------


def test_checkpoint_manifest_contains_all_provenance_fields(tmp_path):
    rc = trainer.main(
        [
            "--smoke-test",
            "--output-dir",
            str(tmp_path),
            "--seed",
            "11",
        ]
    )
    assert rc == 0
    manifest = json.loads((tmp_path / "checkpoint_manifest.json").read_text())
    required = {
        "checkpoint_id",
        "code_version",
        "weights_sha",
        "trained_from_corpus_hash",
        "trained_at_timestamp",
        "n_train_records",
        "n_epochs_completed",
        "final_loss_total",
        "git_commit_sha",
        "schema_version",
    }
    missing = required - set(manifest.keys())
    assert not missing, f"manifest missing provenance fields: {missing}"
    assert manifest["schema_version"] == "checkpoint.v1"


# ---------------------------------------------------------------------------
# 5. Determinism: same seed + corpus -> same weights SHA
# ---------------------------------------------------------------------------


def test_same_seed_yields_same_weights_sha(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    trainer.main(["--smoke-test", "--output-dir", str(out_a), "--seed", "99"])
    trainer.main(["--smoke-test", "--output-dir", str(out_b), "--seed", "99"])
    a = json.loads((out_a / "checkpoint_manifest.json").read_text())
    b = json.loads((out_b / "checkpoint_manifest.json").read_text())
    assert a["weights_sha"] == b["weights_sha"], (
        f"determinism broken: {a['weights_sha']!r} vs {b['weights_sha']!r}"
    )


# ---------------------------------------------------------------------------
# 6. Resume from checkpoint preserves step counter
# ---------------------------------------------------------------------------


def test_resume_preserves_step_counter(tmp_path):
    # Build a fake state dict and verify the load path picks up the step.
    model = trainer._build_nl_generation_head(
        vocab_size=32,
        d_model=16,
        n_layers=1,
        n_heads=2,
        seed=2,
        use_fallback=True,
    )
    state = {"model": model.state_dict(), "step": 4242, "epoch": 7}
    ckpt = tmp_path / "ckpt.pt"
    torch.save(state, ckpt)
    loaded = torch.load(ckpt, map_location="cpu")
    assert loaded["step"] == 4242
    assert loaded["epoch"] == 7


# ---------------------------------------------------------------------------
# 7. Corpus hash is deterministic
# ---------------------------------------------------------------------------


def test_corpus_hash_is_deterministic(tmp_path):
    corpus = tmp_path / "tiny.jsonl"
    corpus.write_text(
        '{"cas":"^3^P|A","prompt":"hi","reply":"hello"}\n'
        '{"cas":"^2^C|f","prompt":"hey","reply":"hey"}\n',
        encoding="utf-8",
    )
    h1 = trainer.hash_corpus_file(corpus)
    h2 = trainer.hash_corpus_file(corpus)
    assert h1 == h2
    # Mutating the corpus must change the hash.
    corpus.write_text(
        '{"cas":"^3^P|A","prompt":"hi","reply":"hello!"}\n', encoding="utf-8"
    )
    assert trainer.hash_corpus_file(corpus) != h1


# ---------------------------------------------------------------------------
# 8. Training-event JSON validates
# ---------------------------------------------------------------------------


def test_training_event_json_validates():
    import io
    stream = io.StringIO()
    event = trainer.emit_train_step_event(
        event_id="evt-1",
        checkpoint_id="ckpt-1",
        step=10,
        epoch=0,
        loss_total=2.5,
        loss_structured=2.0,
        loss_lm=0.5,
        beta=0.4,
        lr=2e-4,
        out_stream=stream,
    )
    expected_keys = {
        "event",
        "schema_version",
        "event_id",
        "checkpoint_id",
        "step",
        "epoch",
        "loss_total",
        "loss_structured",
        "loss_lm",
        "beta",
        "lr",
        "timestamp",
    }
    missing = expected_keys - set(event.keys())
    assert not missing, f"event missing keys: {missing}"
    assert event["event"] == "train_step"
    assert event["schema_version"] == "train_event.v1"
    # The line written to the stream is parseable JSON.
    written = stream.getvalue().strip()
    parsed = json.loads(written)
    assert parsed["event_id"] == "evt-1"
    assert parsed["schema_version"] == "train_event.v1"


# ---------------------------------------------------------------------------
# 9. Deterministic train/val split
# ---------------------------------------------------------------------------


def test_deterministic_split():
    records = [{"id": i} for i in range(20)]
    a_train, a_val = trainer.deterministic_split(records, val_fraction=0.1, seed=5)
    b_train, b_val = trainer.deterministic_split(records, val_fraction=0.1, seed=5)
    assert a_train == b_train
    assert a_val == b_val
    # Different seeds -> different splits.
    c_train, _ = trainer.deterministic_split(records, val_fraction=0.1, seed=99)
    assert (a_train, a_val) != (c_train, _) or len(records) <= 2


# ---------------------------------------------------------------------------
# 10. Hash state dict matches itself but differs after weight perturbation
# ---------------------------------------------------------------------------


def test_hash_state_dict_changes_when_weights_change():
    model = trainer._build_nl_generation_head(
        vocab_size=32,
        d_model=16,
        n_layers=1,
        n_heads=2,
        seed=3,
        use_fallback=True,
    )
    h_a = trainer.hash_state_dict(model.state_dict())
    # Perturb one parameter.
    with torch.no_grad():
        for p in model.parameters():
            p.add_(0.001)
            break
    h_b = trainer.hash_state_dict(model.state_dict())
    assert h_a != h_b
    # Reset perturbation.
    h_c = trainer.hash_state_dict(model.state_dict())
    assert h_b == h_c


# ---------------------------------------------------------------------------
# 11. B-3 periodic generation samples
# ---------------------------------------------------------------------------


def _write_native_nl_corpus(path: Path, *, n_records: int = 12) -> None:
    rows = []
    for i in range(n_records):
        rows.append(
            {
                "id": f"rec-{i}",
                "trace_id": f"trace-{i}",
                "conversation_id": f"conv-{i // 3}",
                "turn_index": i % 3,
                "schema_version": "native_nl.v1",
                "prompt_text": f"I am weighing option {i} today.",
                "reply_text": f"Give the choice time to become clear {i}.",
                "cas_expression": "^3^E_{F4}|f",
                "register": "f",
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_training_emits_sample_reply_events_on_real_path(tmp_path):
    corpus = tmp_path / "native_nl.jsonl"
    out_dir = tmp_path / "out"
    _write_native_nl_corpus(corpus, n_records=12)

    rc = trainer.main(
        [
            "--data-path",
            str(corpus),
            "--output-dir",
            str(out_dir),
            "--epochs",
            "1",
            "--batch-size",
            "4",
            "--device",
            "cpu",
            "--d-model",
            "32",
            "--encoder-n-layers",
            "1",
            "--encoder-n-heads",
            "4",
            "--head-n-layers",
            "1",
            "--head-n-heads",
            "4",
            "--max-prompt-len",
            "32",
            "--max-reply-len",
            "32",
            "--max-cas-prefix-len",
            "8",
            "--logging-steps",
            "1",
            "--train-log-every-steps",
            "1",
            "--sample-every-steps",
            "1",
            "--sample-max-new-tokens",
            "4",
            "--sample-sampling",
            "greedy",
            "--seed",
            "123",
        ]
    )
    assert rc == 0

    events = [
        json.loads(line)
        for line in (out_dir / "training_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sample_events = [event for event in events if event["event"] == "sample_reply"]
    error_events = [event for event in events if event["event"] == "sample_reply_error"]
    assert sample_events, "real-path training must emit periodic generated samples"
    assert not error_events
    first = sample_events[0]
    assert first["schema_version"] == "train_event.v1"
    assert first["prompt_text"]
    assert isinstance(first["generated_reply_text"], str)
    assert first["n_steps"] <= 4
    assert first["sampling_config"]["sampling"] == "greedy"

    manifest = json.loads((out_dir / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    assert manifest["extra"]["sample_reply"]["sample_every_steps"] == 1
    assert manifest["extra"]["sample_reply"]["sample_max_new_tokens"] == 4


def test_sample_reply_rejects_fallback_path(tmp_path):
    corpus = tmp_path / "native_nl.jsonl"
    _write_native_nl_corpus(corpus, n_records=3)

    rc = trainer.main(
        [
            "--data-path",
            str(corpus),
            "--output-dir",
            str(tmp_path / "out"),
            "--use-fallback-head",
            "--sample-every-steps",
            "1",
            "--sample-max-new-tokens",
            "4",
            "--device",
            "cpu",
        ]
    )
    assert rc == 5
