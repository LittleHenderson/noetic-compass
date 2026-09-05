"""Pure AWS-launch contracts. No AWS calls, GPU work or model imports."""
import ast
import copy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta2_launch_under_test",ROOT/"aws"/"launch.py")
launch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launch)


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/"tests")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.plan = json.loads(launch.PLAN_FILE.read_text())
        self.job = "cas-meta2-contract-only"

    def config(self):
        return {**self.plan,"job":self.job,"bucket":self.job+"-807562639912","archive_sha256":"a"*64,"smoke_only":False,
                "manifest":{"source_sha":"b"*40,"baseline_sha":launch.ACCEPTED_BASELINE,"pilot_dir":"research/CAS_META_2_COMPOSITION","meta1_dir":"research/CAS_META_1_LEARNED_SELECTION","meta_runtime_dir":"research/CASFORMER_v0_3_META_LOGIC_WIP","files_sha256":{}}}

    def test_exact_approved_plan(self):
        launch.validate_approval("400.00",self.plan)
        self.assertEqual(self.plan["per_launch_reserved_cap_usd"],"7.00")
        self.assertEqual(self.plan["runtime_seconds_max"],7200)

    def test_old_or_missing_approval_refused(self):
        for value in (None,"100.00","399.99","NaN","Infinity"):
            with self.subTest(value=value),self.assertRaises(launch.LaunchRefused):
                launch.validate_approval(value,self.plan)

    def test_plan_resource_or_gpu_mutations_refused(self):
        for change in ({"instance_type":"g4dn.xlarge"},{"instance_count":2},{"runtime_seconds_max":7201},{"compute_seconds_max":6601},{"automatic_retries":1},{"artifact_objects_max":4},{"on_demand_hourly_usd_max":"2.53"},{"local_neural_execution":True},{"ebs_encrypted":False}):
            with self.subTest(change=change),self.assertRaises(launch.LaunchRefused):
                launch.validate_approval("400.00",{**self.plan,**change})

    def test_boolean_integer_plan_substitution_refused(self):
        with self.assertRaises(launch.LaunchRefused):
            launch.validate_approval("400.00",{**self.plan,"instance_count":True})

    def test_cli_cap_does_not_replace_owner_ledger(self):
        args = types.SimpleNamespace(approved_cap_usd="400.00")
        with patch.object(launch,"verify_launcher_identity",return_value={}),patch.object(launch.budget,"read_ledger",side_effect=launch.budget.BudgetRefused("OWNER_APPROVAL_MISSING")):
            with self.assertRaisesRegex(launch.budget.BudgetRefused,"OWNER_APPROVAL_MISSING"):
                launch.execute(args,self.plan,{})

    def test_reservation_uses_shared_budget_api(self):
        with patch.object(launch.budget,"reserve_budget",return_value={"ok":True}) as reserve:
            self.assertEqual(launch.reserve_budget(self.job,"b"*40,"a"*64,self.plan),{"ok":True})
            reserve.assert_called_once_with(self.job,"b"*40,"a"*64,"7.00",self.plan)

    def test_default_main_performs_no_aws_actions(self):
        output=io.StringIO()
        with patch.object(launch,"execute",side_effect=AssertionError("PAID_PATH")),redirect_stdout(output):
            self.assertEqual(launch.main([]),0)
        self.assertFalse(json.loads(output.getvalue())["aws_actions_performed"])

    def test_source_has_no_torch_import(self):
        tree = ast.parse((ROOT/"aws"/"launch.py").read_text())
        imports = [item for node in ast.walk(tree) if isinstance(node,ast.Import) for item in node.names]
        self.assertFalse(any(item.name.startswith("torch") for item in imports))

    def test_remote_program_compiles_without_executing(self):
        compile(launch.remote_program(self.config()),"<remote-only>","exec")

    def test_remote_neural_gate_follows_confirmed_permit(self):
        code = launch.remote_program(self.config())
        self.assertLess(code.index("cloud_deadline_confirmed"),code.index("'torch==2.11.0'"))
        self.assertIn("CAS_META1_RUN_GPU_TESTS",code)
        self.assertIn("GPU_CONTRACT_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED",code)

    def test_remote_runs_new_campaign_not_old_recovery(self):
        code = launch.remote_program(self.config())
        self.assertIn("cas_meta2.campaign",code)
        self.assertNotIn("cas_meta1.resume",code)
        self.assertIn("--smoke-only",code)
        self.assertIn("SUCCESS_WITHOUT_SAVED_CANDIDATE_CHECKPOINT",code)
        self.assertIn("FULL_CAMPAIGN_WITHOUT_COMPLETED_EVALUATION",code)
        self.assertIn("predictions.jsonl",code)
        self.assertIn("tests/test_policy_gpu.py",code)
        self.assertIn("META2_GPU_POLICY_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED",code)

    def test_remote_output_stays_inside_native_pilot_write_boundary(self):
        code=launch.remote_program(self.config())
        self.assertIn("out = package / m['pilot_dir'] / 'runs' / 'cloud_job'",code)
        self.assertNotIn("out = root / 'evidence'",code)
        self.assertIn("str(out/'campaign')",code)

    def test_campaign_and_process_use_same_remaining_outer_deadline(self):
        code=launch.remote_program(self.config())
        self.assertIn("effective_campaign_seconds = min(CONFIG['compute_seconds_max'],int(deadline-time.time()-180))",code)
        self.assertIn("if effective_campaign_seconds < 60:",code)
        self.assertIn("'--max-wall-seconds',str(effective_campaign_seconds)",code)
        self.assertIn("seconds=effective_campaign_seconds,deadline=deadline",code)
        self.assertLess(code.index("env.pop('CAS_META2_RUN_GPU_TESTS')"),code.index("effective_campaign_seconds ="))
        self.assertEqual(self.plan["runtime_seconds_max"],7200)
        self.assertEqual(self.plan["per_launch_reserved_cap_usd"],"7.00")

    def test_remote_exception_resets_success_code(self):
        code = launch.remote_program(self.config())
        self.assertIn("except BaseException as exc:\n    returncode = 1",code)

    def test_remote_kills_failed_worker_process_group(self):
        code = launch.remote_program(self.config())
        self.assertIn("start_new_session=True",code)
        self.assertIn("os.killpg(process.pid,signal.SIGTERM)",code)
        self.assertIn("os.killpg(process.pid,signal.SIGKILL)",code)

    def test_bootstrap_is_small_pinned_and_has_early_shutdown_timer(self):
        script = launch.user_data(self.config())
        self.assertLess(len(script.encode()),16384)
        self.assertIn("sha256sum -c -",script)
        self.assertLess(script.index("sleep 7100"),script.index("\naws s3 cp"))
        self.assertIn("trap '",script)

    def test_invalid_remote_script_digest_refused(self):
        with self.assertRaises(launch.LaunchRefused):
            launch.user_data(self.config(),"bad")

    def test_unsafe_archive_paths_refused(self):
        for value in ("../escape","/absolute","a\\b","C:/x","a//b","a/./b"):
            with self.subTest(value=value),self.assertRaises(launch.LaunchRefused):
                launch.safe_relative(value)

    def test_archive_hash_mismatch_refused(self):
        path = self.base/"archive.zip"
        path.write_bytes(b"not an archive")
        with self.assertRaisesRegex(launch.LaunchRefused,"ARCHIVE_SHA_MISMATCH"):
            launch.validate_archive(path,"0"*64,"b"*40,self.plan)

    def pinned_archive(self,change=None):
        p,m,r="research/CAS_META_2_COMPOSITION","research/CAS_META_1_LEARNED_SELECTION","research/CASFORMER_v0_3_META_LOGIC_WIP"
        dist="research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
        wheels=[dist+"casformer_reference-0.1.0-py3-none-any.whl",dist+"cas_neural_cjt-0.2.0-py3-none-any.whl"]
        members={p+"/aws/launch.py":b"# fixture",p+"/requirements-gpu.txt":b"numpy==2.2.6\n",m+"/cas_meta1/execution.py":b"# helper",r+"/cas_meta/__init__.py":b"# runtime",wheels[0]:b"wheel fixture 1",wheels[1]:b"wheel fixture 2"}
        protected={"baseline_sha":launch.ACCEPTED_BASELINE,"files":[{"path":name.removeprefix("research/"),"sha256":hashlib.sha256(members[name]).hexdigest()} for name in wheels]}
        baseline=json.dumps(protected).encode()
        members[m+"/BASELINE_MANIFEST.json"]=baseline
        patcher=patch.object(launch,"ACCEPTED_BASELINE_MANIFEST_SHA256",hashlib.sha256(baseline).hexdigest())
        patcher.start()
        self.addCleanup(patcher.stop)
        manifest={"schema_version":2,"source_sha":"b"*40,"baseline_sha":launch.ACCEPTED_BASELINE,"pilot_dir":p,"meta1_dir":m,"meta_runtime_dir":r,"dependency_lock":p+"/requirements-gpu.txt","wheel_paths":wheels}
        if change is not None: change(members,manifest)
        manifest["files_sha256"]={name:hashlib.sha256(raw).hexdigest() for name,raw in members.items()}
        path=self.base/"pinned.zip"
        with zipfile.ZipFile(path,"w") as archive:
            for name,raw in members.items(): archive.writestr(name,raw)
            archive.writestr("launch_manifest.json",json.dumps(manifest))
        return path

    def test_valid_pinned_archive_checks_every_member(self):
        path=self.pinned_archive()
        manifest=launch.validate_archive(path,launch.digest(path),"b"*40,self.plan)
        self.assertEqual(manifest["schema_version"],2)

    def test_changed_frozen_wheel_refused_even_when_outer_hashes_match(self):
        path=self.pinned_archive(lambda members,manifest:members.update({manifest["wheel_paths"][0]:b"changed frozen wheel"}))
        with self.assertRaisesRegex(launch.LaunchRefused,"ACCEPTED_SOURCE_OR_WHEEL_BYTES_CHANGED"):
            launch.validate_archive(path,launch.digest(path),"b"*40,self.plan)

    def test_unregistered_wheel_selection_refused(self):
        path=self.pinned_archive(lambda members,manifest:manifest.update(wheel_paths=["evil.whl","another.whl"]))
        with self.assertRaisesRegex(launch.LaunchRefused,"TWO_FROZEN_WHEELS_REQUIRED"):
            launch.validate_archive(path,launch.digest(path),"b"*40,self.plan)

    def test_gpu_dependency_lock_rejects_cpu_torch(self):
        path=self.pinned_archive(lambda members,manifest:members.update({manifest["dependency_lock"]:b"torch==2.11.0+cpu\n"}))
        with self.assertRaisesRegex(launch.LaunchRefused,"GPU_LOCK_REQUIRES_EXACT_PINS"):
            launch.validate_archive(path,launch.digest(path),"b"*40,self.plan)

    def test_schedule_must_match_every_deadline_field(self):
        target = {"Arn":"terminate","RoleArn":"job-role","Input":"{}","RetryPolicy":{"MaximumRetryAttempts":0}}
        current = {"State":"ENABLED","ScheduleExpression":"at(deadline)","ScheduleExpressionTimezone":"UTC","FlexibleTimeWindow":{"Mode":"OFF"},"ActionAfterCompletion":"DELETE","Target":target}
        launch.verify_schedule(current,target,"at(deadline)")
        for change in ({"State":"DISABLED"},{"ScheduleExpressionTimezone":"PST"},{"FlexibleTimeWindow":{"Mode":"FLEXIBLE"}},{"Target":{}}):
            with self.subTest(change=change),self.assertRaisesRegex(launch.LaunchRefused,"DEADLINE_NOT_CONFIRMED"):
                launch.verify_schedule({**current,**change},target,"at(deadline)")

    def test_unowned_tag_refused(self):
        with self.assertRaisesRegex(launch.LaunchRefused,"OWNERSHIP_MISMATCH"):
            launch.check_tag([{"Key":"cas_meta_job","Value":"someone-else"}],self.job)

    def packet(self,*,partial=False,returncode=0,source="b"*40):
        root = self.base/"artifacts"
        root.mkdir()
        (root/"campaign_receipt.json").write_text('{"status":"test fixture"}')
        archive = self.base/"results.zip"
        record = {"job":self.job,"source_sha":source,"returncode":returncode}
        receipt = launch.build_evidence_bundle(root,archive,8*1024*1024,record)
        result = {"job":self.job,"sha256":launch.digest(archive),"bytes":archive.stat().st_size,"returncode":receipt["returncode"]}
        return archive,result

    def test_complete_packet_has_no_omissions_and_internal_binding(self):
        archive,result = self.packet()
        receipt = launch.verify_downloaded_packet(archive,result,self.job,"b"*40,self.plan)
        self.assertFalse(receipt["partial_evidence"])
        self.assertEqual(receipt["omitted_full_file_count"],0)

    def test_packet_wrong_source_refused(self):
        archive,result = self.packet(source="c"*40)
        with self.assertRaisesRegex(launch.LaunchRefused,"INTERNAL_IDENTITY_MISMATCH"):
            launch.verify_downloaded_packet(archive,result,self.job,"b"*40,self.plan)

    def test_oversized_artifacts_are_explicit_failure_not_silent_omission(self):
        root = self.base/"oversized"
        root.mkdir()
        (root/"large.bin").write_bytes(b"x"*(4*1024*1024))
        archive = self.base/"partial.zip"
        result = launch.build_evidence_bundle(root,archive,4*1024*1024,{"job":self.job,"source_sha":"b"*40,"returncode":0})
        self.assertEqual(result["returncode"],1)
        self.assertTrue(result["partial_evidence"])
        self.assertEqual(result["omitted_full_file_count"],1)

    def test_distinct_expanded_and_compressed_limits_allow_complete_compressible_packet(self):
        root = self.base/"compressible"
        root.mkdir()
        (root/"trace.txt").write_bytes(b"x"*(5*1024*1024))
        archive = self.base/"compressible.zip"
        result = launch.build_evidence_bundle(root,archive,4*1024*1024,{"job":self.job,"source_sha":"b"*40,"returncode":0},8*1024*1024)
        self.assertEqual(result["returncode"],0)
        self.assertFalse(result["partial_evidence"])
        self.assertGreater(result["original_bytes"],4*1024*1024)
        self.assertLess(archive.stat().st_size,4*1024*1024)

    def test_compressed_overflow_is_failure_and_keeps_all_checkpoints_predictions(self):
        root = self.base/"incompressible"
        root.mkdir()
        (root/"trace.bin").write_bytes(os.urandom(5*1024*1024))
        (root/"candidate_cas_best.pt").write_bytes(b"checkpoint fixture")
        (root/"candidate_generic_best.pt").write_bytes(b"checkpoint fixture 2")
        (root/"predictions.jsonl").write_bytes(b'{"sealed":true}\n')
        archive = self.base/"incompressible.zip"
        result = launch.build_evidence_bundle(root,archive,4*1024*1024,{"job":self.job,"source_sha":"b"*40,"returncode":0},8*1024*1024)
        self.assertEqual(result["returncode"],1)
        self.assertTrue(result["partial_evidence"])
        self.assertIn("COMPRESSED_ARTIFACT_CEILING",result["failure"])
        self.assertLess(archive.stat().st_size,4*1024*1024)
        with zipfile.ZipFile(archive) as stored:
            self.assertTrue({"candidate_cas_best.pt","candidate_generic_best.pt","predictions.jsonl"}.issubset(stored.namelist()))

    def test_plan_declares_separate_expanded_and_transfer_ceilings(self):
        self.assertEqual(self.plan["evidence_expanded_bytes_max"],2*1024**3)
        self.assertEqual(self.plan["artifact_bytes_max"],1024**3)
        self.assertEqual(self.plan["archive_expanded_bytes_max"],512*1024**2)

    def test_force_shutdown_refused_without_verified_artifact(self):
        class EC2:
            def __init__(self,job): self.job,self.calls=job,[]
            def describe_instances(self,**kwargs): return {"Reservations":[{"Instances":[{"ClientToken":self.job,"State":{"Name":"shutting-down"},"Tags":[{"Key":"cas_meta_job","Value":self.job}]}]}]}
            def terminate_instances(self,**kwargs): self.calls.append(kwargs); return {}
        ec2 = EC2(self.job)
        with patch.object(launch.time,"monotonic",side_effect=[0,61]):
            with self.assertRaisesRegex(launch.LaunchRefused,"NO_VERIFIED_DOWNLOAD"):
                launch.terminate_owned_instance(ec2,"i-owned",self.job,artifact_verified=False,record=lambda *args,**kwargs:None)
        self.assertEqual(ec2.calls,[{"InstanceIds":["i-owned"]}])

    def test_force_shutdown_requires_verified_artifact_and_owned_token(self):
        class EC2:
            def __init__(self,job): self.job,self.calls=job,[]
            def describe_instances(self,**kwargs): return {"Reservations":[{"Instances":[{"ClientToken":self.job,"State":{"Name":"shutting-down"},"Tags":[{"Key":"cas_meta_job","Value":self.job}]}]}]}
            def terminate_instances(self,**kwargs): self.calls.append(kwargs); return {}
            def get_waiter(self,name): return types.SimpleNamespace(wait=lambda **kwargs:None)
        ec2 = EC2(self.job)
        with patch.object(launch.time,"monotonic",side_effect=[0,61]):
            launch.terminate_owned_instance(ec2,"i-owned",self.job,artifact_verified=True,record=lambda *args,**kwargs:None)
        self.assertEqual(ec2.calls[-1],{"InstanceIds":["i-owned"],"Force":True,"SkipOsShutdown":True})

    def test_uncertain_launch_never_assumed_absent(self):
        ec2 = types.SimpleNamespace(describe_instances=lambda **kwargs:{"Reservations":[]})
        with self.assertRaisesRegex(launch.LaunchRefused,"EXPECTED_EXACTLY_ONE"):
            launch.reconcile_instance(ec2,self.job)

    def test_volume_confirmation_requires_actual_absence(self):
        ec2 = types.SimpleNamespace(describe_volumes=lambda **kwargs:{"Volumes":[]})
        self.assertEqual(launch.confirm_deleted_volumes(ec2,self.job,lambda *args,**kwargs:None),[])

    def test_volume_ownership_mismatch_refused(self):
        ec2 = types.SimpleNamespace(describe_volumes=lambda **kwargs:{"Volumes":[{"VolumeId":"vol-other","State":"available","Tags":[]}]})
        with self.assertRaisesRegex(launch.LaunchRefused,"OWNERSHIP_MISMATCH"):
            launch.confirm_deleted_volumes(ec2,self.job,lambda *args,**kwargs:None)

    def test_cleanup_will_not_delete_untagged_security_group(self):
        deleted=[]
        ec2=types.SimpleNamespace(describe_security_groups=lambda **kwargs:{"SecurityGroups":[{"GroupId":"sg-other","Tags":[]}]},delete_security_group=lambda **kwargs:deleted.append(kwargs))
        receipt={"resources":{"security_group":"sg-other"},"cleanup_errors":[]}
        launch.remove_owned_auxiliary_resources(ec2,None,None,receipt,self.job,"worker","timer",lambda *args,**kwargs:None)
        self.assertEqual(deleted,[])
        self.assertTrue(any("OWNERSHIP_MISMATCH" in error for error in receipt["cleanup_errors"]))

    def test_cleanup_deletes_owned_role_when_policy_already_absent(self):
        from botocore.exceptions import ClientError
        deleted=[]
        def absent_policy(**kwargs): raise ClientError({"Error":{"Code":"NoSuchEntity","Message":"fixture"}},"DeleteRolePolicy")
        iam=types.SimpleNamespace(get_role=lambda **kwargs:{"Role":{"Arn":"owned-arn","Tags":[{"Key":"cas_meta_job","Value":self.job}]}},delete_role_policy=absent_policy,delete_role=lambda **kwargs:deleted.append(kwargs))
        receipt={"resources":{"worker":"owned-arn"},"cleanup_errors":[]}
        launch.remove_owned_auxiliary_resources(None,iam,None,receipt,self.job,"worker","timer",lambda *args,**kwargs:None)
        self.assertEqual(deleted,[{"RoleName":"worker"}])
        self.assertEqual(receipt["cleanup_errors"],[])


if __name__ == "__main__":
    unittest.main(verbosity=2)
