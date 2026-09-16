"""Pure provenance, exact recall and equation-substitution checks.

VALID describes the named checked relation. It never upgrades USER_ATTESTED or
TEST_FIXTURE into independently verified factual truth and grants no write or
commitment authority. The caller supplies an externally anchored ingress set
and the source profile which pins this checker; neither comes from a capsule.
"""
from __future__ import annotations

from .canonical import canonical_json, digest
from .model import ContractError
from .nested_model import Equation, NestedProblem


RECEIPT_SCHEMA = "cncm.verifier-receipt/0.1"
CHECKER_ID = "cncm.semantic-verifier/0.1"
MAX_HISTORY = 256
MAX_TRUSTED_INGRESS = 256
MAX_BINDINGS = 48
_CLAIMS = {"SOURCE_UPDATE": "SOURCE_UPDATE_ADMISSIBLE",
           "MEMORY_RECALL": "EXACT_ACTIVE_SOURCE_RECALL",
           "MEMORY_RESOLUTION": "EXACT_TEMPLATE_SUBSTITUTION"}
_STATUSES = frozenset({"VALID", "INVALID", "UNSUPPORTED", "INCOMPLETE", "COUNTEREXAMPLE_FOUND"})
_SUPPORTS = frozenset({"NONE", "USER_ATTESTED", "TEST_FIXTURE", "MIXED_ATTESTATIONS"})


def _require(condition, reason):
    if not condition:
        raise ContractError(reason)


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _support(statuses):
    kinds = set(statuses)
    return "NONE" if not kinds else next(iter(kinds)) if len(kinds) == 1 else "MIXED_ATTESTATIONS"


def _receipt(domain, status, reason, bindings, source_profile_digest, support="NONE"):
    _require(domain in _CLAIMS and status in _STATUSES and support in _SUPPORTS,
             "closed verifier contract violated")
    _require(_sha(source_profile_digest), "source profile digest required")
    body = {"schema_version": RECEIPT_SCHEMA, "checker_id": CHECKER_ID,
            "source_profile_digest": source_profile_digest,
            "domain": domain, "claim": _CLAIMS[domain], "status": status,
            "reason": reason, "support": support,
            "factual_status": "NOT_INDEPENDENTLY_VERIFIED", "bindings": bindings}
    _require(len(canonical_json(body).encode("utf-8")) <= 262144, "verifier receipt size bound exceeded")
    return {**body, "receipt_digest": digest(body)}


def _typed_inputs(history, trusted_ingress, source_profile_digest):
    from .semantic_model import SourceStatement

    _require(_sha(source_profile_digest), "source profile digest required")
    _require(type(history) is tuple and len(history) <= MAX_HISTORY,
             "bounded source history tuple required")
    _require(type(trusted_ingress) is tuple and len(trusted_ingress) <= MAX_TRUSTED_INGRESS
             and all(_sha(value) for value in trusted_ingress)
             and len(set(trusted_ingress)) == len(trusted_ingress),
             "bounded unique externally trusted ingress digests required")
    for row in history:
        _require(type(row) is SourceStatement, "typed source history required")
        SourceStatement.from_dict(row.to_dict())
    return set(trusted_ingress)


def _key(statement):
    return statement.scope, statement.key, statement.source_id


def _update_reason(heads, seen, statement, trusted):
    if statement.statement_digest not in trusted:
        return "UNTRUSTED_INGRESS"
    if statement.statement_digest in seen:
        return "REPLAYED_STATEMENT"
    prior = heads.get(_key(statement))
    if statement.previous_digest != (prior.statement_digest if prior else None):
        return "STALE_SOURCE_HEAD"
    if statement.action == "RETRACT" and prior is None:
        return "RETRACT_WITHOUT_HEAD"
    if statement.action == "RETRACT" and prior.action == "RETRACT":
        return "SOURCE_ALREADY_REVOKED"
    return None


