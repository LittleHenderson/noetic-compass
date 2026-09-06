"""Pure source-bound v7 dataset, training and sealed-choice recount."""
from dataclasses import asdict


def commands(base,job,spec,manifest_pin,c):
    remote='/opt/cas-meta2/package/'+c.PILOT+'/runs/'+base.rstrip('/')
    root='/opt/cas-meta2/package/'+c.PILOT
    phase=['/opt/cas-meta2/venv/bin/python','-B','-m','cas_meta2.contrast_v7.campaign',
           '--output',remote,'--job',job,'--phase']
    train=['/opt/cas-meta2/venv/bin/python','-B','-m','cas_meta2.contrast_v7.train',
        '--bundle',remote+'/trainer_input','--output',remote+'/training','--job',job,
        '--manifest-sha256',manifest_pin,'--loader-sha256',spec['public_loader_sha256'],
        '--curriculum-seed',str(spec['curriculum_seed']),
        '--curriculum-config',remote+'/curriculum_config.json','--training-config',remote+'/training_config.json',
        '--exclusions',root+'/'+spec['exclusion_inventory_path'],
        '--exclusions-sha256',spec['exclusion_inventory_sha256']]
    return {'dataset':phase+['dataset'],'training':train,'evaluate':phase+['evaluate']}


def bind_choices(neural,rows,tasks,publics,*,canonical,parse,c):
    c.require(type(tasks) is list and len(tasks)==72 and len(publics)==len(rows)==len(neural)==72,
              'V7_EXACT_72_SEALED_CHOICES')
    for index,(n,row,task,public) in enumerate(zip(neural,rows,tasks,publics,strict=True)):
        c.require(type(row) is dict and set(row)=={'case_index','public_sha256','actions'}
            and type(row['case_index']) is int and row['case_index']==index
            and row['public_sha256']==canonical(public) and set(row['actions'])==set(c.ARMS)
            and n=={**row,'actions':{arm:row['actions'][arm] for arm in c.ARMS[:-1]}},
            'V7_SEALED_CHOICE_ATTRIBUTION')
        c.require(row['actions']['rule']==parse(public),'V7_RULE_NOT_PUBLIC_DERIVED')


def cold_child(packet,*,native_base,parent_report,job,spec,cfg,excluded,source,
               manifest_pin,process,c,evidence):
    request=packet.json(native_base+'cold_validation_request.json')
    remote='/opt/cas-meta2/package/'+c.PILOT
    out=remote+'/runs/'+native_base.rstrip('/')
    request_path=out+'/cold_validation_request.json'
    expected={'job':job,'private_data':remote+'/runs/'+c.BASE+'dataset',
        'expected_sha256':manifest_pin,'seed':spec['curriculum_seed'],'config':asdict(cfg),
        'excluded':sorted(excluded),'pins':remote+'/'+spec['source_pins_path'],
        'expected_pins_sha256':spec['source_pins_sha256'],
        'expected_loader_sha256':spec['public_loader_sha256'],'source_sha256':source}
    c.require(request==expected,'V7_COLD_REQUEST_ATTRIBUTION')
    pin=packet.inventory[native_base+'cold_validation_request.json']['sha256']
    code=('import sys;from cas_meta2.contrast_v7.native_evaluation import validate_private_child;'
          'validate_private_child(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])')
    command=['/opt/cas-meta2/venv/bin/python','-B','-c',code,request_path,pin,
             out+'/cold_dataset_validation.json',job]
    record=evidence.process(packet,native_base+'cold_validation_process/process_receipt.json',command,c)
    c.require(record['pid']!=process['pid']
        and evidence.timestamp(process['started_utc'],c)<=evidence.timestamp(record['started_utc'],c)
        <evidence.timestamp(record['finished_utc'],c)<=evidence.timestamp(process['finished_utc'],c),
        'V7_COLD_EXIT_ORDER')
    c.require(packet.json(native_base+'cold_dataset_validation.json')==parent_report,'V7_COLD_RECOUNT_COPY')
    return record


