"""CAS-Native model components."""

from .embedding import CognitiveStateEmbedding, CognitiveStateEmbeddingWithRegister
from .domain_descent import DomainDescentAttention
from .rpm_gate import PrerequisiteGateLayer
from .fractal_attention import FractalAttentionHead
from .loss import CognitiveMetricLoss, InvolutionConstraintLoss
from .register_film import (
    RegisterFiLM,
    NUM_REGISTERS,
    REGISTER_INDEX,
    REGISTER_SYMBOL,
    INVOLUTION_REGISTER_PAIRS,
)
from .topos_reasoner import CognitiveToposReasoner
from .cas_native_model import CASNativeModel, CASNativeConfig

__all__ = [
    "CognitiveStateEmbedding",
    "CognitiveStateEmbeddingWithRegister",
    "DomainDescentAttention",
    "PrerequisiteGateLayer",
    "FractalAttentionHead",
    "CognitiveMetricLoss",
    "InvolutionConstraintLoss",
    "RegisterFiLM",
    "NUM_REGISTERS",
    "REGISTER_INDEX",
    "REGISTER_SYMBOL",
    "INVOLUTION_REGISTER_PAIRS",
    "CognitiveToposReasoner",
    "CASNativeModel",
    "CASNativeConfig",
]
