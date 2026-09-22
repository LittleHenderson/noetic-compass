"""Exercise the shipped full demo and its real imported library."""

from pathlib import Path

from api.notation.compiler import compile_file


def test_full_demo_compiles_with_its_shipped_module():
    demo = Path(__file__).resolve().parents[1] / "docs" / "CAS_FULL_DEMO_APP.cas"
    artifact = compile_file(str(demo))

    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["results"][0]["kind"] == "module"
    assert result["final_result"]["kind"] == "relation"
    assert result["final_result"]["domain_descent_ok"] is True
    bindings = {
        row["name"]: row["value"]
        for row in result["results"]
        if row["kind"] == "binding"
    }
    assert bindings["motif"]["sequence"] == [2, 3, 4]
    assert bindings["library_chain"]["sequence"] == [2, 4]
