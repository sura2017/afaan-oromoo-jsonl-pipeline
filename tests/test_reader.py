"""Tests for JSONL streaming reader."""

import json
import tempfile
import unittest
from pathlib import Path

from src.jsonl_reader import stream_jsonl


class TestJSONLReader(unittest.TestCase):
    """Test suite for stream_jsonl."""

    def test_streaming_valid_lines(self):
        """Verify normal JSONL streaming reading line by line."""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write('{"id": "oro_1", "text": "Sentence one"}\n')
            f.write('{"id": "oro_2", "text": "Sentence two"}\n')
            f.write('{"id": "oro_3", "text": "Sentence three"}\n')
            temp_path = Path(f.name)

        try:
            records = list(stream_jsonl(temp_path))
            self.assertEqual(len(records), 3)
            self.assertEqual(records[0].line_number, 1)
            self.assertEqual(records[0].data["id"], "oro_1")
            self.assertIsNone(records[0].error)
            self.assertEqual(records[2].line_number, 3)
            self.assertEqual(records[2].data["id"], "oro_3")
        finally:
            temp_path.unlink()

    def test_malformed_json_recovery(self):
        """Verify that malformed JSON lines do not crash reader and are flagged."""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write('{"id": "oro_1", "text": "Good line"}\n')
            f.write('{"id": "oro_2", MALFORMED_JSON_LINE\n')
            f.write('{"id": "oro_3", "text": "Another good line"}\n')
            temp_path = Path(f.name)

        try:
            records = list(stream_jsonl(temp_path))
            self.assertEqual(len(records), 3)
            # Record 1 is good
            self.assertIsNone(records[0].error)
            self.assertEqual(records[0].data["id"], "oro_1")
            # Record 2 is malformed
            self.assertIsNotNone(records[1].error)
            self.assertIn("JSONDecodeError", records[1].error)
            self.assertIsNone(records[1].data)
            self.assertEqual(records[1].line_number, 2)
            # Record 3 is good
            self.assertIsNone(records[2].error)
            self.assertEqual(records[2].data["id"], "oro_3")
        finally:
            temp_path.unlink()

    def test_blank_lines_skipped(self):
        """Verify blank lines are gracefully skipped without errors."""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write('{"id": "oro_1", "text": "First"}\n\n   \n\n')
            f.write('{"id": "oro_2", "text": "Second"}\n')
            temp_path = Path(f.name)

        try:
            records = list(stream_jsonl(temp_path))
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0].data["id"], "oro_1")
            self.assertEqual(records[1].data["id"], "oro_2")
        finally:
            temp_path.unlink()

    def test_non_dict_json_flagged(self):
        """Verify valid JSON that is not an object (e.g. list, number) is flagged."""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f:
            f.write('["id", "oro_1"]\n')
            temp_path = Path(f.name)

        try:
            records = list(stream_jsonl(temp_path))
            self.assertEqual(len(records), 1)
            self.assertIsNotNone(records[0].error)
            self.assertIn("expected dict", records[0].error)
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
