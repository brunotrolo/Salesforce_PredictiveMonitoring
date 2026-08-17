"""Weekly retraining CLI: recommend an AnomalyEngine threshold calibration.

Reads a JSON list of observed samples ``[{"threshold", "fp_rate"}]`` and
prints the Calibrator recommendation. Pure observation — the threshold is
never applied automatically (see docs/FEEDBACK_LOOP_SPEC.md, Open Questions).

Usage:
    python -m feedback.calibrate --samples samples.json [--target 0.2]
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recommend AnomalyEngine threshold from observed FP rates"
    )
    parser.add_argument(
        "--samples",
        required=True,
        help='JSON file: [{"threshold": float, "fp_rate": float}, ...]',
    )
    parser.add_argument("--target", type=float, default=0.2, help="Target FP rate")
    args = parser.parse_args(argv)

    with open(args.samples, encoding="utf-8") as f:
        samples = json.load(f)

    from .feedback import Calibrator

    result = Calibrator(target_fp_rate=args.target).recommend(samples)
    print(json.dumps(result.model_dump(), indent=2))
    return 0 if result.status == "recommended" else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
