"""AWS-only decoder comparison using unchanged v3 model parameters.

Pure on import. Both modes use the same greedy loop; only the prefix mask
differs. No training, public parser, beam oracle or prediction repair exists.
"""
import os
import re
import time

from .codec import ACTION_TO_ID, ACTION_VOCABULARY, BOS_ID, EOS_ID, PolicyContractError, validate_public
from .grammar_v3 import GrammarState as OriginalGrammar, GrammarError
from .grammar_viability_v4 import GrammarState as ViableGrammar

MODES = {'v3': OriginalGrammar, 'viability_v4': ViableGrammar}


def require_context(job, device, grammar_mode, max_seconds):
    if (type(job) is not str or re.fullmatch(r'cas-meta2-[0-9]{14}-[0-9a-f]{8}', job) is None
            or os.environ.get('CAS_META2_AWS_JOB_ID') != job
            or os.environ.get('CAS_META2_RUN_DECODER_ABLATION') != '1'):
        raise RuntimeError('EXPLICIT_AWS_DECODER_ABLATION_REQUIRED')
    if type(device) is not str or re.fullmatch(r'cuda(?::[0-9]+)?', device) is None:
        raise RuntimeError('DECODER_CUDA_REQUIRED_NO_CPU_FALLBACK')
    if grammar_mode not in MODES:
        raise ValueError('EXPLICIT_REGISTERED_GRAMMAR_MODE_REQUIRED')
    if type(max_seconds) is not int or not 1 <= max_seconds <= 900:
        raise ValueError('DECODER_TIME_BOUND_INVALID')


def predict_public(model, tokenizer, publics, *, job, grammar_mode,
                   device='cuda', batch_size=32, max_seconds=300):
    require_context(job, device, grammar_mode, max_seconds)
    if type(publics) is not list or not 1 <= len(publics) <= 96 or type(batch_size) is not int or not 1 <= batch_size <= 32:
        raise ValueError('DECODER_BATCH_BOUND_INVALID')
    for public in publics:
        validate_public(public)
    # Import neural modules only after explicit job, device and request checks.
    import torch
    from .policy_v3 import encode_batch, require_cuda
    device = require_cuda(device)
    if 'T4' in torch.cuda.get_device_name(device).upper():
        raise RuntimeError('T4_NOT_AUTHORIZED')
    grammar = MODES[grammar_mode]
    deadline = time.monotonic() + max_seconds
    def check_time():
        if time.monotonic() >= deadline:
            raise RuntimeError('DECODER_ABLATION_DEADLINE')
    actions = []
    model.eval()
    with torch.no_grad():
        for offset in range(0, len(publics), batch_size):
            check_time()
            batch = encode_batch(publics[offset:offset + batch_size], tokenizer, device=device)
            memory = model.encode(batch)
            count = batch['ids'].shape[0]
            ids = torch.full((count, 1), BOS_ID, dtype=torch.long, device=device)
            states = [grammar.from_ids([BOS_ID], max_length=model.config.max_action_length) for _ in range(count)]
            rejected, attempted = [None] * count, [None] * count
            for _ in range(model.config.max_action_length - 1):
                check_time()
                masks = []
                for index, state in enumerate(states):
                    if rejected[index] is not None or state.complete:
                        allowed = (EOS_ID,)
                    else:
                        allowed = state.allowed_ids()
                        if not allowed:
                            rejected[index] = 'GENERATION_GRAMMAR_DEAD_END'
                            allowed = (EOS_ID,)
                    masks.append([token_id in allowed for token_id in range(len(ACTION_VOCABULARY))])
                if all(error is not None or state.complete for error, state in zip(rejected, states)):
                    break
                scores = model.decode(memory, batch, ids)[:, -1]
                if not bool(torch.isfinite(scores).all()):
                    raise PolicyContractError('V3_GENERATION_NONFINITE_MODEL_SCORES')
                mask = torch.tensor(masks, dtype=torch.bool, device=device)
                next_ids = scores.masked_fill(~mask, float('-inf')).argmax(-1)
                ids = torch.cat((ids, next_ids[:, None]), dim=1)
                for index, token_id in enumerate(next_ids.tolist()):
                    if rejected[index] is None and not states[index].complete:
                        try:
                            states[index] = states[index].advance_id(token_id)
                        except (PolicyContractError, GrammarError) as error:
                            rejected[index] = str(error)
                            attempted[index] = [ACTION_TO_ID[t] for t in states[index].prefix] + [token_id]
            for index, state in enumerate(states):
                try:
                    if rejected[index] is not None:
                        raise PolicyContractError(rejected[index])
                    if not state.complete:
                        raise PolicyContractError('GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION')
                    actions.append(state.to_action())
                except (PolicyContractError, GrammarError) as error:
                    row = attempted[index] if attempted[index] is not None else [ACTION_TO_ID[t] for t in state.prefix]
                    actions.append({'status':'REJECTED','reason':str(error),'token_ids':row})
            check_time()
    return actions
