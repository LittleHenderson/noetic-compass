"""Tests for api.notation.color_palette — CAS value-keyed color palette."""

import re
import pytest

from api.notation.color_palette import (
    PALETTE_VERSION,
    noetic_color,
    domain_color,
    drive_color,
    register_treatment,
    axis_color_for_node,
)

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _is_hex(s: str) -> bool:
    return bool(_HEX_RE.match(s))


# ---------------------------------------------------------------------------
# PALETTE_VERSION
# ---------------------------------------------------------------------------

class TestPaletteVersion:
    def test_version_is_set(self):
        assert PALETTE_VERSION == "v1.0"

    def test_version_is_string(self):
        assert isinstance(PALETTE_VERSION, str)


# ---------------------------------------------------------------------------
# noetic_color
# ---------------------------------------------------------------------------

class TestNoeticColor:
    def test_returns_hex_for_all_valid_indices(self):
        for n in range(10):
            result = noetic_color(n)
            assert _is_hex(result), f"noetic_color({n}) = {result!r} is not a valid hex"

    def test_raises_for_negative(self):
        with pytest.raises(ValueError):
            noetic_color(-1)

    def test_raises_for_ten(self):
        with pytest.raises(ValueError):
            noetic_color(10)

    def test_raises_for_float(self):
        with pytest.raises(ValueError):
            noetic_color(3.0)  # type: ignore[arg-type]

    def test_raises_for_string(self):
        with pytest.raises(ValueError):
            noetic_color("3")  # type: ignore[arg-type]

    def test_all_ten_colors_are_distinct(self):
        colors = [noetic_color(n) for n in range(10)]
        assert len(set(colors)) == 10, "Not all 10 Noetic colors are unique"

    def test_deterministic(self):
        for n in range(10):
            assert noetic_color(n) == noetic_color(n)

    def test_specific_value_idea(self):
        assert noetic_color(0) == "#3388BB"

    def test_specific_value_negative(self):
        assert noetic_color(3) == "#CC6677"


# ---------------------------------------------------------------------------
# domain_color
# ---------------------------------------------------------------------------

class TestDomainColor:
    def test_returns_hex_for_all_valid_domains(self):
        for d in ("P", "C", "E", "O"):
            result = domain_color(d)
            assert _is_hex(result), f"domain_color({d!r}) = {result!r} is not a valid hex"

    def test_raises_for_invalid_domain(self):
        with pytest.raises(ValueError):
            domain_color("X")

    def test_raises_for_lowercase(self):
        with pytest.raises(ValueError):
            domain_color("p")

    def test_raises_for_empty(self):
        with pytest.raises(ValueError):
            domain_color("")

    def test_all_four_colors_are_distinct(self):
        colors = [domain_color(d) for d in ("P", "C", "E", "O")]
        assert len(set(colors)) == 4, "Not all 4 Domain colors are unique"

    def test_deterministic(self):
        for d in ("P", "C", "E", "O"):
            assert domain_color(d) == domain_color(d)

    def test_specific_value_principled(self):
        assert domain_color("P") == "#7B7EC4"

    def test_specific_value_operational(self):
        assert domain_color("O") == "#C0883C"


# ---------------------------------------------------------------------------
# drive_color
# ---------------------------------------------------------------------------

class TestDriveColor:
    def test_returns_hex_for_all_valid_drives(self):
        for k in range(1, 8):
            result = drive_color(k)
            assert _is_hex(result), f"drive_color({k}) = {result!r} is not a valid hex"

    def test_raises_for_zero(self):
        with pytest.raises(ValueError):
            drive_color(0)

    def test_raises_for_eight(self):
        with pytest.raises(ValueError):
            drive_color(8)

    def test_raises_for_negative(self):
        with pytest.raises(ValueError):
            drive_color(-1)

    def test_raises_for_float(self):
        with pytest.raises(ValueError):
            drive_color(2.0)  # type: ignore[arg-type]

    def test_all_seven_colors_are_distinct(self):
        colors = [drive_color(k) for k in range(1, 8)]
        assert len(set(colors)) == 7, "Not all 7 Drive colors are unique"

    def test_deterministic(self):
        for k in range(1, 8):
            assert drive_color(k) == drive_color(k)

    def test_specific_value_unity(self):
        assert drive_color(1) == "#4477AA"

    def test_specific_value_purpose(self):
        assert drive_color(7) == "#446688"


# ---------------------------------------------------------------------------
# register_treatment
# ---------------------------------------------------------------------------

