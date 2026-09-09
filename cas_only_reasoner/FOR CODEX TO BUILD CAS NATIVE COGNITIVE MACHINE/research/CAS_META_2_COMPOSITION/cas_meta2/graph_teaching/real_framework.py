"""Real graph→^6 framework hook (AWS path only; lazy torch/cas_cjt imports).

Builds a CANDIDATE copy of the registered decompose module — never the
accepted model — and exposes the exact interfaces the trainer consumes:
registrations, contract, plasticity resolution, tensor digests, and the
module itself. The encoder wiring is a named, fail-closed hook: until the
authorized AWS-package step connects the frozen public tokenizer, the build
refuses with ENCODER_HOOK_NOT_BUILT rather than guessing.

Grounded in the real cas_cjt artifacts:
- ``cas_cjt.neural.RegisteredOperationBank`` (module dict keyed by DECOMPOSE;
  ``_DecomposeTransform`` = two learned tanh views concatenated and merged),
- ``cas_cjt.state.make_operation_contract("^6")`` whose admitted plasticity
  roles are ``("operation:^6", "bias_update_head")`` — this run uses ONLY
  ``operation:^6`` (the module's own parameters); ``bias_update_head`` stays
  frozen.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

TARGET_CONTRACT_ID = "cas.cjt.operation.^6.decompose/0.2"
TARGET_PLASTICITY_ROLE = "operation:^6"


def require(condition, code):
    if not condition:
        raise ValueError(code)


@dataclass
class GraphTrainingFramework:
    torch: object
    device: object
    module: object                       # candidate _DecomposeTransform
    contract: object                     # real OperationContract for ^6
    operation_registrations: tuple
    encoder: object                      # callable: token str -> embedding list

    def contract_for(self, contract_id):
        require(contract_id == self.contract.contract_id, "CONTRACT_ID_MISMATCH")
        return self.contract

    def resolve_plasticity_groups(self, model, role, contract):
        require(role == TARGET_PLASTICITY_ROLE, "PLASTICITY_ROLE_OUTSIDE_RUN_SCOPE")
        names = [name for name, _ in model.named_parameters()]
        require(names, "DECOMPOSE_MODULE_HAS_NO_PARAMETERS")
        return tuple(names)  # every module parameter belongs to operation:^6

    @staticmethod
    def tensor_bytes(parameter):
        return parameter.detach().cpu().numpy().tobytes()

    def build_decompose_model(self, seed):
        return self.module


def build_graph_training_framework(torch, device, *, seed, encoder=None):
    """Lazy real construction; candidate copies only; encoder hook fail-closed."""
    require(encoder is not None, "ENCODER_HOOK_NOT_BUILT")
    try:
        from cas_cjt.neural import RegisteredOperationBank, DECOMPOSE
        from cas_cjt.neural import OPERATION_REGISTRATIONS
        from cas_cjt.types import CASformerConfig
        from cas_cjt.state import make_operation_contract
    except Exception as error:  # noqa: BLE001 - explicit failure, never fallback
        raise ValueError("CAS_CJT_IMPORT_UNRESOLVED:" + str(error)[:200]) from error
    contract = make_operation_contract("^6")
    require(contract.contract_id == TARGET_CONTRACT_ID, "DECOMPOSE_CONTRACT_ID_CHANGED")
    require(TARGET_PLASTICITY_ROLE in contract.plasticity_groups,
            "DECOMPOSE_PLASTICITY_ROLE_NOT_ADMITTED")
    config = CASformerConfig()  # candidate config copy; accepted model untouched
    bank = RegisteredOperationBank(config)
    module = bank.modules_by_operation[DECOMPOSE]
    module.to(device)
    return GraphTrainingFramework(torch=torch, device=device, module=module,
                                  contract=contract,
                                  operation_registrations=tuple(OPERATION_REGISTRATIONS),
                                  encoder=encoder)


FROZEN_ENCODER_MAX_LENGTH = 1024


def build_encoder(torch, publics, d_model, seed):
    """Frozen encoder over the REAL public-record contract.

    Fits the campaign's public tokenizer on the public records (problem +
    three observations each) and provides a fixed seeded projection. The
    encode step returns the problem token ids and the three per-slot
    observation token ids exactly as the codec produces them. Nothing here
    learns.
    """
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    tokenizer = LosslessPublicTokenizer.fit_train(list(publics),
                                                  max_length=FROZEN_ENCODER_MAX_LENGTH)
    vocabulary = tuple(tokenizer.vocabulary)
    index = {token: position for position, token in enumerate(vocabulary)}
    generator = torch.Generator().manual_seed(seed)
    projection = torch.randn((len(vocabulary), d_model), generator=generator)
    projection = projection / (float(d_model) ** 0.5)
    projection.requires_grad_(False)

    def embed(token_id):
        return projection[index.get(token_id, 0)]

    def encode(public):
        encoded = tokenizer.encode_public(public)
        problem_ids = [token_id for token_id, kind in zip(encoded["ids"], encoded["kinds"])
                       if kind == 0]
        slot_ids = {}
        for token_id, kind, slot in zip(encoded["ids"], encoded["kinds"],
                                        encoded["slots"]):
            if kind == 2 and slot in (1, 2, 3):
                slot_ids.setdefault(slot - 1, []).append(token_id)
        require(set(slot_ids) == {0, 1, 2}, "PUBLIC_SLOT_ENCODING_INCOMPLETE")
        return problem_ids, slot_ids

    return {"encode": encode, "embed": embed, "tokenizer": tokenizer,
            "vocabulary_size": len(vocabulary), "projection_frozen": True,
            "max_length": FROZEN_ENCODER_MAX_LENGTH}


class GraphLearner:
    """Real learner over the public-record encoding: module forward on the
    problem tokens, frozen dot-product readout over the three encoded option
    slots, AdamW over the module parameters only (all operation:^6)."""

    def __init__(self, torch, framework, public_tasks, device, learning_rate):
        self.torch = torch
        self.framework = framework
        self.device = device
        self.tasks = public_tasks
        self.module = framework.module
        self._index = {task["record_id"]: position
                       for position, task in enumerate(public_tasks)}
        self.optimizer = torch.optim.AdamW(self.module.parameters(),
                                           lr=learning_rate, weight_decay=0.0)
        self._problem_vectors = []
        self._option_vectors = []
        for task in public_tasks:
            problem_ids, slot_ids = framework.encoder["encode"](task["public"])
            self._problem_vectors.append(self._mean(problem_ids))
            self._option_vectors.append([self._mean(slot_ids[slot])
                                         for slot in (0, 1, 2)])

    def _mean(self, token_ids):
        vectors = [self.framework.encoder["embed"](token_id) for token_id in token_ids]
        require(vectors, "PROBLEM_EMBEDDING_REQUIRED")
        stacked = self.torch.stack(vectors)
        return stacked.mean(dim=0)

    def _position(self, task):
        return self._index[task["record_id"]]

    def forward(self, position):
        value = self.module(self._problem_vectors[position].unsqueeze(0))[0]
        scores = [self.torch.dot(value, vector)
                  for vector in self._option_vectors[position]]
        return self.torch.stack(scores)

    def step(self, task):
        position = self._position(task)
        scores = self.forward(position)
        loss = self.torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            self.torch.tensor([self.tasks[position]["encoded_correct_index"]],
                              device=self.device))
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def eval_loss(self, op, tasks):
        positions = [self._position(task) for task in tasks if task["op"] == op]
        losses = []
        for position in positions:
            scores = self.forward(position)
            losses.append(self.torch.nn.functional.cross_entropy(
                scores.unsqueeze(0),
                self.torch.tensor([self.tasks[position]["encoded_correct_index"]],
                                  device=self.device)).item())
        return {"total": sum(losses) / max(1, len(losses))}

    def checkpoint_identity(self):
        import hashlib as _hashlib
        digest = _hashlib.sha256()
        for _, parameter in self.module.named_parameters():
            digest.update(parameter.detach().cpu().numpy().tobytes())
        return digest.hexdigest()

    def predict(self, task_input):
        position = self._position(task_input)
        scores = self.forward(position)
        return self.tasks[position]["encoded_options"][
            int(self.torch.argmax(scores).item())]
