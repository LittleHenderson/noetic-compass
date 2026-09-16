"""Pure conformance only: authored/simulated rows; no model or torch execution."""
import copy
import json
from pathlib import Path
import pytest

from cas_meta2 import perspective_resonance as p

SOURCE = Path(__file__).resolve().parents[1] / "records/perspective_resonance_001/source"


def fixture():
    family = json.loads((SOURCE / "Perspective_Family_Authoring_Example.json").read_text())
    rows = [json.loads(line) for line in (SOURCE / "public_exercises.jsonl").read_text().splitlines()]
    targets = [json.loads(line) for line in (SOURCE / "teacher_targets.jsonl").read_text().splitlines()]
    return family, rows, targets


def compiled():
    return p.compile_family(*fixture())


def task():
    return {"record_id": "base-public-id", "correct": "via:B", "encoded_correct_index": 1,
            "encoded_options": ["direct", "via:B", "absent"], "family_id": "root1",
            "public": {"problem": "node A kind=idea\nnode B kind=idea\nnode C kind=idea\n"
                        "rel A contains B common=constituent,B\nrel B contains C common=constituent,C\n"
                        "Question: C relative to A",
                       "observations": [{"slot": i, "tag": value, "values": [0.0]*8}
                                        for i, value in enumerate(["direct", "via:B", "absent"])]}}


def test_authored_golden_compiles_to_real_codec_without_teacher_input():
    from cas_meta2.codec import validate_public
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    result = compiled()
    assert result["status"] == "AUTHORED_REFERENCE_ONLY"
    assert result["manifest"]["rows"] == 12
    publics = [row["public"] for row in result["public"]]
    tokenizer = LosslessPublicTokenizer.fit_train(publics, max_length=1024)
    for public in publics:
        validate_public(public)
        assert tokenizer.encode_public(public)
    assert len(result["comparisons"]) == 10


def test_directed_mapping_rejects_reversal_and_incomplete_mapping():
    family, _, _ = fixture()
    view = family["views"][0]
    view["graph"]["contains"][0].reverse()
    with pytest.raises(ValueError, match="DIRECTED_RELATION"):
        p.validate_family(family)
    family, _, _ = fixture()
    family["views"][0]["base_to_view_map"].pop("Kit")
    with pytest.raises(ValueError, match="INCOMPLETE"):
        p.validate_family(family)


def test_rewiring_must_be_exact_declared_change():
    family, _, _ = fixture()
    view = next(v for v in family["views"] if not v["preserves_scoped_relation"])
    view["graph"]["contains"] = family["base_graph"]["contains"]
    with pytest.raises(ValueError, match="REWIRING"):
        p.validate_family(family)


def test_incomplete_source_cannot_be_scored_absent():
    _, rows, _ = fixture()
    rows[0]["graph"]["inventory_complete"] = False
    with pytest.raises(ValueError, match="UNKNOWN_IS_NOT_ABSENT"):
        p.reference_answer(rows[0])


def test_private_target_change_does_not_select_public_context_or_id():
    a = task()
    b = copy.deepcopy(a)
    b["correct"], b["encoded_correct_index"] = "absent", 2
    for round_index in range(16):
        left = p.transform_public(a, round_index=round_index, slot_index=4,
                                  condition="CONNECTED_PERSPECTIVES")
        right = p.transform_public(b, round_index=round_index, slot_index=4,
                                   condition="CONNECTED_PERSPECTIVES")
        assert left["public"] == right["public"] and left["record_id"] == right["record_id"]
        assert left["encoded_options"] == right["encoded_options"]
    assert a == task()


def test_canonical_and_maintenance_are_byte_identical_and_targets_preserved():
    original = task()
    for condition, slot in (("CANONICAL_REVISIT", 0), ("CONNECTED_PERSPECTIVES", 64)):
        assert p.transform_public(original, round_index=1, slot_index=slot,
                                  condition=condition) == original
    for index in range(5):
        changed = p.transform_public(original, round_index=index, slot_index=0,
                                     condition="CONNECTED_PERSPECTIVES")
        for field in ("correct", "encoded_correct_index", "encoded_options", "family_id"):
            assert changed[field] == original[field]
        assert changed["public"]["observations"] == original["public"]["observations"]
        assert changed["public"]["problem"].endswith(original["public"]["problem"])
    assert len({p.transform_public(original, round_index=i, slot_index=0,
                condition="CONNECTED_PERSPECTIVES")["record_id"] for i in range(5)}) == 5


