"""Bounded formal proof/support checks. Candidate generation is not a verifier."""
from fractions import Fraction
from .canonical import canonical_json, digest
from .model import Provenance
from .native_model import _rational
from .semantic_model import MemoryRef
from .semantic_verification import resolve_memory
from .derived_model import DerivedResultRef, require
from .math_model import MathClaim, MathClaimStatus, MathStepOperation, MathStepProposal
from .math_parser import parse_math_statement
from .math_kernel import check_math_step, verify_math_receipt

MAX_SUPPORT_NODES = 16
MAX_SUPPORT_DEPTH = 8
CHECKER_ID = 'cncm.derived-formal-verifier/0.6'


def definition_head(state, ref):
    return next((d for d in reversed(state.derived_definitions) if d.ref == ref), None)


def memory_record(state, record_digest):
    row = next((r for r in state.derived_records if r.kind == 'MEMORY' and r.record_digest == record_digest), None)
    require(row is not None, 'MISSING_DERIVED_WITNESS')
    return row


def latest_memory(state, ref):
    return next((r for r in reversed(state.derived_records) if r.kind == 'MEMORY'
                 and r.body_dict()['reference'] == ref.to_dict()), None)


def compact_binding(binding):
    return {k:v for k,v in binding.to_dict().items() if k != 'receipt_digest'}


def resolved_definition(state, definition, trusted_ingress, profile_digest, dependencies=()):
    """Recompute all active source sets and exact declared derived substitutions."""
    by_ref = {}
    leaves = {}
    definition_dependencies = {definition.definition_digest}
    for row in dependencies:
        body = row.body_dict(); ref = DerivedResultRef.from_dict(body['reference'])
        require(ref.ref_key not in by_ref, 'DUPLICATE_DERIVED_DEPENDENCY')
        by_ref[ref.ref_key] = body['value']
        for binding in body['source_bindings']:
            leaves[canonical_json(binding['ref'])] = binding
        definition_dependencies.update(body['definition_dependencies'])
    wanted = {v.ref_key for _,v in definition.parameters if type(v) is DerivedResultRef}
    require(set(by_ref) == wanted, 'DERIVED_DEPENDENCY_SET_MISMATCH')
    inputs = {}
    for name, value in definition.parameters:
        if type(value) is MemoryRef:
            binding, receipt = resolve_memory(state.memory_statements, value, trusted_ingress,
                                             source_profile_digest=profile_digest)
            require(binding is not None, 'SOURCE_'+receipt['reason'])
            leaves[canonical_json(value.to_dict())] = compact_binding(binding)
            value = binding.value
        elif type(value) is DerivedResultRef:
            value = by_ref[value.ref_key]
        _rational(value)
        inputs[name] = value
    return inputs, [leaves[k] for k in sorted(leaves)], sorted(definition_dependencies)


def validate_admission_dependencies(state, dependencies):
    """Reserve one node for the proposed root and bound its combined support DAG."""
    visited, active, heights = set(), set(), {}
    def visit(row, depth):
        require(depth <= MAX_SUPPORT_DEPTH, 'SUPPORT_DEPTH_EXHAUSTED')
        key = row.record_digest
        require(key not in active, 'CYCLIC_DERIVED_SUPPORT')
        if key in visited:
            require(depth+heights[key]-1 <= MAX_SUPPORT_DEPTH, 'SUPPORT_DEPTH_EXHAUSTED')
            return heights[key]
        require(len(visited)+len(active)+1 < MAX_SUPPORT_NODES, 'SUPPORT_NODE_BOUND_EXCEEDED')
        active.add(key)
        child_heights = [visit(memory_record(state,dependency),depth+1)
                         for dependency in row.body_dict()['derived_dependencies']]
        active.remove(key); visited.add(key)
        heights[key] = 1+max(child_heights,default=0)
        return heights[key]
    require(len(dependencies) <= 5 and len({r.record_digest for r in dependencies}) == len(dependencies),
            'DERIVED_DEPENDENCY_BOUND')
    for row in dependencies: visit(row,2)
    return len(visited)+1


def generate_candidate(inputs):
    """Untrusted finite rational proposal, independently checked on original AST."""
    a,b,c,d,e = (Fraction(inputs[k]) for k in 'abcde')
    require(a != 0 and b != 0, 'NON_UNIQUE_FORMAL_PROBLEM')
    value = str(((e-d)/a-c)/b)
    _rational(value)
    return value


def _proof_inputs(definition, inputs, value, profile_digest):
    require(set(inputs) == set('abcde'), 'proof input names invalid')
    for scalar in inputs.values(): _rational(scalar)
    _rational(value)
    v = definition.variable
    notation = f"({inputs['a']})*(({inputs['b']})*{v}+({inputs['c']}))+({inputs['d']})=({inputs['e']})"
    claim = MathClaim.create(statement=parse_math_statement(notation, declared_variables=(v,)),
        status=MathClaimStatus.ASSUMED,
        provenance=(Provenance('derived_definition', definition.definition_digest, 'formal equation assumption; no world-truth upgrade'),
                    Provenance('source_profile', profile_digest, 'protected checker source identity')))
    proposal = MathStepProposal.create(operation=MathStepOperation.VERIFY_LINEAR_SOLUTION,
        premise_claim_ids=(claim.claim_id,),
        proposed_conclusion=parse_math_statement(v+'=('+value+')', declared_variables=(v,)))
    return claim, proposal


