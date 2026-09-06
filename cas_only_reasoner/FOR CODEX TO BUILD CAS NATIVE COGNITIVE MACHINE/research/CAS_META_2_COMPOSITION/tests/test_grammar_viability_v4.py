"""Synthetic pure language checks, not new learned-model performance."""
import pytest
import test_grammar_v3 as reference
from cas_meta2 import grammar_v3 as old
from cas_meta2.grammar_viability_v4 import GrammarState, GrammarError
from cas_meta2.codec import ACTION_TO_ID, action_to_tokens
from cas_meta2.ir import Limits

pytestmark = pytest.mark.not_gpu


def test_closed_complete_graph_cannot_add_unreachable_procedure():
    prefix = action_to_tokens(reference.action())[:-1]
    assert 'PROC' in old.GrammarState(prefix).allowed_tokens()
    state = GrammarState(prefix)
    assert state.allowed_tokens() == ('[EOS]',)
    with pytest.raises(GrammarError): state.advance('PROC')
    with pytest.raises(GrammarError): GrammarState(prefix + ['PROC'])
    with pytest.raises(GrammarError): GrammarState.from_ids([ACTION_TO_ID[t] for t in prefix + ['PROC']])
    assert state.advance('[EOS]').to_action() == reference.action()


def test_impossible_call_marker_is_not_offered():
    prefix = ['[BOS]', 'BIND0', 'PROC', 'main', 'ALLOW', 'A', 'ENDALLOW']
    limits = Limits(max_procedures=1)
    assert 'CALL' in old.GrammarState(prefix, limits=limits).allowed_tokens()
    state = GrammarState(prefix, limits=limits)
    assert state.allowed_tokens() == ('RUN',)
    with pytest.raises(GrammarError): state.advance('CALL')


def test_unused_helper_can_still_be_declared_before_its_forward_caller():
    expected = reference.action({'main':reference.proc([reference.call('p15')]),
        'p0':reference.proc([reference.run()]),
        'p15':reference.proc([reference.call('p0')])})
    state = GrammarState()
    for token in action_to_tokens(expected): state = state.advance(token)
    assert state.to_action() == expected


@pytest.mark.parametrize('name', [
    'test_forward_and_backward_calls_are_both_preserved',
    'test_branch_reuse_and_first_result_return_are_preserved',
    'test_all_sixteen_procedures_and_maximum_default_depth_are_preserved',
    'test_existing_call_only_wrapper_language_is_not_silently_removed',
    'test_exhaustive_tiny_program_field_combinations',
    'test_all_scope_orders_are_preserved',
    'test_random_acyclic_graphs_with_backward_names_and_earlier_refs',
])
def test_existing_valid_language_corpus_still_roundtrips(name, monkeypatch):
    monkeypatch.setattr(reference, 'GrammarState', GrammarState)
    getattr(reference, name)()


def test_branch_states_remain_detached():
    state = GrammarState().advance('[BOS]')
    left, right = state.advance('BIND0'), state.advance('BIND1')
    assert left.prefix[-1] == 'BIND0' and right.prefix[-1] == 'BIND1'
    assert state.prefix == ('[BOS]',)
