"""Print the CJT production-authority readiness report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.cjt_readiness import (
    assert_cjt_high_authority_features_blocked,
    build_cjt_production_readiness_report,
)


def main() -> int:
    report = build_cjt_production_readiness_report()
    assert_cjt_high_authority_features_blocked(report)
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
