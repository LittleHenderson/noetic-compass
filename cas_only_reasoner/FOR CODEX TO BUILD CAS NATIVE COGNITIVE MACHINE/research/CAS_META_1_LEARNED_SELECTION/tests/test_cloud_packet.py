"""Synthetic byte-only packets; no cloud, Torch, pickle, or model execution."""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspect_cloud_packet",ROOT/"tools"/"inspect_cloud_packet.py")
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)
SOURCE = "a"*40
BASELINE = "0917267b1354e5d036263eaa6ba9a7197eafb776"


def encoded(value): return json.dumps(value,sort_keys=True).encode()
def sha(value): return hashlib.sha256(value).hexdigest()


def packet(tmp_path,files,*,partial=False,selected=None,after_index=None,returncode=None,job="cas-meta1-fixture",source=SOURCE):
    selected = set(files) if selected is None else set(selected)
    entries = [{"path":name,"bytes":len(files[name]),"sha256":sha(files[name])} for name in sorted(files,key=PurePosixPath)]
    index = b"".join(json.dumps(row,sort_keys=True,separators=(",",":")).encode()+b"\n" for row in entries)
    collection = {"job":job,"source_sha":source,"baseline_sha":BASELINE,"archive_sha256":"b"*64,
                  "returncode":(1 if partial else 0) if returncode is None else returncode,"partial_evidence":partial,
                  "original_file_count":len(files),"original_bytes":sum(map(len,files.values())),
                  "included_full_file_count":len(selected),"omitted_full_file_count":len(files)-len(selected),
                  "original_file_index_sha256":sha(index),"index_entries":entries[:1000],"index_entries_omitted":max(0,len(files)-1000)}
    written = {name:files[name] for name in selected}
    if after_index: after_index(written)
    archive = tmp_path/"cloud_artifacts.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
        for name,value in written.items(): z.writestr(name,value)
        z.writestr(inspector.COLLECTION,encoded(collection))
    launch = {"job":job,"source_sha":source,"archive_sha256":"b"*64,"manifest":{"baseline_sha":BASELINE},
              "status":"AWS_JOB_FINISHED" if not partial else "AWS_JOB_FAILED","termination_confirmed":True,
              "result":{"sha256":sha(archive.read_bytes()),"bytes":archive.stat().st_size,"job":job,
                        "returncode":collection["returncode"],"partial_evidence":partial,"omitted_full_file_count":len(files)-len(selected)}}
    receipt = tmp_path/"launch_receipt.json"; receipt.write_bytes(encoded(launch))
    return archive,receipt


def completed_files(mutate=None):
    prefix = inspector.TRAIN
    files,checkpoints,results,predictions = {},{},{},{}
    for family in ("cas","generic"):
        checkpoints[family] = {}
        for state,suffix in (("initial","initial"),("selected","best"),("last","last")):
            name = family+"_"+suffix+".pt"
            value = b"NOT A REAL PICKLE; MUST NEVER BE LOADED: "+name.encode()
            files[prefix+name] = value
            checkpoints[family][state] = {"path":"/remote/training/"+name,"sha256":sha(value)}
    files[prefix+"checkpoints.json"] = encoded(checkpoints)
    for arm in inspector.ARMS:
        success = not arm.endswith("untrained")
        actions = [{"procedure":0,"binding":1}]*2
        predictions[arm] = actions
        rows = []
        for i,action in enumerate(actions):
            verdict = {key:success for key in ("success","procedure_correct","binding_correct","repair_correct","output_correct","evidence_valid")}
            verdict["repair_required"] = False
            rows.append({"case_index":i,"action":action,"verification":verdict,"execution_status":"EXECUTED",
                         "reserved_policy_units":72,"execution_timing":{"wall_seconds":0.125}})
        files[prefix+arm+"_case_results.json"] = encoded(rows)
        expected_count = 2 if success else 0
        results[arm] = {key:expected_count for key in ("success","procedure_correct","binding_correct","repair_correct","output_correct","evidence_valid")}
        results[arm].update(total=2,success_rate=float(success),repair_required_total=0,repair_required_correct=0,
                            execution_failures=0,reserved_policy_units_total_known=144,reserved_policy_units_unknown_cases=0,
                            native_execution_wall_seconds=0.25,all_cases_in_denominator=True)
    prediction_bytes = encoded({"arms":predictions})
    files[prefix+"predictions.json"] = prediction_bytes
    files[prefix+"predictions_seal.json"] = encoded({"sha256":sha(prediction_bytes)})
    receipt = {"status":"CAS_META_1_AWS_GPU_PILOT_COMPLETED","source":{"declared_source_sha":SOURCE},"checkpoints":checkpoints,
               "prediction_sha256":sha(prediction_bytes),"all_test_cases_executed_per_arm":2,"results":results,
               "cas_actual_success_gain":1.0,"generic_actual_success_gain":1.0}
    files[prefix+"receipt.json"] = encoded(receipt)
    if mutate: mutate(files)
    files[prefix+"payload_sha256.json"] = encoded({name[len(prefix):]:sha(value) for name,value in files.items() if name.startswith(prefix)})
    return files


