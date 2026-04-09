"""Tests for CAS notation parser and renderer."""

from api.notation.parser import parse, tokenize, TokenType
from api.notation.renderer import render_plain_english, render_assessment_config


class TestTokenizer:
    def test_single_operator(self):
        tokens = tokenize("CO-3")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.OPERATOR
        assert tokens[0].index == 3

    def test_operator_with_domain(self):
        tokens = tokenize("CO-3^E")
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.OPERATOR
        assert tokens[1].type == TokenType.SUPERSCRIPT
        assert tokens[1].value == "E"

    def test_operator_combination(self):
        tokens = tokenize("CO-2 + CO-3")
        assert len(tokens) == 3
        assert tokens[0].type == TokenType.OPERATOR
        assert tokens[1].type == TokenType.PLUS
        assert tokens[2].type == TokenType.OPERATOR

    def test_fractal(self):
        tokens = tokenize("Phi<2:5:8:3:9>")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.FRACTAL

    def test_rpm(self):
        tokens = tokenize("RPM(F5)")
        assert any(t.type == TokenType.RPM for t in tokens)
        assert any(t.type == TokenType.DRIVE for t in tokens)

    def test_cognitive_state(self):
        tokens = tokenize("P3")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.STATE
        assert tokens[0].index == 3

    def test_arrow(self):
        tokens = tokenize("CO-8 → CO-9")
        assert any(t.type == TokenType.ARROW for t in tokens)


class TestParser:
    def test_single_operator(self):
        result = parse("CO-3")
        assert result.valid
        assert result.operators == [3]

    def test_operator_with_domain(self):
        result = parse("CO-3^E")
        assert result.valid
        assert result.operators == [3]
        assert result.domains == ["E"]

    def test_two_operators(self):
        result = parse("CO-2 + CO-3")
        assert result.valid
        assert result.operators == [2, 3]

    def test_rpm_drive(self):
        result = parse("RPM(F5)")
        assert result.valid
        assert result.is_rpm
        assert result.drives == [4]  # 0-indexed

    def test_fractal_unicode(self):
        result = parse("Phi<2:5:8:3:9>")
        assert result.valid
        assert result.fractal == [2, 5, 8, 3, 9]

    def test_cognitive_state(self):
        result = parse("E7")
        assert result.valid
        assert result.operators == [7]
        assert result.domains == ["E"]

    def test_invalid_operator(self):
        # CO-15 would be out of range but our regex only captures single digit
        result = parse("XYZ")
        assert not result.valid

    def test_arrow_notation(self):
        result = parse("CO-8 → CO-9")
        assert result.valid
        assert result.operators == [8, 9]


class TestRenderer:
    def test_plain_english_operator(self):
        result = parse("CO-3^E")
        text = render_plain_english(result)
        assert "CO-3" in text
        assert "Concretization" in text
        assert "Evaluative" in text

    def test_plain_english_rpm(self):
        result = parse("RPM(F5)")
        text = render_plain_english(result)
        assert "Agency" in text
        assert "RPM" in text

    def test_plain_english_fractal(self):
        result = parse("Phi<1:4:7>")
        text = render_plain_english(result)
        assert "Fractal" in text
        assert "1:4:7" in text

    def test_assessment_config(self):
        result = parse("CO-2^P + CO-5^C")
        config = render_assessment_config(result)
        assert 2 in config["target_operators"]
        assert 5 in config["target_operators"]
        assert "P" in config["target_domains"]
        assert "C" in config["target_domains"]

    def test_invalid_notation_render(self):
        result = parse("!!!invalid!!!")
        text = render_plain_english(result)
        assert "Invalid" in text
