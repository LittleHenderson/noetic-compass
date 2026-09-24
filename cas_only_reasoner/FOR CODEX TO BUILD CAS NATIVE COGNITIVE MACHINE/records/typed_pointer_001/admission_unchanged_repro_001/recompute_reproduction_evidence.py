"""Recompute the unchanged-arm reproduction evidence. AWS ONLY (the P1 slot, then the reading). Never on the laptop.

WRITTEN, NOT RUN (2026-09-24). No part of this module that imports torch has ever been executed. Its first run is the
P1 acceptance on AWS. The pure helpers at the top are covered by `test_unchanged_repro.py` without torch.

WHAT IT DOES. It loads TWO final checkpoints -- the Helm 2.0 seed-17 reference (`c6c49e98...`, committed at c8d5c430)
and a candidate -- and for each one, independently of every identity field the checkpoint stores about itself:
  1. hashes the file bytes (sha256) and refuses a file that is not the expected one;
  2. loads the payload with `torch.load(..., weights_only=True)` on the CPU and inventories EVERY entry of
     model_state (every parameter and persistent buffer), encoder_state (encoder and vocabulary), optimizer_state and
     rng_state: for each tensor its key path, dtype, shape, layout and the sha256 of its logical value bytes (plus
     stride / storage offset / device as envelope); for each tensor-free subtree one typed digest;
  3. re-derives the checkpoint's own four stored identities with the historical function and records whether they
     match the bytes (a corrupt checkpoint reads as invalid evidence, never as a mismatch);
  4. restores it through the PINNED HISTORICAL LOADER (`PointerCourseLearner.restore_checkpoint` of source 20208c92,
     from the unpacked, byte-verified historical package) and runs the COMPLETE pinned public panel (564 course records,
     `public_panel_manifest.json`) forward-only through `PointerCourseLearner.predict` (eval mode, no_grad, depth 8),
     predictions first, then the historical grader (`checker.check_answer`) on every answer. Only a historical
     `require` refusal (a ValueError with a POINTER_/TYPED_ code) is a REFUSED record; any other exception, a
     prediction for the wrong record, or a grader crash is an infrastructure fault that makes the evidence invalid
     (revision 3, review MAJOR 3: never a valid mismatch, never fallback B);
  5. writes ONE evidence file (create-only) that names every input with its sha256. The READER decides; this module
     reports its own level summary only so the reader can cross-check it.

MODES.
  --mode reading     the real reading after the new run: reference = Helm 2.0 final.pt, candidate = the new final.pt.
  --mode acceptance  the P1 reader acceptance, public inputs only (no new run needed): builds synthetic variants of the
                     reference checkpoint and checks that the reader gives the registered verdict for each one:
                     self identity, equal state with a different envelope, continuation-only difference, changed value,
                     changed encoder state, missing key, dtype change, altered output, changed buffer (VACUOUS: the
                     architecture has no buffers, and the case fails if one ever appears), state-equal/output-tampered,
                     and a corrupt reference -- `repro_common.ACCEPTANCE_CASES`, in that order. Writes one acceptance
                     receipt (READER_ACCEPTANCE_PASS only when every registered case is present, in order, and passed).

FAILS CLOSED. Before torch is imported: `GPU_REQUIRED:LINUX_WORKER_REQUIRED` off Linux (so the laptop can never get as
far as a torch import) and `GPU_REQUIRED:EXPLICIT_ENABLE_REQUIRED` unless CAS_META2_RUN_TEACHING_CYCLE=1. After:
`GPU_REQUIRED:CUDA_NOT_AVAILABLE_NO_CPU_FALLBACK` and `GPU_REQUIRED:EXACTLY_ONE_VISIBLE_GPU`. Determinism is set as the
historical worker set it (CUBLAS_WORKSPACE_CONFIG=:4096:8 before the import, deterministic algorithms on, TF32 off). An
environment that is not the pinned numerical environment writes invalid evidence and does no panel work.

WHERE IT RUNS (P1 layout, all paths absolute):
  * the historical package `package_20208c92/source.zip` (sha256 c42370c4...) unpacked at /opt/cas-graph6curr/package,
    the root both historical checkpoints record; this module verifies every one of the 270 members byte for byte and
    refuses any extra .py file there before importing anything from it;
  * this folder's three reader sources plus `policy_pins.json` (read at import; revision 3) and
    `public_panel_manifest.json`, in a separate folder (never inside the root);
  * the reference final.pt and its `final_checkpoint.json` record, taken from git at c8d5c430.

USAGE (on the AWS instance only):
    CAS_META2_RUN_TEACHING_CYCLE=1 python -B recompute_reproduction_evidence.py --mode acceptance \\
        --package-root /opt/cas-graph6curr/package --package-archive <source.zip> \\
        --reference-checkpoint <final.pt> --reference-record <final_checkpoint.json> \\
        --panel-manifest <public_panel_manifest.json> --work-dir <new empty dir> --out <acceptance_receipt.json>
    CAS_META2_RUN_TEACHING_CYCLE=1 python -B recompute_reproduction_evidence.py --mode reading \\
        --package-root /opt/cas-graph6curr/package --package-archive <source.zip> \\
        --reference-checkpoint <final.pt> --reference-record <final_checkpoint.json> \\
        --candidate-checkpoint <new final.pt> --candidate-sha256 <hex> --candidate-job <job> \\
        --panel-manifest <public_panel_manifest.json> --out <reproduction_evidence.json>

LABEL. CLAUDE_BUILT_CLAUDE_CHECKED (temporary Claude builder while Codex is away).
"""
import argparse
from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import repro_common as common  # noqa: E402  (torch-free)