def test_complete_packet_recounts_metrics_and_hashes_fake_checkpoint_bytes(tmp_path):
    archive,receipt = packet(tmp_path,completed_files())
    result = inspector.inspect_packet(archive,receipt)
    assert result["status"] == "VERIFIED_COMPLETED_PACKET"
    assert result["complete_file_index_verified"]
    assert result["metrics"]["cas_trained"]["success_rate"] == 1.0
    assert result["metrics"]["cas_untrained"]["success_rate"] == 0.0
    assert len(result["checkpoints"]) == 6 and all(c["verified"] for c in result["checkpoints"])
    assert result["neural_execution_performed"] is False and result["checkpoint_loading_performed"] is False


def test_complete_index_digest_covers_members_beyond_first_thousand(tmp_path):
    files = completed_files()
    files.update({f"gpu-test-evidence/{i:04d}.json":b"{}" for i in range(1002)})
    archive,receipt = packet(tmp_path,files)
    assert inspector.inspect_packet(archive,receipt)["complete_file_index_verified"]


def test_partial_failure_never_becomes_completed_result(tmp_path):
    files = {"runtime.json":b"{}","omitted-large.log":b"missing original"}
    archive,receipt = packet(tmp_path,files,partial=True,selected={"runtime.json"})
    result = inspector.inspect_packet(archive,receipt)
    assert result["status"] == "VERIFIED_PARTIAL_FAILED_PACKET"
    assert result["omitted_full_file_count"] == 1 and result["complete_file_index_verified"] is False
    assert "metrics" not in result


def test_failed_bootstrap_packet_is_verified_without_training_claim(tmp_path):
    files = {"remote_failure.json":encoded({"message":"install failed"}),"job.json":encoded({"returncode":1})}
    archive,receipt = packet(tmp_path,files,returncode=1)
    result = inspector.inspect_packet(archive,receipt)
    assert result["status"] == "VERIFIED_FAILED_PACKET"
    assert result["complete_file_index_verified"] and "metrics" not in result


def test_outer_archive_hash_is_required(tmp_path):
    archive,receipt = packet(tmp_path,completed_files())
    with archive.open("ab") as output: output.write(b"changed bytes")
    with pytest.raises(inspector.PacketInvalid,match="ARCHIVE_BINDING"):
        inspector.inspect_packet(archive,receipt)


def test_original_member_hash_rejects_updated_outer_archive(tmp_path):
    archive,receipt = packet(tmp_path,completed_files(),after_index=lambda f:f.update({inspector.TRAIN+"cas_initial.pt":b"replacement"}))
    with pytest.raises(inspector.PacketInvalid,match="INDEX_MEMBER_HASH"):
        inspector.inspect_packet(archive,receipt)


def test_recorded_metrics_cannot_disagree_with_case_rows(tmp_path):
    def changed(files):
        name = inspector.TRAIN+"cas_trained_case_results.json"
        rows = json.loads(files[name]); rows[0]["verification"]["success"] = False
        files[name] = encoded(rows)
    archive,receipt = packet(tmp_path,completed_files(changed))
    with pytest.raises(inspector.PacketInvalid,match="METRIC_VALUE"):
        inspector.inspect_packet(archive,receipt)


def test_checkpoint_hash_is_independently_checked_against_candidate_record(tmp_path):
    def changed(files): files[inspector.TRAIN+"cas_initial.pt"] = b"different but outer manifests updated"
    archive,receipt = packet(tmp_path,completed_files(changed))
    with pytest.raises(inspector.PacketInvalid,match="CHECKPOINT_RAW_BYTE_HASH"):
        inspector.inspect_packet(archive,receipt)


@pytest.mark.parametrize("name",["../escape","/absolute","C:/drive","a\\b","CON","nested/file. ","a/../b"])
def test_unsafe_zip_paths_rejected(tmp_path,name):
    files = completed_files(); files[name] = b"unsafe"
    archive,receipt = packet(tmp_path,files)
    with pytest.raises(inspector.PacketInvalid): inspector.inspect_packet(archive,receipt)


def test_windows_case_collisions_rejected(tmp_path):
    files = completed_files(); files.update({"same.txt":b"a","SAME.txt":b"b"})
    archive,receipt = packet(tmp_path,files)
    with pytest.raises(inspector.PacketInvalid,match="CASE_COLLIDING"):
        inspector.inspect_packet(archive,receipt)


