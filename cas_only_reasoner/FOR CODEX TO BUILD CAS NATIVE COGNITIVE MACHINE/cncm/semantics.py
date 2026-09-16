"""CAS-Sem MVP matching, decomposition, inference, and proof verification."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Iterator, Mapping, Sequence

from .canonical import digest
from .model import (
    BranchFrame,
    ContractError,
    DecompositionRecord,
    EvidenceStatus,
    InferenceOperation,
    ProofStep,
    Proposition,
    Provenance,
    ResolverSpec,
    Rule,
)


MAX_MATCH_EXPANSIONS = 4096


class InferenceSearchExhausted(ContractError):
    """The deterministic antecedent-match expansion ceiling was reached."""


class InferenceStepLimitReached(ContractError):
    """A bounded closure stopped while another deterministic proof remained."""


def proposition_map(propositions: Iterable[Proposition]) -> dict[str, Proposition]:
    """Return a deterministically ordered semantic-key map."""
    selected: dict[str, Proposition] = {}
    for proposition in sorted(propositions, key=lambda item: item.key):
        selected.setdefault(proposition.key, proposition)
    return selected


def same_atom(left: Proposition, right: Proposition) -> bool:
    return (
        left.predicate == right.predicate
        and left.arguments == right.arguments
        and left.scope == right.scope
    )


def query_is_supported(branch: BranchFrame, query: Proposition) -> bool:
    return query.key in branch.proposition_map()


def has_authoritative_support(
    branch: BranchFrame, proposition_key: str, *,
    trusted_root_keys: frozenset[str] = frozenset(),
) -> bool:
    """Return true only for asserted or verified, non-hypothetical proof support."""
    propositions = branch.proposition_map()
    eligible = {
        key
        for key, proposition in propositions.items()
        if proposition.evidence_status is not EvidenceStatus.HYPOTHETICAL
    }
    supported = {
        key
        for key, proposition in propositions.items()
        if proposition.evidence_status is EvidenceStatus.ASSERTED
    }
    # Only a versioned coordinator may supply independently checked native
    # roots. The v0.1 coordinator always supplies the empty default. These keys
    # are not read from a caller's proof flag, provenance, or problem packet.
    supported.update(trusted_root_keys & eligible)
    normal_steps: list[tuple[str, set[str]]] = []
    for step in sorted(branch.proof_steps, key=lambda item: item.step_id):
        if not step.verified or step.conclusion.key not in eligible:
            continue
        if step.operation in {InferenceOperation.RECALL, InferenceOperation.RPM_CHILD_RESULT}:
            supported.add(step.conclusion.key)
        elif step.operation in {
            InferenceOperation.INFER_MODUS_PONENS, InferenceOperation.INFER_TRANSITIVE
        } and step.premise_keys:
            normal_steps.append((step.conclusion.key, set(step.premise_keys)))

    dependents: dict[str, list[int]] = {}
    remaining: list[set[str]] = []
    queue = list(sorted(supported))
    for index, (conclusion_key, premises) in enumerate(normal_steps):
        unresolved = premises - supported
        remaining.append(unresolved)
        if not unresolved:
            if conclusion_key not in supported:
                supported.add(conclusion_key)
                queue.append(conclusion_key)
            continue
        for premise_key in unresolved:
            dependents.setdefault(premise_key, []).append(index)

    cursor = 0
    while cursor < len(queue):
        newly_supported = queue[cursor]
        cursor += 1
        for index in dependents.get(newly_supported, ()):
            unresolved = remaining[index]
            unresolved.discard(newly_supported)
            if unresolved:
                continue
            conclusion_key = normal_steps[index][0]
            if conclusion_key in supported:
                continue
            supported.add(conclusion_key)
            queue.append(conclusion_key)
    return proposition_key in supported


def detect_contradictions(propositions: Iterable[Proposition]) -> tuple[str, ...]:
    by_atom: dict[str, set[bool]] = {}
    for proposition in propositions:
        by_atom.setdefault(proposition.atom_key, set()).add(proposition.polarity)
    return tuple(sorted(atom for atom, polarities in by_atom.items() if len(polarities) > 1))


def _unify_pattern(
    pattern: Proposition,
    fact: Proposition,
    bindings: Mapping[str, str],
) -> dict[str, str] | None:
    if (
        pattern.predicate != fact.predicate
        or pattern.polarity != fact.polarity
        or pattern.scope != fact.scope
        or len(pattern.arguments) != len(fact.arguments)
    ):
        return None
    result = dict(bindings)
    for pattern_term, fact_term in zip(pattern.arguments, fact.arguments, strict=True):
        if pattern_term.startswith("?"):
            existing = result.get(pattern_term)
            if existing is not None and existing != fact_term:
                return None
            result[pattern_term] = fact_term
        elif pattern_term != fact_term:
            return None
    return result


def _match_antecedents(
    antecedents: Sequence[Proposition],
    facts: Sequence[Proposition],
    expansion_budget: list[int],
) -> Iterator[tuple[dict[str, str], tuple[str, ...]]]:
    """Iteratively enumerate matches so packet depth cannot exhaust Python's stack."""
    ordered_facts = tuple(sorted(facts, key=lambda item: item.key))
    stack: list[tuple[int, dict[str, str], tuple[str, ...]]] = [(0, {}, ())]
    while stack:
        index, current, premise_keys = stack.pop()
        if index >= len(antecedents):
            yield current, tuple(sorted(premise_keys))
            continue
        pattern = antecedents[index]
        matches: list[tuple[dict[str, str], str]] = []
        for fact in ordered_facts:
            if expansion_budget[0] <= 0:
                raise InferenceSearchExhausted("antecedent match expansion budget exhausted")
            expansion_budget[0] -= 1
            merged = _unify_pattern(pattern, fact, current)
            if merged is not None:
                matches.append((merged, fact.key))
        # Reverse push order preserves the recursive implementation's canonical
        # fact ordering while avoiding recursion-depth failure.
        for merged, fact_key in reversed(matches):
            stack.append((index + 1, merged, premise_keys + (fact_key,)))


