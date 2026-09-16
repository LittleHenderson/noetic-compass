"""Unpacked, committed-source, non-neural perspective package rehearsal."""
from __future__ import annotations
import ast
import importlib.abc
import json
from hashlib import sha256
from pathlib import Path
import socket
import sys
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
DEST=HERE/"extracted"
FORBIDDEN={"torch","boto3","botocore","cas_cjt","casformer","requests","httpx","urllib3"}
attempts=[]

class DenyModelsAndProviders(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            attempts.append(fullname)
            raise AssertionError("FORBIDDEN_MODEL_OR_PROVIDER_IMPORT:"+fullname)
        return None


def blocked_network(*args,**kwargs):
    raise AssertionError("NETWORK_FORBIDDEN_IN_PACKAGE_REHEARSAL")


def hash_file(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    receipt=json.loads((HERE/"receipt.json").read_bytes())
    archive=HERE/"source.zip"
    assert hash_file(archive)==receipt["archive_sha256"]
    manifest=receipt["manifest"]
    assert manifest["source_sha"]=="12f25d301a0dfe9671929fa25b87bf580e71a177"
    assert receipt["status"]=="SOURCE_ONLY_NO_LAUNCH"
    assert not DEST.exists(), "Extraction target must be fresh"
    DEST.mkdir()
    with ZipFile(archive) as package:
        expected=set(manifest["members"])|{manifest["root_manifest"]}
        assert set(package.namelist())==expected
        for name in package.namelist():
            output=(DEST/name).resolve()
            assert output.is_relative_to(DEST.resolve()) and "\\" not in name
            raw=package.read(name)
            if name==manifest["root_manifest"]:
                assert sha256(raw).hexdigest()==receipt["manifest_sha256"]
            else:
                assert sha256(raw).hexdigest()==manifest["files_sha256"][name]
                assert len(raw)==manifest["files_bytes"][name]
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_bytes(raw)
    sys.meta_path.insert(0,DenyModelsAndProviders())
    socket.socket=blocked_network
    socket.create_connection=blocked_network
    pilot=DEST/"research/CAS_META_2_COMPOSITION"
    sys.path.insert(0,str(pilot))
    from cas_meta2 import perspective_resonance as p
    from cas_meta2 import perspective_worker as worker
    from cas_meta2.complementary_teaching import runner as parent
    assert Path(worker.__file__).resolve().is_relative_to(pilot.resolve())
    assert Path(parent.__file__).resolve().is_relative_to(pilot.resolve())
    config=json.loads((pilot/"records/perspective_resonance_001/prepared/unsigned_worker_config.json").read_bytes())
    assert config["execution_enabled"] is False
    bindings=worker.validate_config(dict(config,execution_enabled=True),pilot)
    parent_config=dict(config,execution_enabled=True,candidate="CAS_COMPLEMENTARY_TEACHING_001")
    data=parent.validate_config(parent_config,pilot)
    panels=p.perspective_panels(data["panels"])
    assert {name:len(rows) for name,rows in panels.items()}=={
        "perspective_canonical":90,"perspective_cross_view":90,"perspective_changed_relation":30}
    targets=p.perspective_target_manifest(panels)
    assert len(targets["teacher_targets"])==210 and len(targets["comparisons"])==120
    for condition in p.CONDITIONS:
        callback=worker.transform_factory(condition)
        task=panels["perspective_canonical"][0]
        changed=callback(task,round_index=3,slot_index=0,condition="ALT_COMPONENT_WHOLE")
        assert changed["correct"]==task["correct"]
        assert changed["encoded_options"]==task["encoded_options"]
        assert (changed["public"]!=task["public"])==(condition=="CONNECTED_PERSPECTIVES")
    disabled=False
    try:
        worker.run(config,results=DEST/"unused_results",artifacts=DEST/"unused_artifacts",root=DEST)
    except ValueError as error:
        assert str(error)=="PERSPECTIVE_EXECUTION_DISABLED"
        disabled=True
    assert disabled
    assert not (DEST/"unused_results").exists() and not (DEST/"unused_artifacts").exists()
    worker_text=(DEST/manifest["worker_script"]).read_text()
    ast.parse(worker_text)
    assert "from cas_meta2 import perspective_worker as runner" in worker_text
    assert "timeout=3000" in worker_text
    assert "cas.perspective-result/0.1" in worker_text
    assert "cas.perspective-failure/0.1" in worker_text
    assert not attempts and not FORBIDDEN.intersection(sys.modules)
    proof={"status":"PERSPECTIVE_COMMITTED_PACKAGE_REHEARSAL_PASS",
        "ready_label":"PERSPECTIVE_RESONANCE_READY_NEURAL_UNTESTED",
        "source_sha":receipt["source_sha"],"archive_sha256":receipt["archive_sha256"],
        "manifest_sha256":receipt["manifest_sha256"],"archive_bytes":archive.stat().st_size,
        "archive_members_checked":len(expected),"runtime_source_config_hashes_validated":True,
        "parent_data_sha256":bindings["parent_data_sha256"],
        "native_flow_binding_status":p.NATIVE_STATUS,
        "empirical_response_profile_status":p.EMPIRICAL_STATUS,
        "adaptive_policy_status":"SHADOW_ONLY_DISABLED",
        "disabled_dispatch_rejected_before_runtime":True,
        "additional_panel_rows":210,"semantic_comparisons":120,
        "actual_model_runs":0,"provider_calls":0,"forbidden_import_attempts":attempts,
        "network_disabled":True,"extract_path":str(DEST),"extracted_scratch_gitignored":True}
    (HERE/"rehearsal_proof.json").write_bytes((json.dumps(proof,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps(proof,sort_keys=True))


if __name__=="__main__":
    main()
