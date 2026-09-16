"""Pure checkpoint contracts and explicit mocks; no tensor/model execution."""
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT/"research/CAS_META_2_COMPOSITION"
if str(PILOT) not in sys.path:
    sys.path.insert(0,str(PILOT))

from cncm import rpa_learning_smoke as smoke
from cncm import rpa_learning_adapter as adapter
from cncm import rpa_cube_adapter as cube
from cncm import rpa_learning_worker as worker
from cncm.canonical import canonical_json
from cncm.model import ContractError
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','tensorflow','jax','boto3','botocore',
                                    'requests','httpx','openai','anthropic','cas_cjt','casformer'}:
            raise AssertionError('PROHIBITED_EXECUTION_IMPORT:'+fullname)


@pytest.fixture(autouse=True)
def deny_execution():
    guard=Deny();sys.meta_path.insert(0,guard)
    try:yield
    finally:sys.meta_path.remove(guard)


@pytest.fixture(scope='module')
def sample():
    bundle=cube.cube_node.load_bundle()
    raw=canonical_json(bundle).encode()
    receipt=cube.cube_source_receipt(raw,expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=cube.cube_node.bundle_digest(bundle),source_namespace='smoke_contract_fixture',
        observation_id='pure_mock',observation_time='explicit test fixture',record_version=1)
    document=cube.cube_atlas_from_bundle(bundle,expected_bundle_digest=receipt.canonical_bundle_digest,
        source_receipt=receipt,view_id='view_context')
    case=cube.cube_node.answer_cases(bundle,'view_context')['cases'][0]
    requests=[{'operation':case['op'],'question':case['question'],'assistance':'unassisted'}]
    prepared=adapter.prepare_public_lesson(document,**requests[0])
    tokenizer=LosslessPublicTokenizer.fit_train([prepared['public']],max_length=1024)
    metadata={'schema_version':smoke.SCHEMA,'kind':'INITIAL','seed':7,
        'model_context':{'model_id':'candidate-cas-decompose-ordered-v1','checkpoint_sha256':'a'*64},
        'tokenizer':tokenizer.to_dict(),'ordered_profile':ordered_encoder.profile_identity(
            tokenizer,d_model=64,seed=7,projection_sha256='b'*64),
        'scope':{'allowed':['left.weight','merge.weight','right.weight'],'frozen':[],
                 'contract_id':'cas.cjt.operation.^6.decompose/0.2','role':'operation:^6'},
        'parameter_names':['left.weight','right.weight','merge.weight'],'training_requests':requests,
        'source_binding':{key:value for key,value in prepared['source_binding'].items() if key!='legacy_input_id'},
        'prepared_ids':[prepared['prepared_id']],'legacy_input_ids':[prepared['source_binding']['legacy_input_id']],
        'optimizer_class':'torch.optim.adamw.AdamW','learning_rate':0.003,
        'model_identity':'c'*64,'optimizer_identity':'d'*64,'projection_identity':'e'*64}
    return document,requests,metadata


def test_valid_contract_is_a_copy_and_not_numeric_evidence(sample):
    source=sample[2];result=smoke.validate_checkpoint_contract(source)
    assert result == source and result is not source
    result['model_context']['model_id']='changed'
    assert source['model_context']['model_id']=='candidate-cas-decompose-ordered-v1'


@pytest.mark.parametrize('field,value',[
    ('schema_version','old'),('kind','UNVERIFIED'),('seed',True),('seed',7.0),('seed',-1),
    ('seed',2**31),('optimizer_class','torch.optim.sgd.SGD'),('learning_rate',3),
    ('model_identity','wrong'),('optimizer_identity','F'*64),('projection_identity',None),
    ('prepared_ids',[]),('parameter_names',['left.weight','left.weight']),('source_binding',{}),
])
def test_metadata_refuses_bad_fields(sample,field,value):
    metadata=deepcopy(sample[2]);metadata[field]=value
    with pytest.raises((ContractError,ValueError,TypeError)):
        smoke.validate_checkpoint_contract(metadata)


