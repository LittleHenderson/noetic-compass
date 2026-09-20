"""Pre-flight: drive the POINTER worker end to end with a NON-NEURAL stand-in learner. $0, no torch, no GPU.

Copied from `records/typed_practice_001/preflight_dry_run.py` (282 lines, the practice study's own dry run) and
adapted to this machine. Everything the pointer worker does is real -- config validation, the contract's frozen
material, the ten-pass STRATIFIED schedule, the held-back split, seal before targets, the per-pass logs, every
evaluation, checkpoints, partial checkpoints, reloads, replays, the DG4 identity record, the checkpoint check's
phase order, the ablations, the evidence publisher's create-only rule, delivery and the artifact contract --
EXCEPT the neural parts, which are replaced:

- the learner is a deterministic stand-in, for BOTH machines the job builds. Its "weights" are a hash chain over
  the sealed batches, and its counters follow the POINTER learner's own counting, because that is what
  `pointer_contract.expected_main_delta` compares the summed per-update deltas to as canonical bytes.
  THE COUNTER KEY SET IS `pointer_contract.MAIN_COUNTERS` (11 keys), NOT the practice machine's per-slot set:
  `packet_forward_calls` replaces `slot_forwards`, because the pointer machine has no per-slot forward
  (INTERFACE_SPEC_POINTER section 1, review DG10). One packet forward is one presentation and runs
  `PLANNED_WORK_ROUNDS` = 8 shared message-passing rounds, so `core_forward_*` and `sample_core_passes` advance
  by rounds x packets, never by slots.
- torch/CUDA, the frozen encoder, the framework, the source attestor and the wheel check are stand-ins;
- `stand_in_state_identity` replaces `learner.state_identity`. It returns the START IDENTITY THE STAND-IN
  RECORDED -- read from the pinned practice receipt's own sidecar -- rather than a hash of the stand-in's own
  values, because the real check is a byte-exact hash of real tensors and no non-neural stand-in can reproduce
  one. The consequence is deliberate and is the dry run's honest finding, see below.
- `checker.check_answer` is a fast stand-in (the stand-in answers are not real answers); the real
  `checker.derive_target` is used, memoised by query id and focus world.
- `checker` is NOT imported before the checkpoint check's phase A: the worker requires it to be absent from
  `sys.modules` at that point (`cncm/typed_pointer_worker.py:724`, `:728`), so the stand-in is installed by
  wrapping `_main_training`, which runs after phase A. A stand-in installed at import time would break the one
  custody property this dry run exists to prove.

Expected outcome. The REAL pointer gate reader (`records/typed_pointer_001/evaluate_gates.py`) reads the three
dry-run receipts. I1, I2 and I4 must PASS and I3 must FAIL, so the label is VOID. I3 fails on the reader's V3
guard: the stand-in's identity function cannot tell the whole container from the three `^6` tensors, so the two
identities coincide and the reader correctly refuses a check that compares the job to itself
(`I3:<seed>:DG4_FLAG:whole_container_form_is_a_different_number` and `I3:<seed>:DG4_NOT_DISTINCT_FORM`). It does
NOT fail because "a stand-in's start cannot be the practice study's start": that condition is a HARD requirement
inside the worker (`cncm/typed_pointer_worker.py:859`), so a stand-in whose start differed would abort the job,
fail I1, and make this a PREFLIGHT_FAIL for a reason that could never be fixed at $0. Anything other than the
expected failure set is a bug found for $0, and this script also refuses a run whose REPORT-ONLY phases
(phase A, phase B, ablations) came back anything but COMPLETE.

ONE JOB PER CONTAINER, at $0. The three seeds do NOT share the private checker's presence: `fresh_container()`
drops `cas_meta2.typed_teaching.checker` from `sys.modules` between jobs, because the worker's phase-A custody
check is `"cas_meta2.typed_teaching.checker" in sys.modules` (`cncm/typed_pointer_worker.py:732`) and AWS gives
every job its own container. Without that boundary the first job's phase A is COMPLETE and every later job's is
FAILED with `POINTER_PHASE_A_CUSTODY` -- which is what the first run of this script measured, and which is a
property of the harness's process model, not of the study.

    python preflight_dry_run.py SCRATCH_DIR
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for extra in (ROOT, ROOT / 'research/CAS_META_2_COMPOSITION', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from cas_meta2.typed_teaching import pointer_contract as contract, slots as slot_module
from cas_meta2.teaching_cycle import gpu_adapter
from cncm import typed_pointer_worker as worker, typed_matched_worker as matched_worker, typed_course_worker as base
from cncm import rpa_learning_worker
import evaluate_gates

COUNTERS = contract.MAIN_COUNTERS
CORE_ROUNDS = contract.PLANNED_WORK_ROUNDS
CORE_PARAMETERS = ('left.weight', 'right.weight', 'merge.weight')
# THE REAL CONTAINER'S OWN 48 NAMES, in sorted order. This list MODELS the pointer container so the
# rehearsal can run its ablations without torch, and it must be kept in step with
# `pointer_learner._build_container(...).state_dict()`.
#
# IT HAD FALLEN A DESIGN BEHIND. The previous 25-name list still carried six names from an abandoned
# design -- `round_state_norm`, `round_parent_norm`, `round_child_norm`, `self_mix`, `parent_mix`,
# `child_mix` -- which `typed_pointer_worker.py:168-173` records as having "matched nothing at all".
# The ablation coverage check is constructive over the keys it is handed, so those six names were
# covered by NO component and the rehearsal refused with
# `POINTER_ABLATION_COVERAGE:child_mix:covered=19:of=25`. That failure said nothing about Helm and
# everything about this list: **the $0 gate was testing the wrong shape.** It also had to gain Helm
# 2.0's two new tensors, `state_encode.weight` and `match_key.weight`.
#
# Refresh it with:
#   python -c "import torch,sys; sys.path[:0]=['.','research/CAS_META_2_COMPOSITION']; \
#     from cas_meta2.graph_teaching.real_framework import build_graph_training_framework as b; \
#     from cas_meta2.typed_teaching import pointer_learner as p; \
#     print(sorted(p._build_container(torch,b(torch,torch.device('cpu'),seed=20260917, \
#     encoder={'d_model':64}),torch.device('cpu')).state_dict()))"
CONTAINER_NAMES = (
    'left.weight', 'right.weight', 'merge.weight',
    'attention_key.weight', 'declaration_projection.weight', 'declaration_table',
    'directed_pair_embedding',
    'edge_head.0.weight', 'edge_head.2.bias', 'edge_head.2.weight', 'edge_head.3.bias',
    'edge_head.3.weight',
    'match_key.weight',
    'mode_option_head.0.weight', 'mode_option_head.2.bias', 'mode_option_head.2.weight',
    'mode_option_head.3.bias', 'mode_option_head.3.weight',
    'node_encode.weight',
    'node_head.0.weight', 'node_head.2.bias', 'node_head.2.weight', 'node_head.3.bias',
    'node_head.3.weight',
    'pointer_key.weight',
    'query_norm.bias', 'query_norm.weight', 'query_projection.weight',
    'reach_option_head.0.weight', 'reach_option_head.2.bias', 'reach_option_head.2.weight',
    'reach_option_head.3.bias', 'reach_option_head.3.weight',
    'role_embedding',
    'role_head.0.weight', 'role_head.2.bias', 'role_head.2.weight', 'role_head.3.bias',
    'role_head.3.weight',
    'round_mix', 'round_rate',
    'state_encode.weight',
    'world_head.0.weight', 'world_head.2.bias', 'world_head.2.weight', 'world_head.3.bias',
    'world_head.3.weight',
    'world_projection.weight')
PRACTICE_CHECKPOINTS = ROOT / 'records/typed_practice_001'
CLAUSE_COUNT = 6
I3_STAND_IN_CODES = ('DG4_FLAG:whole_container_form_is_a_different_number', 'DG4_NOT_DISTINCT_FORM')
REQUIRED_PHASE_STATUSES = ('checkpoint_check_phase_a_status', 'checkpoint_check_phase_b_status', 'ablation_status')


def h(text):
    return sha256(text.encode()).hexdigest()


def enc(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def floats(seed, count):
    """`count` deterministic finite floats in [-1, 1] from one seed string. A stand-in weight generator."""
    out, block = [], sha256(seed.encode()).digest()
    while len(out) < count:
        for at in range(0, len(block) - 3, 4):
            if len(out) == count:
                break
            raw = int.from_bytes(block[at:at + 4], "big")
            out.append((raw / 0x7FFFFFFF) - 1.0)
        block = sha256(block).digest()
    return out


def value_of(item):
    return item.data[0] if isinstance(item, FakeTensor) else float(item)


class FakeTensor:
    """A flat float payload with a shape: only the operations the real code paths actually perform."""

    __slots__ = ('data', 'shape', 'identity', 'dtype', 'device', 'requires_grad')

    def __init__(self, data, shape=None, *, identity=None, dtype='float32', device='cuda:0',
                 requires_grad=False):
        self.data = [float(value) for value in data]
        self.shape = tuple(shape) if shape is not None else (len(self.data),)
        self.identity, self.dtype, self.device, self.requires_grad = identity, dtype, device, requires_grad

    # ---- shape ----
    def __len__(self):
        return self.shape[0]

    def __iter__(self):
        if len(self.shape) == 1:
            return iter([self[at] for at in range(self.shape[0])])
        if len(self.shape) == 2:
            return iter([self[at] for at in range(self.shape[0])])
        raise ValueError('STAND_IN_ITER')

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start or 0, self.shape[0] if key.stop is None else key.stop
            width = 1 if len(self.shape) == 1 else self.shape[1]
            data = self.data[start * width:stop * width]
            return FakeTensor(data, (stop - start,) if len(self.shape) == 1 else (stop - start, width),
                              identity=self.identity)
        if isinstance(key, (list, tuple)):
            width = 1 if len(self.shape) == 1 else self.shape[1]
            data = []
            for at in key:
                data += self.data[at * width:(at + 1) * width]
            return FakeTensor(data, (len(key),) if len(self.shape) == 1 else (len(key), width),
                              identity=self.identity)
        width = 1 if len(self.shape) == 1 else self.shape[1]
        data = self.data[key * width:(key + 1) * width]
        return FakeTensor(data, shape=() if len(self.shape) == 1 else (width,), identity=self.identity)

    def _binary(self, other, op):
        if isinstance(other, FakeTensor):
            if other.shape == ():
                return FakeTensor([op(a, other.data[0]) for a in self.data], self.shape,
                                  identity=self.identity)
            if self.shape == ():
                return FakeTensor([op(self.data[0], b) for b in other.data], other.shape,
                                  identity=self.identity)
            require_shape(self.shape == other.shape, 'STAND_IN_BINARY_SHAPE')
            return FakeTensor([op(a, b) for a, b in zip(self.data, other.data)], self.shape,
                              identity=self.identity)
        return FakeTensor([op(a, float(other)) for a in self.data], self.shape, identity=self.identity)

    def __add__(self, other):
        return self._binary(other, lambda a, b: a + b)

    def __radd__(self, other):
        return self._binary(other, lambda a, b: b + a)

    def __sub__(self, other):
        return self._binary(other, lambda a, b: a - b)

    def __mul__(self, other):
        return self._binary(other, lambda a, b: a * b)

    def __rmul__(self, other):
        return self._binary(other, lambda a, b: b * a)

    def __truediv__(self, other):
        return self._binary(other, lambda a, b: a / b)

    def __pow__(self, other):
        return self._binary(other, lambda a, b: a ** b)

    def __eq__(self, other):
        return self._binary(other, lambda a, b: 1.0 if a == b else 0.0)

    def __hash__(self):
        return hash(tuple(self.data))

    def mean(self, dim=None):
        if dim is None:
            return FakeTensor([sum(self.data) / len(self.data)], shape=())
        rows, width = self.shape[0], self.shape[1]
        return FakeTensor([sum(self.data[at * width:(at + 1) * width]) / rows for at in range(width)],
                          (width,), identity=self.identity)

    def sum(self):
        return FakeTensor([sum(self.data)], shape=())

    def sqrt(self):
        return FakeTensor([value ** 0.5 for value in self.data], self.shape, identity=self.identity)

    def isfinite(self):
        return FakeTensor([1.0 if value == value and abs(value) != float('inf') else 0.0
                           for value in self.data], self.shape)

    def all(self):
        return FakeTensor([1.0 if all(value != 0.0 for value in self.data) else 0.0], shape=())

    def item(self):
        return self.data[0]

    def __float__(self):
        return float(self.data[0])

    def __int__(self):
        return int(self.data[0])

    def detach(self):
        return self

    def cpu(self):
        return self

    def to(self, device):
        return FakeTensor(self.data, self.shape, identity=self.identity, dtype=self.dtype, device=device)

    def copy_(self, other):
        require_shape(len(other.data) == len(self.data), 'STAND_IN_COPY_SHAPE')
        self.data = list(other.data)
        return self

    def unsqueeze(self, dim):
        return FakeTensor(self.data, (1,) + self.shape, identity=self.identity)

    def transpose(self, first, second):
        require_shape(self.shape == (self.shape[0], self.shape[1]) and (first, second) == (0, 1),
                      'STAND_IN_TRANSPOSE')
        rows, width = self.shape
        return FakeTensor([self.data[row * width + column] for column in range(width) for row in range(rows)],
                          (width, rows), identity=self.identity)

    def matmul(self, other):
        if len(self.shape) == 2 and len(other.shape) == 1:
            rows, width = self.shape
            return FakeTensor([sum(self.data[row * width + at] * other.data[at] for at in range(width))
                               for row in range(rows)], (rows,), identity=self.identity)
        if len(self.shape) == 2 and len(other.shape) == 2:
            rows, width = self.shape
            columns = other.shape[1]
            return FakeTensor([sum(self.data[row * width + at] * other.data[at * columns + column]
                                   for at in range(width))
                               for row in range(rows) for column in range(columns)], (rows, columns),
                              identity=self.identity)
        if len(self.shape) == 1 and len(other.shape) == 2:
            width = other.shape[1]
            return FakeTensor([sum(self.data[at] * other.data[at * width + column] for at in range(width))
                               for column in range(width)], (width,), identity=self.identity)
        raise ValueError('STAND_IN_MATMUL')

    def __setitem__(self, key, value):
        width = 1 if len(self.shape) == 1 else self.shape[1]
        if isinstance(key, tuple):
            row, column = key
            self.data[row * width + column] = float(value)
            return
        require_shape(not isinstance(key, slice), 'STAND_IN_SETITEM_SLICE')
        self.data[key * width:(key + 1) * width] = [float(value)] * width

    def __matmul__(self, other):
        return self.matmul(other)

    def argmax(self, dim=1):
        rows, width = self.shape
        return FakeTensor([max(range(width), key=lambda at: self.data[row * width + at])
                           for row in range(rows)], (rows,), dtype='int64')


def require_shape(condition, code):
    if not condition:
        raise ValueError(code)


class FakeReadout:
    """`encoder.readout_rows`: a (90, 64) row table whose rows are generated on demand, deterministically."""

    shape = (90, 64)

    def __init__(self, token):
        self.token = token

    def row(self, index):
        return floats('%s:readout:%d' % (self.token, index), 64)

    def __getitem__(self, key):
        if isinstance(key, (list, tuple)):
            return FakeTensor([value for index in key for value in self.row(index)], (len(key), 64))
        return FakeTensor(self.row(key), (64,))


class FakeParameter:
    __slots__ = ('name', 'tensor', 'device', 'dtype', 'requires_grad')

    def __init__(self, name, tensor):
        self.name, self.tensor = name, tensor
        self.device, self.dtype, self.requires_grad = tensor.device, 'float32', True

    def copy_(self, other):
        self.tensor = FakeTensor(other.data, other.shape, identity=other.identity, device=self.device)
        return self

    def to(self, device):
        return self.tensor.to(device)


class FakeModule:
    """The `^6` container: its state dict holds the three core tensors AND the named components the ablations
    reset one at a time, so `_three_key_state` and `_reset_component` both see the shapes they require."""

    def __init__(self, token, names=CONTAINER_NAMES):
        self.training = True
        self._identity = token
        self._parameters = {name: FakeParameter(name, FakeTensor(floats('%s:%s' % (token, name), 8),
                                                                 identity=token))
                            for name in names}

    def state_dict(self):
        return {name: FakeTensor(parameter.tensor.data, parameter.tensor.shape, identity=parameter.tensor.identity)
                for name, parameter in self._parameters.items()}

    def named_parameters(self):
        return list(self._parameters.items())

    def parameters(self):
        return list(self._parameters.values())

    def train(self, mode=True):
        self.training = bool(mode)
        return self

    def eval(self):
        self.training = False
        return self

    def set_identity(self, token):
        self._identity = token
        for name, parameter in self._parameters.items():
            parameter.tensor = FakeTensor(floats('%s:%s' % (token, name), 8), identity=token)

    def __call__(self, incoming):
        rows = incoming.shape[0]
        width = incoming.shape[1]
        out = []
        for row in range(rows):
            base = [incoming.data[row * width + at] for at in range(width)]
            out += [0.5 * base[at] + 0.25 * base[(at + 1) % width] + 0.125 * base[(at + 3) % width]
                    for at in range(width)]
        return FakeTensor(out, (rows, width))


class FakeTorch:
    float32, float64, int64 = 'float32', 'float64', 'int64'

    def __init__(self):
        self.__version__ = '2.11.0+cu128'
        self.version = SimpleNamespace(cuda='12.8')
        self.cuda = SimpleNamespace(
            is_available=lambda: True, device_count=lambda: 1, current_device=lambda: 0,
            get_device_name=lambda device: 'NVIDIA RTX PRO 4500 (stand-in)',
            reset_peak_memory_stats=lambda device: None, max_memory_allocated=lambda device: 0,
            max_memory_reserved=lambda device: 0, manual_seed_all=lambda seed: None)
        self.backends = SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True)),
                                        cudnn=SimpleNamespace(allow_tf32=True))
        self.device = lambda value: value
        self.use_deterministic_algorithms = lambda flag: None
        self.is_tensor = lambda value: isinstance(value, FakeTensor)
        self.no_grad = lambda: _NoGrad()
        self.eye = lambda size, dtype=None: FakeTensor([1.0 if row == column else 0.0
                                                       for row in range(size) for column in range(size)],
                                                      (size, size), dtype=dtype or 'float32')
        self.linalg = SimpleNamespace(solve=self._solve)
        self.optim = SimpleNamespace(AdamW=lambda *a, **k: SimpleNamespace(state_dict=lambda: {}, zero_grad=None))

    @staticmethod
    def _solve(matrix, target):
        size = matrix.shape[0]
        columns = target.shape[1]
        augmented = [list(matrix.data[row * size:(row + 1) * size])
                     + list(target.data[row * columns:(row + 1) * columns]) for row in range(size)]
        for column in range(size):
            pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
            require_shape(augmented[pivot][column] != 0.0, 'STAND_IN_SINGULAR_SYSTEM')
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
            factor = augmented[column][column]
            augmented[column] = [value / factor for value in augmented[column]]
            for row in range(size):
                if row == column:
                    continue
                scale = augmented[row][column]
                augmented[row] = [value - scale * other for value, other
                                  in zip(augmented[row], augmented[column])]
        return FakeTensor([augmented[row][size + at] for row in range(size) for at in range(columns)],
                          (size, columns), dtype='float64')

    def stack(self, values):
        values = list(values)
        require_shape(bool(values), 'STAND_IN_STACK')
        if values[0].shape == ():
            return FakeTensor([value.data[0] for value in values], (len(values),))
        return FakeTensor([item for value in values for item in value.data],
                          (len(values),) + values[0].shape, identity=values[0].identity)

    def zeros(self, *shape, dtype=None, device=None):
        if len(shape) == 1 and isinstance(shape[0], (list, tuple)):
            shape = tuple(shape[0])
        return FakeTensor([0.0] * int(_product(shape)), tuple(int(value) for value in shape), dtype=dtype,
                          device=device or 'cuda:0')

    def tensor(self, value, dtype=None, device=None):
        data, shape = _flatten(value)
        return FakeTensor(data, shape, dtype=dtype or 'float32', device=device or 'cuda:0')

    def sqrt(self, value):
        return value.sqrt()

    def mean(self, value):
        return value.mean()

    def isfinite(self, value):
        return value.isfinite()

    def equal(self, first, second):
        return first.shape == second.shape and first.data == second.data

    def load(self, path, map_location=None, weights_only=None):
        payload = json.loads(Path(path).read_bytes())
        token = payload['identity']
        return {'model_state': {name: FakeTensor(value, identity=token)
                                for name, value in payload['module_state'].items()}}


class _NoGrad:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _product(shape):
    total = 1
    for value in shape:
        total *= int(value)
    return total


def _flatten(value):
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (list, tuple)):
            rows = [_flatten(row) for row in value]
            return [item for row, _shape in rows for item in row], (len(rows), rows[0][1][0])
        return [float(item) for item in value], (len(value),)
    return [float(value)], ()


class FakeEncoder:
    """The frozen typed encoder, stood in: a deterministic slot vector and an on-demand readout table."""

    def __init__(self, torch, token):
        self.torch, self.token = torch, token
        self.identity = {'schema': 'stand-in-encoder/0.1', 'token': token}
        self.symbol_to_index = {}
        self.readout_rows = FakeReadout(token)

    def verify_frozen(self):
        return True

    def work_counters(self):
        return {'stand_in': True}

    def export_state(self):
        return {'stand_in_encoder': self.token}

    def index_of(self, symbol):
        if symbol not in self.symbol_to_index:
            self.symbol_to_index[symbol] = len(self.symbol_to_index)
        return self.symbol_to_index[symbol]

    def encode_slot(self, packet, plan, slot):
        for symbol in slot['symbols']:
            self.index_of(symbol)
        return FakeTensor(floats('%s:%s:%s' % (self.token, plan['record_id'], slot['slot_id']), 64),
                          identity=self.token)


def stand_in_state_identity(torch, value):
    """The stand-in `learner.state_identity`: the token the stand-in RECORDED, not a hash of its own values.

    A real `state_identity` is a byte-exact hash of real tensor bytes; a $0 stand-in cannot produce one that
    equals the practice study's recorded start. So the stand-in carries the recorded start identity as a token
    and returns it. The consequence is the dry run's finding: the token is the same for the three `^6` tensors
    and for the whole container, so the reader's V3 guard sees a job compared to itself and I3 fails.
    """
    tokens = {tensor.identity for tensor in value.values() if getattr(tensor, 'identity', None)}
    if len(tokens) == 1:
        return tokens.pop()
    return sha256(enc({name: tensor.data for name, tensor in sorted(value.items())}).encode()).hexdigest()


def recorded_practice_identity(seed, name='initial'):
    """This seed's recorded start identity, READ from the pinned practice receipt's own sidecar."""
    path = PRACTICE_CHECKPOINTS / ('receipt_%d' % seed) / 'checkpoints' / (name + '_checkpoint.json')
    return json.loads(path.read_bytes())['metadata']['model_state_identity']


def _slot_vector(torch, module, encoder, packet, plan, slot, depth):
    """The post-block vector of one slot, by the forward's own arithmetic: `encode_slot`, the same `rms`, the
    same identity `cast`, `recurrence.run_passes` at the evaluation depth over the registered core."""
    from cas_meta2.recurrent_cjt import recurrence

    def rms(values):
        require_shape(all(torch.is_tensor(value) for value in values), 'POINTER_PHASE_A_DETACHED')
        vector = torch.stack(list(values))
        return torch.sqrt(torch.mean(vector * vector))

    def core(incoming):
        result = module(torch.stack(list(incoming)).unsqueeze(0))[0]
        return result

    encoded = encoder.encode_slot(packet, plan, slot)
    final = recurrence.run_passes(encoded, core, depth=depth, state=None, rms_fn=rms,
                                  cast=lambda value: value,
                                  zeros=lambda count: torch.zeros(count, dtype=encoded.dtype,
                                                                  device=encoded.device))
    return torch.stack(list(final))


def _scores_from_vector(torch, encoder, plan, vector):
    scores = {}
    for slot in plan['slots']:
        indexes = [encoder.index_of(symbol) for symbol in slot['symbols']]
        logits = encoder.readout_rows[indexes] @ vector
        scores[slot['slot_id']] = {symbol: float(logits[at].detach().cpu().item())
                                   for at, symbol in enumerate(slot['symbols'])}
    return scores


def _assemble(packet, scores):
    """The real `slots.score_decisions` / `slots.assemble_answer`, or a RECORDED stand-in if they refuse."""
    try:
        decisions = slot_module.score_decisions(packet, scores)
        return decisions, slot_module.assemble_answer(packet, decisions), 'REAL_SCORE_AND_ASSEMBLE'
    except Exception as error:                                   # noqa: BLE001 - recorded, never hidden
        return {}, {'stand_in': h(enc(scores))[:16]}, 'STAND_IN_FALLBACK:' + type(error).__name__


def _prediction(torch, encoder, packet, plan, scores, *, revision, run_identity_digest, depth):
    decisions, answer, source = _assemble(packet, scores)
    body = {'schema': 'cncm.typed-pointer-stand-in-prediction/0.1', 'record_id': plan['record_id'],
            'packet_digest': plan['packet_digest'], 'slot_plan_digest': plan['plan_digest'], 'depth': depth,
            'model_revision': revision, 'run_context_digest': run_identity_digest,
            'encoder_identity_digest': h(enc(encoder.identity)), 'scores': scores, 'decisions': decisions,
            'answer': answer, 'answer_source': source}
    return {**body, 'prediction_id': 'stand-in-prediction-' + h(enc(body))}


class StandInPracticeLearner:
    """The practice machine, stood in for the checkpoint check: restores a real pinned checkpoint's IDENTITY.

    The checkpoint FILE is a torch pickle and cannot be read without torch, so the stand-in verifies the file
    against the contract's pin by bytes and takes the identity from the sidecar that ships beside it, which is
    the same value `_checkpoint_check_phase_a` reads for `practice_recorded_model_state_identity`.
    """

    def __init__(self, torch, encoder, token, *, device='cuda:0'):
        self.torch, self.encoder, self.device = torch, encoder, device
        self.module = FakeModule(token, names=CORE_PARAMETERS)
        self.counters = {key: 0 for key in COUNTERS}
        self.limits = {'max_updates': 1, 'max_core_calls': 1, 'max_wall_seconds': 1}
        self.cursor = self.model_revision = 0
        self.failed = False
        self.run_identity = {'context': {'run_id': 'stand-in-deleted'}, 'limits': dict(self.limits)}
        self.run_identity_digest = h(enc(self.run_identity))

    def _budget(self):
        return True

    def predict(self, packet, depth):
        plan = slot_module.compile_slots(packet)
        scores = {}
        for slot in plan['slots']:
            vector = _slot_vector(self.torch, self.module, self.encoder, packet, plan, slot, depth)
            indexes = [self.encoder.index_of(symbol) for symbol in slot['symbols']]
            logits = self.encoder.readout_rows[indexes] @ vector
            scores[slot['slot_id']] = {symbol: float(logits[at].detach().cpu().item())
                                       for at, symbol in enumerate(slot['symbols'])}
        return _prediction(self.torch, self.encoder, packet, plan, scores, revision=self.model_revision,
                           run_identity_digest=self.run_identity_digest, depth=depth)

    def state(self):
        return {'model_state_identity': self.module._identity,
                'optimizer_state_identity': h('opt' + self.module._identity),
                'rng_state_identity': h('rng' + self.module._identity),
                'encoder_state_identity': 'stand-in-encoder'}

    @classmethod
    def restore_checkpoint(cls, torch, framework, *, path, expected_sha256, expected_run_identity_digest, device):
        path = Path(path)
        raw = path.read_bytes()
        require_shape(sha256(raw).hexdigest() == expected_sha256, 'STAND_IN_PRACTICE_CHECKPOINT_HASH')
        sidecar = json.loads(path.with_name(path.stem + '_checkpoint.json').read_bytes())
        require_shape(sidecar['run_identity_digest'] == expected_run_identity_digest,
                      'STAND_IN_PRACTICE_RUN_IDENTITY')
        encoder = FakeEncoder(torch, sidecar['metadata']['model_state_identity'])
        learner = cls(torch, encoder, sidecar['metadata']['model_state_identity'], device=device)
        learner.counters = {key: 0 for key in COUNTERS}
        return learner


class StandInPointerLearner:
    """The pointer machine, stood in. Its public surface is `pointer_learner.PointerCourseLearner`'s own."""

    def __init__(self, torch, framework, encoder, *, optimizer_config, run_context, limits, device,
                 tagger=None, python_seed=0, root=None):
        self.torch, self.framework, self.encoder, self.device = torch, framework, encoder, device
        self.tagger, self.python_seed, self.root = tagger, python_seed, str(root)
        self.optimizer_config, self.limits = dict(optimizer_config), dict(limits)
        self.token = recorded_practice_identity(python_seed)
        self.module = FakeModule(self.token)
        self.optimizer = SimpleNamespace(state_dict=lambda: {'stand_in': True}, zero_grad=lambda **k: None)
        self.run_identity = {'context': dict(run_context), 'limits': dict(limits),
                             'initial_model_identity': self.token, 'counters': list(COUNTERS)}
        self.run_identity_digest = h(enc(self.run_identity))
        self.cursor = self.model_revision = 0
        self.counters = {key: 0 for key in COUNTERS}
        self._pending, self.failed = None, False

    def _budget(self):
        if self.failed:
            raise ValueError('STAND_IN_LEARNER_FAILED')

    def _charge_packet(self):
        self.counters['packet_forward_calls'] += 1
        self.counters['core_forward_attempts'] += CORE_ROUNDS
        self.counters['core_forward_calls'] += CORE_ROUNDS
        self.counters['sample_core_passes'] += CORE_ROUNDS
        self.counters['prediction_calls'] += 1

    @staticmethod
    def _focus_node_count(packet):
        focus = packet['source']['focus_world_id']
        for world in packet['source']['worlds']:
            if world['world_id'] == focus:
                return len(world['nodes'])
        raise ValueError('STAND_IN_FOCUS_WORLD')

    def _graph(self, packet):
        self._budget()
        plan = slot_module.compile_slots(packet)
        self._charge_packet()
        indicators = [0] * CLAUSE_COUNT
        if self.tagger is not None and packet['record']['query']['kind'] == 'role_set':
            indicators = list(self.tagger.indicators(packet))
        nodes = self._focus_node_count(packet)
        seed = '%s:%s:%s' % (self.module._identity, plan['record_id'], sum(indicators))
        vector = FakeTensor(floats(seed, 64), identity=self.module._identity)
        scores = _scores_from_vector(self.torch, self.encoder, plan, vector)
        require_shape(set(scores) == {slot['slot_id'] for slot in plan['slots']}, 'STAND_IN_SLOT_COVERAGE')
        prediction = _prediction(self.torch, self.encoder, packet, plan, scores,
                                 revision=self.model_revision, run_identity_digest=self.run_identity_digest,
                                 depth=contract.DESIGN['prediction_depth'])
        hidden = FakeTensor([value for at in range(nodes) for value in floats(seed + ':node:%d' % at, 64)],
                            (nodes, 64), identity=self.module._identity)
        forward = SimpleNamespace(hidden=hidden, focus_offset=0, focus_position=0, blocks=[(0, nodes)])
        return {'packet': packet, 'prediction': prediction, 'plan': plan, 'forward': forward, 'vector': vector}

    def predict(self, packet, depth):
        require_shape(self._pending is None, 'STAND_IN_PENDING_BATCH')
        require_shape(depth == contract.DESIGN['prediction_depth'], 'STAND_IN_PREDICTION_DEPTH')
        self.module.eval()
        return self._graph(packet)['prediction']

    def stage_batch(self, packets, depth, *, cursor, occurrence_ids):
        self._budget()
        require_shape(self._pending is None and cursor == self.cursor
                      and self.counters['optimizer_updates'] < self.limits['max_updates'],
                      'STAND_IN_BATCH_CURSOR')
        require_shape(type(packets) is list and 0 < len(packets) <= len(contract.KINDS)
                      and len(occurrence_ids) == len(packets), 'STAND_IN_BATCH_SHAPE')
        self.module.train()
        results = [self._graph(packet) for packet in packets]
        body = {'schema': 'cncm.typed-pointer-stand-in-batch/0.1', 'cursor': cursor,
                'model_revision': self.model_revision, 'run_identity_digest': self.run_identity_digest,
                'occurrence_ids': list(occurrence_ids),
                'predictions': [result['prediction'] for result in results]}
        public = {**body, 'batch_id': 'stand-in-batch-' + h(enc(body))}
        raw = (enc(public) + '\n').encode()
        self._pending = {'results': results, 'raw': raw, 'model_identity': self.module._identity}
        self.counters['staged_batches'] += 1
        return {'public': public, 'bytes': raw, 'sha256': sha256(raw).hexdigest()}

    def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
        raw = Path(path).read_bytes()
        require_shape(self._pending is not None and raw == self._pending['raw']
                      and sha256(raw).hexdigest() == expected_sha256, 'STAND_IN_SEAL_MISMATCH')
        require_shape(len(target_receipts) == len(self._pending['results']), 'STAND_IN_TARGET_COUNT')
        require_shape(self.module._identity == self._pending['model_identity'], 'STAND_IN_MODEL_CHANGED')
        self.counters['private_loss_plan_calls'] += len(target_receipts)
        for key in ('backward_attempts', 'backward_calls', 'optimizer_step_attempts', 'optimizer_updates'):
            self.counters[key] += 1
        self.module.set_identity(h(self.module._identity + sha256(raw).hexdigest()))
        self.cursor += 1; self.model_revision += 1; self._pending = None
        return {'schema': 'cncm.typed-pointer-stand-in-update/0.1', 'cursor_committed': self.cursor,
                'raw_batch_loss': 1.0 / self.cursor, 'gradient_squared_norm': 1.0,
                'counters': dict(self.counters), 'tasks': []}

    def state(self):
        return {'model_state_identity': self.module._identity,
                'optimizer_state_identity': h('opt' + self.module._identity),
                'rng_state_identity': h('rng' + self.module._identity),
                'encoder_state_identity': 'stand-in-encoder'}

    def export_checkpoint(self, path):
        state = self.module.state_dict()
        payload = {'identity': self.module._identity, 'cursor': self.cursor,
                   'model_revision': self.model_revision, 'counters': dict(self.counters),
                   'run_identity': self.run_identity, 'run_identity_digest': self.run_identity_digest,
                   'limits': self.limits,
                   'module_state': {name: tensor.data for name, tensor in sorted(state.items())}}
        raw = (enc(payload) + '\n').encode()
        with Path(path).open('xb') as stream:
            stream.write(raw)
        metadata = {**self.state(), 'run_identity': self.run_identity,
                    'run_identity_digest': self.run_identity_digest, 'model_revision': self.model_revision,
                    'cursor': self.cursor, 'counters': dict(self.counters), 'elapsed_seconds': 0.0,
                    'training_mode': True}
        return {'path': str(Path(path).resolve()), 'sha256': sha256(raw).hexdigest(), 'bytes': len(raw),
                'run_identity_digest': self.run_identity_digest, 'metadata': metadata}

    @classmethod
    def restore_checkpoint(cls, torch, framework, encoder, *, path, expected_sha256,
                           expected_run_identity_digest, device):
        raw = Path(path).read_bytes()
        require_shape(sha256(raw).hexdigest() == expected_sha256, 'STAND_IN_POINTER_CHECKPOINT_HASH')
        payload = json.loads(raw)
        require_shape(payload['run_identity_digest'] == expected_run_identity_digest,
                      'STAND_IN_POINTER_RUN_IDENTITY')
        obj = cls.__new__(cls)
        obj.torch, obj.framework, obj.encoder, obj.device = torch, framework, encoder, device
        obj.tagger, obj.python_seed, obj.root = None, 0, None
        obj.optimizer_config, obj.limits = {}, dict(payload['limits'])
        obj.token = payload['identity']
        obj.module = FakeModule(obj.token)
        obj.module.set_identity(obj.token)
        obj.optimizer = SimpleNamespace(state_dict=lambda: {'stand_in': True}, zero_grad=lambda **k: None)
        obj.run_identity, obj.run_identity_digest = payload['run_identity'], payload['run_identity_digest']
        obj.cursor, obj.model_revision = payload['cursor'], payload['model_revision']
        obj.counters = dict(payload['counters'])
        obj._pending, obj.failed = None, False
        return obj


