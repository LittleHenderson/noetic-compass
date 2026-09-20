"""Construction-first split-safe curriculum using unchanged native program semantics."""
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import struct

from .. import curriculum_v2 as frozen
from .. import curriculum_v3 as wording
from ..curriculum import graph_signature, parse_problem, permitted_view
from ..ir import validate_program
from ..codec import action_to_tokens
from ..features_v2 import LosslessPublicTokenizer

SCHEMA = 'cas-meta2-contrast-curriculum/6'
FAMILIES = ('step_input','call_target')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


@dataclass(frozen=True)
class Config:
    train_flat: int = 128
    train_pairs_per_cell: int = 64
    validation_flat: int = 32
    validation_pairs_per_cell: int = 8
    test_triplets: int = 24

    def checked(self):
        for key,value in asdict(self).items():
            require(type(value) is int and 1 <= value <= (256 if key=='train_flat' else 64), 'COUNT_BOUND:' + key)
        return self


def flatten(value, path=()):
    if isinstance(value,dict):
        return {p:v for k,x in value.items() for p,v in flatten(x,path+(k,)).items()}
    if isinstance(value,list):
        return {p:v for k,x in enumerate(value) for p,v in flatten(x,path+(k,)).items()}
    return {path:value}


def pair_difference(left,right,family,depth):
    require(family in FAMILIES and type(depth) is int and depth in (2,3), 'PAIR_CELL_INVALID')
    for program in (left,right):
        stats=frozen._target_stats({'program':program,'binding':0})
        require(stats['max_call_depth']==depth and stats['procedure_count']==4,'PAIR_STRUCTURE_INVALID')
    a,b=flatten(left),flatten(right)
    require(set(a)==set(b),'PAIR_SHAPE_CHANGED')
    changed=[p for p in a if a[p]!=b[p]]
    field='input' if family=='step_input' else 'procedure'
    require(len(changed)==1 and len(changed[0])==5 and changed[0][0]=='procedures'
            and changed[0][2]=='steps' and changed[0][-1]==field,'ONE_DECISION_CONTRAST_REQUIRED')
    require(frozen._native_work(left)!=frozen._native_work(right),'CONTRAST_WORK_UNCHANGED')
    return changed[0]


def alternatives(program,family,depth,rng):
    candidates=[]
    for name,proc in program['procedures'].items():
        available=[proc['input']]
        for i,step in enumerate(proc['steps']):
            field='input' if family=='step_input' else 'procedure'
            choices=available if family=='step_input' else (list(program['procedures']) if step['kind']=='CALL' else [])
            for value in choices:
                if value==step.get(field):
                    continue
                candidate=deepcopy(program)
                candidate['procedures'][name]['steps'][i][field]=value
                try:
                    pair_difference(program,candidate,family,depth)
                except ValueError:
                    continue
                candidates.append(candidate)
            available.append(step['output'])
    rng.shuffle(candidates)
    return candidates


def identity(seed,config,excluded):
    require(type(seed) is int and 0<=seed<2**63,'EXPLICIT_SEED_REQUIRED')
    config.checked()
    require(type(excluded) in (set,frozenset) and all(type(x) is str and re.fullmatch('[0-9a-f]{64}',x) for x in excluded),
            'EXPLICIT_EXCLUSION_SET_REQUIRED')
    return sha256(canonical({'schema':SCHEMA,'seed':seed,'config':asdict(config),
                           'exclusions':sorted(excluded),
                           'builder_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
                           'dependencies':wording.dependency_receipt()})).hexdigest()