def audit(packet,*,job,spec,initial,campaign,modules,c,evidence):
    checks,t,d,cur,cam,parent=(modules[k] for k in ('checks','train','data','curriculum','campaign','parent'))
    output=packet.root/c.BASE
    cfg,training=cam.configurations(spec)
    c.require(training.epochs==200 and training.batch_size==16
        and spec['optimizer_steps_per_family']==11200,'V7_FIXED_TRAINING_COUNTS')
    for name,value in [('experiment.json',spec),('curriculum_config.json',asdict(cfg)),
                       ('training_config.json',asdict(training))]:
        c.require(packet.json(c.BASE+name)==value,'V7_CONFIGURATION_CHANGED:'+name)
    excluded=t.registered_exclusions(c.ROOT/spec['exclusion_inventory_path'],
                                    expected_sha256=spec['exclusion_inventory_sha256'])
    c.require(len(excluded)==spec['exclusion_count']==8837,'V7_FULL_EXCLUSION_UNION_REQUIRED')
    source=t.source_identity();campaign_source=cam.source_identity();baseline=initial['baseline']
    c.require(initial=={'source_sha256':source,'campaign_source_sha256':campaign_source,
                       'baseline':baseline,'experiment':campaign['experiment']}
        and campaign['source_sha256']==source and campaign['campaign_source_sha256']==campaign_source,
        'V7_INITIAL_SOURCE_IDENTITY')
    manifest=packet.json(c.BASE+'dataset/manifest.json')
    pin=packet.inventory[c.BASE+'dataset/manifest.json']['sha256']
    opts=dict(expected_sha256=pin,seed=spec['curriculum_seed'],config=cfg,excluded=excluded,
        pins=c.ROOT/spec['source_pins_path'],expected_pins_sha256=spec['source_pins_sha256'],
        expected_loader_sha256=spec['public_loader_sha256'])
    parent_report=parent.validate_bundle(output/'dataset',**opts)
    loaded=d.load_training_bundle(output/'trainer_input',expected_sha256=pin,
        seed=spec['curriculum_seed'],config=cfg,excluded=excluded,
        expected_loader_sha256=spec['public_loader_sha256'])
    c.require(loaded['manifest']==manifest and parent_report['completed'] is True,
              'V7_PARENT_PUBLIC_MANIFEST_COPY')
    base=packet.json(c.BASE+'base_dataset/manifest.json')
    base_pin=packet.inventory[c.BASE+'base_dataset/manifest.json']['sha256']
    for name in ('train.json','validation.json','test_public.json','test_private.json'):
        packet.same_hash(c.BASE+'base_dataset/'+name,base['sha256'][name])
    c.require(packet.raw(c.BASE+'base_dataset/manifest.json')==packet.raw(c.BASE+'dataset/base_manifest.json')
        and packet.raw(c.BASE+'base_dataset/train.json')==packet.raw(c.BASE+'dataset/base_train.json'),
        'V7_RETAINED_BASE_NOT_IDENTICAL')
    for name in ('validation.json','test_public.json','test_private.json'):
        c.require(packet.raw(c.BASE+'base_dataset/'+name)==packet.raw(c.BASE+'dataset/'+name),
                  'V7_HELDOUT_BYTES_CHANGED')
    for name,pin_value in manifest['sha256'].items():
        packet.same_hash(c.BASE+'dataset/'+c.safe_name(name),pin_value)
    expected_public=set(loaded['receipt']['loaded_sha256'])|{'manifest.json'}
    actual_public={name.removeprefix(c.BASE+'trainer_input/') for name in packet.inventory
                   if name.startswith(c.BASE+'trainer_input/')}
    c.require(actual_public==expected_public and 'test_private.json' not in actual_public,
              'V7_PRIVATE_OR_EXTRA_TRAINER_INPUT')
    for name in expected_public:
        c.require(packet.raw(c.BASE+'trainer_input/'+name)==packet.raw(c.BASE+'dataset/'+name),
                  'V7_PUBLIC_EXPORT_BYTES_CHANGED')
    exported=packet.json(c.BASE+'training_bundle_receipt.json')
    expected_export={**loaded['receipt'],'parent_validation':parent_report,
        'parent_reads_private_test_targets':True,
        'export_directory':'/opt/cas-meta2/package/'+c.PILOT+'/runs/'+c.BASE+'trainer_input',
        'training_performed':False}
    c.require(exported==expected_export,'V7_EXPORT_RECEIPT_COPY')
    assembled=cam.validate_assembly_records(base,manifest,parent_report,exported,spec=spec,
        base_pin=base_pin,merged_pin=pin,excluded=excluded)
    assembly=packet.json(c.BASE+'dataset_assembly_receipt.json')
    c.require(assembly['schema']==cam.SCHEMA and assembly['completed'] is True
        and assembly['job']==job and assembly['source_sha256']==campaign_source
        and assembly['base_manifest_sha256']==base_pin and assembly['manifest_sha256']==pin
        and assembly['dataset_id']==manifest['dataset_id'] and assembly['parent_validation']==parent_report
        and assembly['public_export']==exported and all(assembly[k]==v for k,v in assembled.items())
        and assembly['original_training_only'] is True
        and assembly['all_original_graphs_remain_in_fresh_exclusions'] is True
        and all(assembly[k] is False for k in ('neural_execution','training_started',
                                             'native_evaluation_completed','learning_accepted')),
        'V7_ASSEMBLY_RECOUNT_OR_BOUNDARY')
    for key in ('source_pins_sha256','public_loader_sha256','exclusion_inventory_sha256',
                'exclusion_count','original_tasks_sha256','curriculum_seed'):
        c.require(assembly[key]==spec[key],'V7_ASSEMBLY_INPUT_IDENTITY:'+key)
    expected_commands=commands(c.BASE,job,spec,pin,c)
    processes={name:evidence.process(packet,c.BASE+'processes/'+name+'/process_receipt.json',command,c)
               for name,command in expected_commands.items()}
    c.require(all(campaign['processes'][name]==row for name,row in processes.items()),
              'V7_PROCESS_RECEIPT_COPY')
    times=evidence.timestamp
    c.require(assembly['pid']==processes['dataset']['pid']
        and len({row['pid'] for row in processes.values()})==3
        and times(processes['dataset']['started_utc'],c)<=times(assembly['utc'],c)
            <=times(processes['dataset']['finished_utc'],c)
        and times(processes['dataset']['finished_utc'],c)<=times(processes['training']['started_utc'],c)
        and times(processes['training']['finished_utc'],c)<=times(processes['evaluate']['started_utc'],c),
        'V7_MAIN_PROCESS_ORDER')
    gate=checks.check_training(output/'training',output/'processes/training/process_receipt.json',
        output/'trainer_input',expected_command=expected_commands['training'],job=job,
        expected_manifest_sha256=pin,expected_loader_sha256=spec['public_loader_sha256'],
        curriculum_seed=spec['curriculum_seed'],curriculum_config=cfg,excluded=excluded,
        config=training,expected_source=source,expected_baseline=baseline)
    c.require(gate==packet.json(c.BASE+'training_gate.json')==packet.json(c.NATIVE+'training_parent_gate.json'),
              'V7_RECOUNTED_TRAINING_GATE_COPY')
    raw=packet.raw(c.NATIVE+'predictions.jsonl');neural_raw=packet.raw(c.BASE+'training/neural_predictions.jsonl')
    c.require(sha256_bytes(neural_raw)==gate['predictions_sha256'],'V7_NEURAL_PREDICTION_PIN')
    rows=[c.decode(line) for line in raw.splitlines()];neural=[c.decode(line) for line in neural_raw.splitlines()]
    tasks=packet.json(c.BASE+'dataset/test_private.json');publics=packet.json(c.BASE+'dataset/test_public.json')
    c.require([cur.permitted_view(task) for task in tasks]==publics,'V7_PRIVATE_PUBLIC_MAPPING')
    from cas_meta2.codec import canonical_sha256
    bind_choices(neural,rows,tasks,publics,canonical=canonical_sha256,parse=cur.parse_problem,c=c)
    seal=packet.json(c.NATIVE+'predictions_seal.json')
    expected_seal={'schema':'cas-meta2-contrast-evaluation-seal/7','sha256':sha256_bytes(raw),
        'neural_predictions_sha256':gate['predictions_sha256'],'parent_gate_sha256':canonical_sha256(gate),
        'manifest_sha256':pin,'arms':list(c.ARMS),'test_examples':72,'prediction_count':360,
        'rule_input':'public problem and permitted observations only','sealed_utc':seal['sealed_utc']}
    c.require(seal==expected_seal,'V7_NATIVE_SEAL_CHANGED')
    opening=packet.json(c.NATIVE+'private_opening_receipt.json')
    c.require(opening=={'opened_utc':opening['opened_utc'],'prediction_sha256':seal['sha256'],
        'training_exit_receipt_sha256':gate['process_receipt_sha256'],
        'private_sha256':manifest['sha256']['test_private.json']},'V7_PRIVATE_OPENING_BINDING')
    c.require(times(processes['evaluate']['started_utc'],c)<=times(seal['sealed_utc'],c)
        <times(opening['opened_utc'],c)<=times(processes['evaluate']['finished_utc'],c),
        'V7_SEAL_BEFORE_PRIVATE_OPENING')
    cold=cold_child(packet,native_base=c.NATIVE,parent_report=parent_report,job=job,spec=spec,cfg=cfg,
        excluded=excluded,source=source,manifest_pin=pin,process=processes['evaluate'],c=c,evidence=evidence)
    c.require(times(opening['opened_utc'],c)<=times(cold['started_utc'],c),'V7_COLD_PARENT_ORDER')
    return {'tasks':tasks,'predictions':rows,'manifest':manifest,'manifest_sha256':pin,
        'base_manifest_sha256':base_pin,'source':source,'baseline':baseline,'training_gate':gate,
        'assembly':assembly,'parent_validation':parent_report,'public_loader':loaded['receipt'],
        'processes':processes,'cold_process':cold,'seal':seal,'opening':opening,'configuration':asdict(training),
        'boundary':'Original256 are allowed only as exact appended training records; full known exclusions remain in force for fresh base/validation/test. No new tasks or neural computations during review.'}


def sha256_bytes(raw):
    from hashlib import sha256
    return sha256(raw).hexdigest()