def install_checker_stand_in():
    """Installed from inside `_main_training`, which runs AFTER the checkpoint check's phase A.

    The worker requires `cas_meta2.typed_teaching.checker` NOT to be in `sys.modules` when phase A runs
    (`cncm/typed_pointer_worker.py:724`, `:728`), so this stand-in cannot be installed at import time.
    """
    from cas_meta2.typed_teaching import checker
    if getattr(checker, '_stand_in_installed', False):
        return
    targets = {}
    real_derive = checker.derive_target

    def derive(source, query):
        key = str(query['query_id']) + ':' + str(source['focus_world_id'])
        if key not in targets:
            targets[key] = real_derive(source, query)
        return targets[key]

    checker.derive_target = derive
    checker.check_answer = lambda source, query, answer: {'correct': int(h(enc(answer))[:2], 16) % 3 == 0}
    checker._stand_in_installed = True


def install_stand_ins():
    torch = FakeTorch()
    gpu_adapter._cuda = lambda: (torch, 'cuda:0')
    rpa_learning_worker.verify_worker_packages = lambda root: {'source_files': ['stand-in']}
    from cas_meta2.typed_teaching import encoder as encoder_module
    from cas_meta2.typed_teaching import pointer_learner as pointer_module
    from cas_meta2.typed_teaching import practice_learner as practice_module
    encoder_module.build_frozen_typed_encoder = (
        lambda torch_, tokenizer, *, seed, d_model, device: FakeEncoder(torch_, 'encoder-seed-%d' % seed))
    matched_worker._framework = lambda torch_, device, seed: SimpleNamespace(module=None, seed=seed)
    practice_module.PracticeCourseLearner = StandInPracticeLearner
    pointer_module.PointerCourseLearner = StandInPointerLearner
    pointer_module.role_tagger = lambda root: SimpleNamespace(indicators=lambda packet: [0] * CLAUSE_COUNT)
    pointer_module._registered_names = lambda module: {name: name for name in module.state_dict()}
    base._state = lambda torch_, learner: learner.state()
    worker.tensor_state_identity = stand_in_state_identity
    real_main_training = worker._main_training

    def main_training(ctx):
        install_checker_stand_in()
        return real_main_training(ctx)

    worker._main_training = main_training
    return torch