def generate(*,seed,config=Config(),excluded):
    """Builder-only function; private test targets must never be passed to a policy."""
    wording.dependency_receipt()
    ident=identity(seed,config,excluded)
    rng,graphs,inputs=random.Random(seed),set(excluded),set()
    splits={name:[] for name in ('train','validation','test')}
    def task(program,observations,binding,combo,order,split,group,side):
        result=wording._task(program,observations,binding,combo,
                            f'meta2-v6-{ident[:16]}-{split}-{group}-{side}',split,order)
        result['contrast_group']=group
        result['contrast_side']=side
        return result
    for split,flat_count,pair_count,remainder in (
        ('train',config.train_flat,config.train_pairs_per_cell,0),
        ('validation',config.validation_flat,config.validation_pairs_per_cell,2)):
        combos=frozen.wording_combinations(remainder)
        for i in range(flat_count):
            for attempt in range(20000):
                program=frozen._construct(rng,1,i)
                sig=graph_signature(program)
                if sig not in graphs:
                    graphs.add(sig)
                    break
            else:
                raise ValueError('FLAT_SEARCH_EXHAUSTED')
            observations=wording._observations(rng,inputs)
            splits[split].append(task(program,observations,i%3,combos[i%len(combos)],['main'],split,f'flat-{i:04d}','single'))
        for depth in (2,3):
            for family in FAMILIES:
                made=0
                for attempt in range(1,20001):
                    try:
                        left=frozen._construct(rng,depth,attempt*4)
                    except frozen.CurriculumV2Error as error:
                        if str(error)=='V2_NATIVE_RUN_CEILING':
                            continue
                        raise
                    if len(left['procedures'])!=4 or graph_signature(left) in graphs:
                        continue
                    right=next((p for p in alternatives(left,family,depth,rng) if graph_signature(p) not in graphs),None)
                    if right is None:
                        continue
                    observations=wording._observations(rng,inputs)
                    order=list(left['procedures'])
                    rng.shuffle(order)
                    group=f'{depth}-{family}-{made:04d}'
                    for side,program in (('left',left),('right',right)):
                        graphs.add(graph_signature(program))
                        splits[split].append(task(program,observations,made%3,combos[made%len(combos)],order,split,group,side))
                    made+=1
                    if made==pair_count:
                        break
                require(made==pair_count,'PAIR_SEARCH_EXHAUSTED')
        rng.shuffle(splits[split])
    for i in range(config.test_triplets):
        for attempt in range(20000):
            try:
                shallow,deep=frozen._paired_programs(rng,i)
            except frozen.CurriculumV2Error as error:
                if str(error)=='V2_NATIVE_RUN_CEILING':
                    continue
                raise
            signatures={graph_signature(shallow),graph_signature(deep)}
            if len(signatures)==2 and not signatures & graphs:
                graphs.update(signatures)
                break
        else:
            raise ValueError('TEST_PAIR_SEARCH_EXHAUSTED')
        observations=wording._observations(rng,inputs)
        order=list(shallow['procedures'])
        rng.shuffle(order)
        for side,program,remainder in (('same_depth',shallow,0),('wording_shift',shallow,1),('deeper_calls',deep,0)):
            combos=frozen.wording_combinations(remainder)
            splits['test'].append(task(program,observations,i%3,combos[i%len(combos)],order,'test',f'triplet-{i:04d}',side))
    rng.shuffle(splits['test'])
    dataset={'schema':SCHEMA,'seed':seed,'config':asdict(config),'dataset_id':ident,'splits':splits}
    validate(dataset,excluded=excluded)
    return dataset