def test_metadata_closed_and_expected_identity(sample):
    metadata=deepcopy(sample[2]);metadata['private_answer']='not allowed'
    with pytest.raises(ContractError,match='FIELDS'):smoke.validate_checkpoint_contract(metadata)
    metadata=deepcopy(sample[2]);metadata['kind']='FINAL'
    with pytest.raises(ContractError,match='EXPECTED_METADATA'):
        smoke.validate_checkpoint_contract(metadata,expected=sample[2])


@pytest.mark.parametrize('mutator',[
    lambda m:m['ordered_profile'].__setitem__('d_model',32),
    lambda m:m['ordered_profile'].__setitem__('permutation_seed',8),
    lambda m:m['ordered_profile'].__setitem__('legacy_checkpoint_compatible',0),
    lambda m:m['model_context'].__setitem__('checkpoint_sha256','stale'),
    lambda m:m['scope'].__setitem__('frozen',['outside']),
    lambda m:m['training_requests'][0].__setitem__('correct','private'),
    lambda m:m['training_requests'][0].__setitem__('operation','Why'),
])
def test_profile_scope_request_contracts_are_closed(sample,mutator):
    metadata=deepcopy(sample[2]);mutator(metadata)
    with pytest.raises((ContractError,ValueError)):
        smoke.validate_checkpoint_contract(metadata)


def pin(path):
    raw=path.read_bytes()
    return {'path':str(path.resolve()),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def test_checkpoint_bytes_have_external_custody(tmp_path):
    path=tmp_path/'synthetic.bin';path.write_bytes(b'not a tensor checkpoint')
    receipt=pin(path)
    assert smoke.read_checkpoint_bytes(receipt)==b'not a tensor checkpoint'
    path.write_bytes(b'NOT A TENSOR CHECKPOINT')
    with pytest.raises(ContractError):smoke.read_checkpoint_bytes(receipt)


@pytest.mark.parametrize('field,value',[
    ('path','relative.bin'),('bytes',True),('bytes',1.0),('bytes',0),
    ('bytes',smoke.MAX_CHECKPOINT_BYTES+1),('sha256','Z'*64),
])
def test_checkpoint_receipt_refuses_aliases(tmp_path,field,value):
    path=tmp_path/'bytes.bin';path.write_bytes(b'x');receipt=pin(path);receipt[field]=value
    with pytest.raises(ContractError):smoke.read_checkpoint_bytes(receipt)


def test_checkpoint_receipt_extra_fields_refused(tmp_path):
    path=tmp_path/'bytes.bin';path.write_bytes(b'x');receipt=pin(path);receipt['trusted']=True
    with pytest.raises(ContractError,match='FIELDS'):smoke.read_checkpoint_bytes(receipt)


class MockTensor:
    """A byte carrier only; this is not a tensor implementation."""
    def __init__(self,raw=b'\x00\x00\x00\x00',dtype='torch.float32',shape=(1,),finite=True):
        self.raw,self.dtype,self.shape,self.finite=raw,dtype,shape,finite
        self.layout='mock-strided'
    def numel(self):
        count=1
        for item in self.shape:count*=item
        return count
    def detach(self):return self
    def contiguous(self):return self
    def reshape(self,*shape):return self
    def view(self,dtype):return self
    def cpu(self):return self
    def numpy(self):return self
    def tobytes(self):return self.raw


class MockTorch:
    strided='mock-strided';uint8='mock-uint8'
    @staticmethod
    def is_tensor(value):return type(value) is MockTensor
    @staticmethod
    def isfinite(value):
        return SimpleNamespace(all=lambda:SimpleNamespace(item=lambda:value.finite))


def test_tensor_identity_checks_dtype_shape_and_signed_zero_bytes():
    positive=MockTensor(struct.pack('f',0.0));negative=MockTensor(struct.pack('f',-0.0))
    assert smoke.state_identity(MockTorch,positive)!=smoke.state_identity(MockTorch,negative)
    for altered in (MockTensor(positive.raw,dtype='torch.int32'),MockTensor(positive.raw,shape=(1,1)),negative):
        with pytest.raises(ContractError,match='RELOAD_MISMATCH'):
            smoke.require_exact_state(MockTorch,positive,altered)
    assert smoke.require_exact_state(MockTorch,positive,deepcopy(positive))


def test_state_identity_preserves_scalar_and_container_types():
    values=[{'x':1},{'x':True},{'x':1.0},{'x':[1]},{'x':(1,)}]
    assert len({smoke.state_identity(MockTorch,item) for item in values})==len(values)
    assert smoke.state_identity(MockTorch,{'a':1,'b':2})==smoke.state_identity(MockTorch,{'b':2,'a':1})


@pytest.mark.parametrize('value',[float('nan'),float('inf'),object(),{True:1},MockTensor(finite=False),
                                MockTensor(shape=(smoke.MAX_TENSOR_ELEMENTS+1,))])
def test_state_identity_refuses_unbounded_or_unsupported_values(value):
    with pytest.raises(ContractError):smoke.state_identity(MockTorch,value)


def test_state_identity_bounds_cycles_depth_and_node_count():
    cycle=[];cycle.append(cycle)
    with pytest.raises(ContractError,match='TREE_BOUND'):smoke.state_identity(MockTorch,cycle)
    with pytest.raises(ContractError,match='TREE_BOUND'):
        smoke.state_identity(MockTorch,[0]*(smoke.MAX_TREE_NODES+1))


def test_cpu_worker_refused_before_runtime_imports():
    runtime=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:True))
    with pytest.raises(ContractError,match='CUDA_REQUIRED'):
        smoke._guard(runtime,'cpu')


