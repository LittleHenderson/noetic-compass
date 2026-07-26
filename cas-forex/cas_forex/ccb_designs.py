"""B: Cognitive Circuit Board (CCB) executable reference designs.

Encodes the five blueprint CCBs as ``CrcCircuit`` specifications that pass the
Cognitive Rule Check linter (ERROR-free). Each board is a *well-formed design* —
it is NOT a runtime-safety, alignment, memory, or power guarantee. Those claims
are gated separately in ``ccb_readiness`` and remain NOT LICENSED.

Warnings (e.g. CRC-004 reverse-flow on assessment/feedback edges) are expected
and acceptable in these designs; only ERROR-level findings make a board
malformed.
"""

from __future__ import annotations

from cas_forex.crc_linter import CrcCircuit, CrcFuse, CrcReport, CrcVia, run_crc
from cas_forex.cjt_syntax import parse_cjt_expression
from cas_forex.schemas.pcba import PcbaBoardKind


def _circuit(name: str, expressions: list[str], *, vias=None, fuses=None, sequence=None) -> CrcCircuit:
    return CrcCircuit(
        name=name,
        cjts=[parse_cjt_expression(e) for e in expressions],
        vias=vias or [],
        fuses=fuses or [],
        sequence=sequence or [],
    )


def build_csb() -> CrcCircuit:
    """CCB-1 Cognitive Safety Board — pre-amp, balanced differential pair, saturated refusal."""

    return _circuit(
        "CSB",
        [
            "CJT< prompt | ^5^P_{F7}|T => ^8^C_{F2}|A > [beta=3]",
            # Balanced differential pair (attraction vs aversion), equal gain.
            "CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^2^P_{F1}|T > [beta=2]",
            "CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^3^P_{F1}|T > [beta=2]",
            # Risk cascade through evaluation, then saturated refusal lock.
            "CJT< ^8^C_{F2}|A | ^1^C_{F2}|A => ^6^E_{F6}|A > [beta=1.5]",
            "CJT< ^6^E_{F6}|A | ^3^P_{F1}|T => ^9^P_{F1}|T > [beta=2, sat=0.8, region=saturation]",
        ],
        fuses=[CrcFuse(name="refusal_fuse", protects="output", installed_at="cascade")],
        sequence=["prompt", "preamp", "diffpair", "cascade", "output"],
    )


def build_cob() -> CrcCircuit:
    """CCB-2 Cognitive Oscillator Board — descending habit loop with feedback via."""

    return _circuit(
        "COB",
        [
            "CJT< ^7^P_{F6}|T | ^5^P_{F6}|T => ^4^C_{F4}|f > [beta=1]",
            "CJT< ^4^C_{F4}|f | ^5^P_{F6}|T => ^3^E_{F3}|f > [beta=1]",
            "CJT< ^3^E_{F3}|f | ^5^P_{F6}|T => ^9^O_{F5}|f > [beta=1]",
        ],
        vias=[CrcVia(source="^9^O_{F5}|f", target="^7^P_{F6}|T")],  # feedback (expected WARN)
    )


def build_cdab() -> CrcCircuit:
    """CCB-3 Cognitive Differential Amplifier Board — two ideas, shared bias, active load."""

    return _circuit(
        "CDAB",
        [
            "CJT< idea_1 | ^5^E_{F4}|f => ^1^C_{F2}|A > [beta=2]",
            "CJT< idea_2 | ^5^E_{F4}|f => ^1^C_{F2}|A > [beta=2]",
            "CJT< ^1^C_{F2}|A | ^6^C_{F2}|A => ^1^C_{F2}|A > [beta=1.2]",
        ],
    )


def build_cmb() -> CrcCircuit:
    """CCB-4 Cognitive Memory Board — encode, refresh, address-decode via."""

    return _circuit(
        "CMB",
        [
            "CJT< experience | ^1^C_{F2}|A => ^5^E_{F4}|f > [beta=1]",
            "CJT< ^5^E_{F4}|f | ^7^C_{F6}|A => ^5^E_{F4}|f > [beta=1]",
        ],
        vias=[CrcVia(source="^1^C_{F2}|A", target="^5^E_{F4}|f")],  # address decode (descending, clean)
    )


def build_cpmb() -> CrcCircuit:
    """CCB-5 Cognitive Power Management Board — regulator, P→C→E→O sequencer, upstream fuse."""

    return _circuit(
        "CPMB",
        [
            # The four rails as published at Chapter_22:179-182: p_rail
            # ^0^P_{F7}|T, c_rail ^1^C_{F2}|A, e_rail ^6^E_{F6}|A, o_rail
            # ^9^O_{F5}|E, powering up in that order. Each rail's Drive is the
            # one its regulator targets, so the dropout spec and the rail agree.
            "CJT< drive_energy | ^5^P_{F7}|T => ^0^P_{F7}|T > [beta=1]",
            "CJT< ^0^P_{F7}|T | ^5^P_{F7}|T => ^1^C_{F2}|A > [beta=1]",
            "CJT< ^1^C_{F2}|A | ^5^P_{F7}|T => ^6^E_{F6}|A > [beta=1]",
            "CJT< ^6^E_{F6}|A | ^5^P_{F7}|T => ^9^O_{F5}|E > [beta=1]",
        ],
        fuses=[CrcFuse(name="overload_fuse", protects="O_rail", installed_at="C_rail")],
        sequence=["P_rail", "C_rail", "E_rail", "O_rail"],
    )


CCB_BUILDERS = {
    PcbaBoardKind.COGNITIVE_SAFETY_BOARD: build_csb,
    PcbaBoardKind.COGNITIVE_OSCILLATOR_BOARD: build_cob,
    PcbaBoardKind.COGNITIVE_DIFFERENTIAL_AMPLIFIER_BOARD: build_cdab,
    PcbaBoardKind.COGNITIVE_MEMORY_BOARD: build_cmb,
    PcbaBoardKind.COGNITIVE_POWER_MANAGEMENT_BOARD: build_cpmb,
}


def build_all_ccbs() -> dict[PcbaBoardKind, CrcCircuit]:
    return {kind: builder() for kind, builder in CCB_BUILDERS.items()}


def lint_all_ccbs() -> dict[PcbaBoardKind, CrcReport]:
    """Run CRC over every reference board."""

    return {kind: run_crc(circuit) for kind, circuit in build_all_ccbs().items()}
