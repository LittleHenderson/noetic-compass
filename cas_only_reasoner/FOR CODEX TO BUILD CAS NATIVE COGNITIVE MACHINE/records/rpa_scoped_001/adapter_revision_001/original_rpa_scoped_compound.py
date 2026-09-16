"""Versioned read-only scoped navigation over declared compound structure.

Projection extends a validated display document. Runtime authority still comes
only from caller-anchored journal replay, never from a display or navigation hash.
"""
from dataclasses import dataclass, replace
import json
from .canonical import canonical_json, content_id, digest
from .model import ContractError
from .rpa_model import AtlasNode, AtlasLink, AtlasSnapshot, LinkType, NodeKind, NodeStatus
from .compound_program import CallStep
from .procedural_substrate import ProcedureArtifact
from .rpa_compound_adapter import compound_atlas_from_journal, record_body_from_catalog

SCHEMA="cncm.rpa-scoped-compound-view/0.1"
CURSOR_SCHEMA="cncm.rpa-scoped-path/0.1"
MAX_PATH=32

def require(condition,message):
    if not condition:raise ContractError(message)

def scoped_projection(source):
    from tools.render_compound_rpa_view import validate_document
    validate_document(source)
    atlas=AtlasSnapshot.from_dict(source["atlas"])
    nodes=atlas.node_map()
    links={row.link_id:row for row in atlas.links}
    catalog=source["native"]["evidence_catalog"]
    def add(parent,label,fields,evidence,projection,identity):
        key=content_id("scope-part",identity)
        parent_node=nodes[parent]
        row=AtlasNode(key,key,label,parent_node.context,NodeStatus.OBSERVED,
            fields=tuple(sorted((k,v if type(v) is str else canonical_json(v)) for k,v in fields.items())),
            kind=NodeKind.EVIDENCE,evidence_refs=tuple(sorted(set(evidence))))
        require(key not in nodes or nodes[key]==row,"scoped node collision")
        nodes[key]=row
        edge=AtlasLink(content_id("scope-link",{"source":parent,"target":key,"projection":projection}),
            parent,key,LinkType.CONTAINS_PART,projection=projection,evidence_refs=row.evidence_refs)
        links[edge.link_id]=edge
        return key
    for edge in atlas.links:
        if edge.relation is not LinkType.CONTAINS_PART or not edge.projection.startswith("program call step:"):
            continue
        parent,step=nodes[edge.source_id],nodes[edge.target_id]
        fields=dict(step.fields)
        typed=CallStep.from_dict({k:fields[k] for k in ("a_ref","b_ref","c_ref")})
        program_digest=dict(parent.fields)["program_digest"]
        for port,slot in typed.to_dict().items():
            add(step.node_id,port+" ← "+slot,{"port":port,"source_slot":slot,
                "binding_kind":"EARLIER_CALL_RESULT" if slot=="r0" else "ORIGINAL_INPUT",
                "meaning":"Declared symbolic binding; display navigation does not execute this call."},
                (program_digest,), "declared call input binding:"+port,
                {"program":program_digest,"step":step.node_id,"port":port})
    for node in tuple(atlas.nodes):
        fields=dict(node.fields)
        if not node.node_id.startswith("primitive-") or "artifact" not in fields:
            continue
        artifact=ProcedureArtifact.from_dict(json.loads(fields["artifact"]))
        for index,instruction in enumerate(artifact.to_dict()["program"]):
            add(node.node_id,"Instruction "+str(index),{"index":index,"instruction":instruction,
                "meaning":"Declared instruction in the retained artifact; not a new execution."},
                (artifact.artifact_sha256,),"declared primitive instruction:"+str(index),
                {"primitive":artifact.artifact_sha256,"instruction":index})
    # Execution/qualification evidence is a part of the inspected evidence
    # bundle, not a causal child of the program. Preserve that exact meaning.
    for row in catalog["records"]:
        body=record_body_from_catalog(catalog,row["record_digest"])
        program_digest=body.get("artifact_sha256")
        parent="program-"+str(program_digest)
        if parent not in nodes or row["kind"] not in {"EXECUTION","QUALIFICATION","INSTALLATION"}:
            continue
        target="record-"+row["record_digest"]
        if target not in nodes:continue
        edge=AtlasLink(content_id("scope-link",{"source":parent,"record":row["record_digest"]}),
            parent,target,LinkType.CONTAINS_PART,projection="retained evidence bundle record for exact program",
            evidence_refs=(row["record_digest"],))
        links[edge.link_id]=edge
    expanded=replace(atlas,nodes=tuple(nodes.values()),links=tuple(links.values()))
    body={"schema_version":SCHEMA,"source_document_digest":digest(source),"source":source,
          "atlas":expanded.to_dict(),"current_state_hash":source["native"]["current_state_hash"],
          "boundary":"Declared structure and retained evidence only; navigation has zero runtime authority.",
          "geometry":{"profile40_assigned":sum(n.profile40 is not None for n in expanded.nodes),
                      "overlap_certificates":len(expanded.overlap_certificates),
                      "measured_geometry":False}}
    return {**body,"document_digest":digest(body)}