class TestRegisterTreatment:
    _VALID_REGISTERS = ("T", "A", "f", "E")
    _VALID_BORDER_STYLES = {"solid", "dashed", "dotted", "double"}

    def test_returns_dict_for_all_valid_registers(self):
        for r in self._VALID_REGISTERS:
            result = register_treatment(r)
            assert isinstance(result, dict), f"register_treatment({r!r}) is not a dict"

    def test_dict_has_required_keys(self):
        for r in self._VALID_REGISTERS:
            result = register_treatment(r)
            assert "border_style" in result
            assert "color" in result

    def test_border_style_is_valid(self):
        for r in self._VALID_REGISTERS:
            style = register_treatment(r)["border_style"]
            assert style in self._VALID_BORDER_STYLES, (
                f"register_treatment({r!r}) border_style {style!r} not in {self._VALID_BORDER_STYLES}"
            )

    def test_color_is_hex(self):
        for r in self._VALID_REGISTERS:
            color = register_treatment(r)["color"]
            assert _is_hex(color), f"register_treatment({r!r}) color {color!r} is not hex"

    def test_raises_for_invalid_register(self):
        with pytest.raises(ValueError):
            register_treatment("X")

    def test_raises_for_lowercase_t(self):
        with pytest.raises(ValueError):
            register_treatment("t")

    def test_returns_copy_not_reference(self):
        t1 = register_treatment("T")
        t1["color"] = "#000000"
        t2 = register_treatment("T")
        assert t2["color"] != "#000000", "register_treatment returned a mutable reference"

    def test_border_styles_are_distinct(self):
        styles = [register_treatment(r)["border_style"] for r in self._VALID_REGISTERS]
        assert len(set(styles)) == 4, "Not all 4 Register border styles are unique"


# ---------------------------------------------------------------------------
# axis_color_for_node
# ---------------------------------------------------------------------------

class TestAxisColorForNode:
    def test_noetic_takes_precedence_over_domain(self):
        node = {"noetic": 3, "domain": "P"}
        result = axis_color_for_node(node)
        assert result == noetic_color(3)

    def test_noetic_takes_precedence_over_drive(self):
        node = {"noetic": 0, "drive": 5}
        result = axis_color_for_node(node)
        assert result == noetic_color(0)

    def test_noetic_takes_precedence_over_all(self):
        node = {"noetic": 7, "domain": "C", "drive": 2}
        result = axis_color_for_node(node)
        assert result == noetic_color(7)

    def test_domain_takes_precedence_over_drive(self):
        node = {"domain": "E", "drive": 4}
        result = axis_color_for_node(node)
        assert result == domain_color("E")

    def test_drive_used_when_only_drive(self):
        node = {"drive": 6}
        result = axis_color_for_node(node)
        assert result == drive_color(6)

    def test_returns_none_when_no_axis_info(self):
        assert axis_color_for_node({}) is None
        assert axis_color_for_node({"kind": "noetic", "label": "CO-3"}) is None

    def test_returns_none_when_values_are_none(self):
        assert axis_color_for_node({"noetic": None, "domain": None, "drive": None}) is None

    def test_result_is_hex(self):
        for n in range(10):
            result = axis_color_for_node({"noetic": n})
            assert _is_hex(result)  # type: ignore[arg-type]

    def test_string_noetic_coerced(self):
        # axis_color_for_node casts to int; node dict may carry strings from JSON
        node = {"noetic": "5"}
        result = axis_color_for_node(node)
        assert result == noetic_color(5)

    def test_raises_for_out_of_range_noetic_in_node(self):
        with pytest.raises(ValueError):
            axis_color_for_node({"noetic": 10})


# ---------------------------------------------------------------------------
# Cross-axis distinctness
# ---------------------------------------------------------------------------

class TestCrossAxisDistinctness:
    """Noetic colors must not accidentally duplicate Domain or Drive colors."""

    def test_noetic_colors_distinct_from_domain_colors(self):
        noetic_set = {noetic_color(n) for n in range(10)}
        domain_set = {domain_color(d) for d in ("P", "C", "E", "O")}
        overlap = noetic_set & domain_set
        assert not overlap, f"Noetic and Domain share colors: {overlap}"

    def test_noetic_colors_distinct_from_drive_colors(self):
        noetic_set = {noetic_color(n) for n in range(10)}
        drive_set = {drive_color(k) for k in range(1, 8)}
        overlap = noetic_set & drive_set
        assert not overlap, f"Noetic and Drive share colors: {overlap}"

    def test_domain_colors_distinct_from_drive_colors(self):
        domain_set = {domain_color(d) for d in ("P", "C", "E", "O")}
        drive_set = {drive_color(k) for k in range(1, 8)}
        overlap = domain_set & drive_set
        assert not overlap, f"Domain and Drive share colors: {overlap}"