def _history(history, trusted):
    heads, seen = {}, set()
    for row in history:
        reason = _update_reason(heads, seen, row, trusted)
        if reason:
            return heads, seen, "HISTORY_" + reason
        heads[_key(row)] = row
        seen.add(row.statement_digest)
    return heads, seen, None


def _context(history):
    return {"history_digest": digest([row.to_dict() for row in history]),
            "history_count": len(history)}


def validate_source_update(history, statement, trusted_ingress, *, source_profile_digest):
    """Check one proposed append; reconstruct lineage without changing history."""
    from .semantic_model import SourceStatement

    trusted = _typed_inputs(history, trusted_ingress, source_profile_digest)
    _require(type(statement) is SourceStatement, "typed source statement required")
    SourceStatement.from_dict(statement.to_dict())
    heads, seen, reason = _history(history, trusted)
    if reason is None:
        reason = "HISTORY_CAPACITY" if len(history) == MAX_HISTORY else _update_reason(heads, seen, statement, trusted)
    prior = heads.get(_key(statement))
    bindings = {**_context(history), "statement": statement.to_dict(),
                "statement_digest": statement.statement_digest,
                "previous_head_digest": prior.statement_digest if prior else None}
    return _receipt("SOURCE_UPDATE", "INVALID" if reason else "VALID",
                    reason or "SOURCE_UPDATE_ADMISSIBLE", bindings, source_profile_digest, statement.status)


def resolve_memory(history, ref, trusted_ingress, *, source_profile_digest):
    """Recall only current exact heads; conflicting sources and stronger demands refuse."""
    from .semantic_model import MemoryRef, RecallBinding

    trusted = _typed_inputs(history, trusted_ingress, source_profile_digest)
    _require(type(ref) is MemoryRef, "typed memory reference required")
    MemoryRef.from_dict(ref.to_dict())
    heads, _, history_reason = _history(history, trusted)
    matching = [row for (scope, key, _), row in heads.items() if (scope, key) == (ref.scope, ref.key)]
    active = sorted((row for row in matching if row.action == "ASSERT"), key=lambda row: row.statement_digest)
    revoked = sorted(row.statement_digest for row in matching if row.action == "RETRACT")
    digests = tuple(row.statement_digest for row in active)
    statuses = tuple(row.status for row in active)
    values = sorted({row.value for row in active})
    reason = history_reason
    if reason is None:
        reason = ("MISSING" if not matching else "REVOKED" if not active else "CONFLICT" if len(values) != 1
                  else "INSUFFICIENT_EVIDENCE" if ref.evidence_requirement == "INDEPENDENTLY_VERIFIED" else None)
    binding_body = {"ref": ref.to_dict(), "value": values[0] if len(values) == 1 else None,
                    "statement_digests": list(digests), "statuses": list(statuses)}
    payload = {**_context(history), "binding": binding_body, "active_values": values,
               "revoked_head_digests": revoked}
    receipt = _receipt("MEMORY_RECALL", "INVALID" if history_reason else "INCOMPLETE" if reason else "VALID",
                       reason or "EXACT_ACTIVE_SOURCE_RECALL", payload, source_profile_digest, _support(statuses))
    if reason:
        return None, receipt
    return RecallBinding(ref, values[0], digests, statuses, receipt["receipt_digest"]), receipt


def _ref_key(ref):
    return ref.scope, ref.key, ref.evidence_requirement


def _reachable(problem):
    """Independent bounded traversal; no model reference/resolution helpers."""
    from .semantic_model import MemoryRef

    equations = {row.variable: row for row in problem.equations}
    visited, missing, references = set(), set(), {}
    pending = [problem.query_variable]
    while pending:
        variable = pending.pop()
        if variable in visited:
            continue
        visited.add(variable)
        row = equations.get(variable)
        if row is None:
            missing.add(variable)
            continue
        for value in (row.a, row.b, row.constant):
            if type(value) is MemoryRef:
                references[_ref_key(value)] = value
        pending.extend(dependency for dependency, _ in row.terms)
    return equations, visited, missing, references


