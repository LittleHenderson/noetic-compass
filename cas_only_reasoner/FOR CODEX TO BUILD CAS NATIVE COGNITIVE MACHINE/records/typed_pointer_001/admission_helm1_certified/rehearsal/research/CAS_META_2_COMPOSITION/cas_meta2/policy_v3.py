"""Candidate CUDA-only lexical-copy policies; not wired into frozen v2.

The frozen encoders, causal decoder, lossless input and observation-binding
pointer remain. Both families receive the same learned occurrence query/key
and vocabulary/copy gate. Lexical spans are input features, not a program
parser. Grammar constrains emitted syntax equally for all neural arms; it
does not supply the requested program or repair a rejected output.

token_logits are normalized log probabilities of the learned mixture. They
are suitable for cross-entropy/NLL; no auxiliary copy labels are required.
This module is not covered by the frozen-v2-geometry gpu_preflight_v3 helper.
"""
from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as F

from .codec import (ACTION_TO_ID, ACTION_VOCABULARY, BINDING_TOKEN_IDS, BOS_ID, EOS_ID, PAD_ID,
                    PolicyContractError, validate_public)
from .features_v2 import LosslessPublicTokenizer
from .features_v3 import COPY_ACTION_IDS, encode_public_with_spans
from .policy import (CASProgramGenerator as FrozenCASProgramGenerator,
                     GenericProgramGenerator as FrozenGenericProgramGenerator,
                     PolicyConfig, encode_batch as frozen_encode_batch,
                     encode_targets, parameter_count, require_cuda)

SCHEMA = "cas-meta2-lexical-copy-policy/3"
_ENCODER_PREFIXES = ("encoder.", "control_adapter.", "final_norm.")


def encode_batch(publics, tokenizer: LosslessPublicTokenizer, *, device="cuda"):
    device = require_cuda(device)
    if type(publics) is not list or not publics:
        raise PolicyContractError("EMPTY_NEURAL_BATCH")
    featured = [encode_public_with_spans(public, tokenizer) for public in publics]
    batch = frozen_encode_batch(publics, tokenizer, device=device)
    # One masked dummy occurrence makes the no-symbol softmax well-defined.
    size = max(1, max(len(row["occurrences"]) for row in featured))
    starts, ends, action_ids, valid = [], [], [], []
    for row in featured:
        occurrences = row["occurrences"]
        padding = size - len(occurrences)
        starts.append([item["token_start"] for item in occurrences] + [0] * padding)
        ends.append([item["token_end"] for item in occurrences] + [0] * padding)
        action_ids.append([item["action_id"] for item in occurrences] + [PAD_ID] * padding)
        valid.append([True] * len(occurrences) + [False] * padding)
    batch.update({"copy_starts": torch.tensor(starts, dtype=torch.long, device=device),
                  "copy_ends": torch.tensor(ends, dtype=torch.long, device=device),
                  "copy_action_ids": torch.tensor(action_ids, dtype=torch.long, device=device),
                  "copy_valid": torch.tensor(valid, dtype=torch.bool, device=device)})
    return batch