def checked_proof(definition, inputs, value, profile_digest):
    claim, proposal = _proof_inputs(definition, inputs, value, profile_digest)
    receipt = check_math_step(proposal, (claim,))
    require(receipt.accepted and verify_math_receipt(proposal, (claim,), receipt), 'INVALID_FORMAL_PROOF')
    return {'checker_id': CHECKER_ID, 'source_profile_digest': profile_digest,
            'claim': claim.to_dict(), 'proposal': proposal.to_dict(), 'receipt': receipt.to_dict(),
            'verification_status': 'CHECKED_FORMAL_DERIVATION', 'unconditional_world_truth': False}


def verify_proof(definition, inputs, value, proof, profile_digest):
    expected = checked_proof(definition, inputs, value, profile_digest)
    require(canonical_json(proof) == canonical_json(expected), 'FORMAL_PROOF_BINDING_MISMATCH')
    return expected


def inspect_memory(state, ref, trusted_ingress, profile_digest, *, selected=None):
    """Recheck an entire bounded proof/dependency DAG; never generate candidates."""
    row = latest_memory(state, ref) if selected is None else memory_record(state, selected)
    if row is None:
        return {'status':'NEVER_LEARNED', 'reason':'NO_ADMITTED_RESULT', 'memory_digest':None,
                'checked_nodes':0, 'unconditional_world_truth':False}
    visited, active, heights = {}, set(), {}
    def visit(record, depth):
        require(depth <= MAX_SUPPORT_DEPTH, 'SUPPORT_DEPTH_EXHAUSTED')
        key = record.record_digest
        require(key not in active, 'CYCLIC_DERIVED_SUPPORT')
        if key in visited:
            require(depth+heights[key]-1 <= MAX_SUPPORT_DEPTH, 'SUPPORT_DEPTH_EXHAUSTED')
            return heights[key]
        require(len(visited)+len(active) < MAX_SUPPORT_NODES, 'SUPPORT_NODE_BOUND_EXCEEDED')
        active.add(key)
        body = record.body_dict()
        reference = DerivedResultRef.from_dict(body['reference'])
        definition = definition_head(state, reference)
        require(definition is not None and definition.definition_digest == body['definition_digest'], 'SUPERSEDED_DEFINITION')
        require(definition.definition_digest in trusted_ingress, 'UNTRUSTED_DEFINITION')
        require(body['source_profile_digest'] == profile_digest, 'STALE_CHECKER_PROFILE')
        dependencies = tuple(memory_record(state,k) for k in body['derived_dependencies'])
        require(len(dependencies) <= 5 and len(set(body['derived_dependencies'])) == len(dependencies), 'DERIVED_DEPENDENCY_BOUND')
        child_heights = [visit(dependency, depth+1) for dependency in dependencies]
        inputs, leaves, definitions = resolved_definition(state, definition, trusted_ingress, profile_digest, dependencies)
        require(canonical_json(inputs) == canonical_json(body['inputs']), 'STALE_FORMAL_INPUTS')
        require(canonical_json(leaves) == canonical_json(body['source_bindings']), 'STALE_ACTIVE_SOURCE_SET')
        require(definitions == body['definition_dependencies'], 'STALE_DEFINITION_CLOSURE')
        verify_proof(definition, inputs, body['value'], body['proof'], profile_digest)
        require(body['verification_status'] == 'CHECKED_FORMAL_DERIVATION' and body['unconditional_world_truth'] is False,
                'INVALID_MEMORY_EVIDENCE_STATUS')
        active.remove(key); visited[key] = record
        heights[key] = 1+max(child_heights,default=0)
        return heights[key]
    try:
        require(row.body_dict()['reference'] == ref.to_dict(), 'CROSS_CONTEXT_MEMORY')
        visit(row, 1)
        status, reason = 'VERIFIED', 'EXACT_CURRENT_FORMAL_SUPPORT'
    except (ValueError, TypeError, KeyError) as error:
        reason = str(error)
        status = 'CONTRADICTED' if 'SOURCE_CONFLICT' in reason else 'SUPERSEDED' if 'SUPERSEDED_DEFINITION' in reason else 'STALE'
    return {'status':status, 'reason':reason, 'memory_digest':row.record_digest,
            'checked_nodes':len(visited), 'unconditional_world_truth':False}


def verify_derived_bindings(state, problem, trusted_ingress, profile_digest):
    """Protected original typed-input receiver; grounded 0.5 inputs cannot do this."""
    wanted = {r.ref_key:r for r in problem.derived_references}
    require(len(state.derived_bindings) == len(wanted)
            and {row[:2] for row in state.derived_bindings} == set(wanted), 'ORIGINAL_DERIVED_BINDING_SET_MISMATCH')
    values = {}
    for scope,key,record_digest in state.derived_bindings:
        ref = wanted[(scope,key)]
        row = memory_record(state,record_digest)
        require(canonical_json(row.body_dict()['reference']) == canonical_json(ref.to_dict()), 'BORROWED_DERIVED_REFERENCE')
        report = inspect_memory(state,ref,trusted_ingress,profile_digest,selected=record_digest)
        require(report['status'] == 'VERIFIED' and report['memory_digest'] == record_digest, 'STALE_OR_BORROWED_DERIVED_BINDING')
        values[(scope,key)] = row.body_dict()['value']
    # Do not invoke the candidate/host translator being checked. Preserve
    # every original literal and source reference independently.
    from .compound_model import CompoundProblem
    parameters = tuple((name, values[value.ref_key] if type(value) is DerivedResultRef else value)
                       for name,value in problem.parameters)
    return CompoundProblem(problem.reasoning,problem.variable,parameters,problem.budget,
                           problem.updates,problem.construction_limit)