def validate(dataset,*,excluded):
    require(type(dataset) is dict and set(dataset)=={'schema','seed','config','dataset_id','splits'} and dataset['schema']==SCHEMA,
            'DATASET_SCHEMA_INVALID')
    require(type(dataset['config']) is dict and set(dataset['config'])==set(Config.__dataclass_fields__),'CONFIG_FIELDS_INVALID')
    config=Config(**dataset['config']).checked()
    ident=identity(dataset['seed'],config,excluded)
    require(dataset['dataset_id']==ident and set(dataset['splits'])=={'train','validation','test'},'DATASET_ID_OR_SPLITS_INVALID')
    ids,graphs,payloads,summary=set(),{}, {},{}
    for split,tasks in dataset['splits'].items():
        require(type(tasks) is list,'SPLIT_LIST_REQUIRED')
        groups,counts={},Counter()
        for t in tasks:
            require(type(t) is dict and set(t)=={'task_id','public','target','provenance','contrast_group','contrast_side'},'TASK_FIELDS_INVALID')
            require(all(type(t[k]) is str for k in ('task_id','contrast_group','contrast_side')),'TASK_ID_TYPES_INVALID')
            require(t['task_id'] not in ids and t['task_id']==f"meta2-v6-{ident[:16]}-{split}-{t['contrast_group']}-{t['contrast_side']}",'TASK_ID_INVALID')
            ids.add(t['task_id'])
            groups.setdefault(t['contrast_group'],[]).append(t)
            require(parse_problem(t['public'])==t['target'],'PUBLIC_MEANING_MISMATCH')
            stats=frozen._target_stats(t['target'])
            provenance=t['provenance']
            require(type(provenance) is dict and set(provenance)=={'graph_signature','depth','evaluation_group',
                    'triplet_id','wording_combination','definition_order'} and type(provenance['depth']) is int
                    and provenance['triplet_id'] is None and type(provenance['wording_combination']) is list
                    and len(provenance['wording_combination'])==4
                    and all(type(v) is int for v in provenance['wording_combination']),'PROVENANCE_FIELDS_INVALID')
            sig=graph_signature(t['target']['program'])
            require(provenance['graph_signature']==sig and provenance['depth']==stats['max_call_depth']
                    and provenance['evaluation_group']==split,'PROVENANCE_MISMATCH')
            owner=(split,t['contrast_group'])
            require(sig not in excluded,'EXPOSED_GRAPH_REUSED')
            if sig in graphs:
                require(split=='test' and graphs[sig]==owner and t['contrast_side'] in ('same_depth','wording_shift'), 'GRAPH_SPLIT_LEAK')
            graphs[sig]=owner
            for o in t['public']['observations']:
                payload=struct.pack('<8f',*o['values'])
                require(payload not in payloads or payloads[payload]==owner,'OBSERVATION_SPLIT_LEAK')
                payloads[payload]=owner
            remainder=(1 if t['contrast_side']=='wording_shift' else 0) if split=='test' else (0 if split=='train' else 2)
            combo=tuple(provenance['wording_combination'])
            require(combo in frozen.wording_combinations(remainder),'WORDING_SPLIT_LEAK')
            tag=next(o['tag'] for o in t['public']['observations'] if o['slot']==t['target']['binding'])
            require(wording.render_problem(t['target']['program'],tag,combo,definition_order=provenance['definition_order'])==t['public']['problem'],
                    'PUBLIC_RENDER_MISMATCH')
            counts[str(stats['max_call_depth'])]+=1
        if split=='test':
            require(set(groups)=={f'triplet-{i:04d}' for i in range(config.test_triplets)},'TEST_GROUP_COVERAGE')
            for members in groups.values():
                by_side={t['contrast_side']:t for t in members}
                require(len(members)==3 and set(by_side)=={'same_depth','wording_shift','deeper_calls'},'TEST_TRIPLET_INVALID')
                same,words,deep=[by_side[s] for s in ('same_depth','wording_shift','deeper_calls')]
                require(all(validate_program(t['target']['program'])['max_call_depth']==d
                            for t,d in ((same,3),(words,3),(deep,4))),'TEST_DEPTHS_REQUIRED')
                require(same['target']==words['target'],'WORDING_TARGET_CHANGED')
                frozen._validate_pair(same['target']['program'],deep['target']['program'])
                require(all(t['public']['observations']==same['public']['observations'] and t['target']['binding']==same['target']['binding'] for t in members),
                        'TEST_OBSERVATIONS_OR_BINDING_CHANGED')
                require(all(t['provenance']['definition_order']==same['provenance']['definition_order'] for t in members)
                        and same['provenance']['wording_combination']==deep['provenance']['wording_combination']
                        and same['public']['problem']!=words['public']['problem'],'TEST_PRESENTATION_CONTROL_CHANGED')
        else:
            flat=getattr(config,split+'_flat')
            pairs=getattr(config,split+'_pairs_per_cell')
            expected={f'flat-{i:04d}' for i in range(flat)} | {f'{d}-{f}-{i:04d}' for d in (2,3) for f in FAMILIES for i in range(pairs)}
            require(set(groups)==expected,'DEVELOPMENT_GROUP_COVERAGE')
            for group,members in groups.items():
                if group.startswith('flat-'):
                    require(len(members)==1 and members[0]['contrast_side']=='single'
                            and validate_program(members[0]['target']['program'])['max_call_depth']==1,'FLAT_TASK_INVALID')
                    continue
                by_side={t['contrast_side']:t for t in members}
                require(len(members)==2 and set(by_side)=={'left','right'},'PAIR_PARTITION_BROKEN')
                left,right=by_side['left'],by_side['right']
                depth,family,_=group.split('-')
                pair_difference(left['target']['program'],right['target']['program'],family,int(depth))
                require(left['public']['observations']==right['public']['observations'] and left['target']['binding']==right['target']['binding']
                        and left['provenance']['definition_order']==right['provenance']['definition_order']
                        and left['provenance']['wording_combination']==right['provenance']['wording_combination'], 'PAIR_CONTEXT_CHANGED')
        summary[split]={'tasks':len(tasks),'depths':dict(counts),'groups':len(groups)}
    train=dataset['splits']['train']
    tokenizer=LosslessPublicTokenizer.fit_train([t['public'] for t in train],max_length=1024)
    tokens=set(token for t in train for token in action_to_tokens(t['target'],max_length=256))
    for split,tasks in dataset['splits'].items():
        for t in tasks:
            tokenizer.encode_public(t['public'])
            require(set(action_to_tokens(t['target'],max_length=256))<=tokens,'UNSEEN_POSITIVE_ACTION_TOKEN')
    return {'schema':SCHEMA,'dataset_id':ident,'splits':summary,'source':wording.dependency_receipt(),
            'cross_split_graph_overlap':False,'cross_split_observation_overlap':False,'native_outcomes_checked':False,
            'neural_execution':False,'boundary':'Structural and public-meaning checks only; native task correctness still requires execution.'}