def instantiate(pattern: Proposition, bindings: Mapping[str, str]) -> Proposition:
    arguments: list[str] = []
    for term in pattern.arguments:
        if term.startswith("?"):
            if term not in bindings:
                raise ValueError(f"unbound variable: {term}")
            arguments.append(bindings[term])
        else:
            arguments.append(term)
    return Proposition(
        predicate=pattern.predicate,
        arguments=tuple(arguments),
        polarity=pattern.polarity,
        evidence_status=EvidenceStatus.DERIVED,
        provenance=pattern.provenance,
        scope=pattern.scope,
    )


def applicable_proofs(
    branch: BranchFrame,
    rules: Iterable[Rule],
    *,
    max_proofs: int = 1,
    max_match_expansions: int = MAX_MATCH_EXPANSIONS,
    trusted_root_keys: frozenset[str] = frozenset(),
) -> tuple[ProofStep, ...]:
    """Select bounded canonical new Horn proofs without exhaustive materialization."""
    if max_proofs < 1 or max_match_expansions < 1:
        raise ValueError("proof and match limits must be positive")
    existing = branch.proposition_map()
    facts = tuple(existing.values())
    existing_step_ids = {step.step_id for step in branch.proof_steps}
    proposals: list[ProofStep] = []
    seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()
    expansion_budget = [max_match_expansions]
    for rule in sorted(rules, key=lambda item: item.rule_id):
        for bindings, premise_keys in _match_antecedents(
            rule.antecedents,
            facts,
            expansion_budget,
        ):
            conclusion = instantiate(rule.consequent, bindings)
            provenance = tuple(
                sorted(
                    (
                        Provenance("rule", rule.rule_id, "declared CAS-Sem inference"),
                        *rule.provenance,
                    ),
                    key=lambda item: (item.source_type, item.source_id, item.detail),
                )
            )
            conclusion = conclusion.with_status(EvidenceStatus.DERIVED, provenance)
            identity = (conclusion.key, rule.rule_id, tuple(sorted(bindings.items())))
            if conclusion.key in existing and has_authoritative_support(
                branch, conclusion.key, trusted_root_keys=trusted_root_keys
            ):
                # An asserted or already-authoritative result needs no
                # alternate proof.  Tainted derived results deliberately do:
                # a later independent path may establish authority.
                continue
            if identity in seen:
                continue
            seen.add(identity)
            proof = ProofStep.create(
                operation=rule.operation,
                premise_keys=premise_keys,
                rule_id=rule.rule_id,
                conclusion=conclusion,
                substitution=bindings,
                branch_id=branch.branch_id,
                verified=True,
                provenance=provenance,
            )
            # A semantic proposition may have more than one proof path.  An
            # earlier path can depend on hypothetical support, so suppress only
            # an already-recorded proof step, never every alternate proof for
            # the same conclusion key.
            if proof.step_id in existing_step_ids:
                continue
            proposals.append(proof)
            if len(proposals) >= max_proofs:
                return tuple(proposals)
    return tuple(proposals)


