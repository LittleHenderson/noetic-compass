"""Versioned read-only scoped navigation over declared compound structure.

Projection extends a validated display document. Runtime authority still comes
only from caller-anchored journal replay, never from a display or navigation hash.
"""
from dataclasses import dataclass, replace
import json
from .canonical import canonical_json, content_id, digest
from .model import ContractError
from .rpa_model import AtlasNode, AtlasLink, AtlasSnapshot, LinkType, NodeKind, NodeStatus
from .compound_program import CallProgram
from .compound_model import CompoundCall
from .procedural_substrate import ProcedureArtifact
from .rpa_compound_adapter import compound_atlas_from_journal

SCHEMA="cncm.rpa-scoped-compound-view/0.1"
CURSOR_SCHEMA="cncm.rpa-scoped-path/0.1"
MAX_PATH=32

def require(condition,message):
    if not condition:raise ContractError(message)


def _declared_structure(source, atlas):
    """Join the complete displayed artifact structure to retained sealed records.

    The frozen display validator has already checked the catalog's record and
    report digests. Installed artifact bytes determine this finite structure;
    free-standing labels, node names and step fields cannot add declarations.
    This is consistency with retained bytes, not authentication or replay.
    """
    nodes = atlas.node_map()
    native = source['native']
    records = {row['record_digest']:row for row in native['evidence_catalog']['records']}
    programs, primitives = {}, {}

    def remember(mapping, key, artifact):
        require(key not in mapping or canonical_json(mapping[key].to_dict()) == canonical_json(artifact.to_dict()),
                'conflicting retained artifact bytes')
        mapping[key] = artifact

    for row in records.values():
        body = row['body']
        if row['kind'] == 'INSTALLATION':
            artifact = CallProgram.from_dict(body['artifact'])
            qualification = records.get(body['qualification_digest'])
            require(qualification is not None and qualification['kind'] == 'QUALIFICATION'
                    and qualification['body'].get('artifact_sha256') == artifact.program_digest
                    and qualification['body'].get('call_id') == body['call_id']
                    and qualification['body'].get('run_id') == body['run_id'],
                    'installed program lacks exact retained qualification join')
            remember(programs, artifact.program_digest, artifact)
        elif row['kind'] == 'PRIMITIVE_INSTALLATION':
            artifact = ProcedureArtifact.from_dict(body['artifact'])
            remember(primitives, artifact.artifact_sha256, artifact)
    active_program = native['current_program']
    if active_program is not None:
        artifact = CallProgram.from_dict(active_program)
        require(artifact.program_digest in programs
                and canonical_json(programs[artifact.program_digest].to_dict()) == canonical_json(active_program),
                'current program is not the retained installed artifact')
    require(native['dispatch']['compound_head'] is None or native['dispatch']['compound_head'] in programs,
            'active program head is absent from retained installations')
    require(native['dispatch']['primitive_head'] is None or native['dispatch']['primitive_head'] in primitives,
            'active primitive head is absent from retained installations')

    expected_nodes, expected_links = {}, {}
    context = nodes[atlas.current_state_id].context

    def expect_node(key, label, fields, *, kind=NodeKind.EVIDENCE, evidence=()):
        expected_nodes[key] = AtlasNode(key,key,label,context,NodeStatus.OBSERVED,
            fields=tuple(sorted((k,v if type(v) is str else canonical_json(v)) for k,v in fields.items())),
            kind=kind,evidence_refs=tuple(sorted(set(evidence))))

    def expect_link(source_id, target_id, projection, evidence=()):
        identity = {'source':source_id,'target':target_id,'relation':'contains_part','action':None}
        row = AtlasLink(content_id('rpa-link',identity),source_id,target_id,LinkType.CONTAINS_PART,
                        projection=projection,evidence_refs=tuple(sorted(set(evidence))))
        expected_links[row.link_id] = row

    call = CompoundCall.from_dict(native['current_call']) if native['current_call'] is not None else None
    for key, program in programs.items():
        require(program.primitive_sha256 in primitives, 'program pin has no retained installed primitive')
        program_id = 'program-'+key
        expect_node(program_id,'Retained compound call program',
            {'program_digest':key,'primitive_sha256':program.primitive_sha256,
             'active_head':key == native['dispatch']['compound_head'],'historical_installation_is_not_dispatch':True},
            evidence=(key,))
        expect_link(atlas.current_state_id,program_id,'retained compound registry artifact')
        if call is not None and call.artifact_sha256 == key:
            expect_link('current-call',program_id,'current caller exact program pin',(key,call.inputs_digest))
        for index, step in enumerate(program.steps):
            step_id = content_id('step',{'program':key,'index':index})
            expect_node(step_id,'Primitive call step '+str(index),
                {'index':index,**step.to_dict(),'primitive_sha256':program.primitive_sha256},
                kind=NodeKind.IDEA_CONTEXT,evidence=(key,))
            expect_link(program_id,step_id,'program call step:'+str(index))
        expect_link(program_id,'primitive-'+program.primitive_sha256,'exact pinned primitive dependency',
                    (key,program.primitive_sha256))
    for key, primitive in primitives.items():
        primitive_id = 'primitive-'+key
        expect_node(primitive_id,'Retained primitive dependency',
            {'artifact':primitive.to_dict(),'active_head':key == native['dispatch']['primitive_head']},evidence=(key,))
        expect_link(atlas.current_state_id,primitive_id,'retained primitive artifact')

    # Prefixes, known declaration fields and structural link endpoints all
    # participate. Renaming a node or deleting its incoming edge cannot hide it.
    actual_ids = set()
    for node in atlas.nodes:
        fields = dict(node.fields)
        if (node.node_id.startswith(('program-','primitive-','step-')) or 'program_digest' in fields
                or 'artifact' in fields or any(key in fields for key in ('a_ref','b_ref','c_ref'))):
            actual_ids.add(node.node_id)
    for edge in atlas.links:
        if edge.projection is not None and (edge.projection.startswith('program call step:')
                or edge.projection in {'retained compound registry artifact','retained primitive artifact',
                                      'exact pinned primitive dependency','current caller exact program pin'}):
            actual_ids.add(edge.target_id)
    require(actual_ids == set(expected_nodes),'displayed artifact structure omits, renames or adds declarations')
    for key, expected in expected_nodes.items():
        require(canonical_json(nodes[key].to_dict()) == canonical_json(expected.to_dict()),
                'displayed artifact node differs from its exact retained declaration')
    actual_links = {edge.link_id:edge for edge in atlas.links
                    if edge.source_id in actual_ids or edge.target_id in actual_ids}
    require(set(actual_links) == set(expected_links),'displayed artifact edge set differs from retained declarations')
    for key, expected in expected_links.items():
        require(canonical_json(actual_links[key].to_dict()) == canonical_json(expected.to_dict()),
                'displayed artifact edge or primitive pin differs from retained declaration')
    return programs, primitives


