"""Worker/teacher boundary and exact pre-refactor preparation identities."""
import ast
from hashlib import sha256
import json
from pathlib import Path

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle import data, lesson_contract


def payload_sha(value):
    return sha256((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()).hexdigest()


def test_worker_contract_has_no_generator_or_teacher_dependency():
    source = Path(lesson_contract.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add("." * node.level + node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"__import__", "eval", "exec", "compile", "open"}
    assert imports == {"__future__", "copy", "re", "..codec", "..features_v2"}
    for name in ("build_dataset", "validate_dataset", "random", "seed", "SPLIT_COUNTS",
                 "NEW_TAGS", "NEW_CONTEXTS", "EVALUATION_TARGETS"):
        assert not hasattr(lesson_contract, name)
    assert "20260908" not in source


def test_preparation_api_reexports_worker_contract():
    for name in ("SCHEMA", "STAGES", "TeachingDataError", "recover_binding", "make_public",
                 "make_cycle", "validate_cycle", "fit_tokenizer"):
        assert getattr(data, name) is getattr(lesson_contract, name)


def test_frozen_dataset_and_every_training_view_remain_identical():
    # Established from the original data.py at commit 2a4791d6d0fddd04b23882248c679c03e0fbe92f.
    dataset = data.build_dataset()
    assert canonical_sha256(dataset) == "8ea6e0c333a9dee5067e4bbc134c01bfe85352184046fb3b788a77152ec601f3"
    variants = [data.make_cycle(case, assistance, curriculum)
                for curriculum in ("aligned", "ordinary")
                for assistance in ("full", "faded", "none")
                for case in dataset["splits"]["train"]]
    assert len(variants) == 1536
    assert canonical_sha256(variants) == "7491dfed60ff64c04cf0485ddf190a589125013038dbfd3ca22c3b8d27ff3ae3"
    assert payload_sha(data.make_cycle(dataset["splits"]["train"][0])) == \
        "e76e8a0f11c23415067a7fe89f31ca64ff5fb8e6541bbc08c8940408cc95c0c6"


def test_all_prepared_split_artifact_bytes_remain_identical():
    dataset = data.build_dataset()
    assert payload_sha(dataset["splits"]["train"]) == "e51015ba0ee3ac05ed8526f51a468d48641d5df4f0c33c3a96f989d04ebb54c5"
    assert payload_sha(dataset["splits"]["development"]) == "f12851d848f10b69abc8db73b380ec002972ba2dbc651acb2e08924fb34efd16"
    public_hashes = {
        "test_fresh": "557ffa0a0f08c597cb47d12d3987ab2a13182daec36bdf7213a0ccf394de6901",
        "test_context": "80fb7b3be89a16bb37fb2c9eccb6eb0b36751ad5e41dd1104f35233ce959957b",
        "test_names": "f8bb87bb4be47c13a9eb654365dfda5f567e0fa5b7a7969c12606d40625e4c57",
    }
    private_hashes = {
        "test_fresh": "a81c76b08c96449fff3dabc9b20f3adb8d46cefe316a90176afa9885b5e7619e",
        "test_context": "0d35e022903e9a30ca86effe803665685609b743a4c169cbc4e5f1de1051b3ef",
        "test_names": "c5fb91833585c6fca28265ec2001f8c2484b171b5a97c9ea29327402cf5e7333",
    }
    for split in public_hashes:
        cases = dataset["splits"][split]
        assert payload_sha([data.make_public(case) for case in cases]) == public_hashes[split]
        targets = [{"family_id": case["family_id"], "binding": case["target_binding"],
                    "selected_values": next(row["values"] for row in case["observations"]
                                            if row["slot"] == case["target_binding"])} for case in cases]
        assert payload_sha(targets) == private_hashes[split]
