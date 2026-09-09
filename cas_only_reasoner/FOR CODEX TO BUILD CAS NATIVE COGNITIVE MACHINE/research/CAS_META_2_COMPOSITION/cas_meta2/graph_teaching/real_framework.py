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
        from casformer import CASformerConfig  # the reference wheel, not cas_cjt
        from cas_cjt.neural import RegisteredOperationBank, DECOMPOSE
        from cas_cjt.neural import OPERATION_REGISTRATIONS
        from cas_cjt.state import make_operation_contract
    except Exception as error:  # noqa: BLE001 - explicit failure, never fallback
        raise ValueError("CAS_CJT_IMPORT_UNRESOLVED:" + str(error)[:200]) from error
    contract = make_operation_contract("^6")
    require(contract.contract_id == TARGET_CONTRACT_ID, "DECOMPOSE_CONTRACT_ID_CHANGED")
    require(TARGET_PLASTICITY_ROLE in contract.plasticity_groups,
            "DECOMPOSE_PLASTICITY_ROLE_NOT_ADMITTED")
    config = CASformerConfig(d_model=encoder["d_model"], num_heads=2,
                             num_relations=4, num_layers=1, dropout=0.0,
                             attention_dropout=0.0, initial_cutoff=0.01,
                             initial_saturation=100.0)  # candidate config copy
    bank = RegisteredOperationBank(config)
    module = bank.modules_by_operation[DECOMPOSE]
    module.to(device)
    return GraphTrainingFramework(torch=torch, device=device, module=module,
                                  contract=contract,
                                  operation_registrations=tuple(OPERATION_REGISTRATIONS),
                                  encoder=encoder)


FROZEN_ENCODER_MAX_LENGTH = 1024


def build_encoder(torch, publics, d_model, seed, device):
    """Frozen encoder over the REAL public-record contract.

    Fits the campaign's public tokenizer on the public records (problem +
    three observations each) and provides a fixed seeded projection ON THE
    DEVICE the module lives on (attempt 006's preserved error was a CPU/CUDA
    device mismatch exactly here). Nothing here learns.
    """
    from cas_meta2.features_v2 import LosslessPublicTokenizer, _word_token
    tokenizer = LosslessPublicTokenizer.fit_train(list(publics),
                                                  max_length=FROZEN_ENCODER_MAX_LENGTH)
    vocabulary = tuple(tokenizer.vocabulary)
    generator = torch.Generator(device=device).manual_seed(seed)
    projection = torch.randn((len(vocabulary), d_model), generator=generator,
                             device=device)
    projection = projection / (float(d_model) ** 0.5)
    projection.requires_grad_(False)

    def embed(token_id):
        # Attempt 005's MEASURED root cause: the previous string-keyed lookup
        # (index.get(token_id, 0)) received INTEGER token ids while the index
        # maps token STRINGS to positions, so every token silently embedded as
        # projection[0] — all tag vectors were the identical vector (norm
        # 0.9902205467224121 for every tag; every pairwise cosine ≈ 1.0 to
        # within 3.2e-8). Token ids ARE vocabulary positions; index the
        # projection row directly. Invalid internal ids are REJECTED
        # explicitly — never silently mapped to row 0. There is no legitimate
        # unknown token at runtime: the lossless tokenizer's byte fallback
        # guarantees every unit is in-vocabulary.
        require(type(token_id) is int and 0 <= token_id < len(projection),
                "ENCODER_TOKEN_ID_OUT_OF_RANGE")
        return projection[token_id]

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

    # Relationship-preserving problem encoder (owner-directed 2026-09-09).
    # Attempt 006's same-token rewiring contrast measured that mean-pooling
    # over the problem tokens is a BAG OF WORDS: which part belongs to which
    # idea does not survive. The rule below binds each complete connection
    # and each node's contents into ONE joint vector BEFORE aggregation, via
    # a fixed elementwise (Hadamard) product over the segment's rows — a
    # joint, role-sensitive combination, NOT independent role sums. Nothing
    # here learns and nothing computes the task's answer.
    node_id = vocabulary.index(_word_token("node"))
    rel_id = vocabulary.index(_word_token("rel"))
    newline_id = vocabulary.index(_word_token("\n"))

    def encode_problem(public):
        encoded = tokenizer.encode_public(public)
        problem_ids = [token_id for token_id, kind in zip(encoded["ids"], encoded["kinds"])
                       if kind == 0]
        # LINE-based segmentation: "node"/"rel" open a structural segment; the
        # newline closes it. Framing/request tokens (outside structural
        # lines) go to rest, so the question is NEVER bound into a segment.
        segments = []   # each: [marker, ...] token ids of one node / one rel line
        rest = []
        current = None
        for token_id in problem_ids:
            if token_id == newline_id:
                current = None
            elif token_id in (node_id, rel_id):
                current = [token_id]
                segments.append(current)
            elif current is not None:
                current.append(token_id)
            else:
                rest.append(token_id)
        require(segments, "PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED")
        bound = [torch.stack([embed(token_id) for token_id in segment]).prod(dim=0)
                 for segment in segments]
        vector = torch.stack(bound).sum(dim=0)
        if rest:
            vector = vector + torch.stack([embed(token_id)
                                           for token_id in rest]).mean(dim=0)
        return vector

    return {"encode": encode, "embed": embed, "encode_problem": encode_problem,
            "tokenizer": tokenizer,
            "vocabulary_size": len(vocabulary), "projection_frozen": True,
            "structural_problem_binding": True,
            "max_length": FROZEN_ENCODER_MAX_LENGTH, "d_model": d_model}