stop_unless = common.make_stop('UNCHANGED_REPRO_RECOMPUTE_STOPPED:')
MODE_READING, MODE_ACCEPTANCE = common.EVIDENCE_MODES
ENABLE_ENV = 'CAS_META2_RUN_TEACHING_CYCLE'
LOADER = 'cas_meta2.typed_teaching.pointer_learner.PointerCourseLearner.restore_checkpoint (source 20208c92)'
GRADER = 'cas_meta2.typed_teaching.checker.check_answer (source 20208c92)'
VALUE_INLINE_LIMIT = 2048
ACCEPTANCE_JOB = common.job_name('19700101000000')   # an obviously synthetic run id for the acceptance variants
HEAD_OUTPUT_TENSORS = ('node_head.3.weight', 'node_head.3.bias', 'edge_head.3.weight', 'edge_head.3.bias',
                       'role_head.3.weight', 'role_head.3.bias', 'reach_option_head.3.weight',
                       'reach_option_head.3.bias', 'mode_option_head.3.weight', 'mode_option_head.3.bias',
                       'world_head.3.weight', 'world_head.3.bias')


class UnsupportedValue(ValueError):
    """A checkpoint value this inventory cannot encode exactly. It makes the evidence invalid, never a mismatch."""


# =====================================================================================================================
# PURE HELPERS (no torch; tested locally).
# =====================================================================================================================
def key_token(key):
    if type(key) not in (str, int):
        raise UnsupportedValue('KEY_TYPE:' + type(key).__name__)
    return type(key).__name__ + ':' + str(key)


def typed(value):
    """An exact, type-preserving JSON form: a tuple stays a tuple, a float is its hex form (NaN and -0.0 included)."""
    kind = type(value)
    if isinstance(value, Mapping):
        items = sorted(value.items(), key=lambda item: (type(item[0]).__name__, str(item[0])))
        return [kind.__name__, [[key_token(key), typed(item)] for key, item in items]]
    if kind in (list, tuple):
        return [kind.__name__, [typed(item) for item in value]]
    if kind is float:
        return ['float', value.hex()]
    if kind in (bool, int, str) or value is None:
        return [kind.__name__, value]
    raise UnsupportedValue('VALUE_TYPE:' + kind.__name__)