class _LexicalCopy:
    def _init_copy(self):
        device = require_cuda(next(self.parameters()).device)
        with torch.device(device):
            self.copy_query = nn.Linear(self.config.d_model, self.config.d_model, bias=False)
            self.copy_key = nn.Linear(self.config.d_model, self.config.d_model, bias=False)
            self.copy_gate = nn.Linear(self.config.d_model, 1)
        self.register_buffer("copy_symbol_id_mask", torch.tensor(
            [token_id in COPY_ACTION_IDS for token_id in range(len(ACTION_VOCABULARY))],
            dtype=torch.bool, device=device))

    def _occurrence_states(self, memory, batch):
        self._check_device(memory, *batch.values())
        starts, ends = batch["copy_starts"], batch["copy_ends"]
        valid, action_ids = batch["copy_valid"], batch["copy_action_ids"]
        if (starts.ndim != 2 or starts.shape[0] != memory.shape[0] or starts.shape[1] < 1
                or any(value.shape != starts.shape for value in (ends, valid, action_ids))
                or any(value.dtype != torch.long for value in (starts, ends, action_ids))
                or valid.dtype != torch.bool):
            raise PolicyContractError("V3_COPY_OCCURRENCE_GEOMETRY_INVALID")
        invalid_span = valid & ((starts < 1) | (ends <= starts) | (ends > memory.shape[1]))
        id_in_bounds = (action_ids >= 0) & (action_ids < len(ACTION_VOCABULARY))
        supported = id_in_bounds & self.copy_symbol_id_mask[action_ids.clamp(0, len(ACTION_VOCABULARY) - 1)]
        if bool(invalid_span.any()) or bool((valid & ~supported).any()):
            raise PolicyContractError("V3_COPY_OCCURRENCE_VALUE_INVALID")
        positions = torch.arange(memory.shape[1], device=memory.device)[None, None, :]
        selected = valid[:, :, None] & (positions >= starts[:, :, None]) & (positions < ends[:, :, None])
        problem = batch["valid"] & (batch["kinds"] == 0) & (batch["slots"] == 0)
        if bool((selected & ~problem[:, None, :]).any()):
            raise PolicyContractError("V3_COPY_OCCURRENCE_OUTSIDE_PROBLEM")
        weights = selected.to(memory.dtype)
        weights = weights / weights.sum(-1, keepdim=True).clamp_min(1.0)
        return torch.bmm(weights, memory)

    def _decoder_states_and_fixed_logits(self, memory, batch, decoder_input_ids):
        # Same decoder and binding pointer equations as frozen policy.decode;
        # hidden states are exposed only to the new learned copy head.
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
        logits = logits.clone()
        logits[:, :, list(BINDING_TOKEN_IDS)] += pointer
        return hidden, logits

    def decode_with_telemetry(self, memory, batch, decoder_input_ids):
        hidden, fixed_logits = self._decoder_states_and_fixed_logits(memory, batch, decoder_input_ids)
        occurrences = self._occurrence_states(memory, batch)
        scores = torch.bmm(self.copy_query(hidden), self.copy_key(occurrences).transpose(1, 2)) / math.sqrt(self.config.d_model)
        valid = batch["copy_valid"]
        has_occurrences = valid.any(-1)[:, None, None]
        scores = scores.masked_fill(~valid[:, None, :], float("-inf"))
        # No occurrences: softmax finite dummy zeros, then exactly zero copy
        # mass and the unmodified fixed-head distribution (including binding).
        scores = torch.where(has_occurrences, scores, torch.zeros_like(scores))
        occurrence_probabilities = torch.softmax(scores, -1) * valid[:, None, :].to(scores.dtype)
        safe_ids = torch.where(valid, batch["copy_action_ids"], torch.zeros_like(batch["copy_action_ids"]))
        destinations = F.one_hot(safe_ids, num_classes=len(ACTION_VOCABULARY)).to(scores.dtype)
        # Matrix multiplication deterministically sums repeated spellings. It
        # avoids CUDA scatter_add, which may violate deterministic settings.
        copy_probabilities = torch.bmm(occurrence_probabilities, destinations)
        fixed_log_probabilities = torch.log_softmax(fixed_logits, -1)
        gate_logits = self.copy_gate(hidden)
        copy_log = copy_probabilities.clamp_min(torch.finfo(copy_probabilities.dtype).tiny).log()
        copy_log = copy_log.masked_fill(copy_probabilities == 0, float("-inf"))
        mixed = torch.logaddexp(F.logsigmoid(-gate_logits) + fixed_log_probabilities,
                               F.logsigmoid(gate_logits) + copy_log)
        log_probabilities = torch.where(has_occurrences, mixed, fixed_log_probabilities)
        return {"token_logits": log_probabilities,
                "fixed_log_probabilities": fixed_log_probabilities,
                "copy_probabilities": copy_probabilities,
                "occurrence_probabilities": occurrence_probabilities,
                "copy_gate": torch.where(has_occurrences, torch.sigmoid(gate_logits), torch.zeros_like(gate_logits))}

    def decode(self, memory, batch, decoder_input_ids):
        return self.decode_with_telemetry(memory, batch, decoder_input_ids)["token_logits"]


class CASProgramGenerator(_LexicalCopy, FrozenCASProgramGenerator):
    def __init__(self, vocabulary_size, config, *, device="cuda"):
        super().__init__(vocabulary_size, config, device=device)
        self._init_copy()


class GenericProgramGenerator(_LexicalCopy, FrozenGenericProgramGenerator):
    def __init__(self, vocabulary_size, config, ff_width, *, device="cuda"):
        super().__init__(vocabulary_size, config, ff_width, device=device)
        self._init_copy()