def scoped_projection(source):
    from tools.render_compound_rpa_view import validate_document
    # Detach every mutable nested object using the already-validated canonical
    # bytes. Returned display data must not alias the caller's source object.
    source=json.loads(validate_document(source))
    atlas=AtlasSnapshot.from_dict(source["atlas"])
    nodes=atlas.node_map()
    links={row.link_id:row for row in atlas.links}
    catalog=source["native"]["evidence_catalog"]
    programs,primitives=_declared_structure(source,atlas)
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
    for program_digest,program in sorted(programs.items()):
        for index,step in enumerate(program.steps):
            step_id=content_id('step',{'program':program_digest,'index':index})
            for port,slot in step.to_dict().items():
                add(step_id,port+" ← "+slot,{"port":port,"source_slot":slot,
                    "binding_kind":"EARLIER_CALL_RESULT" if slot=="r0" else "ORIGINAL_INPUT",
                    "meaning":"Declared symbolic binding; display navigation does not execute this call."},
                    (program_digest,), "declared call input binding:"+port,
                    {"program":program_digest,"step":step_id,"port":port})
    for primitive_digest,artifact in sorted(primitives.items()):
        for index,instruction in enumerate(artifact.to_dict()["program"]):
            add('primitive-'+primitive_digest,"Instruction "+str(index),{"index":index,"instruction":instruction,
                "meaning":"Declared instruction in the retained artifact; not a new execution."},
                (artifact.artifact_sha256,),"declared primitive instruction:"+str(index),
                {"primitive":artifact.artifact_sha256,"instruction":index})
    # Execution/qualification evidence is a part of the inspected evidence
    # bundle, not a causal child of the program. Preserve that exact meaning.
    for row in catalog["records"]:
        # Artifact identity lives in the already-validated record body, not in
        # the factored verifier reports. Avoid revalidating the entire catalog
        # once for every record while preserving all record digest checks above.
        body=row['body']
        program_digest=(body['artifact']['program_digest'] if row['kind']=='INSTALLATION'
                        else body.get("artifact_sha256"))
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
