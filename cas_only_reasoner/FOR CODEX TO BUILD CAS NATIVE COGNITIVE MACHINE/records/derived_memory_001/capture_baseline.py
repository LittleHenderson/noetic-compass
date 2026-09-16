"""Retain accepted sources and negative evidence before derived-memory work."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json
from cncm.native_profile import load_native_profile
from cncm.nested_profile import load_nested_profile
from cncm.semantic_profile import load_semantic_profile
from cncm.compound_profile import load_compound_profile

def main():
    previous=json.loads((ROOT/"records/rpa_compound_001/acceptance_002/receipt.json").read_bytes())
    sources=previous["sources"]
    paths={r["path"]:r for r in sources}
    for row in json.loads((ROOT/"records/rpa_cube_001/acceptance_001/declared_inputs_before.json").read_bytes()):
        paths[row["path"]]=row
    for row in json.loads((ROOT/"records/rpa_cube_001/acceptance_001/actual_imports.json").read_bytes())["modules"]:
        paths[row["path"]]={k:row[k] for k in ("path","bytes","sha256")}
    for key in tuple(paths):
        raw=(ROOT/key).read_bytes()
        assert len(raw)==paths[key]["bytes"] and hashlib.sha256(raw).hexdigest()==paths[key]["sha256"],key
    negative=[]
    roots=[ROOT/"research/CAS_META_2_COMPOSITION/records/recurrent_cjt_001",
           ROOT/"research/CAS_META_2_COMPOSITION/records/rdcjt_handoff_20260916"]
    for folder in roots:
        for path in folder.rglob("*"):
            if path.is_file():
                raw=path.read_bytes()
                negative.append({"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),
                    "sha256":hashlib.sha256(raw).hexdigest()})
    profiles={name:loader().profile_digest for name,loader in (
        ("native0.2",load_native_profile),("nested0.3",load_nested_profile),
        ("semantic0.4",load_semantic_profile),("compound0.5",load_compound_profile))}
    body={"schema_version":"cncm.derived-memory-preservation/0.1",
          "previous_commit":"ffc710c018866d2a5a1e18e28472f869a654e754",
          "accepted_sources":sorted(paths.values(),key=lambda x:x["path"]),
          "profiles":profiles,"preserved_negative_records":sorted(negative,key=lambda x:x["path"])}
    target=Path(__file__).with_name("source_baseline.json")
    with target.open("x",encoding="utf-8",newline="\n") as out:out.write(canonical_json(body)+"\n")
    print(json.dumps({"sources":len(paths),"negative_files":len(negative),"profiles":profiles,
                     "sha256":hashlib.sha256(target.read_bytes()).hexdigest()}))
if __name__=="__main__":main()
