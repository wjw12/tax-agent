"""Validate local sample JSON coverage and typed parsing for all supported forms."""

from __future__ import annotations

import json
from pathlib import Path

from .input_loader import load_all_sample_inputs
from .registry import validate_manifest_coverage


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "2025-empty-forms" / "download_manifest.json"
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