def verify_proof_step(
    proof: ProofStep,
    branch: BranchFrame,
    rules: Iterable[Rule],
    *, trusted_root_keys: frozenset[str] = frozenset(),
) -> bool:
    """Reconstruct a proof; never trust the incoming verified flag alone."""
    if proof.branch_id != branch.branch_id:
        return False
    if proof.operation in {InferenceOperation.RECALL, InferenceOperation.RPM_CHILD_RESULT}:
        # These operations require their separate authority-bound source
        # reconstruction in the kernel; a self-declared verified flag is never
        # sufficient here.
        return False
    return any(
        candidate.to_dict() == proof.to_dict()
        for candidate in applicable_proofs(branch, rules, trusted_root_keys=trusted_root_keys)
    )


def _unify_consequent_to_query(
    pattern: Proposition,
    query: Proposition,
) -> dict[str, str] | None:
    return _unify_pattern(pattern, query, {})


def decompose_query(
    branch: BranchFrame, query: Proposition, rules: Iterable[Rule], *,
    trusted_root_keys: frozenset[str] = frozenset(),
) -> DecompositionRecord:
    known = branch.proposition_map()
    premises: set[str] = set()
    dependencies: set[str] = set()
    unknowns: set[str] = set()
    predicted: set[str] = set()
    if query.key in known and has_authoritative_support(branch, query.key, trusted_root_keys=trusted_root_keys):
        query_proposition = known[query.key]
        supporting_steps = sorted(
            (
                step
                for step in branch.proof_steps
                if step.verified
                and step.conclusion.key == query.key
                and (
                    step.operation
                    in {InferenceOperation.RECALL, InferenceOperation.RPM_CHILD_RESULT}
                    or all(
                        has_authoritative_support(branch, premise_key, trusted_root_keys=trusted_root_keys)
                        for premise_key in step.premise_keys
                    )
                )
            ),
            key=lambda item: item.step_id,
        )
        if query_proposition.evidence_status is EvidenceStatus.ASSERTED:
            supporting_steps = []
        if supporting_steps:
            selected = supporting_steps[0]
            premises.update(selected.premise_keys)
            if selected.rule_id:
                dependencies.add(selected.rule_id)
        else:
            premises.add(query.key)
        return DecompositionRecord(
            candidate_id=branch.candidate_id,
            premises=tuple(sorted(premises)),
            assumptions=tuple(sorted(item.key for item in branch.assumptions)),
            dependencies=tuple(sorted(dependencies)),
            contradictions=detect_contradictions(branch.propositions),
            unknowns=(),
            required_prerequisites=(),
            predicted_effects=(query.key,),
        )
    for rule in sorted(rules, key=lambda item: item.rule_id):
        bindings = _unify_consequent_to_query(rule.consequent, query)
        if bindings is None:
            continue
        dependencies.add(rule.rule_id)
        predicted.add(query.key)
        for antecedent in rule.antecedents:
            try:
                required = instantiate(antecedent, bindings)
            except ValueError:
                unknowns.add(f"unbound:{rule.rule_id}:{antecedent.key}")
                continue
            premises.add(required.key)
            if required.key not in known:
                unknowns.add(required.key)
    if not dependencies and not has_authoritative_support(branch, query.key, trusted_root_keys=trusted_root_keys):
        unknowns.add(query.key)
    contradictions = detect_contradictions(branch.propositions)
    return DecompositionRecord(
        candidate_id=branch.candidate_id,
        premises=tuple(sorted(premises)),
        assumptions=tuple(sorted(item.key for item in branch.assumptions)),
        dependencies=tuple(sorted(dependencies)),
        contradictions=contradictions,
        unknowns=tuple(sorted(unknowns)),
        required_prerequisites=tuple(sorted(unknowns)),
        predicted_effects=tuple(sorted(predicted)),
    )