def verify_resolution(problem, bindings, resolved_nested_problem, history, trusted_ingress, *, source_profile_digest):
    """Reconstruct every reachable scalar from exact admitted source heads.

    Unreachable equations are explicitly omitted. Missing reachable producers
    remain missing for the live planner to diagnose. No variable is solved here.
    """
    from .semantic_model import SemanticProblem, MemoryRef, RecallBinding

    trusted = _typed_inputs(history, trusted_ingress, source_profile_digest)
    _require(type(problem) is SemanticProblem, "typed semantic problem required")
    SemanticProblem.from_dict(problem.to_dict())
    _require(type(resolved_nested_problem) is NestedProblem, "typed resolved nested problem required")
    NestedProblem.from_dict(resolved_nested_problem.to_dict())
    _require(type(bindings) is tuple and len(bindings) <= MAX_BINDINGS
             and all(type(row) is RecallBinding for row in bindings), "bounded typed recall bindings required")
    for row in bindings:
        RecallBinding.from_dict(row.to_dict())
    _, _, reason = _history(history, trusted)
    payload = {**_context(history), "problem_digest": problem.input_hash,
               "resolved_problem_digest": resolved_nested_problem.input_hash,
               "bindings": [row.to_dict() for row in bindings]}
    if reason:
        return _receipt("MEMORY_RESOLUTION", "INVALID", reason, payload, source_profile_digest)
    if problem.updates and (len(history) < len(problem.updates)
                            or tuple(history[-len(problem.updates):]) != problem.updates):
        return _receipt("MEMORY_RESOLUTION", "INVALID", "PROBLEM_UPDATES_NOT_ADMITTED", payload, source_profile_digest)
    equations, reachable, missing, refs = _reachable(problem)
    wanted = tuple(sorted(refs))
    supplied = tuple(_ref_key(row.ref) for row in bindings)
    payload.update(reachable_variables=sorted(reachable), missing_producers=sorted(missing),
                   omitted_unreachable_equations=sorted(set(equations) - reachable))
    if supplied != wanted:
        return _receipt("MEMORY_RESOLUTION", "INVALID", "BINDING_SET_MISMATCH", payload, source_profile_digest)
    verified = {}
    all_statuses = []
    for binding in bindings:
        key = _ref_key(binding.ref)
        expected, receipt = resolve_memory(history, refs[key], trusted_ingress, source_profile_digest=source_profile_digest)
        if expected is None:
            payload["recall_refusal"] = receipt
            return _receipt("MEMORY_RESOLUTION", receipt["status"], receipt["reason"], payload, source_profile_digest)
        if binding.to_dict() != expected.to_dict():
            return _receipt("MEMORY_RESOLUTION", "INVALID", "RECALL_BINDING_MISMATCH", payload, source_profile_digest)
        verified[key] = binding.value
        all_statuses.extend(binding.statuses)

    def scalar(value):
        return verified[_ref_key(value)] if type(value) is MemoryRef else value

    resolved_equations = tuple(Equation(row.variable, scalar(row.a), scalar(row.b),
                                        rhs_constant=scalar(row.constant), rhs_terms=row.terms)
                               for variable, row in sorted(equations.items()) if variable in reachable)
    expected_problem = NestedProblem(problem.reasoning, problem.query_variable, resolved_equations, problem.budget)
    if expected_problem.to_dict() != resolved_nested_problem.to_dict():
        return _receipt("MEMORY_RESOLUTION", "INVALID", "RESOLVED_PROBLEM_MISMATCH", payload,
                        source_profile_digest, _support(all_statuses))
    return _receipt("MEMORY_RESOLUTION", "VALID", "EXACT_TEMPLATE_SUBSTITUTION", payload,
                    source_profile_digest, _support(all_statuses))
