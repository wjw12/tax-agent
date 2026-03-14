"""Summarize unmapped logical keys and discovered XFA line labels."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "src" / "field_maps"
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        unmapped = payload.get("unmapped_keys", [])
        if not unmapped:
            continue
        labels = ", ".join(sorted(payload.get("line_field_map", {}).keys()))
        print(f"{path.stem}: {unmapped}")
        print(f"  labels: {labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
