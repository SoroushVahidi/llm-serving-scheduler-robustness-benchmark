"""JSONL read/write helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Union


def write_jsonl(records: Iterable[Any], path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


def read_jsonl(path: Union[str, Path]) -> List[Any]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
