"""Independent learner-boundary tests; pure tokenization, never model execution."""
from copy import deepcopy
from hashlib import sha256
import importlib
import importlib.abc
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research/CAS_META_2_COMPOSITION'
DENIED = {'numpy', 'torch', 'tensorflow', 'jax', 'transformers', 'cas_cjt',
          'boto3', 'botocore', 'openai', 'anthropic', 'requests', 'httpx'}


class DenyExecutionImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in DENIED:
            raise AssertionError('FORBIDDEN_EXECUTION_IMPORT:' + fullname)


@pytest.fixture(autouse=True)
def pure_only(monkeypatch):
    # Bounded guard and path change: other test modules retain their environment.
    guard = DenyExecutionImports()
    sys.meta_path.insert(0, guard)
    monkeypatch.syspath_prepend(str(RESEARCH))
    try:
        yield
    finally:
        sys.meta_path.remove(guard)


@pytest.fixture
def api():
    return importlib.import_module('cncm.rpa_learning_adapter')


def project(bundle, namespace='learning-adversarial-fixture', view='view_context'):
    from cncm import rpa_cube_adapter as cube
    from cncm.canonical import canonical_json
    raw = canonical_json(bundle).encode('utf-8')
    return cube.cube_atlas_from_bytes(raw, expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=cube.cube_node.bundle_digest(bundle),
        source_namespace=namespace, observation_id='fixture-001',
        observation_time='explicit test fixture metadata; not an observed time', record_version=1,view_id=view)


@pytest.fixture
def setup(api):
    from cncm import rpa_cube_adapter as cube
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching.ordered_encoder import profile_identity
    bundle = cube.cube_node.load_bundle()
    document = project(bundle)
    prepared = api.prepare_public_lesson(document, operation='LIST_PARTS',
        question={'idea':'Bicycle'}, assistance='unassisted')
    tokenizer = LosslessPublicTokenizer.fit_train([prepared['public']], max_length=1024)
    profile = profile_identity(tokenizer, d_model=64, seed=20260916,
        projection_sha256='a'*64)
    context = {'model_id':'supplied-fixture-model', 'checkpoint_sha256':'b'*64}
    kwargs = {'document':document,'tokenizer':tokenizer,'ordered_profile':profile,'model_context':context}
    lesson = api.bind_prepared_lesson(prepared, **kwargs)
    prediction_kwargs = {k:v for k,v in kwargs.items() if k != 'document'}
    return {'bundle':bundle,'document':document,'prepared':prepared,'lesson':lesson,
            'kwargs':kwargs,'prediction_kwargs':prediction_kwargs}


def packet(api, setup):
    return api.prediction_packet(setup['lesson'], **setup['prediction_kwargs'])


def test_inference_closed_packet_excludes_teacher_and_reconstruction(api, setup, monkeypatch):
    from cncm import rpa_cube_adapter as cube
    expected = packet(api, setup)
    def forbidden(*args, **kwargs):
        raise AssertionError('TEACHER_OR_SOLVER_REACHED_DURING_INFERENCE')
    for name in ('prepare_public_lesson','bind_prepared_lesson','check_source_target'):
        monkeypatch.setattr(api, name, forbidden)
    for module in (cube.cube_profile, importlib.import_module('cas_meta2.graph_teaching.cube_profile')):
        for name in ('derived_answer','compile_public_exercise','public_options'):
            monkeypatch.setattr(module, name, forbidden)
    actual = packet(api, setup)
    assert actual == expected
    assert set(actual) == {'record_id','public','encoded_options'}
    assert api.validate_prediction_packet(actual, **setup['prediction_kwargs']) == expected


@pytest.mark.parametrize('private_key', ['correct','encoded_correct_index','teacher_sidecar','target','op'])
def test_extra_prediction_fields_refused(api, setup, private_key):
    bad = packet(api, setup)
    bad[private_key] = 0
    with pytest.raises(ValueError):
        api.validate_prediction_packet(bad, **setup['prediction_kwargs'])


def test_returned_prediction_has_no_mutable_alias_into_lesson(api, setup):
    original = deepcopy(setup['lesson'])
    output = packet(api, setup)
    output['public']['problem'] += '\ncaller mutation'
    output['public']['observations'][0]['values'][0] = 99.0
    output['encoded_options'].clear()
    assert setup['lesson'] == original


