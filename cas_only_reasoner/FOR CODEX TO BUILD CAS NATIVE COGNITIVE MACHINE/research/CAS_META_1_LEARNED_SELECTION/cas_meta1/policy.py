"""Public-input-only neural selectors. Numerical execution is CUDA-only.

These candidate selectors do not own the frozen CJT execution weights, the
verifier, or publication authority. Tokenizer methods are non-neural and can
be checked locally. Model construction/forward is reserved for the AWS run.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any

import torch
from torch import nn


class PolicyContractError(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def require_cuda(device: str | torch.device = "cuda") -> torch.device:
    requested = torch.device(device)
    if requested.type != "cuda":
        raise RuntimeError("CAS_META_1_GPU_REQUIRED:NO_CPU_FALLBACK")
    if not torch.cuda.is_available():
        raise RuntimeError("CAS_META_1_GPU_REQUIRED:CUDA_UNAVAILABLE")
    index = torch.cuda.current_device() if requested.index is None else requested.index
    if index < 0 or index >= torch.cuda.device_count():
        raise RuntimeError("CAS_META_1_GPU_REQUIRED:DEVICE_UNAVAILABLE")
    return torch.device("cuda", index)


def validate_public(public: dict) -> dict:
    """Reject IDs, gold, provenance, and every undeclared selector field."""
    if type(public) is not dict or set(public) != {"problem", "observations"}:
        raise PolicyContractError("PUBLIC_INPUT_FIELDS_INVALID")
    if type(public["problem"]) is not str or not public["problem"] or len(public["problem"]) > 8192:
        raise PolicyContractError("PUBLIC_PROBLEM_INVALID")
    observations = public["observations"]
    if type(observations) is not list or len(observations) != 3:
        raise PolicyContractError("PUBLIC_OBSERVATIONS_INVALID")
    slots = []
    for item in observations:
        if type(item) is not dict or set(item) != {"slot", "tag", "values"}:
            raise PolicyContractError("PUBLIC_OBSERVATION_FIELDS_INVALID")
        if type(item["slot"]) is not int or item["slot"] not in (0, 1, 2):
            raise PolicyContractError("PUBLIC_SLOT_INVALID")
        if type(item["tag"]) is not str or not item["tag"] or len(item["tag"]) > 256:
            raise PolicyContractError("PUBLIC_TAG_INVALID")
        values = item["values"]
        if type(values) is not list or len(values) != 8 or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in values
        ):
            raise PolicyContractError("PUBLIC_VALUES_INVALID")
        slots.append(item["slot"])
    if sorted(slots) != [0, 1, 2]:
        raise PolicyContractError("PUBLIC_SLOT_COVERAGE_INVALID")
    return public


def _words(text: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE)


SPECIAL = ("[PAD]", "[UNK]", "[CLS]", "[SEP]", "[OBS]", "[VALUES]")


def _public_sequence(public: dict) -> list[tuple[str, int, int, list[float]]]:
    validate_public(public)
    zero = [0.0] * 8
    rows = [("[CLS]", 0, 0, zero)]
    rows.extend((word, 0, 0, zero) for word in _words(public["problem"]))
    rows.append(("[SEP]", 1, 0, zero))
    for observation in sorted(public["observations"], key=lambda item: item["slot"]):
        slot = observation["slot"] + 1
        rows.append(("[OBS]", 2, slot, zero))
        rows.extend((word, 2, slot, zero) for word in _words(observation["tag"]))
        rows.append(("[VALUES]", 3, slot, [float(value) for value in observation["values"]]))
    return rows


@dataclass(frozen=True)
class PublicTokenizer:
    vocabulary: tuple[str, ...]
    fitted_public_sha256: str
    fitted_examples: int
    max_length: int = 128

    @classmethod
    def fit_train(cls, train_public: list[dict], *, max_length: int = 128):
        if not train_public or type(max_length) is not int or max_length < 16:
            raise PolicyContractError("TOKENIZER_TRAIN_INPUT_INVALID")
        words = set()
        for public in train_public:
            rows = _public_sequence(public)
            if len(rows) > max_length:
                raise PolicyContractError("PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
            words.update(row[0] for row in rows)
        return cls(SPECIAL + tuple(sorted(words.difference(SPECIAL))),
                   canonical_sha256(train_public), len(train_public), max_length)

    def encode_public(self, public: dict) -> dict:
        rows = _public_sequence(public)
        if len(rows) > self.max_length:
            raise PolicyContractError("PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION")
        lookup = {word: index for index, word in enumerate(self.vocabulary)}
        return {"ids": [lookup.get(row[0], 1) for row in rows],
                "kinds": [row[1] for row in rows], "slots": [row[2] for row in rows],
                "values": [row[3] for row in rows]}

    def to_dict(self) -> dict:
        return {"schema": "cas-meta1-public-tokenizer/1", "fit_split": "train_only",
                **asdict(self)}

    @property
    def digest(self) -> str:
        return canonical_sha256(self.to_dict())


@dataclass(frozen=True)
class PolicyConfig:
    d_model: int = 32
    heads: int = 4
    layers: int = 2
    cas_ff_width: int = 64
    max_length: int = 128
    max_parameter_mismatch_fraction: float = 0.01

    def validate(self):
        dimensions = (self.d_model, self.heads, self.layers, self.cas_ff_width, self.max_length)
        if any(type(value) is not int or value <= 0 for value in dimensions):
            raise PolicyContractError("POLICY_DIMENSIONS_INVALID")
        if self.d_model % self.heads or self.d_model % 2:
            raise PolicyContractError("POLICY_HEAD_GEOMETRY_INVALID")
        if not 0 <= self.max_parameter_mismatch_fraction <= 0.05:
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


class _PublicSelector(nn.Module):
    def __init__(self, vocabulary_size: int, config: PolicyConfig):
        super().__init__()
        self.config = config
        self.word_embedding = nn.Embedding(vocabulary_size, config.d_model, padding_idx=0)
        self.kind_embedding = nn.Embedding(4, config.d_model)
        self.slot_embedding = nn.Embedding(4, config.d_model)
        self.numeric_projection = nn.Linear(8, config.d_model, bias=False)
        self.procedure_head = nn.Linear(config.d_model, 3)
        self.binding_head = nn.Linear(config.d_model, 3)
        positions = torch.arange(config.max_length, dtype=torch.float32).unsqueeze(1)
        frequencies = torch.exp(torch.arange(0, config.d_model, 2, dtype=torch.float32)
                                * (-math.log(10000.0) / config.d_model))
        encoding = torch.zeros(config.max_length, config.d_model)
        encoding[:, 0::2] = torch.sin(positions * frequencies)
        encoding[:, 1::2] = torch.cos(positions * frequencies)
        self.register_buffer("position_encoding", encoding)

    def embed(self, batch):
        if any(value.device.type != "cuda" for value in batch.values()):
            raise RuntimeError("CAS_META_1_GPU_REQUIRED:CPU_INPUT")
        if any(value.device.type != "cuda" for value in self.parameters()):
            raise RuntimeError("CAS_META_1_GPU_REQUIRED:CPU_PARAMETER")
        length = batch["ids"].shape[1]
        numeric = self.numeric_projection(batch["values"])
        numeric = numeric * (batch["kinds"] == 3).unsqueeze(-1)
        return (self.word_embedding(batch["ids"]) + self.kind_embedding(batch["kinds"])
                + self.slot_embedding(batch["slots"]) + numeric
                + self.position_encoding[:length].unsqueeze(0))

    def classify(self, hidden):
        pooled = hidden[:, 0]
        return {"procedure_logits": self.procedure_head(pooled),
                "binding_logits": self.binding_head(pooled)}


class CASSelector(_PublicSelector):
    def __init__(self, vocabulary_size: int, config: PolicyConfig):
        from casformer import CASformerConfig, CASformerEncoder, LearnedCASControlAdapter
        super().__init__(vocabulary_size, config)
        cas_config = CASformerConfig(d_model=config.d_model, num_heads=config.heads,
                                    num_relations=4, num_layers=config.layers,
                                    d_ff=config.cas_ff_width, initial_cutoff=0.01,
                                    initial_saturation=4.0)
        self.control_adapter = LearnedCASControlAdapter(cas_config)
        self.encoder = CASformerEncoder(cas_config)

    def forward(self, batch):
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
        return self.classify(hidden)


class GenericSelector(_PublicSelector):
    def __init__(self, vocabulary_size: int, config: PolicyConfig, ff_width: int):
        super().__init__(vocabulary_size, config)
        # Independent initializations, as in CASformerEncoder; no cloned-layer
        # identical-initial-value shortcut and no disconnected filler weights.
        self.encoder = nn.ModuleList([
            nn.TransformerEncoderLayer(d_model=config.d_model, nhead=config.heads,
                                       dim_feedforward=ff_width, dropout=0.0,
                                       activation="gelu", batch_first=True, norm_first=True)
            for _ in range(config.layers)
        ])
        self.final_norm = nn.LayerNorm(config.d_model)
        self.ff_width = ff_width

    def forward(self, batch):
        embedded = self.embed(batch)
        hidden = embedded
        for layer in self.encoder:
            hidden = layer(hidden, src_key_padding_mask=~batch["valid"])
        return self.classify(self.final_norm(hidden))


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def build_matched_policies(tokenizer: PublicTokenizer, config: PolicyConfig, *, seed: int, device="cuda"):
    device = require_cuda(device)
    config.validate()
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    with torch.device(device):
        cas = CASSelector(len(tokenizer.vocabulary), config)
    cas_count = parameter_count(cas)
    torch.manual_seed(seed)
    with torch.device(device):
        width_one = GenericSelector(len(tokenizer.vocabulary), config, 1)
    width_one_count = parameter_count(width_one)
    del width_one
    slope = config.layers * (2 * config.d_model + 1)
    ideal = 1 + (cas_count - width_one_count) / slope
    candidates = {max(1, math.floor(ideal)), max(1, math.ceil(ideal))}
    width = min(candidates, key=lambda value: (abs(width_one_count + (value - 1) * slope - cas_count), value))
    if width > 4096:
        raise PolicyContractError("MATCHED_GENERIC_FF_WIDTH_EXCEEDS_BOUND")
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    with torch.device(device):
        generic = GenericSelector(len(tokenizer.vocabulary), config, width)
    generic_count = parameter_count(generic)
    mismatch = abs(cas_count - generic_count) / cas_count
    if mismatch > config.max_parameter_mismatch_fraction:
        raise PolicyContractError("ACTIVE_PARAMETER_MATCH_FAILED")
    return cas, generic, {
        "cas_trainable_parameters": cas_count, "generic_trainable_parameters": generic_count,
        "generic_ff_width": width, "absolute_difference": abs(cas_count - generic_count),
        "relative_difference": mismatch,
        "method": "Real feed-forward width only; no unused filler parameters. Gradient connectivity checked during AWS training.",
    }


@torch.no_grad()
def predict_public(model, tokenizer, publics: list[dict], *, device="cuda", batch_size=64) -> list[dict]:
    require_cuda(device)
    model.eval()
    actions = []
    for offset in range(0, len(publics), batch_size):
        logits = model(encode_batch(publics[offset:offset + batch_size], tokenizer, device=device))
        procedure = logits["procedure_logits"].argmax(-1).tolist()
        binding = logits["binding_logits"].argmax(-1).tolist()
        actions.extend({"procedure": first, "binding": second} for first, second in zip(procedure, binding, strict=True))
    return actions