def test_cuda_unavailable_refused_before_runtime_imports():
    runtime=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False))
    with pytest.raises(ContractError,match='CUDA_REQUIRED'):
        smoke._guard(runtime,'cuda:0')


def test_reload_rejects_metadata_before_deserialization(sample,monkeypatch):
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    calls=[];runtime=SimpleNamespace(load=lambda *a,**k:calls.append('load'))
    bad=deepcopy(sample[2]);bad['kind']='UNKNOWN'
    with pytest.raises(ContractError):
        smoke.reload_worker_candidate(runtime,'cuda',document=sample[0],training_requests=sample[1],checkpoint={},metadata=bad)
    assert calls==[]


def test_reload_rejects_request_substitution_before_deserialization(sample,monkeypatch):
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    requests=deepcopy(sample[1]);requests[0]['assistance']='guided'
    calls=[];runtime=SimpleNamespace(load=lambda *a,**k:calls.append('load'))
    with pytest.raises(ContractError,match='TRAINING_REQUESTS'):
        smoke.reload_worker_candidate(runtime,'cuda',document=sample[0],training_requests=requests,checkpoint={},metadata=sample[2])
    assert calls==[]


def test_reload_does_not_deserialize_wrong_checkpoint_pin(sample,tmp_path,monkeypatch):
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    path=tmp_path/'fake.bin';path.write_bytes(b'fake checkpoint');receipt=pin(path);receipt['sha256']='a'*64
    calls=[];runtime=SimpleNamespace(load=lambda *a,**k:calls.append('load'))
    with pytest.raises(ContractError,match='DIGEST_MISMATCH'):
        smoke.reload_worker_candidate(runtime,'cuda',document=sample[0],training_requests=sample[1],checkpoint=receipt,metadata=sample[2])
    assert calls==[]


def test_reload_uses_checked_bytes_weights_only_cpu_then_refuses_wrong_payload(sample,tmp_path,monkeypatch):
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    path=tmp_path/'fake.bin';path.write_bytes(b'explicit mock bytes');calls=[]
    def load(stream,**kwargs):
        calls.append((stream.read(),kwargs));return {'unexpected':True}
    with pytest.raises(ContractError,match='PAYLOAD_FIELDS'):
        smoke.reload_worker_candidate(SimpleNamespace(load=load),'cuda',document=sample[0],training_requests=sample[1],
                                      checkpoint=pin(path),metadata=sample[2])
    assert calls==[(b'explicit mock bytes',{'map_location':'cpu','weights_only':True})]