def test_semantic_equivariance_and_option_slots_are_not_answers():
    assert p.semantic_answer("via:Folder2", {"Toolbox": "Folder2"}) == "via:Toolbox"
    assert p.semantic_answer(["X", "Y"], {"Toolbox": "Y", "Cloth": "X"}) == ["Cloth", "Toolbox"]
    with pytest.raises(ValueError, match="UNSUPPORTED_SEMANTIC"):
        p.semantic_answer(1, {"Toolbox": "Y"})


def test_missing_native_tap_is_not_inferred_from_scores():
    snapshot = p.native_flow_snapshot(checkpoint_identity="abc", depth=8)
    assert snapshot["status"] == "UNAVAILABLE_NO_NATIVE_FLOW_TAP"
    assert snapshot["raw_current"] is None and snapshot["normalized_allocation"] is None
    assert snapshot["architecture_modified"] is False


def test_report_restore_keeps_missing_denominator_and_rejects_tampering():
    bundle = compiled()
    rows = [{"record_id": t["record_id"], "selected": t["expected_answer"],
             "provenance": "SIMULATED_CHECKER_ANSWERS_NOT_MODEL_OUTPUT"}
            for t in bundle["teacher_targets"][:-1]]
    sealed = p.seal_predictions(rows)
    report = p.behavioral_report(sealed, bundle["teacher_targets"], bundle["comparisons"])
    assert (report["assigned"], report["observed"], report["correct"], report["missing"]) == (12,11,11,1)
    restored = p.behavioral_report(json.loads(json.dumps(sealed)), bundle["teacher_targets"], bundle["comparisons"])
    assert report == restored
    sealed["rows"][0]["selected"] = "absent"
    with pytest.raises(ValueError, match="SEAL_MISMATCH"):
        p.behavioral_report(sealed, bundle["teacher_targets"], bundle["comparisons"])


def test_confident_common_wrong_answers_are_not_competence():
    bundle = compiled()
    targets = [t for t in bundle["teacher_targets"] if t["operation"] == "REACHED_VIA"]
    pairs = [x for x in bundle["comparisons"] if x["left"] in {t["record_id"] for t in targets}]
    rows = [{"record_id": t["record_id"], "selected": "absent", "confidence": .999,
             "provenance": "SIMULATED"} for t in targets]
    report = p.behavioral_report(p.seal_predictions(rows), targets, pairs)
    assert report["pairs"]["invariant"]["agreement"] > 0
    assert report["pairs"]["invariant"]["both_correct"] == 0
    assert report["pairs"]["changed_relation"]["both_correct"] == 0


def profile():
    return {"model_identity":"weights1", "runtime_identity":"runtime1", "input_adapter_identity":"input1",
        "tokenizer_identity":"tokens1", "test_point":"final_hidden", "direction_identity":"frozen_u",
        "intervention_port":"PROPOSED_NOT_BOUND", "depth":8, "dose_grid":[0.,1.,2.],
        "calibration_families":["cal1","cal2"], "calibration_holdout_families":["hold1","hold2"],
        "final_audit_families":["final1"], "units":{"a":"alpha","delta_y":"activation","r_eff":"alpha_per_activation"},
        "max_holdout_rmse":.1, "minimum_positive_slope":.001,
        "uncertainty_method":"ROOT_FAMILY_BOOTSTRAP_2000"}


def response_rows(pr, slope):
    return [{"profile_sha256":p.identity(pr),"root_family_id":f,"a":a,"delta_y":slope*a,
             "provenance":"SIMULATED_NOT_INSTRUMENTED"}
            for f in pr["calibration_families"]+pr["calibration_holdout_families"] for a in pr["dose_grid"]]


def test_calibration_positive_local_fit_is_separate_and_negative_fit_is_rejected():
    pr = profile()
    fitted = p.fit_response(pr, response_rows(pr, 2.))
    assert fitted["r_eff"] == .5 and fitted["holdout_rmse"] == 0
    assert fitted["native_flow_equivalence"] is False and fitted["semantic_mastery_claimed"] is False
    rejected = p.fit_response(pr, response_rows(pr,-2.))
    assert rejected["r_eff"] is None and rejected["status"] == "FIT_REJECTED"


