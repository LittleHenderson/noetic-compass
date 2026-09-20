"""Candidate grammar: remove two provably noncompletable prefix choices.

No problem, gold program, model scores or native result is consulted. This is
not a complete viability solver: other dead ends remain explicit rejections.
The accepted IR, vocabulary, scopes and resource limits are unchanged.
"""
from copy import deepcopy
from dataclasses import dataclass, field

from . import grammar_v3 as frozen
from .codec import ACTION_TO_ID, ACTION_VOCABULARY, DEFAULT_MAX_ACTION_LENGTH
from .ir import Limits

GrammarError = frozen.GrammarError
SCHEMA = 'cas-meta2-prefix-viability/0.1'


def _allowed(base):
    allowed = set(base.allowed_tokens())
    machine = base._machine
    # Closed declared procedures cannot acquire new edges. With no outstanding
    # forward call, another declaration can never become reachable from main.
    if (base.role == 'procedure_or_eos' and machine.procedures
            and not machine.pending_names()):
        allowed.discard('PROC')
    # Do not emit the CALL marker when every target is already structurally
    # forbidden. No legal next token could complete that instruction.
    if base.role == 'step_kind_or_return' and 'CALL' in allowed:
        probe = deepcopy(machine)
        probe.role = 'call_target'
        if not frozen._raw_allowed(probe, base.limits):
            allowed.discard('CALL')
    return tuple(token for token in ACTION_VOCABULARY if token in allowed)


@dataclass(frozen=True)
class GrammarState:
    prefix: tuple[str, ...] = ()
    max_length: int = DEFAULT_MAX_ACTION_LENGTH
    limits: Limits = field(default_factory=Limits)
    _base: frozen.GrammarState = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        # Preserve every original constructor/type/length check, then verify
        # the additional prefix rules so from_ids cannot bypass advance.
        checked = frozen.GrammarState(self.prefix, self.max_length, self.limits)
        base = frozen.GrammarState(max_length=self.max_length, limits=self.limits)
        for token in checked.prefix:
            if token not in _allowed(base):
                raise GrammarError('NONCOMPLETABLE_PREFIX_CHOICE', role=base.role, token=token)
            base = base.advance(token)
        object.__setattr__(self, 'prefix', checked.prefix)
        object.__setattr__(self, '_base', base)

    @classmethod
    def from_ids(cls, prefix_ids, **kwargs):
        base = frozen.GrammarState.from_ids(prefix_ids, **kwargs)
        return cls(base.prefix, base.max_length, base.limits)

    @property
    def role(self):
        return self._base.role

    @property
    def complete(self):
        return self._base.complete

    @property
    def dead_end(self):
        return not self.complete and not self.allowed_tokens()

    def allowed_tokens(self):
        return _allowed(self._base)

    def allowed_ids(self):
        return tuple(ACTION_TO_ID[token] for token in self.allowed_tokens())

    def mask(self):
        allowed = set(self.allowed_ids())
        return tuple(i in allowed for i in range(len(ACTION_VOCABULARY)))

    def advance(self, token):
        if type(token) is not str or token not in self.allowed_tokens():
            raise GrammarError('TOKEN_NOT_ALLOWED', role=self.role, token=token)
        base = self._base.advance(token)
        other = object.__new__(type(self))
        for name, value in (('prefix', base.prefix), ('max_length', self.max_length),
                            ('limits', self.limits), ('_base', base)):
            object.__setattr__(other, name, value)
        return other

    def advance_id(self, token_id):
        if type(token_id) is not int or not 0 <= token_id < len(ACTION_VOCABULARY):
            raise GrammarError('GRAMMAR_TOKEN_IDS_INVALID')
        return self.advance(ACTION_VOCABULARY[token_id])

    def completion_error(self):
        return self._base.completion_error()

    def to_action(self):
        return self._base.to_action()
