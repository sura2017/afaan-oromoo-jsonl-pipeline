"""Output validation ensuring strict compliance with required 3-key schema and controlled vocabulary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class OutputValidator:
    """Validates processed records and final output JSONL files."""

    ALLOWED_KEYS = {"id", "text", "category"}

    def __init__(self, controlled_vocabulary: Optional[List[str]] = None) -> None:
        self.controlled_vocabulary = set(
            controlled_vocabulary
            or [
                "News", "Politics", "Sports", "Religion", "Education", "Health",
                "Economy", "Entertainment", "Technology", "Business", "Agriculture",
                "Science", "Environment", "Culture", "Crime", "Law", "Government",
                "International", "Society", "Lifestyle", "Weather", "Other"
            ]
        )

    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a single output record dictionary.

        Rules:
        - Must contain exactly 'id', 'text', 'category'.
        - 'id' must be non-empty string.
        - 'text' must be non-empty string.
        - 'category' must be in allowed controlled vocabulary.
        - No extra or unexpected keys.
        """
        if not isinstance(record, dict):
            return False, f"Record is not a dict (got {type(record).__name__})"

        record_keys = set(record.keys())
        if record_keys != self.ALLOWED_KEYS:
            missing = self.ALLOWED_KEYS - record_keys
            extra = record_keys - self.ALLOWED_KEYS
            err_parts = []
            if missing:
                err_parts.append(f"Missing keys: {sorted(missing)}")
            if extra:
                err_parts.append(f"Unauthorized extra keys: {sorted(extra)}")
            return False, "; ".join(err_parts)

        # Check 'id'
        rec_id = record.get("id")
        if rec_id is None or not str(rec_id).strip():
            return False, "'id' field is empty or null"

        # Check 'text'
        rec_text = record.get("text")
        if rec_text is None or not isinstance(rec_text, str) or not rec_text.strip():
            return False, "'text' field is empty, null, or not a string"

        # Check 'category'
        rec_cat = record.get("category")
        if rec_cat not in self.controlled_vocabulary:
            return False, f"Invalid category '{rec_cat}' (not in controlled vocabulary)"

        return True, None

    def validate_file(
        self, file_path: Path, check_unique_ids: bool = True
    ) -> Tuple[bool, int, List[str]]:
        """
        Validate an entire output JSONL file.

        Returns:
            (is_valid, record_count, list_of_error_strings)
        """
        if not file_path.exists():
            return False, 0, [f"File does not exist: {file_path}"]

        errors: List[str] = []
        seen_ids: Set[str] = set()
        count = 0

        with open(file_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue

                if line_str.startswith("```"):
                    errors.append(f"Line {line_idx}: Markdown code fence detected")
                    continue

                try:
                    obj = json.loads(line_str)
                except json.JSONDecodeError as exc:
                    errors.append(f"Line {line_idx}: Malformed JSON - {exc.msg}")
                    continue

                valid, err = self.validate_record(obj)
                if not valid:
                    errors.append(f"Line {line_idx}: {err}")
                    continue

                if check_unique_ids:
                    rec_id = str(obj["id"])
                    if rec_id in seen_ids:
                        errors.append(f"Line {line_idx}: Duplicate output ID '{rec_id}'")
                    seen_ids.add(rec_id)

                count += 1

        is_valid = len(errors) == 0 and count > 0
        return is_valid, count, errors