def write(output,*,seed,config=Config(),excluded):
    path=Path(output).absolute()
    require(not path.exists() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (path,*path.parents)),
            'NEW_UNLINKED_OUTPUT_REQUIRED')
    dataset=generate(seed=seed,config=config,excluded=excluded)
    path.mkdir(parents=True,exist_ok=False)
    contents={'train.json':dataset['splits']['train'],'validation.json':dataset['splits']['validation'],
              'test_public.json':[permitted_view(t) for t in dataset['splits']['test']],
              'test_private.json':dataset['splits']['test']}
    hashes={}
    for name,value in contents.items():
        raw=canonical(value)+b'\n'
        with (path/name).open('xb') as stream:
            stream.write(raw)
        hashes[name]=sha256(raw).hexdigest()
    cold={k:v for k,v in dataset.items() if k!='splits'}
    cold['splits']={split:json.loads((path/name).read_bytes()) for split,name in
                    (('train','train.json'),('validation','validation.json'),('test','test_private.json'))}
    report=validate(cold,excluded=excluded)
    require(json.loads((path/'test_public.json').read_bytes())==[permitted_view(t) for t in cold['splits']['test']], 'TEST_PUBLIC_EXPORT_CHANGED')
    manifest={**report,'seed':seed,'config':asdict(config),'sha256':hashes}
    with (path/'manifest.json').open('xb') as stream:
        stream.write(canonical(manifest)+b'\n')
    return manifest
