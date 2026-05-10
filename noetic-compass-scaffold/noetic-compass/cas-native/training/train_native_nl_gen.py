"""Training script for the fully-native CAS NL generation head.

This is the production training pipeline for the *fully-native* CAS English
generation head. No foreign pretrained weights are loaded. The decoder is
random-initialized so the model is trained end-to-end from scratch on the
synthetic ``(CAS, prompt, reply)`` corpus produced by the parallel SDG agent.

Object provenance is load-bearing. Every artifact this script produces —
checkpoints, training records, eval results — carries full provenance
metadata. Given a checkpoint on disk, every event leading up to it is
auditable.

Curriculum on the joint loss::

    L = α · L_structured + β(step) · L_LM

with α held fixed and β linearly ramped via
``cas_native.training.native_nl_gen_curriculum``.

Smoke-test mode: ``--smoke-test`` runs 1 step on CPU against a tiny
synthetic batch and exits 0; suitable for CI and pre-flight checks before
launching the multi-day GPU run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import types
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import torch
import torch.nn as nn

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError):  # pragma: no cover - Python < 3.7
    pass


# Path bootstrap for direct ``python train_native_nl_gen.py`` invocation.
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


from cas_native.training.native_nl_gen_curriculum import BetaScheduler, compute_beta


CODE_VERSION = "v0.1.0"
CHECKPOINT_SCHEMA_VERSION = "checkpoint.v1"
TRAIN_EVENT_SCHEMA_VERSION = "train_event.v1"


# ---------------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------------


def hash_corpus_file(path: str | Path) -> str:
    """Return SHA-256 of the corpus file bytes."""
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_state_dict(state_dict: dict[str, torch.Tensor]) -> str:
    """Deterministic SHA-256 over a state_dict's tensor bytes."""
    h = hashlib.sha256()
    for key in sorted(state_dict.keys()):
        tensor = state_dict[key]
        h.update(key.encode("utf-8"))
        h.update(b"|")
        if isinstance(tensor, torch.Tensor):
            arr = tensor.detach().to("cpu").contiguous().to(torch.float32).numpy()
            h.update(arr.tobytes())
        else:
            h.update(str(tensor).encode("utf-8"))
    return h.hexdigest()


def get_git_commit_sha() -> str:
    """Best-effort git HEAD SHA. Empty string if git not available."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_PROJECT_ROOT),
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode("ascii").strip()
    except Exception:  # pragma: no cover - defensive
        return ""


def utc_iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Manifest dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CheckpointManifest:
    """Full provenance manifest for a saved checkpoint."""

    checkpoint_id: str
    code_version: str
    weights_sha: str
    trained_from_corpus_hash: str
    trained_at_timestamp: str
    n_train_records: int
    n_epochs_completed: int
    final_loss_total: float
    git_commit_sha: str
    schema_version: str = CHECKPOINT_SCHEMA_VERSION
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "code_version": self.code_version,
            "weights_sha": self.weights_sha,
            "trained_from_corpus_hash": self.trained_from_corpus_hash,
            "trained_at_timestamp": self.trained_at_timestamp,
            "n_train_records": int(self.n_train_records),
            "n_epochs_completed": int(self.n_epochs_completed),
            "final_loss_total": float(self.final_loss_total),
            "git_commit_sha": self.git_commit_sha,
            "schema_version": self.schema_version,
            "extra": dict(self.extra),
        }


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------


def _build_nl_generation_head(
    *,
    vocab_size: int,
    d_model: int = 512,
    n_layers: int = 6,
    n_heads: int = 8,
    seed: int = 42,
    use_fallback: bool = False,
) -> nn.Module:
    """Build the NL generation head, random-initialized, no foreign weights.

    Two paths:

    * Real path (default): build the production
      :class:`cas_native.model.nl_generation_head.NLGenerationHead`. This
      head is meant to be attached to a :class:`CASNativeModel` via
      ``attach_nl_gen_head`` and driven through ``forward_with_lm``; calling
      its ``forward`` directly without the encoder will fail with a
      missing-argument error.
    * Fallback path: opt-in via ``use_fallback=True``. Returns the tiny
      :class:`_FallbackNLGenerationHead` whose ``forward(input_ids,
      target_ids, struct_targets, ...)`` shape is suitable for hermetic CPU
      smoke tests and for legacy callers that have not yet wired the
      encoder. The real path NEVER silently falls back — an import or
      construction error raises rather than downgrading.
    """
    torch.manual_seed(int(seed))
    if use_fallback:
        return _FallbackNLGenerationHead(
            vocab_size=int(vocab_size),
            d_model=int(d_model),
            n_layers=int(n_layers),
            n_heads=int(n_heads),
        )
    from cas_native.model.nl_generation_head import (  # type: ignore[import-not-found]
        NLGenerationHead,
        NLGenerationHeadConfig,
    )
    cfg = NLGenerationHeadConfig(
        vocab_size=int(vocab_size),
        d_model=int(d_model),
        n_layers=int(n_layers),
        n_heads=int(n_heads),
    )
    return NLGenerationHead(cfg)


def save_tokenizer_artifacts(
    tokenizer: Any,
    out_dir: Path,
    *,
    english_bpe_path: str = "",
) -> dict[str, Any]:
    """Persist the tokenizer (and any composed BPE artifact) under ``out_dir``.

    A checkpoint is only reusable if the vocab that produced it is colocated.
    This helper ensures ``tokenizer.json`` is always written when a real
    tokenizer is in play. For the composed ``ExtendedHybridCASTokenizer``
    (CAS reserved + English BPE), the helper writes the base tokenizer to
    ``tokenizer.json`` and copies the BPE artifact to ``english_bpe.json``
    so the checkpoint directory is fully self-contained — no dependency on
    the original source paths surviving.

    Returns a dict suitable for inclusion in ``CheckpointManifest.extra``.

    Raises:
        RuntimeError: if neither the tokenizer nor its ``.base`` exposes
            ``save()``. Silent skip is unacceptable — a generation
            checkpoint without its tokenizer cannot be loaded back.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    provenance: dict[str, Any] = {}
    base_for_save = getattr(tokenizer, "base", None)
    is_extended = base_for_save is not None and base_for_save is not tokenizer

    tokenizer_out = out_dir / "tokenizer.json"
    if hasattr(tokenizer, "save") and not is_extended:
        tokenizer.save(tokenizer_out)
    elif base_for_save is not None and hasattr(base_for_save, "save"):
        base_for_save.save(tokenizer_out)
    else:
        raise RuntimeError(
            "tokenizer cannot be saved for checkpoint provenance — "
            "neither tokenizer nor tokenizer.base exposes save()"
        )
    provenance["tokenizer_path"] = str(tokenizer_out)
    provenance["tokenizer_hash"] = hash_corpus_file(tokenizer_out)
    provenance["vocab_size"] = int(getattr(tokenizer, "vocab_size", 0))
    provenance["tokenizer_kind"] = type(tokenizer).__name__

    if english_bpe_path:
        bpe_src = Path(english_bpe_path)
        if not bpe_src.exists():
            raise FileNotFoundError(
                f"english_bpe_path does not exist: {english_bpe_path}"
            )
        bpe_dst = out_dir / "english_bpe.json"
        shutil.copy2(bpe_src, bpe_dst)
        provenance["english_bpe_path"] = str(bpe_dst)
        provenance["english_bpe_hash"] = hash_corpus_file(bpe_dst)
        provenance["english_bpe_source_path"] = str(bpe_src)
        if hasattr(tokenizer, "metadata"):
            try:
                provenance["tokenizer_metadata"] = tokenizer.metadata()
            except Exception:
                pass

    return provenance