def test_teacher_changes_cannot_change_prediction_or_cache_id(api, setup):
    expected = packet(api, setup)
    altered = deepcopy(setup['lesson'])
    altered['teacher_sidecar']['encoded_correct_index'] = 999
    altered['teacher_sidecar']['expected_answer'] = 'PRIVATE TARGET COUNTERFACTUAL'
    assert api.prediction_packet(altered, **setup['prediction_kwargs']) == expected
    with pytest.raises(ValueError):
        api.check_source_target(altered, **setup['kwargs'])


def test_mutated_prepared_target_not_admitted_for_training(api, setup):
    altered = deepcopy(setup['prepared'])
    altered['teacher_sidecar']['encoded_correct_index'] = True
    with pytest.raises(ValueError):
        api.bind_prepared_lesson(altered, **setup['kwargs'])


@pytest.mark.parametrize('mutation', ['problem','options','tag','slot','nonzero','duplicate','extra_public'])
def test_stale_id_or_invalid_public_packet_refused(api, setup, mutation):
    bad = packet(api, setup)
    if mutation == 'problem':
        bad['public']['problem'] += '\npublic bytes changed'
    elif mutation == 'options':
        bad['encoded_options'] = list(reversed(bad['encoded_options']))
    elif mutation == 'tag':
        bad['public']['observations'][0]['tag'] += 'changed'
    elif mutation == 'slot':
        bad['public']['observations'][0]['slot'] = False
    elif mutation == 'nonzero':
        bad['public']['observations'][0]['values'][0] = 1.0
    elif mutation == 'duplicate':
        bad['encoded_options'][1] = deepcopy(bad['encoded_options'][0])
        bad['public']['observations'][1]['tag'] = bad['public']['observations'][0]['tag']
    else:
        bad['public']['correct'] = 0
    with pytest.raises(ValueError):
        api.validate_prediction_packet(bad, **setup['prediction_kwargs'])


@pytest.mark.parametrize('field,value', [('model_id','other-model'),('checkpoint_sha256','c'*64)])
def test_model_context_changes_cache_identity_and_refuses_old_packet(api, setup, field, value):
    old = packet(api, setup)
    changed = deepcopy(setup['kwargs']['model_context']); changed[field] = value
    kwargs = {**setup['kwargs'],'model_context':changed}
    new = api.bind_prepared_lesson(setup['prepared'], **kwargs)
    assert new['learner_input']['record_id'] != old['record_id']
    with pytest.raises(ValueError):
        api.validate_prediction_packet(old, **{**setup['prediction_kwargs'],'model_context':changed})


@pytest.mark.parametrize('field,value', [('projection_sha256','c'*64),('permutation_seed',20260917),('d_model',32)])
def test_actual_ordered_profile_parameters_change_identity(api, setup, field, value):
    from cas_meta2.graph_teaching.ordered_encoder import profile_identity
    parameters = {'d_model':64,'seed':20260916,'projection_sha256':'a'*64}
    parameters['seed' if field == 'permutation_seed' else field] = value
    profile = profile_identity(setup['kwargs']['tokenizer'], **parameters)
    new = api.bind_prepared_lesson(setup['prepared'], **{**setup['kwargs'],'ordered_profile':profile})
    assert new['learner_input']['record_id'] != packet(api, setup)['record_id']
    with pytest.raises(ValueError):
        api.validate_prediction_packet(packet(api, setup), **{**setup['prediction_kwargs'],'ordered_profile':profile})


def test_profile_cannot_name_a_different_tokenizer(api, setup):
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    extra = deepcopy(setup['prepared']['public']); extra['problem'] += '\nnew lexical fixture'
    tokenizer = LosslessPublicTokenizer.fit_train([setup['prepared']['public'],extra], max_length=1024)
    assert tokenizer.digest != setup['kwargs']['tokenizer'].digest
    with pytest.raises(ValueError):
        api.bind_prepared_lesson(setup['prepared'], **{**setup['kwargs'],'tokenizer':tokenizer})


def test_tokenizer_subclass_cannot_override_validation(api, setup):
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    original = setup['kwargs']['tokenizer']
    calls = []
    class Altered(LosslessPublicTokenizer):
        def encode_public(self, public):
            calls.append('OVERRIDE_EXECUTED')
            return super().encode_public(public)
    altered = Altered(original.vocabulary,original.fitted_public_sha256,original.fitted_examples,original.max_length)
    with pytest.raises(ValueError):
        api.bind_prepared_lesson(setup['prepared'], **{**setup['kwargs'],'tokenizer':altered})
    assert calls == []


