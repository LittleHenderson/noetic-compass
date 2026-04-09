"""CAS Assessment Notation Parser.

Parses a subset of the v6.1 BNF grammar translated to CAS terminology.

Supported notation:
  "CO-3"                          → Single operator reference
  "CO-3^E"                        → Operator in domain
  "CO-2 + CO-3"                   → Operator combination
  "CO-8 → CO-9"                   → Causal relationship
  "RPM(F5)"                       → RPM chain for a drive
  "Φ⟨2:5:8:3:9⟩" or "Phi<2:5:8>" → Cognitive fractal
  "P3" or "C7" or "E0" or "O5"   → Cognitive state
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

OPERATOR_NAMES = [
    "Identity", "Reflection", "Abstraction", "Concretization",
    "Integration", "Differentiation", "Unification", "Transformation",
    "Expansion", "Contraction",
]

DOMAIN_NAMES = {"P": "Principled", "C": "Cognitive", "E": "Evaluative", "O": "Operational"}

DRIVE_NAMES = [
    "Unity", "Wisdom", "Vitality", "Connection",
    "Agency", "Structure", "Purpose",
]


class TokenType(Enum):
    OPERATOR = "operator"        # CO-3
    DOMAIN = "domain"            # P, C, E, O
    STATE = "state"              # P3, C7, E0, O5
    DRIVE = "drive"              # F5
    SUPERSCRIPT = "superscript"  # ^E
    PLUS = "plus"                # +
    ARROW = "arrow"              # →
    RPM = "rpm"                  # RPM(...)
    FRACTAL = "fractal"          # Φ⟨...⟩
    LPAREN = "lparen"
    RPAREN = "rparen"
    UNKNOWN = "unknown"


@dataclass
class Token:
    type: TokenType
    value: str
    index: int = -1  # Numeric index if applicable


@dataclass
class ParseResult:
    """Result of parsing CAS notation."""
    tokens: list[Token] = field(default_factory=list)
    operators: list[int] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    drives: list[int] = field(default_factory=list)
    fractal: list[int] | None = None
    is_rpm: bool = False
    valid: bool = True
    error: str = ""
    raw: str = ""


# Regex patterns for tokenization
_PATTERNS = [
    (r"CO-(\d)", TokenType.OPERATOR),
    (r"Φ[⟨<]([\d:]+)[⟩>]", TokenType.FRACTAL),
    (r"Phi[⟨<]([\d:]+)[⟩>]", TokenType.FRACTAL),
    (r"RPM\(", TokenType.RPM),
    (r"F(\d)", TokenType.DRIVE),
    (r"\^([PCEO])", TokenType.SUPERSCRIPT),
    (r"([PCEO])(\d)", TokenType.STATE),
    (r"→|->", TokenType.ARROW),
    (r"\+", TokenType.PLUS),
    (r"\(", TokenType.LPAREN),
    (r"\)", TokenType.RPAREN),
]


def tokenize(notation: str) -> list[Token]:
    """Tokenize CAS notation string."""
    tokens: list[Token] = []
    pos = 0
    text = notation.strip()

    while pos < len(text):
        # Skip whitespace
        if text[pos].isspace():
            pos += 1
            continue

        matched = False
        for pattern, token_type in _PATTERNS:
            m = re.match(pattern, text[pos:])
            if m:
                if token_type == TokenType.OPERATOR:
                    idx = int(m.group(1))
                    tokens.append(Token(type=token_type, value=m.group(0), index=idx))
                elif token_type == TokenType.FRACTAL:
                    tokens.append(Token(type=token_type, value=m.group(0)))
                elif token_type == TokenType.DRIVE:
                    idx = int(m.group(1))
                    tokens.append(Token(type=token_type, value=m.group(0), index=idx))
                elif token_type == TokenType.SUPERSCRIPT:
                    tokens.append(Token(type=token_type, value=m.group(1)))
                elif token_type == TokenType.STATE:
                    domain = m.group(1)
                    op_idx = int(m.group(2))
                    tokens.append(Token(type=token_type, value=m.group(0), index=op_idx))
                else:
                    tokens.append(Token(type=token_type, value=m.group(0)))
                pos += m.end()
                matched = True
                break

        if not matched:
            tokens.append(Token(type=TokenType.UNKNOWN, value=text[pos]))
            pos += 1

    return tokens


def parse(notation: str) -> ParseResult:
    """Parse CAS notation into a structured result.

    Examples:
      "CO-3^E"          → operators=[3], domains=["E"]
      "CO-2 + CO-3"     → operators=[2, 3]
      "RPM(F5)"         → drives=[4], is_rpm=True
      "Φ⟨2:5:8:3:9⟩"   → fractal=[2,5,8,3,9]
      "P3"              → operators=[3], domains=["P"]
    """
    result = ParseResult(raw=notation)

    try:
        tokens = tokenize(notation)
        result.tokens = tokens

        for token in tokens:
            if token.type == TokenType.OPERATOR:
                if 0 <= token.index <= 9:
                    result.operators.append(token.index)
                else:
                    result.valid = False
                    result.error = f"Invalid operator index: {token.index}"

            elif token.type == TokenType.STATE:
                result.operators.append(token.index)
                domain_char = token.value[0]
                if domain_char in DOMAIN_NAMES:
                    result.domains.append(domain_char)

            elif token.type == TokenType.SUPERSCRIPT:
                if token.value in DOMAIN_NAMES:
                    result.domains.append(token.value)

            elif token.type == TokenType.DRIVE:
                if 1 <= token.index <= 7:
                    result.drives.append(token.index - 1)  # 0-indexed
                else:
                    result.valid = False
                    result.error = f"Invalid drive index: {token.index}"

            elif token.type == TokenType.RPM:
                result.is_rpm = True

            elif token.type == TokenType.FRACTAL:
                # Extract indices from Φ⟨2:5:8⟩
                inner = re.search(r"[⟨<]([\d:]+)[⟩>]", token.value)
                if inner:
                    indices = [int(x) for x in inner.group(1).split(":") if x.strip()]
                    if all(0 <= i <= 9 for i in indices) and indices:
                        result.fractal = indices
                    else:
                        result.valid = False
                        result.error = "Invalid fractal indices"

            elif token.type == TokenType.UNKNOWN:
                result.valid = False
                result.error = f"Unexpected character: '{token.value}'"

    except Exception as e:
        result.valid = False
        result.error = str(e)

    return result