def scoped_from_journal(journal,**authority):
    return scoped_projection(compound_atlas_from_journal(journal,**authority))

def validate_scoped(document):
    require(type(document) is dict and type(document.get("source")) is dict,"scoped document required")
    expected=scoped_projection(document["source"])
    require(canonical_json(expected)==canonical_json(document),"scoped projection does not reconstruct")
    return AtlasSnapshot.from_dict(expected["atlas"])

@dataclass(frozen=True,slots=True)
class ScopePath:
    snapshot_digest:str
    path:tuple[str,...]
    def __post_init__(self):
        require(type(self.snapshot_digest) is str and len(self.snapshot_digest)==64
                and all(c in "0123456789abcdef" for c in self.snapshot_digest),"snapshot digest required")
        require(type(self.path) is tuple and 1<=len(self.path)<=MAX_PATH
                and all(type(v) is str for v in self.path) and len(set(self.path))==len(self.path),
                "scope path must be bounded and acyclic")
    def to_dict(self):
        return {"schema_version":CURSOR_SCHEMA,"snapshot_digest":self.snapshot_digest,"path":list(self.path)}

def start_scope(atlas):
    require(type(atlas) is AtlasSnapshot,"typed atlas required")
    return ScopePath(digest(atlas.to_dict()),(atlas.current_state_id,))

def children(atlas,node_id):
    require(node_id in atlas.node_map(),"unknown scope")
    return tuple(sorted({edge.target_id for edge in atlas.links
                         if edge.source_id==node_id and edge.relation is LinkType.CONTAINS_PART}))

def check_path(atlas,cursor):
    require(type(atlas) is AtlasSnapshot and type(cursor) is ScopePath,"typed navigation inputs required")
    require(cursor.snapshot_digest==digest(atlas.to_dict()),"navigation snapshot changed")
    require(cursor.path[0]==atlas.current_state_id,"scope root must be the loaded current state")
    for left,right in zip(cursor.path,cursor.path[1:]):
        require(right in children(atlas,left),"breadcrumb does not follow declared containment")
        require(children(atlas,right),"leaf has no declared interior in this snapshot")
    return cursor

def enter_scope(atlas,cursor,node_id):
    check_path(atlas,cursor)
    require(node_id in children(atlas,cursor.path[-1]),"entry requires a direct declared child")
    require(children(atlas,node_id),"no declared internal structure in this snapshot")
    return check_path(atlas,ScopePath(cursor.snapshot_digest,cursor.path+(node_id,)))

def return_scope(atlas,cursor,index):
    check_path(atlas,cursor)
    require(type(index) is int and 0<=index<len(cursor.path),"breadcrumb index invalid")
    return check_path(atlas,ScopePath(cursor.snapshot_digest,cursor.path[:index+1]))

def local_scope(atlas,cursor):
    check_path(atlas,cursor)
    root=cursor.path[-1]
    ids=(root,*children(atlas,root))
    return {"scope_id":root,"breadcrumb":list(cursor.path),"current_state_id":atlas.current_state_id,
            "snapshot_digest":cursor.snapshot_digest,
            "nodes":[atlas.node_map()[key].to_dict() for key in ids],
            "links":[edge.to_dict() for edge in atlas.links
                     if edge.source_id==root and edge.target_id in ids and edge.relation is LinkType.CONTAINS_PART],
            "authority":"INSPECTION_ONLY"}