def test_calibration_split_units_profile_grid_and_holdout_fail_closed():
    pr = profile()
    pr["calibration_holdout_families"] = ["cal1"]
    with pytest.raises(ValueError,match="SPLITS"):
        p.validate_response_profile(pr)
    pr = profile()
    pr["units"]["a"] = "volts"
    with pytest.raises(ValueError,match="UNITS"):
        p.validate_response_profile(pr)
    pr = profile()
    rows = response_rows(pr,2.)
    rows[0]["profile_sha256"] = "other"
    with pytest.raises(ValueError,match="PROFILE_MISMATCH"):
        p.fit_response(pr,rows)
    rows = response_rows(pr,2.)
    with pytest.raises(ValueError,match="INCOMPLETE_CALIBRATION"):
        p.fit_response(pr,rows[:-1])
    for row in rows:
        if row["root_family_id"].startswith("hold"):
            row["delta_y"] *= 3
    assert p.fit_response(pr,rows)["r_eff"] is None


def test_calibration_does_not_create_a_steering_port():
    with pytest.raises(ValueError,match="NOT_AUTHORIZED"):
        p.calibrated_response_request(profile())
    with pytest.raises(ValueError,match="UNAVAILABLE_NO_APPROVED_INTERVENTION_PORT"):
        p.calibrated_response_request(profile(),execution_authorized=True)


def test_shadow_policy_cannot_select_using_final_audit():
    report = {"deficits": ["mapping"]}
    proposal = p.shadow_proposal(report,evidence_scope="development")
    assert all(proposal[key] is False for key in ("adaptive_policy_enabled",
            "direct_control_mutation","automatic_pass_increase"))
    with pytest.raises(ValueError,match="FINAL_AUDIT"):
        p.shadow_proposal(report,evidence_scope="final_audit")


def test_simulated_scaling_and_collapsed_vectors_are_not_new_distinctions():
    currents, scaled = [1.,2.,1.], [3.,6.,3.]
    assert sum(scaled) > sum(currents)
    assert [x/sum(currents) for x in currents] == [x/sum(scaled) for x in scaled]
    vectors = [[1.,1.],[1.,1.]]
    assert vectors[0] == vectors[1]  # a descriptive counterexample, not a training objective
    assert task()["encoded_options"][0] != task()["encoded_options"][1]


def test_root_family_interval_uses_full_assigned_denominator():
    a = {"per_root_family":{"r1":{"assigned":4,"correct":1},"r2":{"assigned":4,"correct":2}}}
    b = {"per_root_family":{"r1":{"assigned":4,"correct":3},"r2":{"assigned":4,"correct":1}}}
    result = p.paired_root_effect(a,b)
    assert result["effect"] == .125 and result["root_families"] == 2


def test_idea_profile_keeps_behavior_response_native_and_rhythm_separate():
    bundle=compiled()
    sealed=p.seal_predictions([])
    context={key:"source-bound" for key in ("root_family_id","graph_revision","cube_revision","view_revision",
        "model_identity","checkpoint_identity","input_adapter_identity","tokenizer_identity",
        "recurrent_profile","scoring_profile","assistance_profile","source_event_references")}
    context["depth"]=8
    profile=p.idea_response_profile(context=context,sealed_predictions=sealed)
    assert profile["type"]=="IdeaResponseProfile"
    assert profile["native_flow"]["status"]==p.NATIVE_STATUS
    assert profile["behavioral_competence"]["status"]=="UNASSESSED"
    assert profile["single_resonance_score"] is None
    assert profile["adaptive_policy_enabled"] is False


def test_curved_response_does_not_license_constant_positive_resistance():
    pr=profile()
    rows=response_rows(pr,1.)
    for row in rows:
        row["delta_y"]=row["a"]**2
    report=p.fit_response(pr,rows)
    assert report["r_eff"] is None
    assert "MEANINGFUL_NONLINEARITY" in report["failures"]


def test_observer_rejects_teacher_fields_before_prediction_seal():
    with pytest.raises(ValueError,match="PRIVATE_TARGET"):
        p.seal_predictions([{"record_id":"a","nested":{"correct":"direct"}}])


def test_pure_modules_do_not_import_torch_or_provider_sdk():
    import ast
    tree=ast.parse(Path(p.__file__).read_text())
    imported=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    imported += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert not any(name and name.split(".")[0] in {"torch","boto3","cas_cjt","casformer"} for name in imported)


