"""Pure grammar coverage. Synthetic fixtures are not native or learning evidence."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import inspect
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import zipfile

import pytest

from cas_meta2.codec import ACTION_TO_ID, ACTION_VOCABULARY, action_to_ids, action_to_tokens
from cas_meta2.grammar_v3 import (
    GrammarError, GrammarState, MAX_REPRESENTABLE_TOKENS, allowed_token_ids, token_mask,
)
from cas_meta2.ir import Limits, validate_program

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]


def run(cjt='A', source='arg', output='v0'):
    return {'kind': 'RUN', 'cjt_id': cjt, 'input': source, 'output': output}


def call(child, source='arg', output='v1'):
    return {'kind': 'CALL', 'procedure': child, 'input': source, 'output': output}


def proc(steps, returned=None, scope=('A', 'B', 'C', 'R')):
    return {'input': 'arg', 'allowed_cjts': list(scope), 'steps': steps,
            'return': steps[-1]['output'] if returned is None else returned}


def action(procedures=None, binding=0):
    return {'binding': binding, 'program': {'schema': 'cas-meta2-program/0.1',
            'entry': 'main', 'procedures': procedures or {'main': proc([run()])}}}


def roundtrip(expected, **kwargs):
    state = GrammarState(**kwargs)
    seq = action_to_tokens(expected, max_length=state.max_length)
    for token in seq:
        assert token in state.allowed_tokens(), (state.role, token, state.completion_error())
        assert state.mask()[ACTION_TO_ID[token]]
        state = state.advance_id(ACTION_TO_ID[token])
    assert state.complete and not state.dead_end
    assert state.completion_error() is None
    assert state.to_action() == expected
    assert state.allowed_ids() == ()
    assert not any(state.mask())
    assert GrammarState.from_ids(action_to_ids(expected, max_length=state.max_length), **kwargs).to_action() == expected
    return state


def prefix_for(expected, position):
    return GrammarState(tuple(action_to_tokens(expected)[:position]))


@pytest.mark.parametrize('binding', [0, 1, 2])
def test_minimal_roundtrip(binding):
    roundtrip(action(binding=binding))


def test_forward_and_backward_calls_are_both_preserved():
    # Canonical order main,p0,p15. Actual call order main -> p15 -> p0.
    expected = action({'main': proc([run('A'), call('p15', 'v0')], scope=('A', 'B', 'C')),
                       'p15': proc([run('B'), call('p0', 'v0')], scope=('B', 'C')),
                       'p0': proc([run('C')], scope=('C',))})
    roundtrip(expected)
    tokens = action_to_tokens(expected)
    i = len(tokens) - 1 - tokens[::-1].index('CALL')
    assert 'p0' in GrammarState(tuple(tokens[:i + 1])).allowed_tokens()


def test_branch_reuse_and_first_result_return_are_preserved():
    expected = action({'main': proc([run('A', output='v31'), call('p7', 'v31', 'v2'),
                                    call('p7', 'v31', 'v19')], returned='v2'),
                       'p7': proc([run('B', output='v8')])})
    roundtrip(expected)


def test_all_sixteen_procedures_and_maximum_default_depth_are_preserved():
    names = ['main'] + [f'p{i}' for i in range(15, 0, -1)]
    procedures = {}
    for i, name in enumerate(names):
        steps = [run()]
        if i + 1 < len(names):
            steps.append(call(names[i + 1], 'v0'))
        procedures[name] = proc(steps)
    expected = action(procedures)
    assert validate_program(expected['program'])['max_call_depth'] == 16
    roundtrip(expected)


def test_existing_call_only_wrapper_language_is_not_silently_removed():
    # The old IR permits nonempty CALL-only procedures even though the newer
    # learning curriculum requires a real RUN in each frame.
    roundtrip(action({'main': proc([call('p0', 'arg', 'v31')]),
                      'p0': proc([run('A')])}))


def test_exhaustive_tiny_program_field_combinations():
    # All tiny RUN targets, two arbitrary output names, both return choices,
    # and all bindings. No task answer is given to the grammar.
    for cjt, output, take_input, binding in itertools.product(
            ('A', 'B', 'C', 'R'), ('v0', 'v31'), (False, True), (0, 1, 2)):
        roundtrip(action({'main': proc([run(cjt, output=output)],
                                       returned='arg' if take_input else output,
                                       scope=(cjt,))}, binding))


def test_all_scope_orders_are_preserved():
    for order in itertools.permutations(('A', 'B', 'C', 'R')):
        roundtrip(action({'main': proc([run()], scope=order)}))


def test_random_acyclic_graphs_with_backward_names_and_earlier_refs():
    rng = random.Random(818223)  # Synthetic grammar seed, not a curriculum seed.
    for _ in range(120):
        names = ['main'] + rng.sample([f'p{i}' for i in range(16)], rng.randrange(1, 6))
        procedures = {}
        for index, name in enumerate(names):
            variables = iter(rng.sample([f'v{i}' for i in range(32)], 12))
            available = ['arg']
            steps = []
            for _ in range(rng.randrange(1, 4)):
                output = next(variables)
                steps.append(run(rng.choice(('A', 'B', 'C', 'R')), rng.choice(available), output))
                available.append(output)
            # A spanning chain makes all names reachable. Extra calls point
            # forward in graph order, which is independent of lexical order.
            children = names[index + 1:index + 2]
            if index + 2 < len(names) and rng.randrange(2):
                children += [rng.choice(names[index + 2:])]
            for child in children:
                output = next(variables)
                steps.append(call(child, rng.choice(available), output))
                available.append(output)
            procedures[name] = proc(steps, rng.choice(available))
        expected = action(procedures, rng.randrange(3))
        validate_program(expected['program'])
        roundtrip(expected)


def test_semantically_wrong_but_structurally_legal_choices_remain_allowed():
    expected = action({'main': proc([run('A', output='v0'), run('A', output='v1'),
                                    call('p0', 'v0', 'v2')]),
                       'p0': proc([run('B')])})
    wrong = deepcopy(expected)
    wrong['program']['procedures']['main']['steps'][2]['input'] = 'v1'
    wrong['program']['procedures']['main']['return'] = 'v0'
    assert wrong != expected
    roundtrip(expected)
    roundtrip(wrong)


@pytest.mark.parametrize('value', [True, 1, None, {}, ['[BOS]', 4]])
def test_invalid_prefix_types_rejected(value):
    with pytest.raises(GrammarError):
        GrammarState(value)


@pytest.mark.parametrize('value', [True, 1, 0, -1, MAX_REPRESENTABLE_TOKENS + 1, 3.5])
def test_invalid_length_bounds_rejected(value):
    with pytest.raises(GrammarError, match='GRAMMAR_LENGTH_BOUND_INVALID'):
        GrammarState(max_length=value)


@pytest.mark.parametrize('ids', [[True], [-1], [67], ['1'], {}])
def test_invalid_token_ids_rejected(ids):
    with pytest.raises(GrammarError, match='GRAMMAR_TOKEN_IDS_INVALID'):
        GrammarState.from_ids(ids)


def test_helpers_take_ids_and_match_state():
    ids = [ACTION_TO_ID['[BOS]']]
    assert allowed_token_ids(ids) == GrammarState.from_ids(ids).allowed_ids()
    assert token_mask(ids) == GrammarState.from_ids(ids).mask()
    assert len(token_mask(ids)) == len(ACTION_VOCABULARY) == 67


def test_frozen_public_state_and_detached_branches():
    parent = GrammarState(('[BOS]',))
    left, right = parent.advance('BIND0'), parent.advance('BIND1')
    assert left.prefix[-1] != right.prefix[-1]
    assert parent.prefix == ('[BOS]',)
    with pytest.raises(FrozenInstanceError):
        parent.prefix = ()


def test_empty_scope_empty_procedure_and_out_of_scope_run_are_masked():
    state = GrammarState(('[BOS]', 'BIND0', 'PROC', 'main', 'ALLOW'))
    assert 'ENDALLOW' not in state.allowed_tokens()
    state = state.advance('A').advance('ENDALLOW')
    assert 'RETURN' not in state.allowed_tokens()
    assert state.advance('RUN').allowed_tokens() == ('A',)


def test_duplicate_scope_and_nonfresh_or_unbound_values_are_masked():
    state = GrammarState(('[BOS]', 'BIND0', 'PROC', 'main', 'ALLOW', 'A'))
    assert 'A' not in state.allowed_tokens()
    state = state.advance('ENDALLOW').advance('RUN').advance('A')
    assert state.allowed_tokens() == ('arg',)
    state = state.advance('arg').advance('v31').advance('RUN').advance('A')
    assert set(state.allowed_tokens()) == {'arg', 'v31'}
    assert 'v31' not in state.advance('arg').allowed_tokens()


def test_missing_callee_and_unreachable_declaration_block_eos():
    missing = action({'main': proc([run(), call('p7', 'v0')]), 'p7': proc([run('B')])})
    seq = action_to_tokens(missing)
    second = seq.index('PROC', seq.index('PROC') + 1)
    state = GrammarState(tuple(seq[:second]))
    assert '[EOS]' not in state.allowed_tokens()
    assert state.completion_error() == 'STEP_CALLEE_MISSING'
    unused = action({'main': proc([run()]), 'p0': proc([run('B')])})
    state = GrammarState(tuple(action_to_tokens(unused)[:-1]))
    assert state.completion_error() == 'UNREACHABLE_PROCEDURE'
    assert '[EOS]' not in state.allowed_tokens()
    with pytest.raises(GrammarError):
        state.advance('[EOS]')


def test_pending_callee_cannot_be_skipped_by_canonical_declaration_order():
    # Find the boundary directly rather than depending on fixed scope length.
    seq = action_to_tokens(action({'main': proc([run(), call('p1', 'v0')]), 'p1': proc([run('B')])}))
    boundary = seq.index('PROC', seq.index('PROC') + 1)
    state = GrammarState(tuple(seq[:boundary + 1]))
    assert 'p0' in state.allowed_tokens() and 'p1' in state.allowed_tokens()
    assert 'p15' not in state.allowed_tokens() and 'main' not in state.allowed_tokens()


def test_direct_and_indirect_cycles_are_masked_without_banning_backward_calls():
    seq = action_to_tokens(action({'main': proc([run(), call('p15', 'v0')]),
                                   'p0': proc([run('B'), call('p15', 'arg')]),
                                   'p15': proc([run('B')])}))
    # End of p15's RUN: adding CALL p0 would close p0 -> p15 -> p0.
    index = len(seq) - 1 - seq[::-1].index('RETURN')
    state = GrammarState(tuple(seq[:index])).advance('CALL')
    assert 'p0' not in state.allowed_tokens()
    assert 'main' not in state.allowed_tokens()
    assert 'p15' not in state.allowed_tokens()


def test_forward_child_scope_intersects_all_existing_callers():
    expected = action({'main': proc([run(), call('p0', 'v0'), call('p15', 'v0', 'v2')], scope=('A', 'B')),
                       'p0': proc([run('B'), call('p7', 'arg')], scope=('A', 'B')),
                       'p15': proc([run('B'), call('p7', 'arg')], scope=('B',)),
                       'p7': proc([run('B')], scope=('B',))})
    roundtrip(expected)
    seq = action_to_tokens(expected)
    where = next(i for i in range(len(seq) - 2) if seq[i:i + 3] == ['PROC', 'p7', 'ALLOW'])
    assert GrammarState(tuple(seq[:where + 3])).allowed_tokens() == ('B',)


def test_backward_child_scope_escalation_masked():
    expected = action({'main': proc([run(), call('p15', 'v0')]),
                       'p0': proc([run('C')], scope=('C',)),
                       'p15': proc([run('B')], scope=('B',))})
    seq = action_to_tokens(expected)
    last_return = len(seq) - 1 - seq[::-1].index('RETURN')
    state = GrammarState(tuple(seq[:last_return])).advance('CALL')
    assert 'p0' not in state.allowed_tokens()


def test_exact_length_bound_and_no_silent_truncation():
    expected = action()
    size = len(action_to_tokens(expected))
    roundtrip(expected, max_length=size)
    with pytest.raises(GrammarError):
        GrammarState(tuple(action_to_tokens(expected)), max_length=size - 1)
    state = GrammarState(('[BOS]',), max_length=2)
    assert state.dead_end and state.prefix == ('[BOS]',)
    with pytest.raises(GrammarError):
        state.to_action()


def test_instruction_and_per_procedure_step_bounds():
    seq = action_to_tokens(action())
    state = GrammarState(tuple(seq[:seq.index('RETURN')]), limits=Limits(max_instructions=1))
    assert state.allowed_tokens() == ('RETURN',)
    steps = [run('A', output=f'v{i}') for i in range(32)]
    seq = action_to_tokens(action({'main': proc(steps)}))
    state = GrammarState(tuple(seq[:seq.index('RETURN')]))
    assert state.allowed_tokens() == ('RETURN',)


@pytest.mark.parametrize('limits,reason', [
    (Limits(max_expanded_runs=2), 'EXPANDED_RUN_LIMIT'),
    (Limits(max_expanded_instructions=3), 'EXPANDED_INSTRUCTION_LIMIT'),
    (Limits(max_source_bytes=10), 'SOURCE_SIZE_LIMIT'),
])
def test_final_published_ir_budgets_are_enforced(limits, reason):
    expected = action({'main': proc([run(), call('p0', 'v0'), call('p0', 'v0', 'v2')]),
                       'p0': proc([run('B')])})
    state = GrammarState(tuple(action_to_tokens(expected)[:-1]), limits=limits)
    assert state.completion_error() == reason
    assert '[EOS]' not in state.allowed_tokens()


def test_depth_budget_enforced_at_eos():
    expected = action({'main': proc([run(), call('p15', 'v0')]),
                       'p15': proc([run('B'), call('p0', 'v0')]), 'p0': proc([run('C')])})
    state = GrammarState(tuple(action_to_tokens(expected)[:-1]), limits=Limits(max_call_depth=2))
    assert state.completion_error() == 'CALL_DEPTH_LIMIT'
    assert '[EOS]' not in state.allowed_tokens()


def test_procedure_budget_does_not_allow_unfulfillable_new_call():
    seq = action_to_tokens(action())
    state = GrammarState(tuple(seq[:seq.index('RETURN')]), limits=Limits(max_procedures=1)).advance('CALL')
    assert state.dead_end


def test_terminal_action_is_detached_and_no_extra_tokens_are_accepted():
    state = roundtrip(action())
    returned = state.to_action()
    returned['program']['procedures']['main']['return'] = 'arg'
    assert state.to_action() == action()
    with pytest.raises(GrammarError):
        state.advance('[PAD]')


def test_no_problem_parser_or_neural_imports_or_hidden_task_arguments():
    source = (ROOT / 'cas_meta2/grammar_v3.py').read_text()
    assert 'parse_problem' not in source and 'import torch' not in source and 'from .native' not in source
    assert set(inspect.signature(GrammarState).parameters) == {'prefix', 'max_length', 'limits'}
    script = '''import sys
class Block:
 def find_spec(self, fullname, path=None, target=None):
  if fullname.split('.')[0] in {'torch','tensorflow','jax','cupy','boto3','cas_cjt'}:
   raise RuntimeError('NEURAL_IMPORT_FORBIDDEN')
sys.meta_path.insert(0, Block())
sys.path.insert(0, ROOT_VALUE)
from cas_meta2.grammar_v3 import GrammarState
assert GrammarState().allowed_tokens() == ('[BOS]',)
'''.replace('ROOT_VALUE', repr(str(ROOT)))
    subprocess.run([sys.executable, '-B', '-c', script], check=True)


@pytest.mark.parametrize('directory,counts', [
    ('aws_full_002', (256, 48, 72)),
    ('aws_learning_v2_001', (768, 48, 72)),
])
def test_all_previously_registered_exposed_targets_roundtrip(directory, counts):
    # Saved, completed, already-exposed records only. No constructor or new
    # seed is invoked. Missing historical artifacts are reported as skipped.
    path = ROOT / 'records' / directory / 'cloud_artifacts.zip'
    if not path.is_file():
        pytest.skip('Completed historical packet not present in this checkout')
    with zipfile.ZipFile(path) as archive:
        for filename, count in zip(('train.json', 'validation.json', 'test_private.json'), counts, strict=True):
            raw = archive.read('cloud_job/campaign/dataset/' + filename)
            tasks = json.loads(raw)
            assert len(tasks) == count
            for task in tasks:
                roundtrip(task['target'])
