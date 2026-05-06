"""Load and parse Golden Set ground truth."""

from pathlib import Path

import yaml


GOLDEN_SET_PATH = Path(__file__).parent.parent.parent / "golden_set" / "ground_truth.yaml"


def load_ground_truth() -> dict:
    """Load the golden set ground truth YAML."""
    if not GOLDEN_SET_PATH.exists():
        return {"tender": None, "bidders": []}
    with open(GOLDEN_SET_PATH) as f:
        return yaml.safe_load(f)