def typed_bytes(value):
    return json.dumps(typed(value), separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def contains_tensor(value, is_tensor):
    if is_tensor(value):
        return True
    if isinstance(value, Mapping):
        return any(contains_tensor(item, is_tensor) for item in value.values())
    if type(value) in (list, tuple):
        return any(contains_tensor(item, is_tensor) for item in value)
    return False


def value_row(path, value):
    raw = typed_bytes(value)
    row = {'path': list(path), 'kind': 'value', 'type': type(value).__name__, 'sha256': sha256(raw).hexdigest(),
           'typed_bytes': len(raw)}
    if len(raw) <= VALUE_INLINE_LIMIT:
        row['typed_value'] = json.loads(raw)        # disclosure only; the sha256 decides
    return row


def walk_rows(value, is_tensor, tensor_row, path=()):
    """Every tensor as its own row; every tensor-free subtree as ONE typed-digest row; containers of tensors as rows."""
    if is_tensor(value):
        return [tensor_row(list(path), value)]
    if not contains_tensor(value, is_tensor):
        return [value_row(path, value)]
    if isinstance(value, Mapping):
        keys = sorted(value, key=lambda key: (type(key).__name__, str(key)))
        rows = [{'path': list(path), 'kind': 'container', 'type': type(value).__name__,
                 'keys': [key_token(key) for key in keys]}]
        for key in keys:
            rows.extend(walk_rows(value[key], is_tensor, tensor_row, path + (key_token(key),)))
        return rows
    if type(value) in (list, tuple):
        rows = [{'path': list(path), 'kind': 'container', 'type': type(value).__name__, 'length': len(value)}]
        for index, item in enumerate(value):
            rows.extend(walk_rows(item, is_tensor, tensor_row, path + ('[%d]' % index,)))
        return rows
    raise UnsupportedValue('CONTAINER_TYPE:' + type(value).__name__)


def classify_prediction_error(error):
    """`(status, reason)` for an exception raised while predicting one panel record (review MAJOR 3). Pure.

    Only a plain ValueError carrying a historical `require` code (POINTER_... or TYPED_...) is model behaviour: status
    REFUSED, and it stays a panel record. Anything else -- a CUDA fault, out of memory, a TypeError, a ValueError with no
    historical code -- is an infrastructure fault: status ERROR, and the producer reports it, so the evidence is invalid
    (ADMISSION_INVALID_STOP), never a valid mismatch and never fallback B.
    """
    reason = str(error)[:300]
    if type(error) is ValueError and common.is_historical_refusal(reason):
        return 'REFUSED', reason
    return common.PANEL_INFRASTRUCTURE_FAULT, type(error).__name__ + ':' + reason


def grader_digest(checked):
    return common.value_digest({key: value for key, value in checked.items()
                                if key not in common.GRADER_EXCLUDED_KEYS})


def panel_row(record_id, *, status, reason, prediction, checked):
    """One panel record as the evidence stores it: full answer and decisions, the grader's flag and check digest."""
    row = {'record_id': record_id, 'status': status, 'reason': reason, 'answer': None, 'decisions': None,
           'grader_correct': None, 'grader_check_sha256': None, 'scores_sha256': None, 'packet_digest': None,
           'slot_plan_digest': None}
    if type(prediction) is dict:
        row.update(packet_digest=prediction.get('packet_digest'), slot_plan_digest=prediction.get('slot_plan_digest'))
        try:
            row['scores_sha256'] = common.value_digest(prediction.get('scores'))
        except (TypeError, ValueError):
            row['scores_sha256'] = None                # non-finite or non-JSON scores: reported, never deciding
        if status == 'ANSWERED':
            row.update(answer=prediction.get('answer'), decisions=prediction.get('decisions'))
    if status == 'ANSWERED' and type(checked) is dict:
        row.update(grader_correct=checked.get('correct'), grader_check_sha256=grader_digest(checked))
    return row


def producer_levels(reference, candidate, manifest):
    """This module's OWN level summary (a second, simpler implementation). The reader recomputes and must agree."""
    def views(side, parts):
        out = []
        for part in parts:
            for row in side.get(part) or []:
                if row.get('kind') == 'tensor':
                    view = [row.get(key) for key in common.TENSOR_DECIDING_KEYS]
                elif row.get('kind') == 'value':
                    view = ['value', row.get('type'), row.get('sha256')]
                else:
                    view = ['container', row.get('type'), row.get('keys'), row.get('length')]
                out.append(json.dumps([part, row.get('path'), view], sort_keys=True))
        return sorted(out)

    def selected(meta, identity_keys, meta_keys):
        identity = meta['run_identity']
        return common.canonical([{key: identity[key] for key in identity_keys}, {key: meta[key] for key in meta_keys}])

    levels = {level: None for level in common.LEVEL_LABELS}
    ref_file, cand_file = (reference.get('file') or {}).get('sha256'), (candidate.get('file') or {}).get('sha256')
    if ref_file and cand_file:
        levels['file'] = ref_file == cand_file
    complete = all(type(side.get(part)) is list for side in (reference, candidate) for part in common.STATE_PARTS)
    metas = (reference.get('metadata'), candidate.get('metadata'))
    if complete and all(type(meta) is dict for meta in metas):
        try:
            levels['learned_state'] = (views(reference, common.LEARNED_STATE_PARTS)
                                       == views(candidate, common.LEARNED_STATE_PARTS)
                                       and selected(metas[0], common.PREDICTIVE_RUN_IDENTITY, common.PREDICTIVE_METADATA)
                                       == selected(metas[1], common.PREDICTIVE_RUN_IDENTITY, common.PREDICTIVE_METADATA))
            levels['continuation'] = (views(reference, common.CONTINUATION_PARTS)
                                      == views(candidate, common.CONTINUATION_PARTS)
                                      and selected(metas[0], common.CONTINUATION_RUN_IDENTITY,
                                                   common.CONTINUATION_METADATA)
                                      == selected(metas[1], common.CONTINUATION_RUN_IDENTITY,
                                                  common.CONTINUATION_METADATA))
        except (KeyError, TypeError, ValueError):
            levels['learned_state'] = levels['continuation'] = None
    rows = candidate.get('panel')
    if type(rows) is list and len(rows) == len(manifest['rows']) and rows:
        equal = True
        for row, pinned in zip(rows, manifest['rows']):
            if row.get('status') != 'ANSWERED':
                equal = False
                continue
            try:
                view = {'record_id': row.get('record_id'), 'status': 'ANSWERED',
                        'answer_sha256': common.value_digest(row.get('answer')),
                        'decisions_sha256': common.value_digest(row.get('decisions')),
                        'grader_correct': row.get('grader_correct'),
                        'grader_check_sha256': row.get('grader_check_sha256')}
            except (TypeError, ValueError):
                equal = False
                continue
            equal = equal and view == {key: pinned[key] for key in common.PANEL_DECIDING_FIELDS}
        levels['output'] = equal
    return levels


def assemble(mode, *, environment, inputs, sides, producer_reasons, manifest, sources):
    """The evidence document. Pure over its arguments."""
    reference, candidate = sides.get('reference') or {}, sides.get('candidate') or {}
    return {'schema': common.EVIDENCE_SCHEMA, 'label': common.LABEL, 'mode': mode,
            'producer': {'module': Path(__file__).name, 'sources_sha256': dict(sources),
                         'reader_source_sha256': common.reader_source_digest(sources), 'loader': LOADER,
                         'grader': GRADER},
            'policy': common.evidence_policy_block(),
            'panel_manifest': {'path': common.GIT_PREFIX + common.PANEL_MANIFEST_REL,
                               'sha256': common.PANEL_MANIFEST_SHA256, 'record_count': len(manifest['record_ids'])},
            'environment': environment, 'inputs': inputs, 'sides': sides,
            'producer_invalid_reasons': list(producer_reasons),
            'producer_levels': producer_levels(reference, candidate, manifest)}


def encode(document):
    return (json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
            + '\n').encode('ascii')


def write_new(path, raw):
    target = Path(path)
    stop_unless(not target.exists() and target.parent.is_dir(), 'OUTPUT_EXISTS_OR_PARENT_MISSING:' + str(target))
    with target.open('xb') as stream:            # create-only
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    stop_unless(target.read_bytes() == raw, 'OUTPUT_READBACK:' + str(target))
    return {'path': str(target), 'sha256': common.digest(raw), 'bytes': len(raw)}


def input_pin(path, raw):
    return {'path': str(Path(path).resolve()), 'sha256': common.digest(raw), 'bytes': len(raw)}


# =====================================================================================================================
# AWS ONLY.
# =====================================================================================================================
def require_gpu():
    """GPU_REQUIRED, fail closed. The two platform checks run BEFORE torch is imported."""
    stop_unless(platform.system() == 'Linux', 'GPU_REQUIRED:LINUX_WORKER_REQUIRED:this module never runs on the laptop')
    stop_unless(os.environ.get(ENABLE_ENV) == '1',
                'GPU_REQUIRED:EXPLICIT_ENABLE_REQUIRED:set ' + ENABLE_ENV + '=1 on the AWS worker only')
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = common.NUMERICAL_ENVIRONMENT['cublas_workspace_config']
    sys.dont_write_bytecode = True
    import torch
    stop_unless(torch.cuda.is_available(), 'GPU_REQUIRED:CUDA_NOT_AVAILABLE_NO_CPU_FALLBACK')
    stop_unless(torch.cuda.device_count() == 1, 'GPU_REQUIRED:EXACTLY_ONE_VISIBLE_GPU')
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    return torch, torch.device('cuda:0')


def driver_version():
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                             capture_output=True, timeout=30, check=True).stdout.decode('ascii', 'replace').strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out or None