def test_real_arrow_renderer_is_transformed_and_only_query_graph_is_repeated():
    original=task()
    original["public"]["problem"]=original["public"]["problem"].replace(" contains "," --contains--> ")
    changed=p.transform_public(original,round_index=1,slot_index=0,condition="CONNECTED_PERSPECTIVES")
    assert "place B in A" in changed["public"]["problem"]
    original["public"]["problem"]="node X kind=idea\nnode Y kind=idea\nrel X --contains--> Y\nSupport ends.\n"+original["public"]["problem"]
    changed=p.transform_public(original,round_index=1,slot_index=0,condition="CONNECTED_PERSPECTIVES")
    prefix=changed["public"]["problem"].split("\n")[0]
    assert "place B in A" in prefix and "place Y in X" not in prefix


def test_fresh_panel_content_and_changed_relations_are_real_compiled_tasks():
    manifest=SOURCE.parents[1]/"complementary_teaching_001/preparation_20260916/data_manifest.json"
    parent=json.loads(manifest.read_text())
    panels=p.perspective_panels(parent["panels"])
    assert {key:len(rows) for key,rows in panels.items()}=={
        "perspective_canonical":90,"perspective_cross_view":90,"perspective_changed_relation":30}
    base={t["record_id"]:t for t in panels["perspective_canonical"]}
    for t in panels["perspective_cross_view"]:
        source=base[t["canonical_record_id"]]
        assert source["correct"]==t["correct"] and source["encoded_options"]==t["encoded_options"]
        assert source["public"]!=t["public"]
    for t in panels["perspective_changed_relation"]:
        source=base[t["canonical_record_id"]]
        assert source["correct"]!=t["correct"] and source["family_id"]==t["family_id"]
        assert source["encoded_options"]==t["encoded_options"]
    targets=p.perspective_target_manifest(panels)
    assert len(targets["teacher_targets"])==210 and len(targets["comparisons"])==120


def test_perspective_worker_disabled_by_default_before_any_model_import(tmp_path):
    from cas_meta2 import perspective_worker as w
    with pytest.raises(ValueError,match="PERSPECTIVE_OPT_IN"):
        w.validate_config({},tmp_path)
    with pytest.raises(ValueError,match="EXECUTION_DISABLED"):
        w.validate_config({"candidate":p.DIRECTIVE},tmp_path)


def test_worker_restores_real_panel_shape_only_after_parent_seal():
    from cas_meta2 import perspective_worker as w
    manifest=SOURCE.parents[1]/"complementary_teaching_001/preparation_20260916/data_manifest.json"
    panels=p.perspective_panels(json.loads(manifest.read_text())["panels"])
    predictions={name:[{"record_id":t["record_id"],"family_id":t["family_id"],"op":t["op"],
                       "prediction":t["correct"],"scores":[0.,0.,0.],
                       "provenance":"SIMULATED_TEST_ONLY"} for t in tasks]
                 for name,tasks in panels.items()}
    seal=p.identity(predictions)
    for name,rows in predictions.items():
        for row,t in zip(rows,panels[name]):
            row.update({"expected":t["correct"],"correct":True})
    parent={"status":"COMPLEMENTARY_MEASURED","courses":[
        {"condition":condition,"seed":seed,"reload_equal":True,
         "final":{"rows":copy.deepcopy(predictions),"prediction_seal_sha256":seal,
                  "weight_identity":"SIMULATED_WEIGHTS","depth":8}}
        for seed in (101,202,303) for condition in p.CONDITIONS]}
    report=w.restore_reports(parent,panels)
    assert len(report["courses"])==6 and len(report["paired_effects"])==3
    assert all(row["behavioral"]["correct"]==210 for row in report["courses"])
    assert all(row["cross_view"]["effect"]==0 for row in report["paired_effects"])
    parent["courses"][0]["final"]["rows"]["perspective_canonical"][0]["prediction"]="absent"
    with pytest.raises(ValueError,match="PARENT_PREDICTION_SEAL"):
        w.restore_reports(parent,panels)


def test_worker_preserves_parent_budget_failure_and_declares_failure_artifacts(tmp_path,monkeypatch):
    from cas_meta2 import perspective_worker as w
    from cas_meta2.complementary_teaching import runner as parent
    monkeypatch.setattr(w,"validate_config",lambda config,pilot:{"test":"SIMULATED"})
    def failed(config,*,results,artifacts,**kwargs):
        assert config["candidate"]=="CAS_COMPLEMENTARY_TEACHING_001"
        assert config["comparison_conditions"]==list(p.CONDITIONS)
        assert kwargs["panel_transform"] is p.perspective_panels
        parent.write_json(Path(artifacts)/"complementary_report.json",
                          {"status":"TEACHING_INCOMPLETE","courses":[]})
        raise ValueError("SIMULATED_BUDGET_CAP")
    monkeypatch.setattr(parent,"run",failed)
    with pytest.raises(ValueError,match="SIMULATED_BUDGET_CAP"):
        w.run({"candidate":p.DIRECTIVE,"job":"SIMULATED"},
              results=tmp_path/"results",artifacts=tmp_path/"artifacts")
    result=json.loads((tmp_path/"results/result.json").read_text())
    assert result["status"]=="TEACHING_INCOMPLETE"
    assert result["failure"]["message"]=="SIMULATED_BUDGET_CAP"
    assert "perspective_report.json" in {a["name"] for a in result["artifacts"]}


