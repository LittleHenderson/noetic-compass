"""Bounded CCDL document reader, without a semantic engine or execution.

Source: Appendix_C_CCDL_Language_Reference.md, raw SHA256
452d64308f860b1c0e5b6c3f4d9c8a91760822baa9b9fcd1a6e12a4797983d8f.
Reads ONE circuit/board and the explicitly supported schematic/layout forms.
Unsupported families are errors, never ignored statements or valid execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

MAX_SOURCE_BYTES = 65_536
MAX_STATEMENTS = 512
MAX_DEPTH = 32
MAX_TOKENS = 65_536
SCHEMA = "cas.pcba.document/0.1"
COMPONENT_PREFIXES = frozenset("""cjt resistor cap capacitor inductor diode zener transformer opamp oscillator
crystal varactor relay schmitt comparator integrator divider active_load mirror modulator pll tank filter diff
mux demux gate xor xnor fuse reg led adc dac rectifier""".split())
TYPE_NAMES = frozenset("""CJT Resistor Capacitor Inductor Diode Zener Transformer OpAmp Oscillator CrystalOscillator
Varactor Relay Schmitt SchmittTrigger Comparator Integrator LowPass HighPass LC PLL DutyCycle Differential
Photodiode BridgeRectifier ADC DAC LED AND OR NOT NAND NOR XOR XNOR MUX DEMUX Regulator Fuse CircuitBreaker Phi""".split())
RESERVED = COMPONENT_PREFIXES | TYPE_NAMES | frozenset("circuit board input output node feedback probe layer via let".split())
_ASCII_ID = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")
_ID = re.compile(r"[^\W\d_]\w*", re.UNICODE)
_NUMBER = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:s)?")


class PcbaParseError(ValueError):
    def __init__(self, code: str, message: str, line: int = 1, column: int = 1):
        self.code, self.line, self.column, self.message = code, line, column, message
        super().__init__(f"{code} at {line}:{column}: {message}")


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    text: str
    start: int
    end: int
    line: int
    column: int
    nesting: int = 0


def _tokenize(source: str) -> tuple[list[_Token], str]:
    tokens = []
    cleaned = list(source)
    i, line, column = 0, 1, 1

    def error(message, code="E-PCBA-SYNTAX"):
        raise PcbaParseError(code, message, line, column)

    def register(position, depth=1):
        if depth > MAX_DEPTH:
            error("Register nesting exceeds limit", "E-PCBA-LIMIT")
        if position < len(source) and source[position] in "TAfE":
            return position + 1, depth
        if position >= len(source) or source[position] != "⟨":
            error("Malformed register value", "E-PCBA-STATE")
        position, maximum = register(position + 1, depth + 1)
        while position < len(source) and source[position] == ",":
            position, nested = register(position + 1, depth + 1)
            maximum = max(maximum, nested)
        if position >= len(source) or source[position] != "⟩":
            error("Unclosed register set", "E-PCBA-STATE")
        return position + 1, maximum

    while i < len(source):
        char = source[i]
        if char.isspace() or (i == 0 and char == "\ufeff"):
            if char == "\n":
                line, column = line + 1, 1
            else:
                column += 1
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            end = len(source) if end < 0 else end
            for index in range(i, end):
                cleaned[index] = " "
            column += end - i
            i = end
            continue
        if source.startswith("/*", i):
            error("Block comments are not part of CCDL", "E-PCBA-UNSUPPORTED")
        start, start_column, nesting = i, column, 0
        if char == '"':
            end = source.find('"', i + 1)
            if end < 0 or "\n" in source[i:end] or "\r" in source[i:end]:
                error("Strings must be closed on one line")
            i, kind = end + 1, "STRING"
        elif char == "^":
            if i + 1 >= len(source):
                error("Incomplete CAS literal", "E-PCBA-STATE")
            value = source[i + 1]
            if value in "PCEO":
                i, kind = i + 2, "DOMAIN"
            elif value in "0123456789":
                i, kind = i + 2, "STATE"
                if i < len(source) and source[i] == "^":
                    if i + 1 >= len(source) or source[i + 1] not in "PCEO":
                        error("Unknown CAS domain", "E-PCBA-STATE")
                    i += 2
                if source.startswith("_{", i):
                    drive = re.match(r"_\{F[1-7]\}", source[i:])
                    if not drive:
                        error("Malformed CAS drive", "E-PCBA-STATE")
                    i += len(drive.group())
                    nesting = 1
                if i < len(source) and source[i] == "|" and i + 1 < len(source) and not source[i + 1].isspace():
                    i, reg_depth = register(i + 1)
                    nesting = max(nesting, reg_depth)
                if i < len(source) and (source[i].isalnum() or source[i] in "_^⟩"):
                    error("Trailing text inside CAS literal", "E-PCBA-STATE")
            else:
                error("CAS literal requires a Noetic digit or domain", "E-PCBA-STATE")
        else:
            operator = next((op for op in ("=>", "->", "<=", "==", "::", ">=", "!=") if source.startswith(op, i)), None)
            number = _NUMBER.match(source, i)
            word = _ID.match(source, i)
            if operator:
                i, kind = i + len(operator), "PUNCT"
            elif number:
                i = number.end()
                kind = "DURATION" if number.group().endswith("s") else "NUMBER"
            elif word:
                i, kind = word.end(), "ID"
            elif char in "{}[]()<>,:;=.|":
                i, kind = i + 1, "PUNCT"
            else:
                error("Unsupported character %r" % char, "E-PCBA-UNSUPPORTED")
        tokens.append(_Token(kind, source[start:i], start, i, line, start_column, nesting))
        column += i - start
        if len(tokens) > MAX_TOKENS:
            error("Token count exceeds limit", "E-PCBA-LIMIT")
    tokens.append(_Token("EOF", "", len(source), len(source), line, column))
    return tokens, "".join(cleaned)


class _Reader:
    def __init__(self, source):
        self.tokens, self.source = _tokenize(source)
        self.index, self.statement_count, self.depth = 0, 0, 0

    @property
    def token(self):
        return self.tokens[self.index]

    def next_text(self):
        return self.tokens[min(self.index + 1, len(self.tokens) - 1)].text

    def fail(self, message, code="E-PCBA-SYNTAX", token=None):
        token = token or self.token
        raise PcbaParseError(code, message, token.line, token.column)

    def take(self, text=None):
        token = self.token
        if text is not None and token.text != text:
            self.fail("Expected %r, got %r" % (text, token.text))
        if token.kind == "EOF":
            self.fail("Unexpected end of document")
        self.index += 1
        return token

    def identifier(self):
        token = self.token
        if token.kind != "ID" or not _ASCII_ID.fullmatch(token.text) or token.text in RESERVED:
            self.fail("Expected a nonreserved ASCII identifier")
        self.take()
        return token.text

    def raw(self, start):
        return self.source[self.tokens[start].start:self.tokens[self.index - 1].end].strip()

    def enter(self, symbol):
        self.take(symbol)
        self.depth += 1
        if self.depth > MAX_DEPTH:
            self.fail("Nesting exceeds limit", "E-PCBA-LIMIT")

    def leave(self, symbol):
        self.take(symbol)
        self.depth -= 1

    def state(self):
        if self.token.kind != "STATE":
            self.fail("A node requires a full CAS state literal", "E-PCBA-STATE")
        if self.depth + self.token.nesting > MAX_DEPTH:
            self.fail("CAS literal nesting exceeds limit", "E-PCBA-LIMIT")
        return self.take().text

    def count_statement(self, token):
        self.statement_count += 1
        if self.statement_count > MAX_STATEMENTS:
            self.fail("Statement count exceeds limit", "E-PCBA-LIMIT", token)

    def reference(self, *, endpoint=False):
        start = self.index
        if self.token.kind == "STATE":
            self.state()
        elif self.token.kind == "DOMAIN":
            self.take()
        elif not endpoint:
            self.identifier()
        else:
            self.fail("Via endpoints must be a state or domain")
        if not endpoint:
            while True:
                if self.token.text == ".":
                    self.take()
                    self.identifier()
                elif (self.token.text == "[" and self.index + 2 < len(self.tokens)
                      and self.tokens[self.index + 1].kind in ("ID", "NUMBER")
                      and self.tokens[self.index + 2].text == "]"):
                    self.enter("[")
                    if self.token.kind == "ID":
                        self.identifier()
                    else:
                        self.take()
                    self.leave("]")
                else:
                    break
        return self.raw(start)

    def value(self):
        if self.token.text == "[":
            self.enter("[")
            self.value()
            while self.token.text == ",":
                self.take()
                self.value()
            self.leave("]")
        elif self.token.kind in ("NUMBER", "DURATION"):
            self.take()
        elif self.token.kind == "STATE":
            self.state()
        elif self.token.kind == "ID":
            self.take()  # values may be reserved region/parameter words
            if self.token.text == "::":
                self.take()
                if self.token.kind != "ID":
                    self.fail("Expected qualified symbol member")
                self.take()
        elif self.token.kind == "STRING":
            self.fail("String-valued parameters are outside the declared subset", "E-PCBA-UNSUPPORTED")
        else:
            self.fail("Expected a CCDL parameter value")

    def assignment(self, parameters, *, rail_qualifier=False):
        key = self.take()
        if key.kind != "ID":
            self.fail("Expected a parameter key", token=key)
        if key.text in parameters:
            self.fail("Duplicate parameter %s" % key.text, "E-PCBA-DUPLICATE-PARAMETER", key)
        self.take("=")
        start = self.index
        self.value()
        if rail_qualifier and self.token.text == "on":
            self.take()
            if not re.fullmatch("F[1-7]", self.token.text):
                self.fail("Rail qualifier must name F1..F7")
            self.take()
        parameters[key.text] = self.raw(start)

    def parameters(self, existing=None):
        result = {} if existing is None else existing
        if self.token.text != "[":
            return result
        self.enter("[")
        self.assignment(result, rail_qualifier=True)
        while self.token.text == ",":
            self.take()
            self.assignment(result, rail_qualifier=True)
        self.leave("]")
        return result

    def argument(self, parameters):
        if self.token.kind == "ID" and self.next_text() == "=":
            self.assignment(parameters)
        elif self.token.text == "Phi" and self.next_text() == "<":
            self.take()
            self.enter("<")
            self.reference()
            while self.token.text == ",":
                self.take()
                self.reference()
            self.leave(">")
        else:
            self.reference()
            while self.token.text == "|":
                self.take()
                self.reference()
            if self.token.text == "->":
                self.take()
                self.reference()
                while self.token.text == "|":
                    self.take()
                    self.reference()

    def component(self):
        start = self.index
        name = self.take()
        if name.kind != "ID" or not _ASCII_ID.fullmatch(name.text):
            self.fail("Expected component type", token=name)
        if self.token.text != "<":
            self.fail("Only Type<...> components are supported; call/alias forms need another capability", "E-PCBA-UNSUPPORTED")
        self.enter("<")
        parameters = {}
        if name.text == "CJT":
            self.reference()
            self.take("|")
            self.reference()
            self.take("=>")
            self.reference()
        else:
            self.argument(parameters)
            while self.token.text == ",":
                self.take()
                self.argument(parameters)
        self.leave(">")
        self.parameters(parameters)
        return self.raw(start)

    def operand(self):
        start = self.index
        if self.token.kind == "NUMBER":
            self.take()
        else:
            self.reference()
            if self.token.text == "(":
                self.fail("Call operands are outside the schematic assertion subset", "E-PCBA-UNSUPPORTED")
        return self.raw(start)

    def statement(self, document_kind):
        leader = self.take()
        self.count_statement(leader)
        kind = leader.text
        result = {"kind": kind, "location": {"line": leader.line, "column": leader.column}}
        if kind in ("input", "output"):
            self.take(":")
            names = [self.identifier()]
            while self.token.text == ",":
                self.take()
                names.append(self.identifier())
            result["names"] = names
        elif kind == "node":
            result["name"] = self.identifier()
            self.take(":")
            result["state"] = self.state()
        elif kind in COMPONENT_PREFIXES or kind == "let":
            result.update(kind="component", prefix=kind, name=self.identifier())
            self.take("=" if kind == "let" else ":")
            result["expression"] = self.component()
        elif kind == "probe":
            result["name"] = self.identifier()
            self.take(":")
            result["target"] = self.reference()
        elif kind in ("feedback", "via", "transition", "series"):
            if kind == "via" and document_kind != "board":
                self.fail("via is board-only", "E-PCBA-UNSUPPORTED", leader)
            name = None
            if kind in ("via", "transition") or (kind == "feedback" and self.next_text() == ":"):
                name = self.identifier()
                self.take(":")
            result["name"] = name
            result["source"] = self.reference(endpoint=kind == "via")
            self.take("->")
            result["target"] = self.reference(endpoint=kind == "via")
            result["parameters"] = self.parameters() if kind in ("feedback", "via") else {}
        elif kind == "layer":
            if document_kind != "board":
                self.fail("layer is board-only", "E-PCBA-UNSUPPORTED", leader)
            tag = self.take()
            if tag.text not in ("P", "C", "E", "O"):
                self.fail("Layer domain must be P, C, E, or O", token=tag)
            result.update(name=tag.text, domain=tag.text, statements=[])
            self.take(":")
            self.enter("[")
            while True:
                entry = self.token
                self.count_statement(entry)
                entry_name = self.identifier()
                self.take(":")
                result["statements"].append({"kind": "node", "name": entry_name, "state": self.state(),
                                             "location": {"line": entry.line, "column": entry.column}})
                if self.token.text != ",":
                    break
                self.take()
            self.leave("]")
        elif kind == "assert":
            if self.token.text == ":":
                self.take()
            result["left"] = self.operand()
            operator = self.take()
            if operator.text not in ("<", ">", "<=", "=="):
                self.fail("Only <, >, <=, == schematic comparisons are supported", "E-PCBA-UNSUPPORTED", operator)
            result["operator"] = operator.text
            result["right"] = self.operand()
        else:
            self.fail("Statement family %r is not supported by this reader" % kind, "E-PCBA-UNSUPPORTED", leader)
        self.take(";")
        return result

    def document(self):
        kind = self.take()
        if kind.text not in ("circuit", "board"):
            self.fail("Expected one circuit or board block", "E-PCBA-UNSUPPORTED", kind)
        name = self.identifier()
        self.enter("{")
        statements = []
        while self.token.text != "}":
            if self.token.kind == "EOF":
                self.fail("Unclosed document block")
            statements.append(self.statement(kind.text))
        self.leave("}")
        if self.token.kind != "EOF":
            self.fail("Only one complete circuit or board is accepted", "E-PCBA-UNSUPPORTED")
        return {"schema": SCHEMA, "kind": kind.text, "name": name, "statements": statements}


def parse_pcba_document(source: str | bytes) -> dict:
    """Return syntax only, with 1-based original line/character columns.

Hash is SHA256 of exact UTF-8 source bytes, including comments/newlines/BOM.
Raw expression/ref/parameter fields preserve semantic text and whitespace;
comments are replaced by spaces, including inside multiline expressions.
Duplicate parameter keys are errors rather than last-value-wins mutation.
"""
    if type(source) not in (str, bytes):
        raise PcbaParseError("E-PCBA-ENCODING", "Source must be Unicode text or UTF-8 bytes")
    try:
        body = source.encode("utf-8", errors="strict") if type(source) is str else source
        if len(body) > MAX_SOURCE_BYTES:
            raise PcbaParseError("E-PCBA-LIMIT", "UTF-8 source exceeds 64 KiB")
        text = body.decode("utf-8", errors="strict")
    except UnicodeError as error:
        raise PcbaParseError("E-PCBA-ENCODING", "Invalid UTF-8 source") from error
    result = _Reader(text).document()
    result["source_sha256"] = hashlib.sha256(body).hexdigest()
    return result
