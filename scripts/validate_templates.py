"""Validate local sample JSON coverage and typed parsing for all supported forms."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.input_loader import load_all_sample_inputs
from src.registry import validate_manifest_coverage


def main() -> int:
    manifest_path = ROOT / "2025-empty-forms" / "download_manifest.json"
    coverage = validate_manifest_coverage(manifest_path)
    loaded = load_all_sample_inputs()
    report = {
        "coverage": coverage,
        "validated_forms": sorted(loaded.keys()),
    }
    print(json.dumps(report, indent=2))
    return 0 if not any(coverage.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