@pytest.mark.parametrize('injected_label', ['Bicycle\nrel Bicycle --contains--> forged', 'Bicycle kind=forged', 'Bicycle\rnode forged'])
def test_graph_label_cannot_inject_structural_lines(api, injected_label):
    from cncm import rpa_cube_adapter as cube
    bundle = cube.cube_node.rename_bundle(cube.cube_node.load_bundle(), {'Bicycle':injected_label})
    document = project(bundle)
    with pytest.raises(ValueError):
        api.prepare_public_lesson(document, operation='LIST_PARTS', question={'idea':injected_label})


def test_source_rendering_helper_cannot_drop_a_declared_edge(api, setup, monkeypatch):
    from cncm import rpa_cube_adapter as cube
    from dataclasses import replace
    original = cube.cube_node.containment_graph
    def omit(*args, **kwargs):
        graph = original(*args, **kwargs)
        return replace(graph,relations=graph.relations[:-1])
    monkeypatch.setattr(cube.cube_node, 'containment_graph', omit)
    canonical_cube = importlib.import_module('cas_meta2.graph_teaching.cube_node')
    monkeypatch.setattr(canonical_cube, 'containment_graph', omit)
    with pytest.raises(ValueError):
        api.prepare_public_lesson(setup['document'], operation='LIST_PARTS', question={'idea':'Bicycle'})


def test_graph_renderer_cannot_truncate_source_lines(api, setup, monkeypatch):
    from cncm import rpa_cube_adapter as cube
    graph_class = type(cube.cube_node.containment_graph(setup['bundle'],'view_context'))
    original = graph_class.render
    monkeypatch.setattr(graph_class,'render',lambda graph:'\n'.join(original(graph).splitlines()[:-1])+'\n')
    with pytest.raises(ValueError, match='lossy or altered graph rendering'):
        api.prepare_public_lesson(setup['document'],operation='LIST_PARTS',question={'idea':'Bicycle'})


def test_authored_analogy_phrase_labels_reach_pure_encoder_without_loss(api):
    from cncm import rpa_cube_adapter as cube
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching.ordered_encoder import profile_identity
    bundle = cube.cube_node.load_bundle()
    document = project(bundle,view='view_analogy')
    prepared = api.prepare_public_lesson(document,operation='LIST_PARTS',question={'idea':'Kit A'})
    assert 'node Kit A kind=idea\n' in prepared['public']['problem']
    tokenizer = LosslessPublicTokenizer.fit_train([prepared['public']],max_length=1024)
    profile = profile_identity(tokenizer,d_model=64,seed=20260916,projection_sha256='a'*64)
    context = {'model_id':'supplied-analogy-fixture','checkpoint_sha256':'b'*64}
    lesson = api.bind_prepared_lesson(prepared,document=document,tokenizer=tokenizer,
        ordered_profile=profile,model_context=context)
    assert api.prediction_packet(lesson,tokenizer=tokenizer,ordered_profile=profile,model_context=context)['public'] == prepared['public']
    assert lesson['binding']['tokenization']['structural_frame_count'] == len(bundle['cube_nodes'])+len(bundle['branches'])


@pytest.mark.parametrize('mutation', ['bool_index','stale_index','foreign_request','foreign_source'])
def test_teacher_helper_output_requires_receiver_binding(api, setup, monkeypatch, mutation):
    from cncm import rpa_cube_adapter as cube
    original = cube.compile_atlas_lesson
    def fault(*args,**kwargs):
        result = deepcopy(original(*args,**kwargs))
        teacher = result['teacher_sidecar']
        if mutation == 'bool_index': teacher['encoded_correct_index'] = True
        elif mutation == 'stale_index': teacher['encoded_correct_index'] = (teacher['encoded_correct_index']+1)%3
        elif mutation == 'foreign_request': teacher['question'] = {'idea':'Wheel'}
        else: teacher['source_bundle_digest'] = '0'*64
        return result
    monkeypatch.setattr(cube,'compile_atlas_lesson',fault)
    with pytest.raises(ValueError):
        api.prepare_public_lesson(setup['document'],operation='LIST_PARTS',question={'idea':'Bicycle'})


