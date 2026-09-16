"""Record frozen native profiles; imports only symbolic profile readers."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cncm.native_profile import load_native_profile
from cncm.nested_profile import load_nested_profile
from cncm.semantic_profile import load_semantic_profile
from cncm.compound_profile import load_compound_profile
from cncm.derived_profile import load_derived_profile

expected = {
"native0.2": "c37aeb1e5cf3813585b2940037e6bc3793bf99dcf968026c0e38394a5886d607",
"nested0.3": "49f6c321472c6223b42a39ea21e402d2018ce5bd747acfd9266dc638aaf5be38",
"semantic0.4": "6a27f94656b45a4c4732d1a185844517f382390d6e3d1ce4259b63861badcecf",
"compound0.5": "3a7c6f620782ce820145d5e119d8f64c2050008378a9fbfdf94adbd1a9dcfed5",
"derived0.6": "1c1427a6b6b63424df578b437a73866823fe6ab21107916aebc62ba33f82bf64"}
observed = {name: fn().profile_digest for name,fn in (
("native0.2",load_native_profile),("nested0.3",load_nested_profile),
("semantic0.4",load_semantic_profile),("compound0.5",load_compound_profile),
("derived0.6",load_derived_profile))}
if observed != expected:raise RuntimeError("FROZEN_PROFILE_CHANGED")
path = Path(__file__).with_name("profile_preservation.json")
with path.open("x",encoding="utf-8",newline="\n") as stream:
    json.dump({"status":"FIVE_FROZEN_PROFILES_UNCHANGED","profiles":observed,
               "helper_sha256":sha256(Path(__file__).read_bytes()).hexdigest()},
              stream,sort_keys=True,separators=(",",":"));stream.write("\n")
print(json.dumps({"status":"PASS","sha256":sha256(path.read_bytes()).hexdigest()}))
