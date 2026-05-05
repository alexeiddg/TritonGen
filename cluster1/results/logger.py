"""JSONL append logger for GenerationResult records."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from cluster1.results.dataclass import GenerationResult


# Task 5.4
def append_result_jsonl(path: Path, result: GenerationResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
