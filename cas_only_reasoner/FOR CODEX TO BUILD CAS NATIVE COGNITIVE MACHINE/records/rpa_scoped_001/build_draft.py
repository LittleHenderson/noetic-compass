"""Retain exact old-package observations and draft scoped pages without overwrites."""
from pathlib import Path
from hashlib import sha256
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from cncm.canonical import canonical_json
from cncm.rpa_scoped_compound import scoped_projection
from tools.render_scoped_rpa_view import render_scoped_rpa
def put(path,value):
    data=value.encode() if isinstance(value,str) else (canonical_json(value)+"\n").encode()
    with path.open("xb") as out:out.write(data)
def main():
    output=Path(__file__).parent/"development_001"
    output.mkdir(exist_ok=False)
    source=ROOT/"records/rpa_compound_001/acceptance_002"
    raw=(source/"receipt.json").read_bytes()
    assert sha256(raw).hexdigest()=="73bcedec7a2cdd3a761dcc55cef59049bf643645c1ad8dd810ea503fd264cd55"
    receipt=json.loads(raw)
    identities={row["path"]:row for row in receipt["files"]}
    summaries=[]
    for example in receipt["examples"]:
        name=example["name"]
        filename=name+".json"
        raw=(source/filename).read_bytes()
        expected=identities[filename]
        assert len(raw)==expected["bytes"] and sha256(raw).hexdigest()==expected["sha256"]
        original=json.loads(raw)
        document=scoped_projection(original)
        put(output/(name+".json"),document)
        put(output/(name+".html"),render_scoped_rpa(document))
        summaries.append({"name":name,"source":expected,
            "original_nodes":len(original["atlas"]["nodes"]),
            "original_profile40_assigned":sum(row["profile40"] is not None for row in original["atlas"]["nodes"]),
            "original_overlap_certificates":len(original["atlas"]["overlap_certificates"]),
            "scoped_nodes":len(document["atlas"]["nodes"]),
            "current_state_unchanged":document["atlas"]["current_state_id"]==original["atlas"]["current_state_id"],
            "source_unchanged":document["source"]==original,
            "document_digest":document["document_digest"]})
        print(name,flush=True)
    put(output/"baseline_review.json",{"status":"DRAFT_PROJECTED_NOT_BROWSER_ACCEPTED","examples":summaries,
        "boundary":"Exact accepted compound0.5 package only; geometry claims are not generalized to other packages."})
if __name__=="__main__":main()