def test_flat_output_contract_and_no_source_tensor_imports():
    assert len(smoke.OUTPUT_FILES)==len(set(smoke.OUTPUT_FILES))==10
    assert all('/' not in name and '\\' not in name for name in smoke.OUTPUT_FILES)
    assert not {'torch','numpy','cas_cjt','casformer'} & set(sys.modules)


def test_smoke_failure_is_preserved_without_overwrite(sample,tmp_path,monkeypatch):
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    def fail(*args,**kwargs):raise RuntimeError('intentional pure-control construction failure')
    monkeypatch.setattr(smoke.cycle,'create_worker_candidate',fail)
    output=tmp_path/'smoke'
    with pytest.raises(RuntimeError,match='pure-control'):
        smoke.run_worker_smoke(None,'cuda',document=sample[0],training_requests=sample[1],
                               prediction_requests=sample[1],seed=7,output=output)
    raw=(output/'failure.json').read_bytes();body=json.loads(raw)
    assert body['status']=='MECHANICAL_SMOKE_OR_RELOAD_FAILED'
    assert body['learning_improvement_established'] is False
    with pytest.raises(FileExistsError):
        smoke.run_worker_smoke(None,'cuda',document=sample[0],training_requests=sample[1],
                               prediction_requests=sample[1],seed=7,output=output)
    assert (output/'failure.json').read_bytes()==raw


@pytest.fixture(scope='module')
def exact_material():
    document,training,prediction=worker.smoke_material(ROOT)
    rows=[adapter.prepare_public_lesson(document,**request) for request in training]
    return document,training,prediction,rows


def test_exact_three_operation_smoke_material_prepares_distinct_request_identities(exact_material):
    document,training,prediction,expected=exact_material
    rows=smoke._prepared(document,training)
    assert rows==expected and len(rows)==3 and len(prediction)==6
    assert [r['request']['operation'] for r in rows]==['LIST_PARTS','FIND_SHARED_PART','REACHED_VIA']
    assert len({r['source_binding']['legacy_input_id'] for r in rows})==3
    assert len({r['prepared_id'] for r in rows})==3
    assert len({canonical_json(smoke._source_context(r['source_binding'],per_request=True)) for r in rows})==1


@pytest.mark.parametrize('field,value',[
    ('source_file_sha256','a'*64),('source_bundle_digest','b'*64),('source_receipt_digest','c'*64),
    ('source_namespace','foreign'),('source_context_id','other-scene'),('base_current_state_id','other-current'),
    ('rendering_schema','foreign-render'),('source_authorship_authenticated',True),('world_truth_established',True),
    ('source_authorship_authenticated',0),('world_truth_established',0),
])
def test_mixed_real_source_context_or_authority_still_refused(exact_material,monkeypatch,field,value):
    document,training,_,expected=exact_material
    rows=deepcopy(expected);rows[1]['source_binding'][field]=value
    cursor=iter(rows);monkeypatch.setattr(adapter,'prepare_public_lesson',lambda *a,**k:next(cursor))
    with pytest.raises(ContractError,match='SMOKE_SOURCE_'):
        smoke._prepared(document,training)


def test_prepared_binding_refuses_unknown_field_and_stale_per_request_id(exact_material,monkeypatch):
    document,training,_,expected=exact_material
    for key,value,error in [('extra','unsupported','BINDING_FIELDS'),
                            ('legacy_input_id','cube-input-'+'a'*64,'PREPARED_ID_MISMATCH')]:
        rows=deepcopy(expected);rows[1]['source_binding'][key]=value
        cursor=iter(rows);monkeypatch.setattr(adapter,'prepare_public_lesson',lambda *a,**k:next(cursor))
        with pytest.raises(ContractError,match=error):smoke._prepared(document,training)


def test_prepared_request_order_cannot_be_substituted(exact_material,monkeypatch):
    document,training,_,expected=exact_material
    cursor=iter([expected[1],expected[0],expected[2]])
    monkeypatch.setattr(adapter,'prepare_public_lesson',lambda *a,**k:next(cursor))
    with pytest.raises(ContractError,match='PREPARED_REQUEST'):smoke._prepared(document,training)