def test_optional_extract_requires_new_owned_records_directory(tmp_path,monkeypatch):
    archive,receipt = packet(tmp_path,completed_files())
    monkeypatch.setattr(inspector,"ROOT",tmp_path)
    destination = tmp_path/"records"/"inspected"
    result = inspector.inspect_packet(archive,receipt,extract_to=destination)
    assert result["extracted_to"] == str(destination.resolve())
    assert (destination/inspector.TRAIN/"cas_initial.pt").read_bytes().startswith(b"NOT A REAL PICKLE")
    with pytest.raises(inspector.PacketInvalid,match="NEW_OWNED"):
        inspector.inspect_packet(archive,receipt,extract_to=destination)
    with pytest.raises(inspector.PacketInvalid,match="NEW_OWNED"):
        inspector.inspect_packet(archive,receipt,extract_to=tmp_path/"outside-records")


def recovery_files(monkeypatch, mutate=None):
    prefix = inspector.RECOVERY
    files, checkpoints, checkpoint_checks = {}, {}, []
    for family in ('cas','generic'):
        checkpoints[family] = {'optimizer_steps':840}
        for state,suffix in (('initial','initial'),('selected','best'),('last','last')):
            name = family+'_'+suffix+'.pt'
            record = {'path':'/original/'+name,'sha256':sha(('fake '+name).encode())}
            checkpoints[family][state] = record
            checkpoint_checks.append({'file':inspector.TRAIN+name,'verified':True,'sha256':record['sha256']})
    action = {'procedure':0,'binding':1}
    predictions = {'arms':{arm:[action]*72 for arm in inspector.ARMS}}
    files[prefix+'predictions.json'] = encoded(predictions)
    prediction_hash = sha(files[prefix+'predictions.json'])
    files[prefix+'predictions_seal.json'] = encoded({'sha256':prediction_hash,'test_private_labels_loaded':False,'sealed_utc':'2026-09-05T10:00:00+00:00'})
    files[prefix+'test_gold_opening_receipt.json'] = encoded({'prediction_sha256_before_opening':prediction_hash,'opened_utc':'2026-09-05T10:00:01+00:00'})
    files[prefix+'checkpoints.json'] = encoded(checkpoints)
    monkeypatch.setattr(inspector,'ORIGINAL_METADATA_SHA256',{name:sha(files[prefix+name]) for name in inspector.ORIGINAL_METADATA_SHA256})
    files[prefix+'predecessor_inspection.json'] = encoded({'archive_sha256':inspector.ORIGINAL_PACKET,
        'source_sha':inspector.ORIGINAL_SOURCE,'job':inspector.ORIGINAL_JOB,'partial_evidence':False,
        'complete_file_index_verified':True,'checkpoints':checkpoint_checks})
    files[prefix+'custody.json'] = encoded({'original_source':inspector.ORIGINAL_SOURCE,'original_job':inspector.ORIGINAL_JOB,
        'original_packet_sha256':inspector.ORIGINAL_PACKET,'original_predictions_sha256':prediction_hash,
        'recovery_source':SOURCE,'checkpoints':checkpoints,'training_performed':False,
        'selector_predictions_changed':False,'private_targets_changed':False})
    all_rows = {arm:[] for arm in inspector.ARMS}
    for index in range(72):
        case = prefix+f'cases/case_{index:04d}/'
        comparison = {'new_input_sha256':sha(b'input'),'old_input_sha256':sha(b'input'),
            'new_output_sha256':sha(b'output'),'old_output_sha256':sha(b'output'),
            'output_bytes_equal':True,'frozen_weight_bytes_unchanged':True}
        files[case+'reference_comparison.json'] = encoded(comparison)
        case_rows = {}
        for name in ('reference',*inspector.ARMS):
            files[case+name+'/native.db'] = b'fake database bytes; never executed'
            result = {'status':'EXECUTED','reference':name == 'reference','selected_action':action,
                'input_tensor_bytes_sha256':sha(b'input'),'output_tensor_bytes_sha256':sha(b'output'),
                'evidence_sha256':{'native.db':sha(files[case+name+'/native.db'])}}
            files[case+name+'/result.json'] = encoded(result)
            if name == 'reference': continue
            success = not name.endswith('untrained')
            verdict = {key:success for key in ('success','procedure_correct','binding_correct','repair_correct','output_correct','evidence_valid')}
            verdict['repair_required'] = False
            row = {'case_index':index,'action':action,'verification':verdict,'execution_status':'EXECUTED',
                'failure':None,'reserved_policy_units':72,'execution_timing':{'wall_seconds':0.125}}
            all_rows[name].append(row); case_rows[name] = row
            files[case+name+'_case_result.json'] = encoded(row)
        files[case+'completed.json'] = encoded({'case_index':index,'arms':case_rows,'reference_comparison':comparison})
    metrics = {}
    for arm,rows in all_rows.items():
        files[prefix+arm+'_case_results.json'] = encoded(rows)
        metrics[arm] = inspector.recount(rows)
    files[prefix+'receipt.json'] = encoded({'status':'CAS_META_1_EVALUATION_RECOVERY_COMPLETED','source_sha':SOURCE,
        'original_source_sha':inspector.ORIGINAL_SOURCE,'original_packet_sha256':inspector.ORIGINAL_PACKET,
        'original_prediction_sha256':prediction_hash,'training_performed':False,'selector_forward_performed':False,
        'cases_per_arm':72,'arms':5,'new_reference_count':72,'checkpoints':checkpoints,
        'cross_gpu_reference_output_differences':0,'results':metrics,'cas_actual_success_gain':1.0,'generic_actual_success_gain':1.0})
    if mutate: mutate(files)
    files[prefix+'payload_sha256.json'] = encoded({name[len(prefix):]:sha(value) for name,value in files.items()})
    return files