def environment(torch, device):
    import numpy
    return {'platform_system': platform.system(), 'platform_release': platform.release(),
            'python_version': platform.python_version(), 'device': str(device),
            'visible_gpu_count': torch.cuda.device_count(), 'torch_version': str(torch.__version__),
            'cuda_version': torch.version.cuda, 'cudnn_version': torch.backends.cudnn.version(),
            'gpu_name': torch.cuda.get_device_name(device), 'numpy_version': numpy.__version__,
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'matmul_allow_tf32': bool(torch.backends.cuda.matmul.allow_tf32),
            'cudnn_allow_tf32': bool(torch.backends.cudnn.allow_tf32),
            'cublas_workspace_config': os.environ.get('CUBLAS_WORKSPACE_CONFIG'),
            'driver_version': driver_version()}


def verify_package(package_root, package_archive):
    """The unpacked root must be exactly the pinned historical package: every member's bytes, and no extra .py file."""
    root = Path(package_root).resolve()
    stop_unless(root.as_posix() == common.HISTORICAL_PACKAGE_ROOT and root.is_dir(),
                'PACKAGE_ROOT_IS_NOT_THE_RECORDED_ROOT:' + root.as_posix())
    raw = Path(package_archive).read_bytes()
    stop_unless(common.digest(raw) == common.ARCHIVE_SHA256 and len(raw) == common.ARCHIVE_BYTES,
                'PACKAGE_ARCHIVE_IS_NOT_THE_PINNED_ARCHIVE')
    with ZipFile(io.BytesIO(raw)) as bundle:
        names = [info.filename for info in bundle.infolist()]
        stop_unless(len(names) == len(set(names)) == common.MEMBER_COUNT, 'PACKAGE_MEMBER_COUNT')
        for name in names:                       # one member at a time: bounded memory
            target = root / name
            stop_unless(target.is_file() and target.read_bytes() == bundle.read(name),
                        'PACKAGE_ROOT_FILE_IS_NOT_THE_ARCHIVE_MEMBER:' + name)
    members = set(names)
    extras = sorted(path.relative_to(root).as_posix() for path in root.rglob('*.py')
                    if path.relative_to(root).as_posix() not in members)
    stop_unless(not extras, 'PACKAGE_ROOT_HAS_EXTRA_PYTHON_FILES:' + '|'.join(extras)[:800])
    return root, {'archive': input_pin(package_archive, raw), 'root': root.as_posix(), 'members_verified': len(names)}


class Historical:
    """The historical source's own functions, imported ONLY from the verified package root."""

    def __init__(self, root):
        sys.path[:0] = [str(root), str(root / 'research/CAS_META_2_COMPOSITION')]
        from cas_meta2.typed_teaching import checker, encoder, pointer_contract, pointer_learner, source
        from cas_meta2.typed_teaching.learner import state_identity
        from cncm import typed_matched_worker
        for module in (checker, encoder, pointer_contract, pointer_learner, source, typed_matched_worker):
            stop_unless(Path(module.__file__).resolve().is_relative_to(root),
                        'HISTORICAL_MODULE_NOT_FROM_THE_PACKAGE_ROOT:' + module.__name__)
        self.checker, self.encoder, self.contract = checker, encoder, pointer_contract
        self.pointer_learner, self.source, self.matched = pointer_learner, source, typed_matched_worker
        self.state_identity = state_identity


class Context:
    def __init__(self, torch, device, historical, tokenizer, packets, manifest):
        self.torch, self.device, self.h = torch, device, historical
        self.tokenizer, self.packets, self.manifest = tokenizer, packets, manifest
        self.record_ids = manifest['record_ids']


