"""CAS-Native model components."""

from .embedding import CognitiveStateEmbedding, CognitiveStateEmbeddingWithRegister
from .domain_descent import DomainDescentAttention
from .rpm_gate import PrerequisiteGateLayer
from .fractal_attention import FractalAttentionHead
from .loss import CognitiveMetricLoss, InvolutionConstraintLoss, ProposerRuleFourLoss
from .expression_proposer import (
    ExpressionProposerHead,
    ExpressionProposal,
    NUM_NOETICS,
    NUM_DOMAINS,
    DEFAULT_MAX_OPERANDS,
    DEFAULT_BOTTLENECK_DIM,
    OPERAND_COUNT_BUCKETS,
)
from .structured_prediction import (
    AUTHORITY_LABELS,
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
    StructuredPrediction,
    StructuredPredictionHead,
    structured_prediction_loss,
)
from .register_film import (
    RegisterFiLM,
    NUM_REGISTERS,
    REGISTER_INDEX,
    REGISTER_SYMBOL,
    INVOLUTION_REGISTER_PAIRS,
)
from .topos_reasoner import CognitiveToposReasoner
from .meta_logic_constructs import (
    CASConstructKind,
    CONSTRUCT_VOCABULARY,
    EXPRESSION_KIND_LABELS,
    META_LOGIC_EXEMPLARS,
    classify_expression,
    construct_tokens,
)
from .cas_native_model import CASNativeModel, CASNativeConfig

__all__ = [
    "CognitiveStateEmbedding",
    "CognitiveStateEmbeddingWithRegister",
    "DomainDescentAttention",
    "PrerequisiteGateLayer",
    "FractalAttentionHead",
    "CognitiveMetricLoss",
    "InvolutionConstraintLoss",
    "ProposerRuleFourLoss",
    "ExpressionProposerHead",
    "ExpressionProposal",
    "NUM_NOETICS",
    "NUM_DOMAINS",
    "DEFAULT_MAX_OPERANDS",
    "DEFAULT_BOTTLENECK_DIM",
    "OPERAND_COUNT_BUCKETS",
    "AUTHORITY_LABELS",
    "DOMAIN_LABELS",
    "DRIVE_LABELS",
    "EXPRESSION_FAMILY_LABELS",
    "META_RELATION_LABELS",
    "REGISTER_LABELS",
    "REGISTER_MODE_LABELS",
    "TRANSITION_KIND_LABELS",
    "TURN_TYPE_LABELS",
    "StructuredPrediction",
    "StructuredPredictionHead",
    "structured_prediction_loss",
    "RegisterFiLM",
    "NUM_REGISTERS",
    "REGISTER_INDEX",
    "REGISTER_SYMBOL",
    "INVOLUTION_REGISTER_PAIRS",
    "CognitiveToposReasoner",
    "CASConstructKind",
    "CONSTRUCT_VOCABULARY",
    "EXPRESSION_KIND_LABELS",
    "META_LOGIC_EXEMPLARS",
    "classify_expression",
    "construct_tokens",
    "CASNativeModel",
    "CASNativeConfig",
]