def _build_cas_native_model_with_head(
    *,
    vocab_size: int,
    d_model: int = 512,
    n_layers: int = 6,
    n_heads: int = 8,
    head_n_layers: int = 6,
    head_n_heads: int = 8,
    seed: int = 42,
) -> nn.Module:
    """Build a full :class:`CASNativeModel` and attach a real :class:`NLGenerationHead`.

    d_model is enforced to match between encoder and head. Mismatch raises
    rather than silently projecting.
    """
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    from cas_native.model.nl_generation_head import (
        NLGenerationHead,
        NLGenerationHeadConfig,
    )

    torch.manual_seed(int(seed))
    enc_cfg = CASNativeConfig(
        d_model=int(d_model),
        n_layers=int(n_layers),
        n_heads=int(n_heads),
        vocab_size=int(vocab_size),
    )
    encoder = CASNativeModel(enc_cfg)

    head_cfg = NLGenerationHeadConfig(
        vocab_size=int(vocab_size),
        d_model=int(d_model),
        n_heads=int(head_n_heads),
        n_layers=int(head_n_layers),
    )
    head = NLGenerationHead(head_cfg)

    if encoder.config.d_model != head.config.d_model:
        raise ValueError(
            f"d_model mismatch: CASNativeModel={encoder.config.d_model}, "
            f"NLGenerationHead={head.config.d_model}. Match them at construction."
        )
    encoder.attach_nl_gen_head(head)
    return encoder