def tensor_row(torch, path, value):
    """One tensor: the deciding fields, and the container layout as envelope. Sparse tensors are left unhashed."""
    layout = str(value.layout)
    strided = layout == 'torch.strided'
    row = {'path': list(path), 'kind': 'tensor', 'dtype': str(value.dtype), 'shape': [int(x) for x in value.shape],
           'layout': layout, 'numel': int(value.numel()),
           'envelope': {'stride': [int(x) for x in value.stride()] if strided else None,
                        'storage_offset': int(value.storage_offset()) if strided else None,
                        'device': str(value.device), 'is_contiguous': bool(value.is_contiguous()) if strided else None}}
    if not strided:
        row['sha256'] = None
        return row
    flat = value.detach().to('cpu').contiguous().reshape(-1)
    raw = flat.view(torch.uint8).numpy().tobytes()
    row['sha256'], row['value_bytes'] = sha256(raw).hexdigest(), len(raw)
    return row


def run_panel(ctx, learner):
    """Forward-only over the pinned panel in pinned order: ALL predictions first, then the historical grader.

    Returns `(rows, faults)`. A historical refusal stays a REFUSED record. Every infrastructure fault (any other
    exception, a prediction for the wrong record, a grader crash) is an ERROR row AND a named fault; `load_side` turns
    any fault into a producer invalid reason (revision 3, review MAJOR 3).
    """
    fault = common.PANEL_INFRASTRUCTURE_FAULT
    predictions = []
    for record_id in ctx.record_ids:
        try:
            predictions.append((record_id, 'ANSWERED', None,
                                learner.predict(ctx.packets[record_id], common.PREDICTION_DEPTH)))
        except Exception as error:                          # noqa: BLE001 - classified, never silently a record
            status, reason = classify_prediction_error(error)
            predictions.append((record_id, status, reason, None))
    rows, faults = [], []
    for record_id, status, reason, prediction in predictions:
        checked = None
        if status == 'ANSWERED' and (type(prediction) is not dict or prediction.get('record_id') != record_id):
            status, reason = fault, 'PREDICTION_RECORD_ID_MISMATCH'
        elif status == 'ANSWERED':
            packet = ctx.packets[record_id]
            try:
                checked = ctx.h.checker.check_answer(packet['source'], packet['record']['query'], prediction['answer'])
            except Exception as error:                      # noqa: BLE001 - a grader crash is a fault, not a record
                status, reason = fault, 'GRADER:' + type(error).__name__ + ':' + str(error)[:200]
        if status == fault:
            faults.append(record_id + ':' + reason[:120])
        rows.append(panel_row(record_id, status=status, reason=reason, prediction=prediction, checked=checked))
    return rows, faults


def load_side(ctx, *, path, expected_sha256, label):
    """`(side, producer_reasons)` for one checkpoint. Nothing about the checkpoint's own stored identities is trusted."""
    torch, h = ctx.torch, ctx.h
    raw = Path(path).read_bytes()
    side = {'file': input_pin(path, raw)}
    if side['file']['sha256'] != expected_sha256:
        return side, [label + '_FILE_SHA256_IS_NOT_THE_EXPECTED_ONE']
    try:
        payload = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    except Exception as error:                              # noqa: BLE001
        return side, [label + '_CHECKPOINT_NOT_LOADABLE:' + type(error).__name__]
    del raw
    if not isinstance(payload, Mapping) or sorted(payload) != list(common.PAYLOAD_KEYS):
        return side, [label + '_PAYLOAD_KEYS']
    reasons = []
    side['payload_keys'], side['payload_schema'] = sorted(payload), payload['schema']
    try:
        side['metadata'] = json.loads(json.dumps(payload['metadata'], allow_nan=False))
    except (TypeError, ValueError):
        reasons.append(label + '_METADATA_NOT_JSON')
    for part in common.STATE_PARTS:
        try:
            side[part] = walk_rows(payload[part], torch.is_tensor, lambda where, value: tensor_row(torch, where, value))
        except UnsupportedValue as error:
            reasons.append(label + '_UNSUPPORTED_VALUE:' + part + ':' + str(error))
    stored = payload['metadata'] if isinstance(payload['metadata'], Mapping) else {}
    side['producer_identities_consistent'] = {
        part: h.state_identity(torch, payload[part + '_state']) == stored.get(part + '_state_identity')
        for part in ('model', 'optimizer', 'encoder', 'rng')}
    del payload
    try:
        encoder = h.encoder.build_frozen_typed_encoder(torch, ctx.tokenizer, seed=h.contract.ENCODER_SEED, d_model=64,
                                                       device=ctx.device)
        learner = h.pointer_learner.PointerCourseLearner.restore_checkpoint(
            torch, h.matched._framework(torch, ctx.device, common.MODEL_SEED), encoder, path=Path(path),
            expected_sha256=expected_sha256,
            expected_run_identity_digest=(side.get('metadata') or {}).get('run_identity_digest'), device=ctx.device)
    except Exception as error:                              # noqa: BLE001 - the loader's refusal is evidence
        side['restore'] = {'status': 'REFUSED', 'reason': type(error).__name__ + ':' + str(error)[:300],
                           'loader': LOADER}
        side['panel'] = []
        return side, reasons
    side['restore'] = {'status': 'RESTORED', 'reason': None, 'loader': LOADER}
    side['state_dict_keys'] = sorted(learner.module.state_dict())
    side['buffers'] = sorted(name for name, _ in learner.module.named_buffers())
    before = h.state_identity(torch, dict(learner.module.state_dict()))
    side['panel'], faults = run_panel(ctx, learner)
    if faults:
        reasons.append(label + '_PANEL_INFRASTRUCTURE_FAULTS:%d:first=%s' % (len(faults), faults[0]))
    side['inference_mode'] = {'module_training': bool(learner.module.training), 'no_grad': True,
                              'prediction_depth': common.PREDICTION_DEPTH, 'entry': 'PointerCourseLearner.predict'}
    side['panel_left_learned_state_unchanged'] = h.state_identity(torch, dict(learner.module.state_dict())) == before
    del learner, encoder
    torch.cuda.empty_cache()
    return side, reasons