class GraphLearner:
    """Real learner over the public-record encoding: module forward on the
    problem tokens, frozen dot-product readout over the three encoded option
    slots, AdamW over the module parameters only (all operation:^6).

    Representation follow-up 001 (owner-authorized 2026-09-09): the OPTION
    slots are SUM-pooled instead of mean-pooled. ATTEMPT 005's measurement
    later located the ORIGINAL collapse BEFORE pooling: the embed lookup
    returned one vector for every token (integer ids through a string-keyed
    index), so every option vector was a count-scaled copy of the same row.
    With the lookup repaired, the sum-vs-mean choice is downstream and stays
    as follow-up 001 prepared it. The PROBLEM side (module input) is
    UNCHANGED: still mean-pooled, exactly as in attempt 010 — one variable
    at a time.

    Representation correction 002 (owner-directed 2026-09-09, PREPARED not
    launched): the pure inspection
    (tools/graph_training_representation_inspection.py) measured that
    sum-pooled differences are DOMINATED BY TOKEN COUNT — e.g. LIST_PARTS
    options always differ in length (median spread 10 tokens, vs ~0.5 content
    tokens unique to an option), because the shared framing tokens are added
    once per part. Sum = count × mean, so count differences never canceled.
    The correction: option vectors now sum ONLY the tokens that are NOT
    shared by all three options. Semantics, per the owner's mathematical
    review: in exact arithmetic, removing an IDENTICAL vector from every
    option shifts every score by the same amount and leaves softmax
    probabilities, loss, and gradients unchanged. This removal is
    PER-OCCURRENCE and therefore count-respecting — the vector removed from
    an option differs from another option's whenever shared tokens occur
    with different counts, so it can change score differences only through
    those count differences; any finite-precision benefit (large common
    contributions removed before summation) is a HYPOTHESIS to be measured,
    not an automatic recovery of information. FIND_SHARED_PART options
    ([OBS] + one tag token each) have EQUAL length — equal length does not
    rule out projected-vector collapse (sum = 2 × mean), so its flatness is
    not explained by answer length; the distinct tag vectors and the module
    output are measured by the diagnostic instead.

    Relationship encoder 001 (owner-directed 2026-09-09, PREPARED not
    launched): the PROBLEM vector is now built by the structural encoder
    (``encoder["encode_problem"]``): each complete node line and each
    complete relation line is bound into ONE joint vector by a fixed
    elementwise (Hadamard) product over its token rows, the bound segment
    vectors are summed, and the non-structural tokens (framing/request) are
    mean-pooled on top. Complete source-relationship-target pairings and
    node-contents associations survive; independent role sums are NOT used.
    The module interface (one d_model vector in, one out), the repaired
    token lookup, the option path, the learning scope, and the teaching
    allowance are UNCHANGED. See RELATIONSHIP_ENCODER_001.md."""

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
            _problem_ids, slot_ids = framework.encoder["encode"](task["public"])
            self._problem_vectors.append(
                framework.encoder["encode_problem"](task["public"]))
            content = self._content_ids(slot_ids)
            zero = self.torch.zeros_like(self._problem_vectors[-1])
            self._option_vectors.append([self._sum(item) if item else zero
                                         for item in content])

    def _sum(self, token_ids):
        """Follow-up 001: options are summed, NOT averaged, so the frozen
        readout sees each option's distinct tokens instead of one collapsed
        direction (the measured ln(3) mechanism)."""
        vectors = [self.framework.encoder["embed"](token_id) for token_id in token_ids]
        require(vectors, "OPTION_EMBEDDING_REQUIRED")
        stacked = self.torch.stack(vectors)
        return stacked.sum(dim=0)

    def _content_ids(self, slot_ids):
        """Correction 002: per-occurrence removal of tokens shared by all
        three options (count-respecting; NOT an identical-vector shift). An
        option whose tokens are ALL shared by the other two (a strict subset
        option — 10 of the 60 training+practice records have one) yields
        EMPTY content, represented by the zero vector: its score relative to
        the common baseline is exactly the common shift."""
        sequences = [slot_ids[slot] for slot in (0, 1, 2)]
        shared = set(sequences[0]) & set(sequences[1]) & set(sequences[2])
        return [[token_id for token_id in sequence if token_id not in shared]
                for sequence in sequences]

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
        if task_input["record_id"] in self._index:
            position = self._position(task_input)
            scores = self.forward(position)
            return self.tasks[position]["encoded_options"][
                int(self.torch.argmax(scores).item())]
        # sealed-split path: encode the public record on demand (attempt 008's
        # preserved error: the training index does not contain sealed records)
        _problem_ids, slot_ids = self.framework.encoder["encode"](task_input["public"])
        value = self.module(
            self.framework.encoder["encode_problem"](task_input["public"]).unsqueeze(0))[0]
        content = self._content_ids(slot_ids)
        scores = self.torch.stack([self.torch.dot(value, self._sum(item))
                                   for item in content])
        return task_input["encoded_options"][int(self.torch.argmax(scores).item())]