def test_target_admission_cannot_borrow_identical_graph_from_other_namespace(api, setup):
    foreign = project(setup['bundle'],namespace='other-source-custody-fixture')
    # Public inference does not authenticate source custody; target admission must bind it.
    assert packet(api,setup) == setup['lesson']['learner_input']
    with pytest.raises(ValueError, match='source-grounded teacher reconstruction'):
        api.check_source_target(setup['lesson'],**{**setup['kwargs'],'document':foreign})


@pytest.mark.parametrize('ceiling', [16,2048])
def test_actual_tokenizer_ceiling_cannot_change_frozen_worker_contract(api, setup, ceiling):
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching.ordered_encoder import profile_identity
    original = setup['kwargs']['tokenizer']
    tokenizer = LosslessPublicTokenizer(original.vocabulary,original.fitted_public_sha256,
        original.fitted_examples,ceiling)
    profile = profile_identity(tokenizer,d_model=64,seed=20260916,projection_sha256='a'*64)
    with pytest.raises(ValueError, match='token ceiling'):
        api.bind_prepared_lesson(setup['prepared'],**{**setup['kwargs'],'tokenizer':tokenizer,'ordered_profile':profile})


def test_unseen_text_over_actual_token_budget_refused_without_truncation(api, setup):
    from cncm import rpa_cube_adapter as cube
    labels = cube.cube_node.view_labels(setup['bundle'],'view_context')
    mapping = {label:'Unseen'+'q'*90+str(index) for index,label in enumerate(labels.values())}
    foreign_bundle = cube.cube_node.rename_bundle(setup['bundle'],mapping)
    foreign_document = project(foreign_bundle)
    prepared = api.prepare_public_lesson(foreign_document,operation='REACHED_VIA',
        question={'part':mapping['Wheel'],'idea':mapping['Bicycle']})
    with pytest.raises(ValueError, match='PUBLIC_INPUT_TOO_LONG:NO_SILENT_TRUNCATION'):
        api.bind_prepared_lesson(prepared,**{**setup['kwargs'],'document':foreign_document})


@pytest.mark.parametrize('field,value', [('worker_observed',True),('projection_bytes_verified',True),
    ('checkpoint_bytes_verified',True),('cached_vectors_verified',True),('numeric_encoder_calls',1),
    ('neural_calls',1),('optimizer_updates',1)])
def test_supplied_metadata_cannot_be_relabelled_as_executed_capability(api, setup, field, value):
    forged = deepcopy(setup['lesson']); forged['binding'][field] = value
    with pytest.raises(ValueError, match='public binding changed'):
        api.prediction_packet(forged,**setup['prediction_kwargs'])


@pytest.mark.parametrize('field,value', [('max_length',2048),('tokenizer_sha256','c'*64),
    ('frame_scaling','invented-normalization'),('native_flow','MEASURED'),('d_model',True),('permutation_seed',False)])
def test_resealed_incompatible_ordered_profile_refused(api, setup, field, value):
    from cncm.canonical import digest
    profile = deepcopy(setup['kwargs']['ordered_profile']); profile[field] = value
    profile['identity_sha256'] = digest({k:v for k,v in profile.items() if k!='identity_sha256'})
    with pytest.raises(ValueError):
        api.validate_prediction_packet(packet(api,setup),**{**setup['prediction_kwargs'],'ordered_profile':profile})


def fake_candidate(api, setup):
    """Metadata-only test double; never an instantiated neural learner."""
    from cncm import rpa_learning_cycle as cycle
    public = packet(api, setup)
    target = api.check_source_target(setup['lesson'], **setup['kwargs'])
    framework = SimpleNamespace(module=object())
    class FakeLearner:
        def __init__(self):
            self.tasks = [{**deepcopy(public),'encoded_correct_index':target['encoded_correct_index']}]
            self._index = {public['record_id']:0}
            self.framework = framework
            self.module = framework.module
            self.calls = []
        def predict(self, task):
            assert set(task) == {'record_id','public','encoded_options'}
            self.calls.append(deepcopy(task))
            return deepcopy(task['encoded_options'][0])
    learner = FakeLearner()
    predictor = cycle.PublicPredictor(learner, training_packets=[public], **setup['prediction_kwargs'])
    scope = {'allowed':['trainable'],'frozen':['frozen'],'contract_id':'fixture-contract','role':'fixture-role'}
    return {**setup['kwargs'],'lessons':[setup['lesson']],'framework':framework,
            'learner':learner,'predictor':predictor,'scope':scope}