def setup(args):
    """GPU first, then the environment, the pinned manifest and record, the verified package and the material."""
    torch, device = require_gpu()
    started = time.monotonic()
    recorded = environment(torch, device)
    manifest_raw = Path(args.panel_manifest).read_bytes()
    manifest = common.load_panel_manifest(stop_unless, manifest_raw)
    record_raw = Path(args.reference_record).read_bytes()
    stop_unless(common.digest(record_raw) == manifest['inputs']['checkpoint_record']['sha256'],
                'REFERENCE_RECORD_IS_NOT_THE_PINNED_ONE')
    root, package = verify_package(args.package_root, args.package_archive)
    historical = Historical(root)
    frozen, tokenizer, _ = historical.contract.load_material(root)
    packets = dict(historical.contract.public_packets(frozen))
    del frozen
    stop_unless(list(packets) == manifest['record_ids'], 'PANEL_ORDER_IS_NOT_THE_COURSE_ORDER')
    course = root / 'records/typed_course_001/checks_002/public_course.json'
    inputs = {'package_root': root.as_posix(), 'package': package,
              'panel_manifest': input_pin(args.panel_manifest, manifest_raw),
              'reference_record': input_pin(args.reference_record, record_raw),
              'course': input_pin(course, course.read_bytes())}
    stop_unless(inputs['course']['sha256'] == manifest['inputs']['course']['sha256'], 'COURSE_IS_NOT_THE_PINNED_ONE')
    ctx = Context(torch, device, historical, tokenizer, packets, manifest)
    return ctx, recorded, inputs, json.loads(record_raw)['metadata'], started


def reading_mode(args):
    ctx, recorded, inputs, _, started = setup(args)
    stop_unless(common.is_hex(args.candidate_sha256, 64) and common.stamp_of(args.candidate_job) is not None,
                'CANDIDATE_SHA256_OR_JOB_FORM')
    reasons = ['ENVIRONMENT_NOT_PINNED:' + ','.join(common.environment_violations(recorded))
               ] if common.environment_violations(recorded) else []
    sides = {}
    if not reasons:
        sides['reference'], found = load_side(ctx, path=args.reference_checkpoint,
                                              expected_sha256=common.REFERENCE_FINAL_PT_SHA256, label='REFERENCE')
        reasons += found
        sides['candidate'], found = load_side(ctx, path=args.candidate_checkpoint,
                                              expected_sha256=args.candidate_sha256, label='CANDIDATE')
        reasons += found
    inputs.update(reference={**sides.get('reference', {}).get('file', {}),
                             'expected_sha256': common.REFERENCE_FINAL_PT_SHA256},
                  candidate={**sides.get('candidate', {}).get('file', {}), 'expected_sha256': args.candidate_sha256,
                             'job': args.candidate_job})
    evidence = assemble(MODE_READING, environment=recorded, inputs=inputs, sides=sides, producer_reasons=reasons,
                        manifest=ctx.manifest, sources=common.source_hashes())
    evidence['elapsed_seconds'] = time.monotonic() - started
    written = write_new(args.out, encode(evidence))
    print(json.dumps({'evidence': written, 'producer_levels': evidence['producer_levels'],
                      'producer_invalid_reasons': reasons,
                      'verdict': 'NOT_GIVEN_HERE_run_read_reproduction.py_on_the_committed_evidence'}), flush=True)
    return 0


# ---------------------------------------------------------------------------------------------------------------------
# P1 reader acceptance: synthetic variants of the PUBLIC reference checkpoint, each with its registered verdict.
# ---------------------------------------------------------------------------------------------------------------------
def acceptance_specs(torch):
    """`[(case, mutate(payload), expected verdict, expected levels)]`. Every variant also gets a new envelope."""
    def nudge(tensor):
        flat = tensor.reshape(-1)
        flat[0] = torch.nextafter(flat[0], torch.tensor(float('inf'), dtype=tensor.dtype))

    def flip_heads(payload):
        for name in HEAD_OUTPUT_TENSORS:
            payload['model_state'][name].mul_(-1)

    def retype(payload):
        payload['model_state']['round_rate'] = payload['model_state']['round_rate'].to(torch.float64)

    return [
        ('equal_state_different_envelope', lambda p: None, common.REPRODUCED,
         {'file': False, 'learned_state': True, 'output': True, 'continuation': True}),
        ('continuation_only_different', lambda p: nudge(p['optimizer_state']['state'][0]['exp_avg']),
         common.REPRODUCED, {'learned_state': True, 'output': True, 'continuation': False}),
        ('changed_value', lambda p: nudge(p['model_state']['round_rate']), common.DOES_NOT_REPRODUCE,
         {'learned_state': False}),
        ('changed_encoder_state', lambda p: nudge(p['encoder_state']['readout']), common.DOES_NOT_REPRODUCE,
         {'learned_state': False}),
        ('missing_key', lambda p: p['model_state'].pop('round_rate'), common.INVALID_STOP, {'learned_state': False}),
        ('dtype_change', retype, common.INVALID_STOP, {'learned_state': False}),
        ('altered_output', flip_heads, common.DOES_NOT_REPRODUCE, {'learned_state': False, 'output': False}),
    ]


