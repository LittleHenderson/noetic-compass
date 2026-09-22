"""Use the existing atlas workbench for source-bound saved Helm predictions."""
from cncm.rpa_coordinates import (
    CANONICAL_LABELS, COORDINATE_LABELS, DENOMINATOR_LABEL, NUMERICAL_POLICY,
)
from cncm.rpa_recorded_helm import view_payload
from tools.render_rpa_ohm_view import _render_atlas_payload


def render_recorded_helm_view(document):
    # The separate adapter checks original records/checker reconstruction first.
    # Coordinate and calculation implementations are reused, never fabricated.
    payload = view_payload(document)
    payload.update(labels=list(CANONICAL_LABELS), coordinate_labels=list(COORDINATE_LABELS),
                   denominator_label=DENOMINATOR_LABEL, numerical_policy=NUMERICAL_POLICY)
    return _render_atlas_payload(payload)
