"""Pure diagnostic paired curriculum construction, not a held-out experiment."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 926601


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore'}:
            raise RuntimeError('LOCAL_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN')


sys.meta_path.insert(0, Guard())
sys.path.insert(0, str(ROOT))
from cas_meta2 import curriculum_v2 as frozen
from cas_meta2 import curriculum_v3 as wording
from cas_meta2.curriculum import graph_signature, parse_problem, check_native_topology
from cas_meta2.ir import validate_program
from cas_meta2.codec import action_to_tokens
from cas_meta2.features_v2 import LosslessPublicTokenizer


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def reachable(program):
    seen, pending = set(), [program['entry']]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        pending.extend(s['procedure'] for s in program['procedures'][name]['steps'] if s['kind'] == 'CALL')
    return seen == set(program['procedures'])


def changed_fields(left, right, path=()):
    if type(left) is not type(right):
        return [path]
    if isinstance(left, dict):
        if set(left) != set(right):
            return [path]
        return [p for key in left for p in changed_fields(left[key], right[key], path+(key,))]
    if isinstance(left, list):
        if len(left) != len(right):
            return [path]
        return [p for i,(a,b) in enumerate(zip(left,right)) for p in changed_fields(a,b,path+(i,))]
    return [] if left == right else [path]


def validate_pair(left, right, family, depth):
    for program in (left, right):
        stats = frozen._target_stats({'program':program,'binding':0})
        if stats['max_call_depth'] != depth or len(program['procedures']) != 4 or not reachable(program):
            raise ValueError('PAIR_DEPTH_PROCEDURE_COUNT_OR_REACHABILITY')
    paths = changed_fields(left,right)
    expected_field = 'input' if family == 'step_input' else 'procedure'
    if len(paths) != 1 or len(paths[0]) != 5 or paths[0][0] != 'procedures' or paths[0][2] != 'steps' or paths[0][-1] != expected_field:
        raise ValueError('EXACTLY_ONE_TARGET_DECISION_REQUIRED')
    if frozen._native_work(left) == frozen._native_work(right):
        raise ValueError('CONTRAST_MUST_CHANGE_NATIVE_WORK')
    if graph_signature(left) == graph_signature(right):
        raise ValueError('CONTRAST_GRAPH_MUST_CHANGE')
    return paths[0]


def alternatives(program, family, depth, rng):
    variants = []
    for name, proc in program['procedures'].items():
        available = [proc['input']]
        for i, step in enumerate(proc['steps']):
            if family == 'step_input':
                choices, field = available, 'input'
            elif step['kind'] == 'CALL':
                choices, field = list(program['procedures']), 'procedure'
            else:
                choices, field = [], 'procedure'
            for replacement in choices:
                if replacement == step.get(field):
                    continue
                candidate = deepcopy(program)
                candidate['procedures'][name]['steps'][i][field] = replacement
                try:
                    location = validate_pair(program,candidate,family,depth)
                except ValueError:
                    continue
                variants.append((candidate,location))
            available.append(step['output'])
    rng.shuffle(variants)
    return variants


def main():
    output = HERE / 'receipt.json'
    if output.exists() or (HERE / 'tasks.json').exists():
        raise ValueError('NEW_PROBE_OUTPUT_REQUIRED')
    wording.dependency_receipt()
    paths = [ROOT/'cas_meta2'/n for n in ('curriculum.py','curriculum_v2.py','curriculum_v3.py',
              'ir.py','codec.py','features_v2.py','exclusions_v3.json','development_exclusions_v3.json')]
    source_hashes = {p.name:sha256(p.read_bytes()).hexdigest() for p in paths}
    excluded = set(wording.exclusion_inventory()[0]) | set(wording.registered_development_exclusions())
    old_inputs = {}
    for name in ('train.json','validation.json','test_private.json'):
        path = ROOT/'records/decoder_dataset_reconstruction_v4_001/dataset'/name
        raw = path.read_bytes()
        old_inputs[name] = sha256(raw).hexdigest()
        excluded.update(graph_signature(t['target']['program']) for t in json.loads(raw))
    rng, seen, observation_bytes = random.Random(SEED), set(excluded), set()
    tasks, pairs, attempts = [], [], Counter()
    combinations = frozen.wording_combinations(0)
    for depth in (2,3):
        for family in ('step_input','call_target'):
            made = 0
            while made < 32:
                attempts[f'{depth}/{family}'] += 1
                if attempts[f'{depth}/{family}'] > 20000:
                    raise ValueError('BOUNDED_PAIR_SEARCH_EXHAUSTED')
                index = attempts[f'{depth}/{family}'] * 4
                try:
                    left = frozen._construct(rng,depth,index)
                except frozen.CurriculumV2Error as error:
                    if str(error) == 'V2_NATIVE_RUN_CEILING':
                        continue
                    raise
                if len(left['procedures']) != 4 or graph_signature(left) in seen:
                    continue
                selected = next(((p,loc) for p,loc in alternatives(left,family,depth,rng)
                                 if graph_signature(p) not in seen),None)
                if selected is None:
                    continue
                right, location = selected
                pair_id = f'contrast-probe-{SEED}-{depth}-{family}-{made:03d}'
                observations = wording._observations(rng,observation_bytes)
                binding = len(pairs) % 3
                order = list(left['procedures'])
                rng.shuffle(order)
                combination = combinations[len(pairs) % len(combinations)]
                pair_tasks = []
                for side,program in (('left',left),('right',right)):
                    task = wording._task(program,observations,binding,combination,
                                         pair_id+'-'+side,'diagnostic_training_probe',order)
                    assert parse_problem(task['public']) == task['target']
                    task['contrast'] = {'pair_id':pair_id,'family':family,'side':side}
                    tasks.append(task)
                    pair_tasks.append(task)
                    seen.add(graph_signature(program))
                if pair_tasks[0]['public']['problem'] == pair_tasks[1]['public']['problem']:
                    raise ValueError('PUBLIC_CONTRAST_MISSING')
                if pair_tasks[0]['public']['observations'] != pair_tasks[1]['public']['observations']:
                    raise ValueError('PAIRED_OBSERVATIONS_CHANGED')
                pairs.append({'pair_id':pair_id,'depth':depth,'family':family,'changed_target_path':list(location),
                              'task_ids':[t['task_id'] for t in pair_tasks]})
                made += 1
    tokenizer = LosslessPublicTokenizer.fit_train([t['public'] for t in tasks],max_length=1024)
    for task in tasks:
        tokenizer.encode_public(task['public'])
        action_to_tokens(task['target'],max_length=256)
    # Negative controls: identical pairs and additional target changes must fail.
    controls = 0
    for pair in pairs[:1] + pairs[32:33]:
        left,right = [next(t['target']['program'] for t in tasks if t['task_id']==i) for i in pair['task_ids']]
        for malformed in (left, {**deepcopy(right),'entry':'missing'}):
            try:
                validate_pair(left,malformed,pair['family'],pair['depth'])
            except ValueError:
                controls += 1
            else:
                raise AssertionError('INVALID_PAIR_ACCEPTED')
    assert controls == 4
    assert len(tasks) == 256 and len(pairs) == 128 and len(seen-excluded) == 256
    assert source_hashes == {p.name:sha256(p.read_bytes()).hexdigest() for p in paths}
    task_raw = (json.dumps(tasks,sort_keys=True,indent=2)+'\n').encode()
    (HERE/'tasks.json').write_bytes(task_raw)
    record = {'schema':'cas-meta2-contrast-curriculum-probe/0.1','seed':SEED,
              'task_count':len(tasks),'pair_count':len(pairs),'pairs_per_depth_and_family':32,
              'depths':[2,3],'procedures_per_task':4,'target_changes_per_pair':1,
              'all_pairs_change_symbolic_native_work':True,'all_procedures_reachable':True,
              'public_meaning_checked':True,'training_input_limit':1024,'action_token_limit':256,
              'negative_controls_passed':controls,'attempts':dict(attempts),
              'prior_excluded_graphs':len(excluded),'prior_data_sha256':old_inputs,
              'source_sha256':source_hashes,'tasks_sha256':sha256(task_raw).hexdigest(),
              'exposed_graph_signatures':sorted(seen-excluded),'pairs':pairs,
              'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
              'neural_execution':False,'native_outcomes_checked':False,'training_performed':False,
              'fresh_evaluation':False,'fit_probe_only':True,
              'boundary':'Prototype practice data, not a launched curriculum or native correctness result. '
                         'Keep both members of each pair in one partition. Exclude all prototype graphs from future held-out evaluation. '
                         'One-field contrast is a training hypothesis, not a demonstrated improvement.'}
    output.write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('task_count','pair_count','attempts','negative_controls_passed',
                      'prior_excluded_graphs','tasks_sha256','training_performed')},indent=2))


if __name__ == '__main__':
    main()