def test_recovery_recounts_all_360_rows_without_loading_checkpoints(tmp_path,monkeypatch):
    archive,receipt = packet(tmp_path,recovery_files(monkeypatch))
    report = inspector.inspect_packet(archive,receipt)
    assert report['status'] == 'VERIFIED_COMPLETED_RECOVERY_PACKET'
    assert all(metrics['total'] == 72 for metrics in report['metrics'].values())
    assert report['predecessor_bytes_independently_rechecked'] is False
    assert report['checkpoint_loading_performed'] is False


@pytest.mark.parametrize('mutation,reason',[
    ('denominator','RECOVERY_DENOMINATOR'),('checkpoint','ORIGINAL_METADATA_BYTES'),
    ('action','RECOVERY_ACTION_SEAL'),('native','RECOVERY_NATIVE_EVIDENCE_HASH'),
    ('metric','METRIC_VALUE')])
def test_recovery_rejects_inconsistent_evidence_with_updated_outer_hashes(tmp_path,monkeypatch,mutation,reason):
    def mutate(files):
        prefix = inspector.RECOVERY
        if mutation == 'native':
            files[prefix+'cases/case_0000/cas_trained/native.db'] = b'replaced'; return
        name = prefix+('checkpoints.json' if mutation == 'checkpoint' else 'cas_trained_case_results.json' if mutation == 'action' else 'receipt.json')
        value = json.loads(files[name])
        if mutation == 'denominator': value['cases_per_arm'] = 71
        elif mutation == 'checkpoint': value['cas']['optimizer_steps'] = 841
        elif mutation == 'action': value[0]['action']['binding'] = 2
        else: value['results']['cas_trained']['success'] = 71
        files[name] = encoded(value)
    archive,receipt = packet(tmp_path,recovery_files(monkeypatch,mutate))
    with pytest.raises(inspector.PacketInvalid,match=reason): inspector.inspect_packet(archive,receipt)


def test_recovery_requires_complete_payload_manifest(tmp_path,monkeypatch):
    files = recovery_files(monkeypatch)
    files[inspector.RECOVERY+'unlisted.txt'] = b'not in payload manifest'
    archive,receipt = packet(tmp_path,files)
    with pytest.raises(inspector.PacketInvalid,match='RECOVERY_PAYLOAD_COVERAGE'):
        inspector.inspect_packet(archive,receipt)


def test_recovery_can_independently_rehash_original_raw_checkpoint_bytes(tmp_path,monkeypatch):
    files = recovery_files(monkeypatch)
    originals = {inspector.TRAIN+name:files[inspector.RECOVERY+name] for name in inspector.ORIGINAL_METADATA_SHA256}
    for family in ('cas','generic'):
        for suffix in ('initial','best','last'):
            name = family+'_'+suffix+'.pt'; originals[inspector.TRAIN+name] = ('fake '+name).encode()
    old = tmp_path/'original'; old.mkdir()
    archive,_ = packet(old,originals,returncode=1,job=inspector.ORIGINAL_JOB,source=inspector.ORIGINAL_SOURCE)
    monkeypatch.setattr(inspector,'ORIGINAL_PACKET',sha(archive.read_bytes()))
    files = recovery_files(monkeypatch)
    archive,receipt = packet(tmp_path,files)
    report = inspector.inspect_packet(archive,receipt,predecessor_run_dir=old)
    assert report['original_checkpoint_bytes_independently_rechecked'] is True
    assert report['checkpoint_loading_performed'] is False
