"""Pure next-decision sites for assisted development diagnostics.

This module never predicts, completes, repairs, or executes a program. Exact
procedure names and conservative consumed-state correspondence are required.
Value renaming is accepted only through unique, unchanged producer addresses.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json

from .. import codec, grammar_v3
from ..ir import Limits

SCHEMA = "cas-meta2-development-decision-sites/1"
ROLES = ("observation_binding", "call_target", "call_input", "run_input",
         "parent_return", "child_return")
VALUE_ROLES = frozenset(("call_input", "run_input", "parent_return", "child_return"))
CORRESPONDENCE = ("MATCHED", "CONTEXT_CHANGED", "SITE_MISSING", "AMBIGUOUS_MAPPING")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return sha256(_canonical(value).encode()).hexdigest()


def _definition_context(machine):
    """Retain producer positions; never merge equal-looking native operations."""
    procedures, mappings = {}, {}
    for name, procedure in machine.procedures.items():
        mapping = {"arg": [name, "INPUT"]}
        steps = []
        for index, step in enumerate(procedure["steps"]):
            source = mapping[step["input"]]
            identity = [name, index]
            steps.append({"kind": step["kind"],
                          "target": step.get("procedure", step.get("cjt_id")),
                          "input_definition": source,
                          "output_definition": identity})
            mapping[step["output"]] = identity
        mappings[name] = mapping
        returned = procedure["return"]
        procedures[name] = {
            "scope": list(procedure["allowed_cjts"]),
            "steps": steps,
            "return_definition": None if returned is None else mapping[returned],
        }
    return procedures, mappings


def _role(state):
    machine = state._machine
    if state.role == "observation_binding":
        return "observation_binding"
    if state.role == "call_target":
        return "call_target"
    if state.role == "step_input":
        return "call_input" if machine.step["kind"] == "CALL" else "run_input"
    if state.role == "return_value":
        return "parent_return" if machine.current == "main" else "child_return"
    return None


def _site(state, ids, index, chosen_id):
    role = _role(state)
    if role is None:
        return None
    machine = state._machine
    procedure = machine.current
    instruction = (len(machine.procedures[procedure]["steps"])
                   if procedure is not None else None)
    address = [procedure, "RETURN" if role.endswith("_return") else instruction, role]
    definitions, mappings = _definition_context(machine)
    values = mappings.get(procedure, {})
    partial = {"kind": machine.step["kind"]} if machine.step else {}
    if "procedure" in machine.step:
        partial["target"] = machine.step["procedure"]
    if "cjt_id" in machine.step:
        partial["target"] = machine.step["cjt_id"]
    if "input" in machine.step:
        partial["input_definition"] = values[machine.step["input"]]
    allowed_tokens = list(state.allowed_tokens())
    normalized_allowed = ([values[token] for token in allowed_tokens]
                          if role in VALUE_ROLES else allowed_tokens)
    context = {
        "binding": machine.binding,
        "procedures": definitions,
        "current": procedure,
        "instruction_index": instruction,
        "grammar_role": state.role,
        "partial_instruction": partial,
        "available_definitions": sorted(
            (values[name] for name in machine.available), key=_canonical),
        "edges": {name: sorted(children) for name, children in machine.edges.items()},
        "pending_forward_calls": sorted(machine.pending_names()),
        "last_declared_procedure": machine.last_name,
        "global_instruction_count": machine.instructions,
        "prefix_length": len(state.prefix),
        "max_action_length": state.max_length,
        "limits": dict(vars(state.limits)),
        "allowed_choices": sorted(normalized_allowed, key=_canonical),
    }
    chosen = None if chosen_id is None else codec.ACTION_VOCABULARY[chosen_id]
    return {
        "key": _canonical(address), "address": address, "role": role,
        "procedure": procedure, "instruction_index": instruction,
        "grammar_role": state.role, "token_index": index,
        "prefix_ids": list(ids[:index]), "prefix_sha256": _digest(list(ids[:index])),
        "chosen_token_id": chosen_id, "chosen_token": chosen,
        "observed": chosen_id is not None,
        "chosen_token_allowed": None if chosen_id is None else chosen in allowed_tokens,
        "allowed_tokens": allowed_tokens,
        "allowed_ids": [codec.ACTION_TO_ID[token] for token in allowed_tokens],
        "single_option": len(allowed_tokens) == 1,
        "value_definitions": values,
        "context": context, "context_sha256": _digest(context),
    }


def extract_sites(token_ids, *, max_length=256, limits=None):
    """Extract pre-token sites from one actual stream, including a stopped site.

    token_index includes BOS=0. prefix_ids excludes the choice being scored.
    A final semantic site may have observed=False if no choice was emitted.
    Invalid emitted tokens are recorded but never advanced through the grammar.
    """
    state = grammar_v3.GrammarState(
        max_length=max_length, limits=Limits() if limits is None else limits)
    result = {"schema": SCHEMA, "sites": [], "termination": None, "error": None,
              "complete": False, "registered_max_action_length": max_length,
              "model_called": False, "completion_generated": False}
    if type(token_ids) not in (list, tuple):
        result.update(termination="INVALID_TOKEN_IDS", error={"code": "TOKEN_SEQUENCE_REQUIRED"})
        return result
    if any(type(value) is not int or not 0 <= value < len(codec.ACTION_VOCABULARY)
           for value in token_ids):
        result.update(termination="INVALID_TOKEN_IDS", error={"code": "TOKEN_ID_INVALID"})
        return result
    ids = list(token_ids)
    result["stream_sha256"] = _digest(ids)
    result["saved_token_count"] = len(ids)
    for index, token_id in enumerate(ids):
        site = _site(state, ids, index, token_id)
        if site is not None:
            result["sites"].append(site)
        token = codec.ACTION_VOCABULARY[token_id]
        if token not in state.allowed_tokens():
            result.update(termination="INVALID_EMITTED_TOKEN",
                          error={"code": "TOKEN_NOT_ALLOWED", "token_index": index,
                                 "token_id": token_id, "token": token,
                                 "grammar_role": state.role,
                                 "allowed_ids": list(state.allowed_ids())})
            break
        state = state.advance(token)
    else:
        if state.complete:
            # EOS is checked by the actual grammar, not a role label alone.
            state.to_action()
            result.update(termination="COMPLETE", complete=True)
        else:
            site = _site(state, ids, len(ids), None)
            if site is not None:
                result["sites"].append(site)
            raw = grammar_v3._raw_allowed(state._machine, state.limits)
            budget_stop = state.dead_end and (
                len(ids) >= max_length or
                (len(ids) == max_length - 1 and bool(raw) and "[EOS]" not in raw))
            result["termination"] = ("TOKEN_BUDGET_STOP" if budget_stop else
                                     "GRAMMAR_DEAD_END" if state.dead_end else
                                     "INCOMPLETE_CONTINUABLE")
    result.update(stop_role=state.role, consumed_token_count=len(state.prefix),
                  terminal_allowed_ids=list(state.allowed_ids()),
                  completion_error=state.completion_error())
    return result


def _expected_choice(reference_site, generated_site):
    token = reference_site["chosen_token"]
    if reference_site["role"] in VALUE_ROLES:
        definition = reference_site["value_definitions"].get(token)
        names = [name for name, identity in generated_site["value_definitions"].items()
                 if definition is not None and identity == definition]
        if not names:
            return None, "MISSING_DEFINITION"
        if len(names) != 1:
            return None, "AMBIGUOUS_MAPPING"
        token = names[0]
    token_id = codec.ACTION_TO_ID[token]
    return token_id, "LEGAL" if token_id in generated_site["allowed_ids"] else "ILLEGAL"


def _summary(rows, extras):
    counts = Counter(row["correspondence"] for row in rows)
    scored = [row for row in rows if row["correct"] is not None]
    return {
        "reference_sites": len(rows), "matched": counts["MATCHED"],
        "context_changed": counts["CONTEXT_CHANGED"], "missing": counts["SITE_MISSING"],
        "ambiguous": counts["AMBIGUOUS_MAPPING"], "generated_extra_sites": len(extras),
        "expected_illegal": sum(row["expected_choice"] == "ILLEGAL" for row in rows),
        "expected_missing_definition": sum(row["expected_choice"] == "MISSING_DEFINITION" for row in rows),
        "scored": len(scored), "correct": sum(row["correct"] is True for row in scored),
        "wrong": sum(row["correct"] is False for row in scored),
        "single_option_scored": sum(row["generated_site"]["single_option"] for row in scored),
        "multi_option_scored": sum(not row["generated_site"]["single_option"] for row in scored),
        "scored_identical_prefix": sum(not row["preceding_tokens_differ"] for row in scored),
        "correct_identical_prefix": sum(
            row["correct"] is True and not row["preceding_tokens_differ"] for row in scored),
        "scored_after_prefix_divergence": sum(row["preceding_tokens_differ"] for row in scored),
        "correct_after_prefix_divergence": sum(
            row["correct"] is True and row["preceding_tokens_differ"] for row in scored),
        "matched_without_emitted_choice": sum(
            row["correspondence"] == "MATCHED" and not row["generated_site"]["observed"]
            for row in rows),
    }


def compare_sites(reference_ids, generated_ids, *, max_length=256, limits=None):
    """Compare a checked development reference with an unchanged generated stream.

    Gold choices are labels only. Changed contexts, absent sites, and ambiguous
    mappings stay in reference denominators but do not become correctness scores.
    """
    reference = extract_sites(reference_ids, max_length=max_length, limits=limits)
    if not reference["complete"]:
        raise ValueError("REFERENCE_COMPLETE_VALID_PROGRAM_REQUIRED")
    generated = extract_sites(generated_ids, max_length=max_length, limits=limits)
    indexed = defaultdict(list)
    for index, site in enumerate(generated["sites"]):
        indexed[site["key"]].append((index, site))
    rows, consumed = [], set()
    for ref in reference["sites"]:
        candidates = indexed[ref["key"]]
        row = {"reference_site": ref, "generated_site": None,
               "correspondence": "SITE_MISSING", "reason": "ADDRESS_NOT_REACHED",
               "expected_token_id": None, "expected_choice": "NO_SITE", "correct": None,
               "preceding_tokens_differ": None, "context_differences": []}
        if len(candidates) > 1:
            row.update(correspondence="AMBIGUOUS_MAPPING", reason="DUPLICATE_GENERATED_ADDRESS",
                       expected_choice="AMBIGUOUS_MAPPING")
            consumed.update(index for index, _ in candidates)
        elif candidates:
            index, gen = candidates[0]
            consumed.add(index)
            expected_id, legality = _expected_choice(ref, gen)
            differences = sorted(key for key in ref["context"]
                                 if ref["context"][key] != gen["context"][key])
            row.update(generated_site=gen, expected_token_id=expected_id, expected_choice=legality,
                       preceding_tokens_differ=ref["prefix_ids"] != gen["prefix_ids"],
                       context_differences=differences)
            if legality == "AMBIGUOUS_MAPPING":
                row.update(correspondence="AMBIGUOUS_MAPPING", reason="DUPLICATE_VALUE_DEFINITION")
            elif ref["context"] != gen["context"]:
                reason = ("PREFIX_LENGTH_OR_TOKEN_BUDGET_CHANGED" if "prefix_length" in differences
                          or "max_action_length" in differences else "CONSUMED_CONTEXT_DIFFERS")
                row.update(correspondence="CONTEXT_CHANGED", reason=reason)
            else:
                row.update(correspondence="MATCHED", reason="UNIQUE_ADDRESS_AND_CONTEXT")
                if legality == "LEGAL" and gen["observed"]:
                    row["correct"] = gen["chosen_token_id"] == expected_id
        rows.append(row)
    extras = [site for index, site in enumerate(generated["sites"]) if index not in consumed]
    summaries = {role: _summary(
        [row for row in rows if row["reference_site"]["role"] == role],
        [site for site in extras if site["role"] == role]) for role in ROLES}
    return {
        "schema": SCHEMA, "reference": reference, "generated": generated,
        "rows": rows, "extra_generated_sites": extras, "summaries": summaries,
        "totals": _summary(rows, extras),
        "boundary": "Development-prefix diagnostic only; no autonomous task success, "
                    "semantic equivalence, repaired generation, model call, or native execution.",
    }