def derive_closure(
    facts: Iterable[Proposition],
    rules: Iterable[Rule],
    *,
    branch_id: str,
    max_steps: int,
    stop_key: str | None = None,
) -> tuple[dict[str, Proposition], tuple[ProofStep, ...], bool]:
    """Pure bounded closure used only to verify an RPM child packet."""
    branch = BranchFrame(
        branch_id=branch_id,
        parent_branch_id=None,
        active_goal_id="rpm_child",
        candidate_id="rpm_child",
        assumptions=(),
        propositions=tuple(proposition_map(facts).values()),
        recalled_memory_ids=(),
        proof_steps=(),
        decompositions=(),
        hard_constraints=(),
        contradictions=(),
        unknowns=(),
        status=branch_status_open(),
        created_at_tick=0,
    )
    proofs: list[ProofStep] = []
    if stop_key is not None and stop_key in branch.proposition_map():
        return branch.proposition_map(), (), False
    complete = False
    for _ in range(max_steps):
        next_proofs = applicable_proofs(branch, rules)
        if not next_proofs:
            complete = True
            break
        chosen = next_proofs[0]
        propositions = proposition_map((*branch.propositions, chosen.conclusion))
        branch = replace(
            branch,
            propositions=tuple(propositions.values()),
            proof_steps=branch.proof_steps + (chosen,),
        )
        proofs.append(chosen)
        if stop_key is not None and stop_key in branch.proposition_map():
            return branch.proposition_map(), tuple(proofs), False
    if not complete:
        complete = not applicable_proofs(branch, rules)
    return branch.proposition_map(), tuple(proofs), complete


def branch_status_open():
    # Local import avoids a circular-looking name in generated schema documentation.
    from .model import BranchStatus

    return BranchStatus.OPEN


def resolve_rpm_child(
    resolver: ResolverSpec,
    *,
    branch_id: str,
    max_steps: int,
) -> tuple[Proposition, ProofStep, int] | None:
    closure, child_proofs, complete = derive_closure(
        resolver.facts,
        resolver.rules,
        branch_id=f"{branch_id}:rpm",
        max_steps=max_steps,
        stop_key=resolver.target.key,
    )
    target = closure.get(resolver.target.key)
    if target is None:
        if not complete:
            raise InferenceStepLimitReached(
                "RPM resolver closure exceeded the available inference-step budget"
            )
        return None
    source_steps = tuple(step.step_id for step in child_proofs if step.conclusion.key == target.key)
    proof = ProofStep.create(
        operation=InferenceOperation.RPM_CHILD_RESULT,
        premise_keys=source_steps or (target.key,),
        rule_id=None,
        conclusion=replace(
            target,
            evidence_status=EvidenceStatus.DERIVED,
            provenance=(Provenance("rpm_resolver", digest(resolver.to_dict())[:16], "bounded child result"),),
        ),
        substitution={},
        branch_id=branch_id,
        verified=True,
        provenance=(Provenance("rpm_resolver", digest(resolver.to_dict())[:16], "bounded child result"),),
    )
    return proof.conclusion, proof, len(child_proofs)


def inference_fingerprint(branches: Iterable[BranchFrame], active_goal_id: str) -> str:
    payload = {
        "active_goal_id": active_goal_id,
        "branches": [
            {
                "branch_id": branch.branch_id,
                "status": branch.status.value,
                "propositions": sorted(item.key for item in branch.propositions),
                "unknowns": sorted(branch.unknowns),
                "contradictions": sorted(branch.contradictions),
            }
            for branch in sorted(branches, key=lambda item: item.branch_id)
        ],
    }
    return digest(payload)