def full_material_metadata(sample,exact_material):
    _,training,_,rows=exact_material
    metadata=deepcopy(sample[2]);metadata['training_requests']=deepcopy(training)
    metadata['source_binding']=smoke._source_context(rows[0]['source_binding'],per_request=True)
    metadata['prepared_ids']=[r['prepared_id'] for r in rows]
    metadata['legacy_input_ids']=[r['source_binding']['legacy_input_id'] for r in rows]
    return metadata


def test_full_material_initial_checkpoint_preparation_uses_pure_explicit_mocks(
        sample,exact_material,tmp_path,monkeypatch):
    document,training,_,rows=exact_material
    metadata=full_material_metadata(sample,exact_material)
    tokenizer=LosslessPublicTokenizer.fit_train([row['public'] for row in rows],max_length=1024)
    profile=ordered_encoder.profile_identity(tokenizer,d_model=64,seed=worker.SEED,projection_sha256='b'*64)
    names=metadata['parameter_names'];model_state={name:MockTensor() for name in names}
    optimizer_type=type('AdamW',(),{'__module__':'torch.optim.adamw',
        'state_dict':lambda self:{'state':{},'param_groups':[{'params':[0,1,2],'lr':0.003}]}})
    candidate={'document':document,'seed':worker.SEED,'tokenizer':tokenizer,'ordered_profile':profile,
        'scope':metadata['scope'],'model_context':metadata['model_context'],
        'learner':SimpleNamespace(device='cuda:0',optimizer=optimizer_type()),
        'framework':SimpleNamespace(module=SimpleNamespace(state_dict=lambda:model_state,
            named_parameters=lambda:iter(model_state.items())))}
    payloads=[]
    class SavingMockTorch(MockTorch):
        @staticmethod
        def save(payload,stream):
            payloads.append(deepcopy(payload));stream.write(b'EXPLICIT_MOCK_CHECKPOINT_NOT_TORCH')
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    monkeypatch.setattr(smoke,'_projection',lambda *a:MockTensor())
    result=smoke.write_worker_checkpoint(SavingMockTorch,candidate,kind='INITIAL',training_requests=training,
                                          path=tmp_path/'initial.mock')
    assert (tmp_path/'initial.mock').read_bytes()==b'EXPLICIT_MOCK_CHECKPOINT_NOT_TORCH'
    assert result['metadata']==payloads[0]['metadata']
    assert 'legacy_input_id' not in result['metadata']['source_binding']
    assert result['metadata']['legacy_input_ids']==[r['source_binding']['legacy_input_id'] for r in rows]
    assert result['metadata']['prepared_ids']==[r['prepared_id'] for r in rows]
    smoke.validate_checkpoint_contract(result['metadata'])


@pytest.mark.parametrize('mutation,error',[
    ('legacy_order','RELOAD_LEGACY_INPUT_IDS'),('prepared_order','RELOAD_PREPARED_IDS'),
    ('source_namespace','RELOAD_SOURCE_BINDING')])
def test_reload_binds_all_three_request_identities_before_decode(
        sample,exact_material,monkeypatch,mutation,error):
    document,training,_,_=exact_material
    metadata=full_material_metadata(sample,exact_material)
    if mutation=='legacy_order':metadata['legacy_input_ids'].reverse()
    elif mutation=='prepared_order':metadata['prepared_ids'].reverse()
    else:metadata['source_binding']['source_namespace']='foreign'
    monkeypatch.setattr(smoke,'_guard',lambda *a:None)
    calls=[]
    runtime=SimpleNamespace(load=lambda *a,**k:calls.append('load'))
    with pytest.raises(ContractError,match=error):
        smoke.reload_worker_candidate(runtime,'cuda',document=document,training_requests=training,
            checkpoint={},metadata=metadata)
    assert calls==[]


@pytest.mark.parametrize('value',[[],[True],['cube-input-bad'],('cube-input-'+'a'*64,)])
def test_legacy_input_identity_list_shape_is_closed(sample,value):
    metadata=deepcopy(sample[2]);metadata['legacy_input_ids']=value
    with pytest.raises(ContractError,match='LEGACY_INPUT_IDENTITIES'):
        smoke.validate_checkpoint_contract(metadata)