def fresh_container():
    """The per-JOB container boundary, at $0: discard the private checker from this interpreter.

    The worker's own custody rule is `"cas_meta2.typed_teaching.checker" in sys.modules`
    (`cncm/typed_pointer_worker.py:732`), and phase A refuses to run once that module is imported. On AWS each
    job is its own container, so the flag is False for every job; three jobs in ONE interpreter would leave it
    True for job 2 and job 3, and their phase A would be recorded FAILED for a reason that says nothing about
    the study -- seed 20260917 was COMPLETE and seed 20260918 FAILED with `POINTER_PHASE_A_CUSTODY` on the first
    run of this script. Dropping the module between jobs reproduces exactly what a fresh container starts with,
    and `install_checker_stand_in` re-installs its stand-in on the fresh module at the next job's first use.
    """
    sys.modules.pop('cas_meta2.typed_teaching.checker', None)


class CreateOnlyPublisher:
    """The live evidence publisher's rule, at $0: each new name under results/ is stored once and never
    replaced; names ending .partial/.tmp are skipped; a stored name whose bytes later differ is a conflict
    (on AWS: EVIDENCE_DIGEST_CONFLICT, which fails the final upload). Scans several times a second."""

    def __init__(self, results):
        self.results, self.store, self.conflicts, self.scans = Path(results), {}, [], 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def scan(self):
        self.scans += 1
        for path in sorted(self.results.rglob("*")):
            try:
                if not path.is_file() or path.name.endswith((".partial", ".tmp")):
                    continue
                digest = sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            key = path.relative_to(self.results).as_posix()
            if key not in self.store:
                self.store[key] = digest
            elif self.store[key] != digest and key not in self.conflicts:
                self.conflicts.append(key)

    def _loop(self):
        while not self._stop.is_set():
            self.scan()
            time.sleep(0.1)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set(); self._thread.join(); self.scan()


