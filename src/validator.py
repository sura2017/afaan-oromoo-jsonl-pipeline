"""Input record validation and duplicate ID detection."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple


class RecordValidator:
    """Validates raw input records and ensures ID integrity and uniqueness."""

    def __init__(self, check_duplicates: bool = True) -> None:
        self.check_duplicates = check_duplicates
        self.seen_ids: Set[str] = set()

    def validate_record(
        self, data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Validate input JSON object.

        Returns:
            (is_valid, id_str, text_str, error_message)
        """
        # 1. Validate ID key
        if "id" not in data:
            return False, None, None, "Missing 'id' field in record"

        raw_id = data.get("id")
        if raw_id is None:
            return False, None, None, "'id' field is null"

        id_str = str(raw_id).strip()
        if not id_str:
            return False, None, None, "'id' field is empty"

        # 2. Check duplicate IDs
        if self.check_duplicates:
            if id_str in self.seen_ids:
                return False, id_str, None, f"Duplicate ID encountered: '{id_str}'"
            self.seen_ids.add(id_str)

        # 3. Validate text key
        if "text" not in data:
            return False, id_str, None, "Missing 'text' field in record"

        raw_text = data.get("text")
        if raw_text is None:
            return False, id_str, None, "'text' field is null"

        if not isinstance(raw_text, str):
            return False, id_str, None, f"'text' field is not a string (got {type(raw_text).__name__})"

        text_str = raw_text.strip()
        if not text_str:
            return False, id_str, None, "'text' field is empty or contains only whitespace"

        return True, id_str, raw_text, None

    def reset(self) -> None:
        """Clear seen IDs."""
        self.seen_ids.clear()
