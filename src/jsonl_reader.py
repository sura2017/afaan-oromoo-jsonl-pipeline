"""Streaming JSONL reader for large-scale dataset processing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional, Tuple


@dataclass
class RawRecord:
    """Represents a raw line read from JSONL."""

    line_number: int
    raw_text: str
    data: Optional[dict] = None
    error: Optional[str] = None


def stream_jsonl(file_path: Path) -> Generator[RawRecord, None, None]:
    """
    Stream a JSONL file line by line without loading it into RAM.

    Yields RawRecord with line_number, raw_text, parsed data, or error description.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                # Blank lines are skipped
                continue

            try:
                data = json.loads(line_str)
                if not isinstance(data, dict):
                    yield RawRecord(
                        line_number=line_num,
                        raw_text=line_str,
                        data=None,
                        error="Line content is valid JSON but not a JSON object (expected dict)",
                    )
                else:
                    yield RawRecord(
                        line_number=line_num,
                        raw_text=line_str,
                        data=data,
                        error=None,
                    )
            except json.JSONDecodeError as exc:
                yield RawRecord(
                    line_number=line_num,
                    raw_text=line_str,
                    data=None,
                    error=f"JSONDecodeError: {exc.msg} (col {exc.colno})",
                )
