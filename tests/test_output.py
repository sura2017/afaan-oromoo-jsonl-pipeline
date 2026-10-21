"""Tests for output validation and strict 3-key schema enforcement."""

import json
import tempfile
import unittest
from pathlib import Path

from src.output_validator import OutputValidator


class TestOutputValidation(unittest.TestCase):
    """Test suite for OutputValidator."""

    def setUp(self):
        self.validator = OutputValidator()

    def test_valid_record(self):
        """Verify strict 3-key valid record passes."""
        rec = {
            "id": "oro_0000001",
            "text": "Abboota mana kiristaanaa qulqulluu Atnaatewoos.",
            "category": "Religion",
        }
        valid, err = self.validator.validate_record(rec)
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_unauthorized_extra_keys_rejected(self):
        """Verify extra keys like 'raw_text', 'confidence', 'source' are strictly rejected."""
        rec = {
            "id": "oro_0000001",
            "text": "Valid text.",
            "category": "Sports",
            "confidence": 0.98,
            "source": "fanabc",
        }
        valid, err = self.validator.validate_record(rec)
        self.assertFalse(valid)
        self.assertIn("Unauthorized extra keys", err)

    def test_missing_required_keys_rejected(self):
        """Verify missing key causes failure."""
        rec = {
            "id": "oro_0000001",
            "text": "Valid text.",
        }
        valid, err = self.validator.validate_record(rec)
        self.assertFalse(valid)
        self.assertIn("Missing keys", err)

    def test_empty_fields_rejected(self):
        """Verify empty id or empty text fails."""
        rec1 = {"id": "", "text": "Some text", "category": "Sports"}
        valid1, _ = self.validator.validate_record(rec1)
        self.assertFalse(valid1)

        rec2 = {"id": "oro_1", "text": "   ", "category": "Sports"}
        valid2, _ = self.validator.validate_record(rec2)
        self.assertFalse(valid2)

    def test_invalid_category_rejected(self):
        """Verify category not in controlled vocabulary is rejected."""
        rec = {
            "id": "oro_1",
            "text": "Some text.",
            "category": "UnregisteredCategory123",
        }
        valid, err = self.validator.validate_record(rec)
        self.assertFalse(valid)
        self.assertIn("not in controlled vocabulary", err)

    def test_file_validation_pass_and_fail(self):
        """Verify validate_file checks entire JSONL file correctly."""
        # Good file
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write(json.dumps({"id": "1", "text": "One.", "category": "News"}) + "\n")
            f.write(json.dumps({"id": "2", "text": "Two.", "category": "Sports"}) + "\n")
            good_path = Path(f.name)

        try:
            is_valid, count, errors = self.validator.validate_file(good_path)
            self.assertTrue(is_valid)
            self.assertEqual(count, 2)
            self.assertEqual(len(errors), 0)
        finally:
            good_path.unlink()

        # Bad file with duplicate ID and markdown fence
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write("```json\n")
            f.write(json.dumps({"id": "1", "text": "One.", "category": "News"}) + "\n")
            f.write(json.dumps({"id": "1", "text": "Duplicate id.", "category": "News"}) + "\n")
            bad_path = Path(f.name)

        try:
            is_valid, count, errors = self.validator.validate_file(bad_path)
            self.assertFalse(is_valid)
            self.assertTrue(any("Markdown" in e for e in errors))
            self.assertTrue(any("Duplicate" in e for e in errors))
        finally:
            bad_path.unlink()


if __name__ == "__main__":
    unittest.main()