def prepare_fake_training(monkeypatch, candidate, action):
    trainer = importlib.import_module('cas_meta2.graph_teaching.trainer')
    monkeypatch.setattr(trainer,'scope_parameters',lambda *args:deepcopy(candidate['scope']))
    monkeypatch.setattr(trainer,'parameter_snapshot',lambda *args:{'trainable':'same','frozen':'same'})
    monkeypatch.setattr(trainer,'run_training',action)


def test_predictor_refuses_mutated_training_public_cache_before_predict(api, setup):
    candidate = fake_candidate(api, setup)
    candidate['learner'].tasks[0]['public']['problem'] += '\nCACHE BYTES CHANGED'
    with pytest.raises(ValueError):
        candidate['predictor'].predict(packet(api, setup))
    assert candidate['learner'].calls == []


def test_predictor_refuses_prediction_input_mutation(api, setup):
    candidate = fake_candidate(api, setup)
    def mutate(task):
        task['public']['problem'] += '\nMUTATED BY CALLBACK'
        return task['encoded_options'][0]
    candidate['learner'].predict = mutate
    with pytest.raises(ValueError, match='MUTATED_INPUT'):
        candidate['predictor'].predict(packet(api, setup))


@pytest.mark.parametrize('invalid_result', [None, True, 0, {'answer':'invented'}])
def test_predictor_rejects_nonoption_result(api, setup, invalid_result):
    candidate = fake_candidate(api, setup)
    candidate['learner'].predict = lambda task:invalid_result
    with pytest.raises(ValueError, match='NOT_UNIQUE_OPTION'):
        candidate['predictor'].predict(packet(api, setup))


def test_training_registry_target_is_bound_to_source_before_updates(api, setup, monkeypatch):
    from cncm import rpa_learning_cycle as cycle
    candidate = fake_candidate(api, setup)
    original = candidate['learner'].tasks[0]['encoded_correct_index']
    candidate['learner'].tasks[0]['encoded_correct_index'] = (original+1)%3
    calls = []
    prepare_fake_training(monkeypatch,candidate,lambda *args,**kwargs:calls.append('TRAINING_ENTERED'))
    with pytest.raises(ValueError, match='TRAINING_REGISTRY_TARGET_MISMATCH'):
        cycle.run_bound_training(candidate)
    assert calls == []


def test_boolean_index_alias_not_accepted_as_source_checked_target(api, setup, monkeypatch):
    from cncm import rpa_cube_adapter as cube
    from cncm import rpa_learning_cycle as cycle
    selected = setup
    if setup['lesson']['teacher_sidecar']['encoded_correct_index'] not in (0,1):
        for case in cube.cube_node.answer_cases(setup['bundle'],'view_context')['cases']:
            prepared = api.prepare_public_lesson(setup['document'],operation=case['op'],question=case['question'])
            if prepared['teacher_sidecar']['encoded_correct_index'] in (0,1):
                lesson = api.bind_prepared_lesson(prepared, **setup['kwargs'])
                selected = {**setup,'prepared':prepared,'lesson':lesson}
                break
    candidate = fake_candidate(api, selected)
    index = candidate['learner'].tasks[0]['encoded_correct_index']
    assert type(index) is int and index in (0,1)
    candidate['learner'].tasks[0]['encoded_correct_index'] = bool(index)
    calls = []
    prepare_fake_training(monkeypatch,candidate,lambda *args,**kwargs:calls.append('TRAINING_ENTERED'))
    with pytest.raises(ValueError, match='TRAINING_REGISTRY_TARGET_MISMATCH'):
        cycle.run_bound_training(candidate)
    assert calls == []


def test_training_registry_target_mutation_during_updates_detected(api, setup, monkeypatch):
    from cncm import rpa_learning_cycle as cycle
    candidate = fake_candidate(api, setup)
    def change(*args,**kwargs):
        row = candidate['learner'].tasks[0]
        row['encoded_correct_index'] = (row['encoded_correct_index']+1)%3
        return {'fixture_only':True}
    prepare_fake_training(monkeypatch,candidate,change)
    with pytest.raises(ValueError, match='TRAINING_REGISTRY_TARGET_MISMATCH'):
        cycle.run_bound_training(candidate)


