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


def build_encoder(torch, texts, d_model, seed):
    """Frozen encoder: the campaign's public tokenizer over the lesson prompts
    plus a fixed seeded projection. Nothing here learns."""
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    tokenizer = LosslessPublicTokenizer.fit_train(tuple(texts),
                                                  max_length=FROZEN_ENCODER_MAX_LENGTH)
    vocabulary = tuple(tokenizer.vocabulary)
    index = {token: position for position, token in enumerate(vocabulary)}
    generator = torch.Generator().manual_seed(seed)
    projection = torch.randn((len(vocabulary), d_model), generator=generator)
    projection = projection / (float(d_model) ** 0.5)
    projection.requires_grad_(False)

    def embed(token):
        return projection[index.get(token, 0)]

    return {"embed": embed, "tokenizer": tokenizer,
            "vocabulary_size": len(vocabulary),
            "projection_frozen": True,
            "max_length": FROZEN_ENCODER_MAX_LENGTH}


class GraphLearner:
    """Real learner: module forward + frozen readout + AdamW over the module
    parameters only (they all belong to operation:^6). Candidate copy only."""

    def __init__(self, torch, framework, tasks, device, learning_rate):
        self.torch = torch
        self.framework = framework
        self.device = device
        self.tasks = tasks
        self.module = framework.module
        self.optimizer = torch.optim.AdamW(self.module.parameters(),
                                           lr=learning_rate, weight_decay=0.0)
        self._question_vectors = [self._embed_question(task) for task in tasks]
        self._option_vectors = [[self._embed_option(option) for option in task["options"]]
                                for task in tasks]

    def _embed(self, tokens):
        vectors = [self.framework.encoder["embed"](token) for token in tokens]
        stacked = self.torch.stack(vectors)
        return stacked.mean(dim=0)

    def _embed_question(self, task):
        return self._embed(task["tokens"])

    def _embed_option(self, option):
        return self._embed([str(option)])

    def forward(self, task_index):
        value = self.module(self._question_vectors[task_index].unsqueeze(0))[0]
        scores = [self.torch.dot(value, vector) for vector in
                  self._option_vectors[task_index]]
        return self.torch.stack(scores)

    def step(self, task_index):
        scores = self.forward(task_index)
        loss = self.torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            self.torch.tensor([self.tasks[task_index]["correct_index"]],
                              device=self.device))
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def eval_loss(self, op, tasks):
        indices = [index for index, task in enumerate(self.tasks) if task["op"] == op]
        losses = []
        for index in indices:
            scores = self.forward(index)
            losses.append(self.torch.nn.functional.cross_entropy(
                scores.unsqueeze(0),
                self.torch.tensor([self.tasks[index]["correct_index"]],
                                  device=self.device)).item())
        return {"total": sum(losses) / max(1, len(losses))}

    def checkpoint_identity(self):
        import hashlib as _hashlib
        digest = _hashlib.sha256()
        for _, parameter in self.module.named_parameters():
            digest.update(parameter.detach().cpu().numpy().tobytes())
        return digest.hexdigest()

    def predict(self, task_input):
        index = next(i for i, task in enumerate(self.tasks)
                     if task["record_id"] == task_input["record_id"])
        scores = self.forward(index)
        return self.tasks[index]["options"][int(self.torch.argmax(scores).item())]
