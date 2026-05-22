"""Atlas Viewer Spatial Evidence Layer — v0.0 stub.

Serves the ``SpatialEvidenceArtifact`` JSON consumed by the atlas-viewer
``visualGroundingApi.ts`` client. The artifact links CAS trace steps to
visual primitives (points / boxes / polylines / regions) on an image so a
reviewer can see exactly what visual evidence a reasoning step refers to.

v0.0 stub: returns a single in-memory demo artifact for trace_id
``demo-trace-001`` only. Any other trace_id resolves to HTTP 404. Replace
with a DB-backed lookup at v0.1+ when user-uploaded artifacts ship.

Registered in ``api/main.py`` alongside the other route modules. The
artifact's ``image_url`` is a base64 data URL produced at module load
from the colocated demo SVG (see ``_load_demo_image_data_url``); see the
docstring there for the deployment-time caveat.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/atlas", tags=["atlas_visual_grounding"])


def _load_demo_image_data_url() -> str:
    """Read the demo SVG fixture and return it as a data: URL.

    The atlas-viewer client expects an ``image_url`` field that resolves in an
    <img> tag. Returning a relative path like ``/fixtures/...`` requires a
    matching static mount that we don't ship at v0.0; embedding the SVG as a
    data URL avoids the path-mismatch and works regardless of whether the
    client calls this route from the cockpit, the standalone API, or a test.
    The SVG is ~3 KB so the inline payload cost is trivial.
    """
    svg_path = (
        Path(__file__).resolve().parent.parent.parent
        / "atlas-viewer"
        / "src"
        / "fixtures"
        / "visualGroundingDemoImage.svg"
    )
    try:
        svg_bytes = svg_path.read_bytes()
    except OSError:
        # Fall back to a relative path; the cockpit's loadFixtures.ts injects
        # the bundled URL anyway, so this only affects standalone API consumers.
        return "/fixtures/visualGroundingDemoImage.svg"
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


_DEMO_IMAGE_URL = _load_demo_image_data_url()


VisualPrimitiveKind = Literal["point", "box", "polyline", "region"]
VisualPrimitiveSource = Literal["human_annotation", "fixture", "model_output", "cas_trace"]
CasAxis = Literal["Noetic", "Domain", "Drive", "Register"]


class EvidenceRef(BaseModel):
    trace_id: str | None = None
    packet_id: str | None = None
    row_id: str | None = None
    token_index: int | None = Field(default=None, ge=0)


class VisualPrimitive(BaseModel):
    id: str = Field(min_length=1)
    kind: VisualPrimitiveKind
    image_id: str = Field(min_length=1)
    label: str | None = None
    coords_norm: list[float] = Field(min_length=2)
    coords_px: list[float] | None = None
    cas_axis: CasAxis | None = None
    cas_label: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: VisualPrimitiveSource
    evidence_ref: EvidenceRef | None = None
    explanation: str | None = None


class VisualGroundedTraceStep(BaseModel):
    trace_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    token_index: int | None = Field(default=None, ge=0)
    text_span: str | None = None
    cas_state: str | None = None
    primitive_ids: list[str]
    evidence_packet_ref: str | None = None


class SpatialEvidenceArtifact(BaseModel):
    schema_version: Literal["spatial_evidence_v1"]
    trace_id: str = Field(min_length=1)
    image_id: str = Field(min_length=1)
    image_url: str = Field(min_length=1)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    primitives: list[VisualPrimitive]
    grounded_steps: list[VisualGroundedTraceStep]


_DEMO_TRACE_ID = "demo-trace-001"

_DEMO_ARTIFACT = SpatialEvidenceArtifact(
    schema_version="spatial_evidence_v1",
    trace_id=_DEMO_TRACE_ID,
    image_id="demo-image-001",
    image_url=_DEMO_IMAGE_URL,
    image_width=640,
    image_height=480,
    primitives=[
        VisualPrimitive(
            id="vp-001",
            kind="box",
            image_id="demo-image-001",
            label="Coffee cup body",
            coords_norm=[0.6640625, 0.7083333, 0.140625, 0.1145833],
            coords_px=[425.0, 340.0, 90.0, 55.0],
            cas_axis="Noetic",
            cas_label="^9^E|E",
            confidence=0.92,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-1"),
            explanation=(
                "The model noticed a porcelain cup outline on the table and grounded it "
                "as an embodied perceptual landing — a visible object brought to Mind."
            ),
        ),
        VisualPrimitive(
            id="vp-002",
            kind="point",
            image_id="demo-image-001",
            label="Coffee cup handle tip",
            coords_norm=[0.8515625, 0.775],
            coords_px=[545.0, 372.0],
            cas_axis="Domain",
            cas_label="^9^O|E",
            confidence=0.81,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-2"),
            explanation=(
                "The model fixated on the curved handle as an affordance — an "
                "operational-domain feature signaling how the cup is grasped."
            ),
        ),
        VisualPrimitive(
            id="vp-003",
            kind="box",
            image_id="demo-image-001",
            label="Open book on table",
            coords_norm=[0.125, 0.725, 0.375, 0.125],
            coords_px=[80.0, 348.0, 240.0, 60.0],
            cas_axis="Noetic",
            cas_label="^6^C|E",
            confidence=0.88,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-3"),
            explanation=(
                "The model recognized the open-book silhouette with twin pages — a "
                "compositional object whose internal structure (text lines, spine) is "
                "decomposable."
            ),
        ),
        VisualPrimitive(
            id="vp-004",
            kind="box",
            image_id="demo-image-001",
            label="Window frame with sunlit pane",
            coords_norm=[0.59375, 0.0833333, 0.34375, 0.4583333],
            coords_px=[380.0, 40.0, 220.0, 220.0],
            cas_axis="Domain",
            cas_label="^0^P|E",
            confidence=0.90,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-4"),
            explanation=(
                "The model anchored the rectangular window aperture as the dominant "
                "scene boundary — a principled-domain frame containing the light source."
            ),
        ),
        VisualPrimitive(
            id="vp-005",
            kind="point",
            image_id="demo-image-001",
            label="Sun disc center",
            coords_norm=[0.765625, 0.25],
            coords_px=[490.0, 120.0],
            cas_axis="Register",
            cas_label="^4^E|E",
            confidence=0.86,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-5"),
            explanation=(
                "The model located the bright sun disc at the brightest intensity peak — "
                "an embodied resonance with the warmest pixel cluster in the scene."
            ),
        ),
        VisualPrimitive(
            id="vp-006",
            kind="polyline",
            image_id="demo-image-001",
            label="Rising steam wisp",
            coords_norm=[
                0.7421875,
                0.6875,
                0.71875,
                0.6416667,
                0.734375,
                0.5833333,
                0.71875,
                0.5208333,
            ],
            coords_px=[475.0, 330.0, 460.0, 308.0, 470.0, 280.0, 460.0, 250.0],
            cas_axis="Drive",
            cas_label="F3|E",
            confidence=0.74,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-6"),
            explanation=(
                "The model traced a vertical wisp rising from the cup rim, reading it as "
                "evidence of warmth — vitality-drive in embodied register."
            ),
        ),
        VisualPrimitive(
            id="vp-007",
            kind="region",
            image_id="demo-image-001",
            label="Open-page region",
            coords_norm=[
                0.125,
                0.75,
                0.3125,
                0.725,
                0.5,
                0.75,
                0.5,
                0.85,
                0.3125,
                0.8333333,
                0.125,
                0.85,
            ],
            coords_px=[80.0, 360.0, 200.0, 348.0, 320.0, 360.0, 320.0, 408.0, 200.0, 400.0, 80.0, 408.0],
            cas_axis="Noetic",
            cas_label="^5^C|E",
            confidence=0.79,
            source="fixture",
            evidence_ref=EvidenceRef(packet_id="demo-packet-001", row_id="row-7"),
            explanation=(
                "The model outlined both pages as a single readable surface — a "
                "Mind-composed-of-Ideas substrate seen from the outside, registered embodied."
            ),
        ),
    ],
    grounded_steps=[
        VisualGroundedTraceStep(
            trace_id=_DEMO_TRACE_ID,
            step_id="step-001",
            token_index=5,
            text_span="a coffee cup",
            cas_state="^9^E|E",
            primitive_ids=["vp-001", "vp-002"],
            evidence_packet_ref="demo-packet-001",
        ),
        VisualGroundedTraceStep(
            trace_id=_DEMO_TRACE_ID,
            step_id="step-002",
            token_index=9,
            text_span="an open book",
            cas_state="^6^C|E",
            primitive_ids=["vp-003", "vp-007"],
            evidence_packet_ref="demo-packet-001",
        ),
        VisualGroundedTraceStep(
            trace_id=_DEMO_TRACE_ID,
            step_id="step-003",
            token_index=13,
            text_span="under a sunny window",
            cas_state="^4^E|E",
            primitive_ids=["vp-004", "vp-005"],
            evidence_packet_ref="demo-packet-001",
        ),
        VisualGroundedTraceStep(
            trace_id=_DEMO_TRACE_ID,
            step_id="step-004",
            token_index=17,
            text_span="with steam rising",
            cas_state="^8^O|E",
            primitive_ids=["vp-006", "vp-001"],
            evidence_packet_ref="demo-packet-001",
        ),
    ],
)


@router.get("/visual-grounding/{trace_id}", response_model=SpatialEvidenceArtifact)
async def get_spatial_evidence(trace_id: str) -> SpatialEvidenceArtifact:
    """Return the SpatialEvidenceArtifact for ``trace_id``.

    v0.0 stub: only ``demo-trace-001`` resolves; everything else is 404.
    """
    if trace_id != _DEMO_TRACE_ID:
        raise HTTPException(status_code=404, detail="spatial evidence not found")
    return _DEMO_ARTIFACT
