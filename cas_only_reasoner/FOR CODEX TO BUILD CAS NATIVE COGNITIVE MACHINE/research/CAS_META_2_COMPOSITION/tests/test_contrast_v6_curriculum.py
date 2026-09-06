"""Pure split, contrast, meaning, and export checks; no models or provider calls."""
from copy import deepcopy
import json
import sys
import pytest
from cas_meta2.contrast_v6 import curriculum as c


@pytest.fixture(scope='module')
def sample():
    return c.generate(seed=926603,config=c.Config(train_flat=32,train_pairs_per_cell=8,
                      validation_flat=8,validation_pairs_per_cell=2,test_triplets=3),excluded=frozenset())


def test_pure_roundtrip_and_expected_counts(sample):
    result=c.validate(json.loads(c.canonical(sample)),excluded=frozenset())
    assert result['splits']['train']['tasks']==96
    assert result['splits']['validation']['tasks']==24
    assert result['splits']['test']['tasks']==9
    assert result['native_outcomes_checked'] is False
    assert 'torch' not in sys.modules and 'boto3' not in sys.modules


def test_construction_is_deterministic(sample):
    assert c.generate(seed=926603,config=c.Config(**sample['config']),excluded=frozenset())==sample


@pytest.mark.parametrize('field',list(c.Config.__dataclass_fields__))
@pytest.mark.parametrize('value',[True,0,-1,1000,1.5])
def test_count_bounds(field,value):
    with pytest.raises(ValueError):
        c.Config(**{field:value}).checked()


@pytest.mark.parametrize('seed',[True,-1,2**63,'3'])
def test_seed_bounds(seed):
    with pytest.raises(ValueError):
        c.identity(seed,c.Config(),frozenset())


def test_exclusion_identity_and_coverage(sample):
    sig=sample['splits']['train'][0]['provenance']['graph_signature']
    with pytest.raises(ValueError,match='DATASET_ID_OR_SPLITS_INVALID'):
        c.validate(sample,excluded=frozenset({sig}))
    changed=deepcopy(sample)
    changed['dataset_id']=c.identity(changed['seed'],c.Config(**changed['config']),frozenset({sig}))
    # The old IDs cannot masquerade as a newly excluded dataset.
    with pytest.raises(ValueError):
        c.validate(changed,excluded=frozenset({sig}))


@pytest.mark.parametrize('mutation',['gold_in_public','target_binding','pair_removed','task_duplicate',
                                   'pair_split','wording_split','graph_provenance','group_name','side'])
def test_cold_mutations_fail(sample,mutation):
    d=deepcopy(sample)
    t=next(t for t in d['splits']['train'] if t['contrast_side']=='left')
    if mutation=='gold_in_public': t['public']['target']=t['target']
    elif mutation=='target_binding': t['target']['binding']=(t['target']['binding']+1)%3
    elif mutation=='pair_removed': d['splits']['train'].remove(t)
    elif mutation=='task_duplicate': d['splits']['train'].append(deepcopy(t))
    elif mutation=='pair_split':
        d['splits']['train'].remove(t)
        d['splits']['validation'].append(t)
    elif mutation=='wording_split': t['provenance']['wording_combination']=[0,0,0,2]
    elif mutation=='graph_provenance': t['provenance']['graph_signature']='0'*64
    elif mutation=='group_name': t['contrast_group']='wrong'
    else: t['contrast_side']='single'
    with pytest.raises(ValueError):
        c.validate(d,excluded=frozenset())


def test_does_not_mutate_input(sample):
    before=deepcopy(sample)
    c.validate(sample,excluded=frozenset())
    assert sample==before


@pytest.mark.parametrize('field',['depth','wording_combination','extra'])
def test_provenance_types_fail_closed(sample,field):
    d=deepcopy(sample)
    p=d['splits']['train'][0]['provenance']
    if field=='depth': p[field]=True
    elif field=='wording_combination': p[field]=[False,False,False,False]
    else: p[field]='unrecognized'
    with pytest.raises(ValueError,match='PROVENANCE_FIELDS_INVALID'):
        c.validate(d,excluded=frozenset())


def test_deeper_test_cannot_be_replaced_by_shallow(sample):
    d=deepcopy(sample)
    deep=next(t for t in d['splits']['test'] if t['contrast_side']=='deeper_calls')
    shallow=next(t for t in d['splits']['test'] if t['contrast_group']==deep['contrast_group'] and t['contrast_side']=='same_depth')
    deep['public']=deepcopy(shallow['public'])
    deep['target']=deepcopy(shallow['target'])
    deep['provenance']=deepcopy(shallow['provenance'])
    with pytest.raises(ValueError):
        c.validate(d,excluded=frozenset())


def test_one_decision_and_nontrivial_work_required(sample):
    t=next(t for t in sample['splits']['train'] if t['contrast_side']=='left')
    with pytest.raises(ValueError,match='ONE_DECISION_CONTRAST_REQUIRED'):
        c.pair_difference(t['target']['program'],t['target']['program'],'step_input',t['provenance']['depth'])


def test_export_public_only_and_refuse_overwrite(tmp_path,sample):
    output=tmp_path/'data'
    manifest=c.write(output,seed=926603,config=c.Config(**sample['config']),excluded=frozenset())
    public=json.loads((output/'test_public.json').read_bytes())
    assert len(public)==9 and all(set(p)=={'problem','observations'} for p in public)
    assert all('target' not in p and 'provenance' not in p for p in public)
    assert set(manifest['sha256'])=={'train.json','validation.json','test_public.json','test_private.json'}
    before={p.name:p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError,match='NEW_UNLINKED_OUTPUT_REQUIRED'):
        c.write(output,seed=926603,config=c.Config(**sample['config']),excluded=frozenset())
    assert before=={p.name:p.read_bytes() for p in output.iterdir()}
