"""Pure prefix grammar for the existing CAS-META-2 codec and IR.

Masks depend only on generated tokens and explicit published-language bounds.
They never receive a public problem, expected program, task parser, output,
checkpoint, or native runtime. Structural admission is not task correctness.
Backward and forward calls are both legal; a prefix is never repaired.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .codec import (
    ACTION_TO_ID, ACTION_VOCABULARY, CJT_NAMES, DEFAULT_MAX_ACTION_LENGTH,
    PROCEDURE_NAMES, SCHEMA, VARIABLE_NAMES, PolicyContractError,
    tokens_to_action, validate_action,
)
from .ir import IRValidationError, Limits, validate_program


GRAMMAR_SCHEMA = 'cas-meta2-prefix-grammar/0.1'
# Sixteen codec procedures, each with four scope symbols and 32 four-token
# steps, plus declaration/return markers, BOS, binding and EOS.
MAX_REPRESENTABLE_TOKENS = 16 * (3 + 4 + 1 + 32 * 4 + 3) + 3
_ORDER = {name: i for i, name in enumerate(sorted(PROCEDURE_NAMES,
                                                        key=lambda n: (n != 'main', n)))}


class GrammarError(ValueError):
    def __init__(self, code, *, role=None, token=None):
        self.code, self.role, self.token = code, role, token
        super().__init__(code)


@dataclass
class _Machine:
    role: str = 'bos'
    binding: int | None = None
    procedures: dict = field(default_factory=dict)
    edges: dict = field(default_factory=dict)
    current: str | None = None
    last_name: str | None = None
    available: set = field(default_factory=set)
    step: dict = field(default_factory=dict)
    instructions: int = 0

    def reaches(self, start, target):
        seen, pending = set(), [start]
        while pending:
            name = pending.pop()
            if name == target:
                return True
            if name not in seen:
                seen.add(name)
                pending.extend(self.edges.get(name, ()))
        return False

    def pending_names(self):
        return {name for children in self.edges.values() for name in children
                if name not in self.procedures}

    def action(self):
        return {'binding': self.binding, 'program': {
            'schema': SCHEMA, 'entry': 'main', 'procedures': deepcopy(self.procedures)}}


def _completion_error(machine, limits):
    try:
        action = machine.action()
        validate_action(action)
        validate_program(action['program'], limits)
    except IRValidationError as exc:
        return exc.code
    except PolicyContractError as exc:
        return str(exc)
    return None


def _declaration_names(machine, limits):
    if len(machine.procedures) >= min(16, limits.max_procedures):
        return set()
    if not machine.procedures:
        return {'main'}
    # Do not jump over an already-called undeclared name: canonical ordering
    # would then make its required later declaration impossible.
    pending = machine.pending_names()
    ceiling = min((_ORDER[name] for name in pending), default=len(_ORDER))
    return {name for name in PROCEDURE_NAMES if name not in machine.procedures
            and _ORDER[machine.last_name] < _ORDER[name] <= ceiling}


def _raw_allowed(machine, limits):
    role = machine.role
    if role == 'bos':
        return {'[BOS]'}
    if role == 'observation_binding':
        return {'BIND0', 'BIND1', 'BIND2'}
    if role == 'procedure_or_eos':
        result = {'PROC'} if _declaration_names(machine, limits) else set()
        if machine.procedures and _completion_error(machine, limits) is None:
            result.add('[EOS]')
        return result
    if role == 'procedure_name':
        return _declaration_names(machine, limits)
    if role == 'allow_marker':
        return {'ALLOW'}
    if role == 'allowed_cjt':
        scope = machine.procedures[machine.current]['allowed_cjts']
        allowed = set(CJT_NAMES) - set(scope)
        for parent, children in machine.edges.items():
            if machine.current in children:
                allowed &= set(machine.procedures[parent]['allowed_cjts'])
        return allowed | ({'ENDALLOW'} if scope else set())
    if role == 'step_kind_or_return':
        steps = machine.procedures[machine.current]['steps']
        result = {'RETURN'} if steps else set()
        if len(steps) < 32 and machine.instructions < limits.max_instructions:
            if set(VARIABLE_NAMES[1:]) - machine.available:
                result.update(('RUN', 'CALL'))
        return result
    if role == 'run_cjt':
        return set(machine.procedures[machine.current]['allowed_cjts'])
    if role == 'call_target':
        result = set()
        parent_scope = set(machine.procedures[machine.current]['allowed_cjts'])
        pending = machine.pending_names()
        for name in PROCEDURE_NAMES:
            if machine.reaches(name, machine.current):
                continue
            if name in machine.procedures:
                if not set(machine.procedures[name]['allowed_cjts']) <= parent_scope:
                    continue
            else:
                if _ORDER[name] <= _ORDER[machine.last_name]:
                    continue
                if len(machine.procedures) + len(pending | {name}) > min(16, limits.max_procedures):
                    continue
            result.add(name)
        return result
    if role == 'step_input':
        return set(machine.available)
    if role == 'step_output':
        return set(VARIABLE_NAMES[1:]) - machine.available
    if role == 'return_value':
        # The IR permits returning arg. Native accepted-Effect/topology checks
        # remain separate; this grammar does not introduce task-specific rules.
        return set(machine.available)
    if role == 'endproc_marker':
        return {'ENDPROC'}
    if role == 'complete':
        return set()
    raise GrammarError('UNKNOWN_GRAMMAR_STATE', role=role)


def _allowed(machine, limits, used, max_length):
    if used >= max_length:
        return ()
    result = _raw_allowed(machine, limits)
    if used == max_length - 1:
        result &= {'[EOS]'}
    return tuple(token for token in ACTION_VOCABULARY if token in result)


def _consume(machine, token):
    role = machine.role
    if role == 'bos':
        machine.role = 'observation_binding'
    elif role == 'observation_binding':
        machine.binding = int(token[-1])
        machine.role = 'procedure_or_eos'
    elif role == 'procedure_or_eos':
        machine.role = 'complete' if token == '[EOS]' else 'procedure_name'
    elif role == 'procedure_name':
        machine.current = machine.last_name = token
        machine.procedures[token] = {'input': 'arg', 'allowed_cjts': [], 'steps': [], 'return': None}
        machine.edges[token] = set()
        machine.available = {'arg'}
        machine.role = 'allow_marker'
    elif role == 'allow_marker':
        machine.role = 'allowed_cjt'
    elif role == 'allowed_cjt':
        if token == 'ENDALLOW':
            machine.role = 'step_kind_or_return'
        else:
            machine.procedures[machine.current]['allowed_cjts'].append(token)
    elif role == 'step_kind_or_return':
        if token == 'RETURN':
            machine.role = 'return_value'
        else:
            machine.step = {'kind': token}
            machine.role = 'run_cjt' if token == 'RUN' else 'call_target'
    elif role in ('run_cjt', 'call_target'):
        machine.step['cjt_id' if role == 'run_cjt' else 'procedure'] = token
        machine.role = 'step_input'
    elif role == 'step_input':
        machine.step['input'] = token
        machine.role = 'step_output'
    elif role == 'step_output':
        machine.step['output'] = token
        machine.procedures[machine.current]['steps'].append(machine.step)
        if machine.step['kind'] == 'CALL':
            machine.edges[machine.current].add(machine.step['procedure'])
        machine.instructions += 1
        machine.available.add(token)
        machine.step = {}
        machine.role = 'step_kind_or_return'
    elif role == 'return_value':
        machine.procedures[machine.current]['return'] = token
        machine.role = 'endproc_marker'
    elif role == 'endproc_marker':
        machine.current = None
        machine.available = set()
        machine.role = 'procedure_or_eos'
    else:
        raise GrammarError('TOKEN_AFTER_COMPLETION', role=role, token=token)


@dataclass(frozen=True)
class GrammarState:
    """Immutable public prefix state; advance returns a detached new state.

    Default limits are the frozen codec/IR defaults, not native task semantics.
    A caller may explicitly register smaller bounds. No valid continuation is
    forced or invented when a generated prefix reaches a dead end.
    """
    prefix: tuple[str, ...] = ()
    max_length: int = DEFAULT_MAX_ACTION_LENGTH
    limits: Limits = field(default_factory=Limits)
    _machine: _Machine = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if type(self.max_length) is not int or not 2 <= self.max_length <= MAX_REPRESENTABLE_TOKENS:
            raise GrammarError('GRAMMAR_LENGTH_BOUND_INVALID')
        if type(self.limits) is not Limits:
            raise GrammarError('GRAMMAR_LIMITS_INVALID')
        if type(self.prefix) not in (tuple, list) or len(self.prefix) > self.max_length:
            raise GrammarError('GRAMMAR_PREFIX_INVALID_OR_TOO_LONG')
        object.__setattr__(self, 'prefix', tuple(self.prefix))
        machine = _Machine()
        for used, token in enumerate(self.prefix):
            if type(token) is not str or token not in _allowed(machine, self.limits, used, self.max_length):
                raise GrammarError('TOKEN_NOT_ALLOWED', role=machine.role, token=token)
            _consume(machine, token)
        object.__setattr__(self, '_machine', machine)

    @classmethod
    def from_ids(cls, prefix_ids, **kwargs):
        if type(prefix_ids) not in (tuple, list) or any(
            type(i) is not int or not 0 <= i < len(ACTION_VOCABULARY) for i in prefix_ids
        ):
            raise GrammarError('GRAMMAR_TOKEN_IDS_INVALID')
        return cls(tuple(ACTION_VOCABULARY[i] for i in prefix_ids), **kwargs)

    @property
    def role(self):
        return self._machine.role

    @property
    def complete(self):
        return self.role == 'complete'

    @property
    def dead_end(self):
        return not self.complete and not self.allowed_tokens()

    def allowed_tokens(self):
        return _allowed(self._machine, self.limits, len(self.prefix), self.max_length)

    def allowed_ids(self):
        return tuple(ACTION_TO_ID[token] for token in self.allowed_tokens())

    def mask(self):
        allowed = set(self.allowed_ids())
        return tuple(i in allowed for i in range(len(ACTION_VOCABULARY)))

    def advance(self, token):
        if type(token) is not str or token not in self.allowed_tokens():
            raise GrammarError('TOKEN_NOT_ALLOWED', role=self.role, token=token)
        # Reuse validated prefix state without rescanning all earlier tokens.
        # The copy keeps sibling branches and their available values detached.
        other = object.__new__(type(self))
        object.__setattr__(other, 'prefix', self.prefix + (token,))
        object.__setattr__(other, 'max_length', self.max_length)
        object.__setattr__(other, 'limits', self.limits)
        machine = deepcopy(self._machine)
        _consume(machine, token)
        object.__setattr__(other, '_machine', machine)
        return other

    def advance_id(self, token_id):
        if type(token_id) is not int or not 0 <= token_id < len(ACTION_VOCABULARY):
            raise GrammarError('GRAMMAR_TOKEN_IDS_INVALID')
        return self.advance(ACTION_VOCABULARY[token_id])

    def completion_error(self):
        if self.role not in ('procedure_or_eos', 'complete'):
            return 'PROGRAM_PREFIX_INCOMPLETE'
        return _completion_error(self._machine, self.limits)

    def to_action(self):
        if not self.complete:
            raise GrammarError('PROGRAM_PREFIX_INCOMPLETE')
        action = tokens_to_action(list(self.prefix), max_length=self.max_length)
        validate_program(action['program'], self.limits)
        return action


def allowed_token_ids(prefix_ids, *, max_length=DEFAULT_MAX_ACTION_LENGTH, limits=None):
    return GrammarState.from_ids(prefix_ids, max_length=max_length,
                                 limits=Limits() if limits is None else limits).allowed_ids()


def token_mask(prefix_ids, *, max_length=DEFAULT_MAX_ACTION_LENGTH, limits=None):
    return GrammarState.from_ids(prefix_ids, max_length=max_length,
                                 limits=Limits() if limits is None else limits).mask()
