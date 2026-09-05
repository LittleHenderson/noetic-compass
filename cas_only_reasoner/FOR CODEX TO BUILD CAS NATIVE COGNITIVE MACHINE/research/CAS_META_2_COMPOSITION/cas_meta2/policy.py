"""CUDA-only, public-input-conditioned autoregressive program generators.

Both candidates decode the same symbolic program vocabulary one token at a
time. They differ only in the encoder. No whole-program classification head,
gold-program lookup, interpreter, verifier or task ID enters prediction.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
from torch import nn

from .codec import (ACTION_VOCABULARY, BINDING_TOKEN_IDS, BOS_ID, EOS_ID, PAD_ID,
                    PolicyContractError, PublicTokenizer, action_to_ids,
                    ids_to_action, validate_public)


def require_cuda(device: str | torch.device = "cuda") -> torch.device:
    requested = torch.device(device)
    if requested.type != "cuda":
        raise RuntimeError("CAS_META_2_GPU_REQUIRED:NO_CPU_FALLBACK")
    if not torch.cuda.is_available():
        raise RuntimeError("CAS_META_2_GPU_REQUIRED:CUDA_UNAVAILABLE")
    index = torch.cuda.current_device() if requested.index is None else requested.index
    if index < 0 or index >= torch.cuda.device_count():
        raise RuntimeError("CAS_META_2_GPU_REQUIRED:DEVICE_UNAVAILABLE")
    return torch.device("cuda", index)


@dataclass(frozen=True)
class PolicyConfig:
    d_model: int = 64
    heads: int = 4
    layers: int = 2
    cas_ff_width: int = 128
    decoder_layers: int = 1
    decoder_ff_width: int = 128
    max_length: int = 512
    max_action_length: int = 256
    max_parameter_mismatch_fraction: float = 0.01

    def validate(self):
        dimensions = (self.d_model, self.heads, self.layers, self.cas_ff_width,
                      self.decoder_layers, self.decoder_ff_width, self.max_length,
                      self.max_action_length)
        if any(type(value) is not int or value <= 0 for value in dimensions):
            raise PolicyContractError("POLICY_DIMENSIONS_INVALID")
        if self.d_model % self.heads or self.d_model % 2:
            raise PolicyContractError("POLICY_HEAD_GEOMETRY_INVALID")
        if self.max_action_length < 16 or self.max_action_length > 512:
            raise PolicyContractError("POLICY_ACTION_BOUND_INVALID")
        if not 0 <= self.max_parameter_mismatch_fraction <= 0.01:
            raise PolicyContractError("PARAMETER_MATCH_TOLERANCE_INVALID")


def encode_batch(publics: list[dict], tokenizer: PublicTokenizer, *, device="cuda") -> dict:
    device = require_cuda(device)
    if not publics:
        raise PolicyContractError("EMPTY_NEURAL_BATCH")
    rows = [tokenizer.encode_public(public) for public in publics]
    length = max(len(row["ids"]) for row in rows)
    ids, kinds, slots, values, valid = [], [], [], [], []
    for row in rows:
        count = len(row["ids"])
        padding = length - count
        ids.append(row["ids"] + [0] * padding)
        kinds.append(row["kinds"] + [0] * padding)
        slots.append(row["slots"] + [0] * padding)
        values.append(row["values"] + [[0.0] * 8 for _ in range(padding)])
        valid.append([True] * count + [False] * padding)
    return {"ids": torch.tensor(ids, dtype=torch.long, device=device),
            "kinds": torch.tensor(kinds, dtype=torch.long, device=device),
            "slots": torch.tensor(slots, dtype=torch.long, device=device),
            "values": torch.tensor(values, dtype=torch.float32, device=device),
            "valid": torch.tensor(valid, dtype=torch.bool, device=device)}


def encode_targets(actions: list[dict], *, device="cuda", max_length: int = 256) -> dict:
    """Teacher-forcing tensors for training only; prediction never calls this."""
    device = require_cuda(device)
    if not actions:
        raise PolicyContractError("EMPTY_TARGET_BATCH")
    rows = [action_to_ids(action, max_length=max_length) for action in actions]
    length = max(len(row) for row in rows) - 1
    inputs = [row[:-1] + [PAD_ID] * (length + 1 - len(row)) for row in rows]
    targets = [row[1:] + [PAD_ID] * (length + 1 - len(row)) for row in rows]
    target_ids = torch.tensor(targets, dtype=torch.long, device=device)
    return {"decoder_input_ids": torch.tensor(inputs, dtype=torch.long, device=device),
            "target_ids": target_ids, "valid": target_ids != PAD_ID,
            "lengths": torch.tensor([len(row) - 1 for row in rows], device=device)}


def _positions(length, width, device):
    positions = torch.arange(length, dtype=torch.float32, device=device).unsqueeze(1)
    frequencies = torch.exp(torch.arange(0, width, 2, dtype=torch.float32, device=device)
                            * (-math.log(10000.0) / width))
    encoding = torch.zeros(length, width, device=device)
    encoding[:, 0::2] = torch.sin(positions * frequencies)
    encoding[:, 1::2] = torch.cos(positions * frequencies)
    return encoding


class _ProgramGenerator(nn.Module):
    def __init__(self, vocabulary_size: int, config: PolicyConfig, *, device="cuda"):
        device = require_cuda(device)
        config.validate()
        super().__init__()
        self.config = config
        with torch.device(device):
            self.word_embedding = nn.Embedding(vocabulary_size, config.d_model, padding_idx=0)
            self.kind_embedding = nn.Embedding(4, config.d_model)
            self.slot_embedding = nn.Embedding(4, config.d_model)
            self.numeric_projection = nn.Linear(8, config.d_model, bias=False)
            self.action_embedding = nn.Embedding(len(ACTION_VOCABULARY), config.d_model, padding_idx=PAD_ID)
            self.decoder = nn.ModuleList([
                nn.TransformerDecoderLayer(d_model=config.d_model, nhead=config.heads,
                                           dim_feedforward=config.decoder_ff_width,
                                           dropout=0.0, activation="gelu",
                                           batch_first=True, norm_first=True)
                for _ in range(config.decoder_layers)
            ])
            self.decoder_norm = nn.LayerNorm(config.d_model)
            self.token_head = nn.Linear(config.d_model, len(ACTION_VOCABULARY))
            # A real observation pointer: each binding-token logit reads the
            # corresponding public slot representation. Same in both arms.
            self.binding_query = nn.Linear(config.d_model, config.d_model, bias=False)
            self.binding_key = nn.Linear(config.d_model, config.d_model, bias=False)
        self.register_buffer("position_encoding", _positions(config.max_length, config.d_model, device))
        self.register_buffer("action_positions", _positions(config.max_action_length, config.d_model, device))

    def _check_device(self, *tensors):
        device = require_cuda(next(self.parameters()).device)
        if any(value.device != device for value in self.parameters()):
            raise RuntimeError("CAS_META_2_GPU_REQUIRED:MIXED_PARAMETER_DEVICES")
        if any(value.device != device for value in self.buffers()):
            raise RuntimeError("CAS_META_2_GPU_REQUIRED:MIXED_BUFFER_DEVICES")
        if any(value.device != device for value in tensors):
            raise RuntimeError("CAS_META_2_GPU_REQUIRED:CPU_OR_MIXED_INPUT")

    def embed(self, batch):
        self._check_device(*batch.values())
        length = batch["ids"].shape[1]
        if not 1 <= length <= self.config.max_length:
            raise PolicyContractError("PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
        numeric = self.numeric_projection(batch["values"])
        numeric = numeric * (batch["kinds"] == 3).unsqueeze(-1)
        return (self.word_embedding(batch["ids"]) + self.kind_embedding(batch["kinds"])
                + self.slot_embedding(batch["slots"]) + numeric
                + self.position_encoding[:length].unsqueeze(0))

    def decode(self, memory, batch, decoder_input_ids):
        self._check_device(memory, decoder_input_ids, *batch.values())
        length = decoder_input_ids.shape[1]
        if not 1 <= length <= self.config.max_action_length:
            raise PolicyContractError("ACTION_TOO_LONG:NO_SILENT_TRUNCATION")
        hidden = self.action_embedding(decoder_input_ids) + self.action_positions[:length].unsqueeze(0)
        causal = torch.triu(torch.ones(length, length, dtype=torch.bool, device=hidden.device), diagonal=1)
        for layer in self.decoder:
            hidden = layer(hidden, memory, tgt_mask=causal,
                           tgt_key_padding_mask=decoder_input_ids == PAD_ID,
                           memory_key_padding_mask=~batch["valid"])
        hidden = self.decoder_norm(hidden)
        logits = self.token_head(hidden)
        slot_states = []
        for slot in (1, 2, 3):
            selected = (batch["slots"] == slot) & batch["valid"]
            weight = selected.to(memory.dtype).unsqueeze(-1)
            slot_states.append((memory * weight).sum(1) / weight.sum(1).clamp_min(1.0))
        keys = self.binding_key(torch.stack(slot_states, dim=1))
        pointer = torch.einsum("btd,bsd->bts", self.binding_query(hidden), keys) / math.sqrt(self.config.d_model)
        # CopySlices keeps gradients connected to token_head and both pointer
        # projections; this is learned content addressing, not tag-string rules.
        logits = logits.clone()
        logits[:, :, list(BINDING_TOKEN_IDS)] += pointer
        return logits

    def forward(self, batch, decoder_input_ids):
        memory = self.encode(batch)
        return {"token_logits": self.decode(memory, batch, decoder_input_ids)}


class CASProgramGenerator(_ProgramGenerator):
    def __init__(self, vocabulary_size: int, config: PolicyConfig, *, device="cuda"):
        device = require_cuda(device)
        from casformer import CASformerConfig, CASformerEncoder, LearnedCASControlAdapter
        super().__init__(vocabulary_size, config, device=device)
        cas_config = CASformerConfig(d_model=config.d_model, num_heads=config.heads,
                                    num_relations=4, num_layers=config.layers,
                                    d_ff=config.cas_ff_width, initial_cutoff=0.01,
                                    initial_saturation=4.0)
        with torch.device(device):
            self.control_adapter = LearnedCASControlAdapter(cas_config)
            self.encoder = CASformerEncoder(cas_config)

    def encode(self, batch):
        embedded = self.embed(batch)
        batch_size, length, _ = embedded.shape
        shape = (batch_size, self.config.heads, length, length)
        valid = batch["valid"]
        mask = (valid[:, None, :, None] & valid[:, None, None, :]).expand(shape)
        relations = ((batch["kinds"][:, :, None] - batch["kinds"][:, None, :]) % 4)
        relations = relations[:, None].expand(shape)
        controls = self.control_adapter(
            embedded, bias=embedded,
            policy_resistance=torch.full(shape, 0.1, device=embedded.device, dtype=embedded.dtype),
            readiness=torch.ones(shape, device=embedded.device, dtype=embedded.dtype),
            region_multiplier=torch.ones(shape, device=embedded.device, dtype=embedded.dtype),
            topology_mask=mask, permission_mask=mask, relation_ids=relations,
        )
        hidden, _ = self.encoder(embedded, controls)
        return hidden


class GenericProgramGenerator(_ProgramGenerator):
    def __init__(self, vocabulary_size: int, config: PolicyConfig, ff_width: int, *, device="cuda"):
        device = require_cuda(device)
        super().__init__(vocabulary_size, config, device=device)
        with torch.device(device):
            self.encoder = nn.ModuleList([
                nn.TransformerEncoderLayer(d_model=config.d_model, nhead=config.heads,
                                           dim_feedforward=ff_width, dropout=0.0,
                                           activation="gelu", batch_first=True, norm_first=True)
                for _ in range(config.layers)
            ])
            self.final_norm = nn.LayerNorm(config.d_model)
        self.ff_width = ff_width

    def encode(self, batch):
        hidden = self.embed(batch)
        for layer in self.encoder:
            hidden = layer(hidden, src_key_padding_mask=~batch["valid"])
        return self.final_norm(hidden)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def build_matched_policies(tokenizer: PublicTokenizer, config: PolicyConfig, *, seed: int, device="cuda"):
    device = require_cuda(device)
    config.validate()
    if config.max_length < tokenizer.max_length:
        raise PolicyContractError("TOKENIZER_MODEL_LENGTH_MISMATCH")
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    cas = CASProgramGenerator(len(tokenizer.vocabulary), config, device=device)
    cas_count = parameter_count(cas)
    torch.manual_seed(seed)
    probe = GenericProgramGenerator(len(tokenizer.vocabulary), config, 1, device=device)
    probe_count = parameter_count(probe)
    del probe
    slope = config.layers * (2 * config.d_model + 1)
    ideal = 1 + (cas_count - probe_count) / slope
    candidates = {max(1, math.floor(ideal)), max(1, math.ceil(ideal))}
    width = min(candidates, key=lambda value: (abs(probe_count + (value - 1) * slope - cas_count), value))
    if width > 4096:
        raise PolicyContractError("MATCHED_GENERIC_FF_WIDTH_EXCEEDS_BOUND")
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    generic = GenericProgramGenerator(len(tokenizer.vocabulary), config, width, device=device)
    generic_count = parameter_count(generic)
    mismatch = abs(cas_count - generic_count) / cas_count
    if mismatch > config.max_parameter_mismatch_fraction:
        raise PolicyContractError("ACTIVE_PARAMETER_MATCH_FAILED")
    return cas, generic, {
        "cas_trainable_parameters": cas_count, "generic_trainable_parameters": generic_count,
        "generic_ff_width": width, "absolute_difference": abs(cas_count - generic_count),
        "relative_difference": mismatch, "action_vocabulary_size": len(ACTION_VOCABULARY),
        "decoder": "identical causal Transformer decoder plus learned observation pointer",
        "method": "Real encoder feed-forward width only; no disconnected filler parameters.",
    }


@torch.no_grad()
def predict_public(model, tokenizer, publics: list[dict], *, device="cuda", batch_size=32) -> list[dict]:
    """Greedy open generation. Only syntax decoding follows neural prediction.

    Invalid or incomplete sequences remain rejected. No repair using a rule
    selector, gold answer, expected graph, evaluator or hidden task metadata.
    """
    device = require_cuda(device)
    if type(batch_size) is not int or batch_size < 1:
        raise PolicyContractError("PREDICTION_BATCH_SIZE_INVALID")
    for public in publics:
        validate_public(public)
    model.eval()
    actions = []
    for offset in range(0, len(publics), batch_size):
        batch = encode_batch(publics[offset:offset + batch_size], tokenizer, device=device)
        memory = model.encode(batch)
        count = batch["ids"].shape[0]
        ids = torch.full((count, 1), BOS_ID, dtype=torch.long, device=device)
        finished = torch.zeros(count, dtype=torch.bool, device=device)
        for _ in range(model.config.max_action_length - 1):
            logits = model.decode(memory, batch, ids)[:, -1]
            next_ids = logits.argmax(-1)
            next_ids = torch.where(finished, EOS_ID, next_ids)
            ids = torch.cat((ids, next_ids[:, None]), dim=1)
            finished = finished | (next_ids == EOS_ID)
            if bool(finished.all()):
                break
        for row in ids.tolist():
            try:
                if EOS_ID not in row[1:]:
                    raise PolicyContractError("GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION")
                row = row[:row.index(EOS_ID, 1) + 1]
                actions.append(ids_to_action(row, max_length=model.config.max_action_length))
            except PolicyContractError as error:
                actions.append({"status": "REJECTED", "reason": str(error),
                                "token_ids": row})
    return actions