@pytest.mark.parametrize('attribute', ['framework','module'])
def test_training_mismatched_learner_model_refused_before_updates(api, setup, monkeypatch, attribute):
    from cncm import rpa_learning_cycle as cycle
    candidate = fake_candidate(api, setup)
    setattr(candidate['learner'],attribute,object())
    calls = []
    prepare_fake_training(monkeypatch,candidate,lambda *args,**kwargs:calls.append('TRAINING_ENTERED'))
    with pytest.raises(ValueError, match='LEARNER_MODEL_MISMATCH'):
        cycle.run_bound_training(candidate)
    assert calls == []


@pytest.mark.parametrize('attribute', ['framework','module'])
def test_training_model_binding_changes_during_updates_detected(api, setup, monkeypatch, attribute):
    from cncm import rpa_learning_cycle as cycle
    candidate = fake_candidate(api, setup)
    def change(*args,**kwargs):
        setattr(candidate['learner'],attribute,object())
        return {'fixture_only':True}
    prepare_fake_training(monkeypatch,candidate,change)
    with pytest.raises(ValueError, match='LEARNER_MODEL_MISMATCH'):
        cycle.run_bound_training(candidate)


def test_training_predictor_for_other_learner_refused(api, setup, monkeypatch):
    from cncm import rpa_learning_cycle as cycle
    candidate = fake_candidate(api, setup)
    foreign = fake_candidate(api, setup)
    candidate['predictor'] = foreign['predictor']
    calls = []
    prepare_fake_training(monkeypatch,candidate,lambda *args,**kwargs:calls.append('TRAINING_ENTERED'))
    with pytest.raises(ValueError):
        cycle.run_bound_training(candidate)
    assert calls == []


def test_private_target_loader_runs_only_after_prediction_file_is_retained(api, setup, tmp_path):
    from cncm import rpa_learning_cycle as cycle
    from cncm.canonical import digest
    candidate = fake_candidate(api, setup)
    public = packet(api, setup)
    destination = tmp_path/'prediction_seal.json'
    seal = cycle.seal_predictions(candidate['predictor'],[public],path=destination)
    checked = api.check_source_target(setup['lesson'], **setup['kwargs'])
    def targets():
        assert destination.is_file() and sha256(destination.read_bytes()).hexdigest() == seal['sha256']
        assert len(candidate['learner'].calls) == 1
        return {public['record_id']:{'public_input_digest':digest(public),
            'encoded_correct_index':checked['encoded_correct_index'],
            'expected_answer':deepcopy(public['encoded_options'][checked['encoded_correct_index']]),
            'operation':'LIST_PARTS'}}
    scored = cycle.score_sealed_predictions(seal,targets_loader=targets)
    assert scored['total'] == 1


@pytest.mark.parametrize('mutation', ['changed_bytes','bool_index','duplicate_choice','duplicate_id','nonhex_digest','bad_record_id'])
def test_invalid_retained_seal_refused_before_private_loader(api, setup, tmp_path, mutation):
    from cncm import rpa_learning_cycle as cycle
    from cncm.canonical import canonical_json
    import json
    candidate = fake_candidate(api, setup)
    destination = tmp_path/'prediction_seal.json'
    seal = cycle.seal_predictions(candidate['predictor'],[packet(api, setup)],path=destination)
    body = json.loads(destination.read_bytes())
    row = body['predictions'][0]
    if mutation == 'changed_bytes':
        destination.write_bytes(destination.read_bytes()+b' ')
    else:
        if mutation == 'bool_index': row['selected_index'] = False
        elif mutation == 'duplicate_choice': row['encoded_options'][1] = deepcopy(row['encoded_options'][0])
        elif mutation == 'nonhex_digest': row['public_input_digest'] = 'z'*64
        elif mutation == 'bad_record_id': row['record_id'] = ''
        else: body['predictions'].append(deepcopy(row))
        raw = (canonical_json(body)+'\n').encode()
        destination.write_bytes(raw)
        seal = {'path':str(destination),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    calls = []
    with pytest.raises(ValueError):
        cycle.score_sealed_predictions(seal,targets_loader=lambda:calls.append('PRIVATE_TARGETS_OPENED'))
    assert calls == []
