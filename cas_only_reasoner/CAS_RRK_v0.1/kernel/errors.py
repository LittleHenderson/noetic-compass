"""Typed kernel faults. Every violation surfaces as one of these."""


class KernelFault(Exception):
    """Base class for all typed kernel faults."""


class AuthorityViolation(KernelFault):
    """An intent exceeded its issuer's authority or failed validation."""


class StackFault(KernelFault):
    """An RPM stack rule was violated (missing parent, lost return address)."""


class BudgetExhausted(KernelFault):
    """A resource budget (branches, ticks) was consumed."""


class LoopLimitReached(KernelFault):
    """Repeated state without progress hit the tick ceiling."""


class TraceSealError(KernelFault):
    """An attempt to authorize a transition or stop without a sealed trace."""


class ConflictError(KernelFault):
    """Intents could not be resolved deterministically."""