class _FallbackNLGenerationHead(nn.Module):
    """Tiny random-init decoder used when the parallel model agent has not
    yet shipped the real ``NLGenerationHead``.

    Architecture:
      - token embedding
      - N standard transformer decoder layers
      - LM head (vocab projection)
      - structured-prediction projection used to compute ``L_structured``

    The forward returns a dict with ``logits``, ``lm_loss``, ``structured_loss``,
    ``total_loss``, mirroring the contract the real head will expose.
    """

    def __init__(
        self,
        *,
        vocab_size: int,
        d_model: int = 64,
        n_layers: int = 2,
        n_heads: int = 4,
    ) -> None:
        super().__init__()
        self.vocab_size = int(vocab_size)
        self.d_model = int(d_model)
        self.embed = nn.Embedding(self.vocab_size, self.d_model)
        layer = nn.TransformerDecoderLayer(
            d_model=self.d_model,
            nhead=int(n_heads),
            dim_feedforward=self.d_model * 2,
            batch_first=True,
            dropout=0.0,
        )
        self.decoder = nn.TransformerDecoder(layer, num_layers=int(n_layers))
        self.lm_head = nn.Linear(self.d_model, self.vocab_size)
        self.struct_head = nn.Linear(self.d_model, 32)
        # Explicit random init.
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(
        self,
        input_ids: torch.Tensor,
        target_ids: torch.Tensor | None = None,
        struct_targets: torch.Tensor | None = None,
        **kwargs: Any,
    ) -> dict[str, torch.Tensor]:
        emb = self.embed(input_ids)
        # Self-attended decoder w/ no cross memory: use embeddings as memory.
        out = self.decoder(emb, emb)
        logits = self.lm_head(out)
        result: dict[str, torch.Tensor] = {"logits": logits, "hidden_states": out}
        if target_ids is not None:
            shifted_logits = logits.reshape(-1, self.vocab_size)
            shifted_targets = target_ids.reshape(-1)
            lm_loss = nn.functional.cross_entropy(
                shifted_logits, shifted_targets, ignore_index=-100
            )
            result["lm_loss"] = lm_loss
        pooled = out.mean(dim=1)
        struct_logits = self.struct_head(pooled)
        result["struct_logits"] = struct_logits
        if struct_targets is not None:
            struct_loss = nn.functional.cross_entropy(struct_logits, struct_targets)
            result["structured_loss"] = struct_loss
        return result


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_corpus(path: str | Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Load a JSONL corpus of ``{cas, prompt, reply}`` records."""
    path = Path(path)
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit is not None and len(records) >= int(limit):
                break
    return records


def deterministic_split(
    records: list[dict[str, Any]],
    *,
    val_fraction: float = 0.05,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Seeded 95/5 train/val split."""
    rng = random.Random(int(seed))
    indices = list(range(len(records)))
    rng.shuffle(indices)
    n_val = max(1, int(round(len(records) * float(val_fraction)))) if records else 0
    val_idx = set(indices[:n_val])
    train = [records[i] for i in range(len(records)) if i not in val_idx]
    val = [records[i] for i in range(len(records)) if i in val_idx]
    return train, val


# ---------------------------------------------------------------------------
# Synthetic data for the smoke test
# ---------------------------------------------------------------------------


def _build_smoke_batch(
    *,
    vocab_size: int = 64,
    seq_len: int = 8,
    batch_size: int = 2,
    seed: int = 42,
) -> dict[str, torch.Tensor]:
    """One tiny synthetic batch for the CPU smoke test."""
    g = torch.Generator().manual_seed(int(seed))
    input_ids = torch.randint(
        0, int(vocab_size), (int(batch_size), int(seq_len)), generator=g
    )
    target_ids = torch.randint(
        0, int(vocab_size), (int(batch_size), int(seq_len)), generator=g
    )
    struct_targets = torch.randint(0, 32, (int(batch_size),), generator=g)
    return {
        "input_ids": input_ids,
        "target_ids": target_ids,
        "struct_targets": struct_targets,
    }


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------


def emit_train_step_event(
    *,
    event_id: str,
    checkpoint_id: str,
    step: int,
    epoch: int,
    loss_total: float,
    loss_structured: float,
    loss_lm: float,
    beta: float,
    lr: float,
    out_stream: Any = sys.stdout,
) -> dict[str, Any]:
    """Print + return the structured ``train_step`` event."""
    event = {
        "event": "train_step",
        "schema_version": TRAIN_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "checkpoint_id": checkpoint_id,
        "step": int(step),
        "epoch": int(epoch),
        "loss_total": float(loss_total),
        "loss_structured": float(loss_structured),
        "loss_lm": float(loss_lm),
        "beta": float(beta),
        "lr": float(lr),
        "timestamp": utc_iso_now(),
    }
    try:
        out_stream.write(json.dumps(event, sort_keys=True) + "\n")
        out_stream.flush()
    except Exception:  # pragma: no cover
        pass
    return event


def _record_task_type(record: dict[str, Any]) -> str:
    """Best-effort extraction of the per-record task type for logging.

    Path D records carry ``v1mix_task_type``; older records may carry
    ``task_type`` or ``slot``. Returns an empty string when none are
    set (event field stays present but empty for downstream parsers).
    """
    for key in ("v1mix_task_type", "task_type", "slot"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _record_category(record: dict[str, Any]) -> str:
    """Best-effort extraction of the per-record category for logging.

    Path D Wave 2.5 records carry ``category`` (e.g. ``rpm_chain``,
    ``compound_state``, ``v76_production``). Returns empty when not
    present.
    """
    value = record.get("category")
    if isinstance(value, str) and value.strip():
        return value
    return ""


def emit_sample_reply_event(
    *,
    event_id: str,
    checkpoint_id: str,
    step: int,
    epoch: int,
    sample_index: int,
    record: dict[str, Any],
    generated: dict[str, Any],
    out_stream: Any = sys.stdout,
) -> dict[str, Any]:
    """Write a ``sample_reply`` event for qualitative B-3 monitoring."""
    event = {
        "event": "sample_reply",
        "schema_version": TRAIN_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "checkpoint_id": checkpoint_id,
        "step": int(step),
        "epoch": int(epoch),
        "sample_index": int(sample_index),
        "record_id": str(record.get("id", "")),
        "trace_id": str(record.get("trace_id", "")),
        "conversation_id": str(record.get("conversation_id", "")),
        "turn_index": record.get("turn_index"),
        "task_type": _record_task_type(record),
        "category": _record_category(record),
        "prompt_text": _record_text(record, ("prompt_text", "prompt")),
        "target_reply_text": _record_text(record, ("reply_text", "reply")),
        "generated_reply_text": str(generated.get("reply_text", "")),
        "cas_expression": _record_text(record, ("cas_expression",)),
        "register": str(record.get("register", "T")),
        "n_steps": int(generated.get("n_steps", 0)),
        "stopped_on_eos": bool(generated.get("stopped_on_eos", False)),
        "sampling_config": dict(generated.get("config", {})),
        "token_ids_preview": list(generated.get("token_ids", []))[:32],
        "timestamp": utc_iso_now(),
    }
    line = json.dumps(event, sort_keys=True)
    try:
        out_stream.write(line + "\n")
        out_stream.flush()
    except Exception:  # pragma: no cover
        pass
    print(line, flush=True)
    return event


def emit_sample_reply_error_event(
    *,
    event_id: str,
    checkpoint_id: str,
    step: int,
    epoch: int,
    sample_index: int,
    record: dict[str, Any],
    error: Exception,
    out_stream: Any = sys.stdout,
) -> dict[str, Any]:
    """Write a non-fatal sampling error event and keep training moving."""
    event = {
        "event": "sample_reply_error",
        "schema_version": TRAIN_EVENT_SCHEMA_VERSION,
        "event_id": event_id,
        "checkpoint_id": checkpoint_id,
        "step": int(step),
        "epoch": int(epoch),
        "sample_index": int(sample_index),
        "record_id": str(record.get("id", "")),
        "trace_id": str(record.get("trace_id", "")),
        "task_type": _record_task_type(record),
        "category": _record_category(record),
        "prompt_text": _record_text(record, ("prompt_text", "prompt")),
        "cas_expression": _record_text(record, ("cas_expression",)),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": utc_iso_now(),
    }
    line = json.dumps(event, sort_keys=True)
    try:
        out_stream.write(line + "\n")
        out_stream.flush()
    except Exception:  # pragma: no cover
        pass
    print(line, flush=True)
    return event


def _record_text(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string value for ``keys``."""
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


# ---------------------------------------------------------------------------
# Smoke-test runner
# ---------------------------------------------------------------------------


def run_smoke_test(args: argparse.Namespace) -> int:
    """1-step CPU smoke. Returns 0 on success."""
    torch.manual_seed(int(args.seed))
    random.seed(int(args.seed))
    batch = _build_smoke_batch(
        vocab_size=64, seq_len=8, batch_size=2, seed=int(args.seed)
    )
    model = _build_nl_generation_head(
        vocab_size=64,
        d_model=32,
        n_layers=2,
        n_heads=4,
        seed=int(args.seed),
        use_fallback=True,
    )
    model.train()
    optim = torch.optim.AdamW(model.parameters(), lr=float(args.lr))

    beta = compute_beta(
        step=0,
        beta_start=float(args.beta_lm_start),
        beta_end=float(args.beta_lm_end),
        curriculum_steps=int(args.beta_curriculum_steps),
    )
    out = model(**batch)
    loss_lm = out.get("lm_loss", torch.tensor(0.0))
    loss_struct = out.get("structured_loss", torch.tensor(0.0))
    if not isinstance(loss_lm, torch.Tensor):
        loss_lm = torch.tensor(float(loss_lm))
    if not isinstance(loss_struct, torch.Tensor):
        loss_struct = torch.tensor(float(loss_struct))
    total = float(args.alpha_structured) * loss_struct + beta * loss_lm
    optim.zero_grad(set_to_none=True)
    total.backward()
    optim.step()

    checkpoint_id = str(uuid.uuid4())
    event = emit_train_step_event(
        event_id=str(uuid.uuid4()),
        checkpoint_id=checkpoint_id,
        step=0,
        epoch=0,
        loss_total=float(total.item()),
        loss_structured=float(loss_struct.item()),
        loss_lm=float(loss_lm.item()),
        beta=beta,
        lr=float(args.lr),
    )
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = CheckpointManifest(
        checkpoint_id=checkpoint_id,
        code_version=CODE_VERSION,
        weights_sha=hash_state_dict(model.state_dict()),
        trained_from_corpus_hash="smoke_synthetic",
        trained_at_timestamp=utc_iso_now(),
        n_train_records=int(batch["input_ids"].shape[0]),
        n_epochs_completed=0,
        final_loss_total=float(total.item()),
        git_commit_sha=get_git_commit_sha(),
        extra={"smoke_test": True, "first_event_id": event["event_id"]},
    )
    with (out_dir / "checkpoint_manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest.to_dict(), fh, indent=2, sort_keys=True)
    print(json.dumps({"event": "smoke_test_ok", "checkpoint_id": checkpoint_id}))
    return 0


# ---------------------------------------------------------------------------
# Real training run
# ---------------------------------------------------------------------------


def run_training(args: argparse.Namespace) -> int:
    """Full training run.

    Two execution modes, both load the corpus from ``--data-path``:

    * Real path (default): builds a full ``CASNativeModel``, attaches a
      ``NLGenerationHead`` via ``attach_nl_gen_head``, runs every batch
      through ``forward_with_lm``, and computes a reply-only masked
      cross-entropy on ``out["lm_logits"]``. Records are tokenized live
      via ``NativeNLCollator``. Records must carry ``prompt_text`` /
      ``reply_text`` / ``cas_expression``; pre-tokenized records are
      ignored on this path.
    * Fallback path (``--use-fallback-head``): legacy
      ``_FallbackNLGenerationHead`` driven by the pre-tokenized
      ``input_ids`` / ``target_ids`` records. For hermetic CI and legacy
      callers; not used for production training.
    """
    from cas_native.training.datasets.native_nl_collator import NativeNLCollator
    from cas_native.training.masked_ce_loss import masked_cross_entropy

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "training_events.jsonl"

    # Validate observability cadence — modulo-by-zero is silent and corrupts
    # the train_progress signal, so reject early.
    if int(args.train_log_every_steps) <= 0:
        print(json.dumps({
            "event": "fatal",
            "reason": "train_log_every_steps_must_be_positive",
            "got": int(args.train_log_every_steps),
        }))
        return 4

    if not args.data_path:
        print(json.dumps({"event": "fatal", "reason": "no_data_path"}))
        return 2
    corpus_hash = hash_corpus_file(args.data_path)
    records = load_corpus(args.data_path, limit=args.limit)
    if not records:
        print(json.dumps({"event": "fatal", "reason": "empty_corpus"}))
        return 3
    train_records, val_records = deterministic_split(
        records, val_fraction=0.05, seed=int(args.seed)
    )

    seed = int(args.seed)
    torch.manual_seed(seed)
    random.seed(seed)
    device = torch.device(args.device)

    use_fallback = bool(getattr(args, "use_fallback_head", False))
    use_cas_prefix = bool(getattr(args, "use_cas_prefix", False))
    sample_every_steps = int(getattr(args, "sample_every_steps", 0) or 0)
    sample_max_new_tokens = int(getattr(args, "sample_max_new_tokens", 0) or 0)
    if sample_every_steps < 0:
        print(json.dumps({
            "event": "fatal",
            "reason": "sample_every_steps_must_be_non_negative",
            "got": sample_every_steps,
        }))
        return 5
    if sample_every_steps > 0 and sample_max_new_tokens <= 0:
        print(json.dumps({
            "event": "fatal",
            "reason": "sample_max_new_tokens_must_be_positive",
            "got": sample_max_new_tokens,
        }))
        return 5
    if sample_every_steps > 0 and use_fallback:
        print(json.dumps({
            "event": "fatal",
            "reason": "sample_reply_requires_real_generation_path",
        }))
        return 5

    generate_reply_fn = None
    sample_record_index = int(getattr(args, "sample_record_index", 0) or 0)
    sample_indices_arg = str(getattr(args, "sample_record_indices", "") or "").strip()
    sample_pool: list[dict[str, Any]] = []
    sample_rotation: list[tuple[int, dict[str, Any]]] = []
    sample_rotation_pos = 0
    if sample_every_steps > 0:
        from cas_native.inference.native_nl_generate import generate_reply

        generate_reply_fn = generate_reply
        sample_pool = val_records if val_records else train_records
        if not sample_pool:
            print(json.dumps({
                "event": "fatal",
                "reason": "sample_reply_requested_but_no_val_or_train_records",
            }))
            return 5
        # Resolve rotation indices. --sample-record-indices wins when set;
        # otherwise fall back to a single-element rotation built from the
        # legacy --sample-record-index flag (preserves prior behavior).
        raw_indices: list[int] = []
        if sample_indices_arg:
            for token in sample_indices_arg.split(","):
                token = token.strip()
                if not token:
                    continue
                try:
                    raw_indices.append(int(token))
                except ValueError:
                    print(json.dumps({
                        "event": "fatal",
                        "reason": "sample_record_indices_not_integer",
                        "token": token,
                    }))
                    return 5
        else:
            raw_indices = [sample_record_index]
        # Dedupe while preserving order; clamp into pool bounds.
        seen: set[int] = set()
        for idx in raw_indices:
            wrapped = idx % len(sample_pool)
            if wrapped in seen:
                continue
            seen.add(wrapped)
            sample_rotation.append((wrapped, sample_pool[wrapped]))
        if not sample_rotation:
            print(json.dumps({
                "event": "fatal",
                "reason": "sample_rotation_empty_after_resolution",
            }))
            return 5
        # Emit a rotation manifest so the run history names which records
        # are being sampled before the first generation event fires.
        print(json.dumps({
            "event": "sample_rotation_pool",
            "n_records": len(sample_rotation),
            "indices": [i for i, _ in sample_rotation],
            "record_ids": [str(r.get("id", "")) for _, r in sample_rotation],
            "task_types": [_record_task_type(r) for _, r in sample_rotation],
            "categories": [_record_category(r) for _, r in sample_rotation],
        }))

    # Tokenizer provenance — recorded in checkpoint_manifest so a checkpoint
    # is never separated from the vocab needed to decode it.
    tokenizer_provenance: dict[str, Any] = {}

    if use_fallback:
        # Legacy path: pre-tokenized records, fallback head, single forward call.
        vocab_size = int(getattr(args, "vocab_size", 0) or 32000)
        model = _build_nl_generation_head(
            vocab_size=vocab_size,
            d_model=int(args.d_model),
            n_layers=int(args.head_n_layers),
            n_heads=int(args.head_n_heads),
            seed=seed,
            use_fallback=True,
        ).to(device)
        collator = None
        tokenizer = None
    else:
        # Real path: build tokenizer (frozen on this corpus's text), build the
        # full encoder + head pipeline, prepare a live collator.
        from cas_native.training.tokenizer import HybridCASTokenizer

        loaded_from_path = ""
        if getattr(args, "tokenizer_path", ""):
            tokenizer = HybridCASTokenizer.load(args.tokenizer_path)
            loaded_from_path = str(args.tokenizer_path)
        else:
            tokenizer = HybridCASTokenizer.from_records(train_records, freeze=True)

        # Optional English BPE composition for fluent generation. The base
        # HybridCASTokenizer alone is acceptable for CPU smoke; production
        # generation uses the extended path.
        english_bpe_path = str(getattr(args, "english_bpe_path", "") or "")
        if english_bpe_path:
            tokenizer = tokenizer.with_english_bpe(english_bpe_path)

        # Option C task-token overlay (commit ebd5be1 + this bundle).
        # When --prepend-task-token is set, wrap the (already-extended)
        # tokenizer with [VALID]/[INVALID] at IDs vocab_size and
        # vocab_size+1. The wrapped tokenizer claims +2 vocab, which
        # the model construction below picks up automatically.
        prepend_task_token = bool(getattr(args, "prepend_task_token", False))
        task_token_id_for_callback = None
        wrapped_pre_task_vocab = int(tokenizer.vocab_size)
        if prepend_task_token:
            from cas_native.training.tokenizer_task_tokens import (
                extend_with_task_tokens,
            )
            tokenizer = extend_with_task_tokens(tokenizer)
            task_token_id_for_callback = tokenizer.task_token_ids.for_task_type

        # Save tokenizer + (when set) BPE artifact into out_dir; raises
        # loudly if the tokenizer cannot be persisted (silent skip is
        # unacceptable for checkpoint provenance).
        tokenizer_provenance = save_tokenizer_artifacts(
            tokenizer,
            out_dir,
            english_bpe_path=english_bpe_path,
        )
        if loaded_from_path:
            tokenizer_provenance["loaded_from_path"] = loaded_from_path
        tokenizer_provenance["use_cas_prefix"] = use_cas_prefix
        tokenizer_provenance["prepend_task_token"] = prepend_task_token
        if prepend_task_token:
            tokenizer_provenance["task_token_ids"] = {
                "valid": tokenizer.task_token_ids.valid,
                "invalid": tokenizer.task_token_ids.invalid,
            }

        vocab_size = int(tokenizer.vocab_size)
        model = _build_cas_native_model_with_head(
            vocab_size=vocab_size,
            d_model=int(args.d_model),
            n_layers=int(args.encoder_n_layers),
            n_heads=int(args.encoder_n_heads),
            head_n_layers=int(args.head_n_layers),
            head_n_heads=int(args.head_n_heads),
            seed=seed,
        ).to(device)
        collator = NativeNLCollator(
            tokenizer,
            max_prompt_len=int(args.max_prompt_len),
            max_reply_len=int(args.max_reply_len),
            max_cas_prefix_len=int(args.max_cas_prefix_len),
            prepend_task_token=prepend_task_token,
            task_token_id_for=task_token_id_for_callback,
        )

    if args.resume_from:
        resume_path = Path(args.resume_from)
        state = torch.load(resume_path, map_location=device)
        model_state = state["model"]
        # If the checkpoint's vocab is smaller than the model's
        # current vocab (Option C v1 -> v1c), expand embedding rows
        # via warm-start from semantic anchors.
        # Detect by inspecting any state-dict tensor whose first dim
        # is supposed to be vocab. We assume the model has at least
        # one such weight matching the pattern.
        # Probe canonical vocab-shaped keys directly. The earlier
        # heuristic "min first-dim of any 'embedding'-keyed tensor"
        # is wrong: ``cognitive_embedding.projection.*`` also contains
        # the word ``embedding`` and has first dim 40 (the cognitive
        # state count), which collapsed ``old_vocab`` to 40 and caused
        # the warm-start to incorrectly resize every cognitive head.
        # Token-vocab tensors live at well-known keys; use those.
        canonical_vocab_keys = (
            "token_embedding.weight",
            "nl_gen_head.token_embedding.weight",
            "lm_head.weight",
            "nl_gen_head.lm_head.weight",
        )
        old_vocab_candidates = set()
        for key in canonical_vocab_keys:
            tensor = model_state.get(key)
            if isinstance(tensor, torch.Tensor) and tensor.dim() >= 2:
                old_vocab_candidates.add(int(tensor.shape[0]))
        if not old_vocab_candidates:
            old_vocab = vocab_size  # nothing to detect; assume no resize
        elif len(old_vocab_candidates) > 1:
            raise RuntimeError(
                f"checkpoint has inconsistent vocab dims across "
                f"canonical keys: {sorted(old_vocab_candidates)}"
            )
        else:
            old_vocab = next(iter(old_vocab_candidates))
        warm_start_log = None
        if old_vocab != vocab_size:
            from cas_native.training.vocab_expansion import (
                WarmStartCopy,
                expand_state_dict_for_vocab_extension,
            )
            if not prepend_task_token:
                raise RuntimeError(
                    f"checkpoint vocab {old_vocab} != current vocab "
                    f"{vocab_size} but --prepend-task-token is OFF; "
                    "cannot vocab-expand without warm-start anchors"
                )
            # Anchor IDs are the existing [TASK_EXPR] / [TASK_EXPLAIN]
            # special-token positions in the wrapped tokenizer's base.
            # Their IDs are in the underlying HybridCASTokenizer at
            # the canonical SPECIAL_TOKENS positions (7 and 8).
            from cas_native.training.tokenizer import SPECIAL_TOKENS
            task_expr_id = SPECIAL_TOKENS.index("[TASK_EXPR]")
            task_explain_id = SPECIAL_TOKENS.index("[TASK_EXPLAIN]")
            valid_id = tokenizer.task_token_ids.valid
            invalid_id = tokenizer.task_token_ids.invalid
            warm_starts = [
                WarmStartCopy(
                    source_id=task_expr_id, source_token="[TASK_EXPR]",
                    target_id=valid_id, target_token="[VALID]",
                ),
                WarmStartCopy(
                    source_id=task_explain_id, source_token="[TASK_EXPLAIN]",
                    target_id=invalid_id, target_token="[INVALID]",
                ),
            ]
            model_state, warm_start_log = expand_state_dict_for_vocab_extension(
                state_dict=model_state,
                old_vocab=old_vocab,
                new_vocab=vocab_size,
                warm_starts=warm_starts,
            )
            print(json.dumps({
                "event": "vocab_expansion",
                "old_vocab": old_vocab,
                "new_vocab": vocab_size,
                "expanded_keys": warm_start_log.expanded_keys,
                "warm_starts": [
                    {
                        "source_id": w.source_id,
                        "source_token": w.source_token,
                        "target_id": w.target_id,
                        "target_token": w.target_token,
                    }
                    for w in warm_start_log.warm_starts
                ],
            }))
            tokenizer_provenance["vocab_expansion"] = warm_start_log.to_dict()
        model.load_state_dict(model_state)
        starting_step = int(state.get("step", 0))
        starting_epoch = int(state.get("epoch", 0))
    else:
        starting_step = 0
        starting_epoch = 0

    optim = torch.optim.AdamW(model.parameters(), lr=float(args.lr))
    scheduler = BetaScheduler(
        beta_start=float(args.beta_lm_start),
        beta_end=float(args.beta_lm_end),
        curriculum_steps=int(args.beta_curriculum_steps),
    )

    checkpoint_id = str(uuid.uuid4())
    global_step = starting_step
    final_loss = 0.0
    epochs_completed = starting_epoch
    train_start_time = time.perf_counter()

    with events_path.open("a", encoding="utf-8") as event_stream:
        for epoch in range(starting_epoch, int(args.epochs)):
            random.shuffle(train_records)
            batches_per_epoch = max(1, (len(train_records) + int(args.batch_size) - 1) // int(args.batch_size))
            batch_in_epoch = 0
            for batch_start in range(0, len(train_records), int(args.batch_size)):
                batch_records = train_records[batch_start : batch_start + int(args.batch_size)]
                if use_fallback:
                    batch = _records_to_batch(batch_records, device=device)
                    if batch is None:
                        continue
                    out = model(**batch)
                    loss_lm_t = out.get("lm_loss", torch.tensor(0.0, device=device))
                    loss_struct_t = out.get(
                        "structured_loss", torch.tensor(0.0, device=device)
                    )
                else:
                    assert collator is not None
                    batch = collator(batch_records, device=device)
                    if batch is None:
                        continue
                    # CAS prefix opt-in. NLGenerationHead.forward now
                    # accepts cas_prefix_mask, so PAD positions in the
                    # padded prefix are blocked from self-attention.
                    # Bottleneck-z and register-id continue to carry CAS
                    # state alongside the discrete prefix.
                    cas_prefix_arg = batch["cas_prefix_ids"] if use_cas_prefix else None
                    cas_prefix_mask_arg = batch["cas_prefix_mask"] if use_cas_prefix else None
                    out = model.forward_with_lm(
                        batch["input_ids"],
                        batch["lm_decoder_input_ids"],
                        attention_mask=batch["attention_mask"],
                        cas_prefix_ids=cas_prefix_arg,
                        cas_prefix_mask=cas_prefix_mask_arg,
                        register_id=batch["register_id"],
                    )
                    loss_lm_t = masked_cross_entropy(
                        out["lm_logits"],
                        batch["lm_targets"],
                        batch["loss_mask"],
                    )
                    # First bridge: structured loss path is wired separately
                    # (B-2.5 follow-on). LM-only here.
                    loss_struct_t = torch.tensor(0.0, device=device)

                beta = scheduler.value_at(global_step)
                total = float(args.alpha_structured) * loss_struct_t + beta * loss_lm_t
                optim.zero_grad(set_to_none=True)
                total.backward()
                optim.step()
                global_step += 1
                batch_in_epoch += 1
                final_loss = float(total.item())

                # train_progress: always-print for batches 1, 3, 5 of epoch 0,
                # then every --train-log-every-steps. Disambiguates "stuck"
                # from "slow."
                tps_now = batch_in_epoch / max(time.perf_counter() - train_start_time, 1e-6)
                always_log = (epoch == starting_epoch and batch_in_epoch in (1, 3, 5))
                if always_log or global_step % int(args.train_log_every_steps) == 0:
                    elapsed = time.perf_counter() - train_start_time
                    eta_min = (batches_per_epoch - batch_in_epoch) / max(tps_now, 1e-6) / 60.0
                    progress = {
                        "event": "train_progress",
                        "epoch": epoch,
                        "batch_in_epoch": batch_in_epoch,
                        "batches_per_epoch": batches_per_epoch,
                        "global_step": global_step,
                        "train_loss_avg": float(final_loss),
                        "elapsed_sec": float(elapsed),
                        "batches_per_sec": float(tps_now),
                        "eta_epoch_min": float(eta_min),
                        "mode": "fallback" if use_fallback else "real",
                    }
                    print(json.dumps(progress, sort_keys=True), flush=True)

                if global_step % int(args.logging_steps) == 0:
                    emit_train_step_event(
                        event_id=str(uuid.uuid4()),
                        checkpoint_id=checkpoint_id,
                        step=global_step,
                        epoch=epoch,
                        loss_total=final_loss,
                        loss_structured=float(loss_struct_t.item()),
                        loss_lm=float(loss_lm_t.item()),
                        beta=beta,
                        lr=float(args.lr),
                        out_stream=event_stream,
                    )

                if sample_every_steps > 0 and global_step % sample_every_steps == 0:
                    assert generate_reply_fn is not None
                    assert sample_rotation, "sample_rotation must be non-empty when sample_every_steps>0"
                    rot_idx, sample_record = sample_rotation[
                        sample_rotation_pos % len(sample_rotation)
                    ]
                    sample_rotation_pos += 1
                    was_training = bool(model.training)
                    try:
                        generated = generate_reply_fn(
                            model=model,
                            tokenizer=tokenizer,
                            prompt_text=_record_text(sample_record, ("prompt_text", "prompt")),
                            cas_expression=_record_text(sample_record, ("cas_expression",)) or None,
                            register=str(sample_record.get("register", "T")),
                            max_prompt_len=int(args.max_prompt_len),
                            max_cas_prefix_len=int(args.max_cas_prefix_len),
                            max_new_tokens=sample_max_new_tokens,
                            sampling=str(args.sample_sampling),
                            temperature=float(args.sample_temperature),
                            top_p=float(args.sample_top_p),
                            use_cas_prefix=use_cas_prefix,
                            device=device,
                            return_trace=bool(args.sample_return_trace),
                        )
                        emit_sample_reply_event(
                            event_id=str(uuid.uuid4()),
                            checkpoint_id=checkpoint_id,
                            step=global_step,
                            epoch=epoch,
                            sample_index=rot_idx,
                            record=sample_record,
                            generated=generated,
                            out_stream=event_stream,
                        )
                    except Exception as exc:
                        emit_sample_reply_error_event(
                            event_id=str(uuid.uuid4()),
                            checkpoint_id=checkpoint_id,
                            step=global_step,
                            epoch=epoch,
                            sample_index=rot_idx,
                            record=sample_record,
                            error=exc,
                            out_stream=event_stream,
                        )
                    finally:
                        if was_training:
                            model.train()
                        else:
                            model.eval()
            epochs_completed = epoch + 1

    # Save final checkpoint with full manifest.
    state = {
        "model": model.state_dict(),
        "step": global_step,
        "epoch": epochs_completed,
    }
    ckpt_path = out_dir / "model_final.pt"
    torch.save(state, ckpt_path)
    manifest = CheckpointManifest(
        checkpoint_id=checkpoint_id,
        code_version=CODE_VERSION,
        weights_sha=hash_state_dict(model.state_dict()),
        trained_from_corpus_hash=corpus_hash,
        trained_at_timestamp=utc_iso_now(),
        n_train_records=len(train_records),
        n_epochs_completed=int(epochs_completed),
        final_loss_total=float(final_loss),
        git_commit_sha=get_git_commit_sha(),
        extra={
            "n_val_records": len(val_records),
            "global_step": global_step,
            "curriculum": scheduler.to_provenance(),
            "checkpoint_path": str(ckpt_path),
            "tokenizer": tokenizer_provenance,
            "use_fallback_head": use_fallback,
            "use_cas_prefix": use_cas_prefix,
            "sample_reply": {
                "sample_every_steps": sample_every_steps,
                "sample_record_index": sample_record_index,
                "sample_record_indices_arg": sample_indices_arg,
                "sample_rotation_indices": [i for i, _ in sample_rotation],
                "sample_rotation_record_ids": [
                    str(r.get("id", "")) for _, r in sample_rotation
                ],
                "sample_rotation_task_types": [
                    _record_task_type(r) for _, r in sample_rotation
                ],
                "sample_rotation_categories": [
                    _record_category(r) for _, r in sample_rotation
                ],
                "sample_rotation_n_events_emitted": int(sample_rotation_pos),
                "sample_max_new_tokens": sample_max_new_tokens,
                "sample_sampling": str(getattr(args, "sample_sampling", "greedy")),
                "sample_temperature": float(getattr(args, "sample_temperature", 0.8)),
                "sample_top_p": float(getattr(args, "sample_top_p", 0.9)),
                "sample_return_trace": bool(getattr(args, "sample_return_trace", False)),
            },
        },
    )
    with (out_dir / "checkpoint_manifest.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest.to_dict(), fh, indent=2, sort_keys=True)
    print(
        json.dumps(
            {
                "event": "training_complete",
                "checkpoint_id": checkpoint_id,
                "global_step": global_step,
                "n_epochs": int(epochs_completed),
            }
        )
    )
    return 0


def _records_to_batch(
    records: list[dict[str, Any]],
    *,
    device: torch.device,
) -> dict[str, torch.Tensor] | None:
    """Best-effort record-to-tensor batcher.

    Records are expected to carry pre-tokenized ``input_ids`` /
    ``target_ids`` (and optionally ``struct_targets``). When the parallel
    tokenizer agent's HybridCASTokenizer ships, this function will be
    swapped for the tokenizer-aware path; until then the records' own ids
    are passed through directly.
    """
    if not records:
        return None
    ids_a: list[list[int]] = []
    ids_b: list[list[int]] = []
    structs: list[int] = []
    for rec in records:
        ids_a.append([int(v) for v in (rec.get("input_ids") or [])])
        ids_b.append([int(v) for v in (rec.get("target_ids") or [])])
        structs.append(int(rec.get("struct_target") or 0))
    if not any(ids_a) or not any(ids_b):
        return None
    max_a = max(len(x) for x in ids_a)
    max_b = max(len(x) for x in ids_b)
    if max_a == 0 or max_b == 0:
        return None
    pad = 0
    a = [row + [pad] * (max_a - len(row)) for row in ids_a]
    b = [row + [-100] * (max_b - len(row)) for row in ids_b]
    return {
        "input_ids": torch.tensor(a, dtype=torch.long, device=device),
        "target_ids": torch.tensor(b, dtype=torch.long, device=device),
        "struct_targets": torch.tensor(structs, dtype=torch.long, device=device),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Train the fully-native CAS NL generation head. Random-init "
            "weights, no foreign pretrained models. Emits checkpoint, "
            "training_events.jsonl, and full provenance manifest."
        )
    )
    p.add_argument("--data-path", type=str, default="")
    p.add_argument("--output-dir", type=str, default="./out_native_nl_gen")
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--smoke-test", action="store_true")
    p.add_argument("--resume-from", type=str, default="")
    p.add_argument("--alpha-structured", type=float, default=1.0)
    p.add_argument("--beta-lm-start", type=float, default=0.1)
    p.add_argument("--beta-lm-end", type=float, default=1.0)
    p.add_argument("--beta-curriculum-steps", type=int, default=10000)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--logging-steps", type=int, default=50)
    p.add_argument("--vocab-size", type=int, default=32000)
    # Real-path wiring (default: real). Use --use-fallback-head for the
    # legacy pre-tokenized smoke path.
    p.add_argument(
        "--use-fallback-head",
        action="store_true",
        help=(
            "Use the legacy _FallbackNLGenerationHead with pre-tokenized "
            "input_ids/target_ids records. Default is the real path: full "
            "CASNativeModel + NLGenerationHead via attach_nl_gen_head + "
            "forward_with_lm."
        ),
    )
    p.add_argument("--tokenizer-path", type=str, default="")
    p.add_argument(
        "--english-bpe-path",
        type=str,
        default="",
        help=(
            "Path to a saved English-BPE artifact (see "
            "cas_native.training.english_bpe_extension.train_english_bpe). "
            "When set, composes the base HybridCASTokenizer with the BPE "
            "merges to produce an ExtendedHybridCASTokenizer for fluent "
            "English generation. Recommended for any production training run."
        ),
    )
    p.add_argument(
        "--use-cas-prefix",
        action="store_true",
        help=(
            "Pass cas_prefix_ids + cas_prefix_mask into NLGenerationHead.forward "
            "via forward_with_lm. As of the B-4 cas_prefix_mask fix "
            "(2026-05-09), padded prefixes are safely masked from "
            "self-attention. Defaults to OFF for backwards-compatibility "
            "with v0 (B-3) checkpoints; enable for new training runs that "
            "want the head to see the discrete CAS-prefix tokens directly."
        ),
    )
    p.add_argument("--d-model", type=int, default=512)
    p.add_argument("--encoder-n-layers", type=int, default=6)
    p.add_argument("--encoder-n-heads", type=int, default=8)
    p.add_argument("--head-n-layers", type=int, default=6)
    p.add_argument("--head-n-heads", type=int, default=8)
    p.add_argument("--max-prompt-len", type=int, default=256)
    p.add_argument("--max-reply-len", type=int, default=256)
    p.add_argument("--max-cas-prefix-len", type=int, default=32)
    p.add_argument(
        "--prepend-task-token",
        action="store_true",
        help=(
            "Option C: prepend [VALID]/[INVALID] task token at "
            "cas_prefix_ids[0] based on the record's task_type. "
            "Wraps the tokenizer in TaskTokenExtendedTokenizer "
            "(vocab grows by +2). When --resume-from points at a "
            "smaller-vocab checkpoint, embedding/lm_head rows are "
            "expanded with warm-start: [TASK_EXPR] -> [VALID], "
            "[TASK_EXPLAIN] -> [INVALID]."
        ),
    )
    p.add_argument("--train-log-every-steps", type=int, default=20)
    p.add_argument(
        "--sample-every-steps",
        type=int,
        default=0,
        help=(
            "When >0, periodically run autoregressive generate_reply() on a "
            "held-out record and emit sample_reply events. Real path only; "
            "disabled by default."
        ),
    )
    p.add_argument(
        "--sample-record-index",
        type=int,
        default=0,
        help=(
            "Index into the validation split for periodic sample_reply "
            "events. Used only when --sample-record-indices is empty."
        ),
    )
    p.add_argument(
        "--sample-record-indices",
        type=str,
        default="",
        help=(
            "Comma-separated list of record indices to rotate through "
            "for periodic sample_reply events. Round-robin: the Nth "
            "sampling event picks indices[N %% len]. When set, overrides "
            "--sample-record-index. Recommended for any run that should "
            "monitor sample diversity across tasks/categories (the "
            "rotation pool is logged at startup as a "
            "'sample_rotation_pool' event so the run history names "
            "which records are being watched)."
        ),
    )
    p.add_argument("--sample-max-new-tokens", type=int, default=80)
    p.add_argument(
        "--sample-sampling",
        type=str,
        default="greedy",
        choices=("greedy", "temperature", "top_p"),
    )
    p.add_argument("--sample-temperature", type=float, default=0.8)
    p.add_argument("--sample-top-p", type=float, default=0.9)
    p.add_argument("--sample-return-trace", action="store_true")
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.smoke_test:
        args.device = "cpu"
        return run_smoke_test(args)
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        print(
            json.dumps(
                {
                    "event": "warn",
                    "reason": "cuda_unavailable_falling_back_to_cpu",
                }
            )
        )
        args.device = "cpu"
    return run_training(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "CHECKPOINT_SCHEMA_VERSION",
    "CODE_VERSION",
    "CheckpointManifest",
    "TRAIN_EVENT_SCHEMA_VERSION",
    "build_parser",
    "deterministic_split",
    "emit_sample_reply_error_event",
    "emit_sample_reply_event",
    "emit_train_step_event",
    "hash_corpus_file",
    "hash_state_dict",
    "load_corpus",
    "main",
    "run_smoke_test",
    "run_training",
]
