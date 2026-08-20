import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_json_schemas_are_valid_draft_2020_12():
    schemas = sorted((ROOT / "schemas").glob("*.json"))
    assert len(schemas) == 10
    payloads = []
    for path in schemas:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["type"] == "object"
        payloads.append(payload)
    try:
        import jsonschema
    except ImportError:
        return
    for payload in payloads:
        jsonschema.Draft202012Validator.check_schema(payload)


def test_runner_and_core_have_no_network_transport_imports():
    forbidden = {"openai", "requests", "httpx", "aiohttp", "boto3", "socket"}
    for name in ("core.py", "board_change_v2.py"):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & forbidden), f"{name} imports network transport: {imported & forbidden}"