def build_matched_policies(tokenizer: LosslessPublicTokenizer, config: PolicyConfig, *, seed: int, device="cuda"):
    device = require_cuda(device)
    config.validate()
    if type(tokenizer) is not LosslessPublicTokenizer or config.max_length < tokenizer.max_length:
        raise PolicyContractError("TOKENIZER_MODEL_LENGTH_MISMATCH")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise PolicyContractError("V3_POLICY_SEED_INVALID")
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
    # The head is initialized after family-specific encoders. Explicitly copy
    # the common initial parameters so differing encoder RNG use cannot change
    # shared starts. These are live trained parameters, not frozen or filler.
    cas_parameters = dict(cas.named_parameters())
    common = []
    with torch.no_grad():
        for name, parameter in generic.named_parameters():
            if name.startswith(_ENCODER_PREFIXES):
                continue
            original = cas_parameters.get(name)
            if original is None or original.shape != parameter.shape:
                raise PolicyContractError("V3_SHARED_PARAMETER_GEOMETRY_MISMATCH")
            parameter.copy_(original)
            common.append(name)
    generic_count = parameter_count(generic)
    mismatch = abs(cas_count - generic_count) / cas_count
    if mismatch > config.max_parameter_mismatch_fraction:
        raise PolicyContractError("ACTIVE_PARAMETER_MATCH_FAILED")
    return cas, generic, {"schema": SCHEMA,
        "cas_trainable_parameters": cas_count, "generic_trainable_parameters": generic_count,
        "generic_ff_width": width, "absolute_difference": abs(cas_count - generic_count),
        "relative_difference": mismatch, "action_vocabulary_size": len(ACTION_VOCABULARY),
        "copy_symbol_ids": list(COPY_ACTION_IDS), "common_initial_parameter_names": common,
        "common_initialization": "CAS shared parameters copied exactly to generic before any update.",
        "decoder": "Same causal decoder and observation pointer plus same lexical occurrence copy mixture.",
        "output_kind": "normalized_log_probabilities",
        "copy_pooling": "Mean of encoder states across complete exact lexical-unit spans in public.problem only.",
        "copy_aggregation": "Sum learned occurrence probabilities for repeated exact spellings into unchanged 67-token vocabulary.",
        "frozen_candidate_parameter_names": [family + "." + name
            for family, model in (("cas", cas), ("generic", generic))
            for name, parameter in model.named_parameters() if not parameter.requires_grad],
        "method": "Real encoder feed-forward width only; no disconnected filler parameters.",
        "candidate_only": True, "covered_by_frozen_v2_geometry_preflight": False}


@torch.no_grad()
def predict_public(model, tokenizer, publics: list[dict], *, device="cuda", batch_size=32):
    """Same input-independent grammar for every neural checkpoint/family.

    No public parser, semantic masking, beam oracle, fallback, repair or gold
    access. Grammar failures remain explicit rejected actions.
    """
    from .grammar_v3 import GrammarError, GrammarState
    device = require_cuda(device)
    if type(publics) is not list or type(batch_size) is not int or batch_size < 1:
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
        states = [GrammarState.from_ids([BOS_ID], max_length=model.config.max_action_length) for _ in range(count)]
        rejected = [None] * count
        attempted_failure_ids = [None] * count
        for _ in range(model.config.max_action_length - 1):
            masks = []
            for index, state in enumerate(states):
                if rejected[index] is not None or state.complete:
                    masks.append([token_id == EOS_ID for token_id in range(len(ACTION_VOCABULARY))])
                    continue
                allowed = state.allowed_ids()
                if not allowed:
                    rejected[index] = "GENERATION_GRAMMAR_DEAD_END"
                    allowed = (EOS_ID,)
                masks.append([token_id in allowed for token_id in range(len(ACTION_VOCABULARY))])
            if all(error is not None or state.complete for error, state in zip(rejected, states)):
                break
            scores = model.decode(memory, batch, ids)[:, -1]
            if not bool(torch.isfinite(scores).all()):
                raise PolicyContractError("V3_GENERATION_NONFINITE_MODEL_SCORES")
            mask = torch.tensor(masks, dtype=torch.bool, device=device)
            next_ids = scores.masked_fill(~mask, float("-inf")).argmax(-1)
            ids = torch.cat((ids, next_ids[:, None]), dim=1)
            for index, token_id in enumerate(next_ids.tolist()):
                if rejected[index] is None and not states[index].complete:
                    try:
                        states[index] = states[index].advance_id(token_id)
                    except (PolicyContractError, GrammarError) as error:
                        rejected[index] = str(error)
                        attempted_failure_ids[index] = [ACTION_TO_ID[token] for token in states[index].prefix] + [token_id]
        for index, state in enumerate(states):
            try:
                if rejected[index] is not None:
                    raise PolicyContractError(rejected[index])
                if not state.complete:
                    raise PolicyContractError("GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION")
                actions.append(state.to_action())
            except (PolicyContractError, GrammarError) as error:
                # The shared neural batch may contain dummy EOS padding after
                # this row stopped. That padding is not emitted token evidence.
                row = (attempted_failure_ids[index] if attempted_failure_ids[index] is not None
                       else [ACTION_TO_ID[token] for token in state.prefix])
                actions.append({"status": "REJECTED", "reason": str(error), "token_ids": row})
    return actions