def build_variant(ctx, payload, work, name, mutate):
    torch, h = ctx.torch, ctx.h
    variant = deepcopy(payload)
    meta = variant['metadata']
    meta['run_identity']['context']['run_id'] = ACCEPTANCE_JOB
    meta['init_args']['run_context']['run_id'] = ACCEPTANCE_JOB
    meta['elapsed_seconds'] = float(meta['elapsed_seconds']) + 1.25
    meta['run_identity_digest'] = h.source.digest(meta['run_identity'])
    mutate(variant)
    for part in ('model', 'optimizer', 'encoder', 'rng'):        # self-consistent, so only the loader can refuse it
        meta[part + '_state_identity'] = h.state_identity(torch, variant[part + '_state'])
    meta['learnable_names'] = sorted(variant['model_state'])
    path = work / (name + '.pt')
    with path.open('xb') as stream:
        torch.save(variant, stream)
    return path, common.digest(path.read_bytes())


def judge(case, evidence, ctx, *, job, candidate_sha256, record_metadata, expected_verdict, expected_levels):
    import read_reproduction as reader                          # torch-free
    evaluated = reader.evaluate_evidence(json.loads(encode(evidence)), ctx.manifest, expected_candidate_job=job,
                                         expected_candidate_sha256=candidate_sha256,
                                         admitted_sources=common.source_hashes(),
                                         reference_record_metadata=record_metadata, required_mode=MODE_ACCEPTANCE)
    levels = evaluated['levels']
    verdict = reader.decide(not evaluated['invalid_reasons'], levels['file'], levels['learned_state'],
                            levels['output'], levels['continuation'])
    passed = verdict == expected_verdict and all(levels.get(key) is value for key, value in expected_levels.items())
    return {'case': case, 'expected_verdict': expected_verdict, 'expected_levels': expected_levels,
            'observed_verdict': verdict, 'observed_levels': common.level_labels(levels),
            'invalid_reasons': evaluated['invalid_reasons'][:20],
            'panel_record_differences': evaluated['differences'].get('panel_record_count'),
            'evidence_sha256': common.digest(encode(evidence)), 'pass': passed}