WRITE_VIOLATIONS, ACTIVE_RESULTS = [], []


def _write_audit(event, args):
    """Record every write-mode open of a file under an active results/ whose name is not *.partial."""
    if event != "open" or not ACTIVE_RESULTS:
        return
    path, mode, flags = (list(args) + [None, None, None])[:3]
    if not isinstance(path, (str, bytes)) and not hasattr(path, "__fspath__"):
        return
    text = os.fsdecode(os.fspath(path))
    writing = (isinstance(mode, str) and any(c in mode for c in "wxa+")) or (
        mode is None and isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
    if writing and text.startswith(ACTIVE_RESULTS[0]) and not text.endswith(".partial"):
        WRITE_VIOLATIONS.append(text)


def _integrity_verdict(failures):
    """The dry run's expectation, as a computation.

    Nothing outside I3 may fail; I3 must fail once (or more) for EVERY registered seed; and every I3 code must
    be one of the stand-in's own self-comparison codes. Anything else is a bug found for $0.
    """
    outside = sorted(code for code in failures if not code.startswith("I3:"))
    inside = sorted(code for code in failures if code.startswith("I3:"))
    seeds = sorted({code.split(":")[1] for code in inside})
    codes_ok = all(len(code.split(":", 2)) == 3 and code.split(":", 2)[2] in I3_STAND_IN_CODES
                   for code in inside)
    return (inside, outside, seeds, not outside and codes_ok
            and seeds == [str(seed) for seed in sorted(contract.MODEL_SEEDS)])


def main(scratch):
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=False)
    install_stand_ins()
    sys.addaudithook(_write_audit)
    source_sha = "d" * 40
    jobs, timings, publishing, phases = [], {}, {}, {}
    for seed in contract.MODEL_SEEDS:
        fresh_container()
        job = "cas-meta2-tpntr-20260919000000-dddddddd-m-%d" % seed
        receipt = scratch / ("receipt_%d" % seed)
        results = receipt / "collected/results"
        results.mkdir(parents=True)
        config = contract.make_config(ROOT, source_sha=source_sha, job=job, bucket=job + contract.BUCKET_SUFFIX,
                                      model_seed=seed)
        began = time.monotonic()
        ACTIVE_RESULTS[:] = [str(results.resolve())]
        before = len(WRITE_VIOLATIONS)
        with CreateOnlyPublisher(results) as publisher:
            result = worker.run(config, ROOT, results, results / "artifacts",
                                attestor=SimpleNamespace(snapshot=lambda: {"stand_in": True}))
        ACTIVE_RESULTS[:] = []
        timings[seed] = time.monotonic() - began
        staging = results.parent / "pointer_staging"
        publishing[seed] = {"scans": publisher.scans, "files": len(publisher.store),
                            "conflicts": publisher.conflicts,
                            "direct_writes_under_results": WRITE_VIOLATIONS[before:],
                            "staging_left": sorted(p.name for p in staging.iterdir()) if staging.exists() else [],
                            "partial_left": sorted(str(p.name) for p in results.rglob("*.partial"))}
        require_verdict(result is not None and result.get("status") == worker.DELIVERED_STATUS,
                        result.get("failure") if result else None)
        report = json.loads((results / "artifacts/worker_report.json").read_bytes())
        phases[seed] = {key: report.get(key) for key in REQUIRED_PHASE_STATUSES}
        phases[seed]["claim_bearing"] = report.get("claim_bearing")
        phases[seed]["schedule_plan_mode"] = report.get("schedule_plan_mode")
        (receipt / "result.json").write_text(json.dumps({"completed_deliverable": True, "cleanup": {"complete": True}}))
        jobs.append({"model_seed": seed, "receipt_dir": str(receipt), "job": job})
        print(json.dumps({"dry_run_seed_delivered": seed, "seconds": timings[seed]}), flush=True)
    study = scratch / "study.json"
    study.write_text(json.dumps({"jobs": jobs}))
    reading = evaluate_gates.evaluate(study)
    failures = reading["gates"]["integrity"]["failures"]
    inside, outside, seeds_with_i3, integrity_ok = _integrity_verdict(failures)
    clean = all(not row["conflicts"] and row["files"] > 0 and not row["direct_writes_under_results"]
                and not row["staging_left"] and not row["partial_left"] for row in publishing.values())
    phases_ok = all(row[key] == "COMPLETE" for row in phases.values() for key in REQUIRED_PHASE_STATUSES[:3]) \
        and all(row["claim_bearing"] is True and row["schedule_plan_mode"] == "REGISTERED"
                for row in phases.values())
    verdict = ("PREFLIGHT_PASS" if (integrity_ok and reading["label"] == "VOID" and clean and phases_ok)
               else "PREFLIGHT_FAIL")
    frozen = contract.load_material(ROOT)[0]
    summary = {"schema": "cncm.typed-pointer-preflight-dry-run/0.1", "verdict": verdict,
               "expected_i3_codes": list(I3_STAND_IN_CODES),
               "observed_integrity_failures_i3": inside, "observed_integrity_failures_outside_i3": outside,
               "seeds_with_an_i3_failure": seeds_with_i3, "label_on_stand_in": reading["label"],
               "worker_seconds_per_seed": timings, "report_only_phase_status": phases,
               "create_only_publisher_simulation": publishing,
               "main_updates_per_seed": contract.pointer_schedule(frozen)[1]["main_updates"],
               "main_counters": list(COUNTERS),
               "gate_population": {k: reading[k] for k in ("held_questions", "eligible_questions",
                                                           "shortcut_questions", "held_records",
                                                           "trained_records", "excluded_records")},
               "boundary": "Stand-in learner for both machines, torch, encoder, framework, attestor, identity "
                           "function and answer checker. Proves control flow, counts, artifacts, logs, the "
                           "checkpoint check's phase order, reloads, replays, ablations, the DG4 record, delivery "
                           "and the gate reader; proves nothing about numerics or AWS packaging."}
    print(json.dumps(summary, indent=1), flush=True)
    return summary


def require_verdict(condition, detail):
    if not condition:
        raise SystemExit('POINTER_PREFLIGHT_STOPPED:' + json.dumps(detail)[:2000])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: preflight_dry_run.py SCRATCH_DIR")
    outcome = main(sys.argv[1])
    raise SystemExit(0 if outcome["verdict"] == "PREFLIGHT_PASS" else 1)
