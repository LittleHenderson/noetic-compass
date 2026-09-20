"""CAS Native Cognitive Machine deterministic reference kernel."""

from .api import KernelSession, ReplayReport, boot, replay, run, validate_problem, verify_evidence
from .conversation import (
    ClarificationReason,
    ConversationTrace,
    ConversationTurn,
    ConversationalMind,
    DialogueState,
    ReferenceResolution,
    ReferenceStatus,
    TurnStatus,
)
from .cognitive_apprenticeship import (
    cognitive_apprenticeship_demo_cases,
    run_cognitive_apprenticeship_demo,
)
from .engine import CognitiveMachine, RunResult
from .language_apprenticeship import (
    language_qualification_demo_cases,
    run_language_qualification_demo,
)
from .math_api import (
    check_math_step,
    find_math_counterexample,
    parse_math_expression,
    parse_math_statement,
    solve_math,
    validate_math_notation,
    verify_math_receipt,
    verify_math_result,
    verify_counterexample_result,
)
from .math_counterexample import CounterexampleResult, CounterexampleStatus
from .math_engine import MathRunResult, MathTerminalStatus
from .math_model import ExactRational, MathClaim, MathStepProposal, MathStepReceipt
from .model import ProblemPacket, TerminalStatus

__all__ = [
    "ClarificationReason",
    "CognitiveMachine",
    "ConversationTrace",
    "ConversationTurn",
    "ConversationalMind",
    "DialogueState",
    "ExactRational",
    "KernelSession",
    "MathClaim",
    "MathRunResult",
    "MathStepProposal",
    "MathStepReceipt",
    "MathTerminalStatus",
    "ProblemPacket",
    "ReferenceResolution",
    "ReferenceStatus",
    "ReplayReport",
    "RunResult",
    "TerminalStatus",
    "TurnStatus",
    "CounterexampleResult",
    "CounterexampleStatus",
    "boot",
    "check_math_step",
    "cognitive_apprenticeship_demo_cases",
    "find_math_counterexample",
    "language_qualification_demo_cases",
    "parse_math_expression",
    "parse_math_statement",
    "replay",
    "run",
    "run_cognitive_apprenticeship_demo",
    "run_language_qualification_demo",
    "solve_math",
    "validate_math_notation",
    "validate_problem",
    "verify_evidence",
    "verify_math_receipt",
    "verify_math_result",
    "verify_counterexample_result",
]
__version__ = "0.1.0"