def test_worker_rejects_windows_only_package_paths_before_runtime(tmp_path):
    from cas_meta2 import perspective_worker as w
    row={"path":"cas_meta2\\perspective_resonance.py","bytes":1,"sha256":"0"*64}
    sources={"files":[row],"aggregate_sha256":p.identity([row])}
    for relative,value in ((w.SOURCES_PATH,sources),(w.BINDINGS_PATH,{})):
        path=tmp_path/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value))
    config={"candidate":p.DIRECTIVE,"execution_enabled":True,"training":True,"optimizer_updates":960,
            "perspective_sources_file_sha256":w.file_hash(tmp_path/w.SOURCES_PATH),
            "perspective_bindings_file_sha256":w.file_hash(tmp_path/w.BINDINGS_PATH)}
    with pytest.raises(ValueError,match="PORTABLE_PATH"):
        w.validate_config(config,tmp_path)


def test_real_packaged_dispatch_and_failure_schemas_are_perspective_specific():
    from aws import perspective_resonance_launch as launch
    text=launch.render_worker()
    assert "from cas_meta2 import perspective_worker as runner" in text
    assert "cas.recurrent-cjt-result/1" not in text
    assert "cas.perspective-result/0.1" in text and "cas.perspective-failure/0.1" in text
    files=launch.package_data_files()
    assert "research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py" in files
    assert any(path.endswith("cas_meta2/perspective_worker.py") for path in files)
    assert all("\\" not in path for path in files)
    evidence=launch.evidence_contract()
    assert evidence["required_count"]==125
    raw=json.dumps(evidence)
    assert "perspective_report.json" in raw and "CANONICAL_REVISIT_101" in raw
    assert "ALT_COMPONENT_WHOLE" not in raw
    assert "timeout=3000" in text and "timeout=MAX_WALL_SECONDS + 1800" not in text


@pytest.mark.parametrize("field,value",[
    ("training",False),("training",None),("optimizer_updates",160),
    ("optimizer_updates",None),("max_wall_seconds",1200),("max_wall_seconds",None),
    ("conditions",["CANONICAL_REVISIT"]),("conditions",None)])
def test_top_authority_budget_must_bind_real_training_before_provider(field,value):
    from aws import perspective_resonance_launch as launch
    authority={"schema":launch.AUTHORITY_SCHEMA,"candidate":p.DIRECTIVE,
        "reservation_usd":"7.00","training":True,"optimizer_updates":960,
        "max_wall_seconds":3000,"conditions":list(p.CONDITIONS)}
    if value is None:
        authority.pop(field)
    else:
        authority[field]=value
    class Provider:
        bound=False
        def bind_authority(self,authority):
            self.bound=True
            raise AssertionError("Provider must not be reached")
    provider=Provider()
    request={"schema":launch.REQUEST_SCHEMA,"launch_authorized":False,
        "job":"cas-meta2-perspective-20260916000000-deadbeef",
        "source_sha":"1"*40,"archive_sha256":"2"*64,"manifest_sha256":"3"*64}
    with pytest.raises(ValueError,match="AUTHORITY_TRAINING_BUDGET"):
        launch.execute(request,authority,provider)
    assert provider.bound is False


def test_package_inputs_do_not_discover_new_scratch_or_package_receipts(tmp_path,monkeypatch):
    from aws import perspective_resonance_launch as launch
    monkeypatch.setattr(launch,"ROOT",tmp_path)
    before=launch.package_data_files()
    for relative in ("package_later/receipt.json","scratch/report.json","rehearsal/outcome.xml"):
        path=tmp_path/"records/perspective_resonance_001"/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("{}")
    after=launch.package_data_files()
    assert after==before
    assert not any("/package_later/" in path or "/scratch/" in path or "/rehearsal/" in path for path in after)
    assert any(path.endswith("prepared/source_manifest.json") for path in after)
    assert any(path.endswith("source/teacher_targets.jsonl") for path in after)