def acceptance_mode(args):
    ctx, recorded, inputs, record_metadata, started = setup(args)
    torch = ctx.torch
    work = Path(args.work_dir)
    stop_unless(not work.exists(), 'WORK_DIR_EXISTS:' + str(work))
    work.mkdir(parents=True)
    violations = common.environment_violations(recorded)
    sources = common.source_hashes()
    cases = []
    if violations:
        cases.append({'case': 'environment', 'pass': False, 'invalid_reasons': ['ENVIRONMENT_NOT_PINNED:'
                                                                                + ','.join(violations)]})
    else:
        reference_raw = Path(args.reference_checkpoint).read_bytes()
        stop_unless(common.digest(reference_raw) == common.REFERENCE_FINAL_PT_SHA256, 'REFERENCE_IS_NOT_THE_PINNED_ONE')
        inputs['reference_checkpoint'] = input_pin(args.reference_checkpoint, reference_raw)
        reference, found = load_side(ctx, path=args.reference_checkpoint,
                                     expected_sha256=common.REFERENCE_FINAL_PT_SHA256, label='REFERENCE')
        base = {**inputs, 'reference': {**reference['file'], 'expected_sha256': common.REFERENCE_FINAL_PT_SHA256}}

        def evidence_for(reference_side, candidate_side, reasons, candidate_sha, job):
            return assemble(MODE_ACCEPTANCE, environment=recorded, sides={'reference': reference_side,
                                                                          'candidate': candidate_side},
                            inputs={**base, 'reference': {**(reference_side.get('file') or {}),
                                                          'expected_sha256': common.REFERENCE_FINAL_PT_SHA256},
                                    'candidate': {**(candidate_side.get('file') or {}),
                                                  'expected_sha256': candidate_sha, 'job': job}},
                            producer_reasons=reasons, manifest=ctx.manifest, sources=sources)

        def record(case, evidence, **expected):
            write_new(work / (case + '.evidence.json'), encode(evidence))
            cases.append(judge(case, evidence, ctx, record_metadata=record_metadata, **expected))

        record('self_identity', evidence_for(reference, deepcopy(reference), found, common.REFERENCE_FINAL_PT_SHA256,
                                             common.HELM2_JOB),
               job=common.HELM2_JOB, candidate_sha256=common.REFERENCE_FINAL_PT_SHA256,
               expected_verdict=common.REPRODUCED,
               expected_levels={'file': True, 'learned_state': True, 'output': True, 'continuation': True})
        payload = torch.load(io.BytesIO(reference_raw), map_location='cpu', weights_only=True)
        envelope_evidence = None
        for case, mutate, verdict, levels in acceptance_specs(torch):
            path, sha = build_variant(ctx, payload, work, case, mutate)
            candidate, more = load_side(ctx, path=path, expected_sha256=sha, label='CANDIDATE')
            evidence = evidence_for(reference, candidate, found + more, sha, ACCEPTANCE_JOB)
            record(case, evidence, job=ACCEPTANCE_JOB, candidate_sha256=sha, expected_verdict=verdict,
                   expected_levels=levels)
            if case == 'equal_state_different_envelope':
                envelope_evidence = evidence
        del payload
        # changed-buffer (policy acceptance list): VACUOUS for this architecture. pointer_learner.py at 20208c92
        # registers no buffer, so every model_state entry is a learnable parameter. Buffers would be ordinary
        # model_state rows (state_dict includes persistent buffers) and are compared the same way; the pure tests carry
        # a SYNTHETIC buffer case. This case passes ONLY while the restored reference really has no buffers; if one
        # ever appears, the acceptance FAILS until a real changed-buffer variant is built (revision 3, MINOR 6).
        buffers = reference.get('buffers')
        cases.append({'case': 'changed_buffer', 'status': common.VACUOUS, 'reference_buffers': buffers,
                      'pass': buffers == [],
                      'why': 'no registered buffers in the historical architecture; nothing to change'})
        if envelope_evidence is not None:           # state equal, one answer tampered: output never overridden
            tampered = json.loads(encode(envelope_evidence))
            row = tampered['sides']['candidate']['panel'][0]
            row['answer'] = {**row['answer'], 'tampered_by_acceptance': True}
            tampered['producer_levels'] = producer_levels(tampered['sides']['reference'],
                                                          tampered['sides']['candidate'], ctx.manifest)
            record('state_equal_output_tampered', tampered, job=ACCEPTANCE_JOB,
                   candidate_sha256=tampered['inputs']['candidate']['sha256'],
                   expected_verdict=common.DOES_NOT_REPRODUCE, expected_levels={'learned_state': True, 'output': False})
        corrupt = bytearray(reference_raw)
        corrupt[len(corrupt) // 2] ^= 0x01
        corrupt_path = work / 'corrupt_reference.pt'
        with corrupt_path.open('xb') as stream:
            stream.write(bytes(corrupt))
        del corrupt, reference_raw
        broken, more = load_side(ctx, path=corrupt_path, expected_sha256=common.REFERENCE_FINAL_PT_SHA256,
                                 label='REFERENCE')
        record('corrupt_reference', evidence_for(broken, deepcopy(reference), more, common.REFERENCE_FINAL_PT_SHA256,
                                                 common.HELM2_JOB),
               job=common.HELM2_JOB, candidate_sha256=common.REFERENCE_FINAL_PT_SHA256,
               expected_verdict=common.INVALID_STOP, expected_levels={})
    passed = ([case.get('case') for case in cases] == list(common.ACCEPTANCE_CASES)
              and all(case['pass'] is True for case in cases))
    receipt = {'schema': common.ACCEPTANCE_SCHEMA, 'label': common.LABEL,
               'status': common.ACCEPTANCE_PASS if passed else common.ACCEPTANCE_FAIL, 'cases': cases,
               'registered_cases': list(common.ACCEPTANCE_CASES),
               'environment': recorded, 'environment_violations': violations, 'inputs': inputs,
               'producer': {'sources_sha256': sources, 'reader_source_sha256': common.reader_source_digest(sources)},
               'policy': common.policy_pointers(), 'policy_pins_sha256': common.PINS_SHA256,
               'panel_manifest_sha256': common.PANEL_MANIFEST_SHA256,
               'numerical_environment_sha256': common.environment_digest(),
               'elapsed_seconds': time.monotonic() - started,
               'what_this_does_not_show': ('Acceptance uses synthetic variants of ONE public checkpoint. It shows the '
                                           'reader and this module give the registered verdicts; it says nothing '
                                           'about whether the new run reproduces.')}
    written = write_new(args.out, encode(receipt))
    print(json.dumps({'receipt': written, 'status': receipt['status'],
                      'cases': {case['case']: case['pass'] for case in cases}}), flush=True)
    return 0 if passed else 3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--mode', required=True, choices=('reading', 'acceptance'))
    parser.add_argument('--package-root', required=True)
    parser.add_argument('--package-archive', required=True)
    parser.add_argument('--reference-checkpoint', required=True)
    parser.add_argument('--reference-record', required=True)
    parser.add_argument('--panel-manifest', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--candidate-checkpoint')
    parser.add_argument('--candidate-sha256')
    parser.add_argument('--candidate-job')
    parser.add_argument('--work-dir')
    args = parser.parse_args(argv)
    if args.mode == 'reading':
        stop_unless(args.candidate_checkpoint and args.candidate_sha256 and args.candidate_job,
                    'READING_NEEDS_CANDIDATE_CHECKPOINT_SHA256_AND_JOB')
        return reading_mode(args)
    stop_unless(args.work_dir, 'ACCEPTANCE_NEEDS_WORK_DIR')
    return acceptance_mode(args)


if __name__ == '__main__':
    raise SystemExit(main())
