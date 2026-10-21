#!/usr/bin/env python3
"""
Independent JSONL dataset validation script.

Verifies:
- Valid JSON on each line
- Exactly three keys: id, text, category
- 'id' exists and is non-empty
- 'text' exists and is non-empty string
- 'category' is in controlled vocabulary
- No duplicate IDs
- UTF-8 validity
- No markdown fences or explanations
- Returns clear PASS / FAIL exit code
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import PipelineConfig
from src.output_validator import OutputValidator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently validate a cleaned JSONL dataset file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to output JSONL file to validate",
    )
    parser.add_argument(
        "--config-dir", "-c",
        type=str,
        default="config",
        help="Path to config directory with categories.json",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Do not fail on duplicate record IDs",
    )

    args = parser.parse_args()
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"[FAIL] Target file does not exist: {file_path}", file=sys.stderr)
        return 1

    config = PipelineConfig(config_dir=Path(args.config_dir))
    validator = OutputValidator(controlled_vocabulary=config.controlled_vocabulary)

    # Configure UTF-8 for console output on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"Validating dataset file: {file_path}")
    print(f"Controlled categories ({len(validator.controlled_vocabulary)}): {sorted(validator.controlled_vocabulary)}")
    print("-" * 60)

    is_valid, record_count, errors = validator.validate_file(
        file_path=file_path,
        check_unique_ids=not args.allow_duplicates,
    )

    if is_valid:
        print(f"[PASS] All {record_count:,} records are valid!")
        print("  [+] Strict 3-key schema: {'id', 'text', 'category'}")
        print("  [+] Non-empty text and non-empty IDs")
        print("  [+] All categories belong to controlled vocabulary")
        print("  [+] No duplicate IDs detected")
        print("  [+] UTF-8 encoding valid")
        print("  [+] No markdown formatting or code fences")
        print("  [+] Exactly one JSON record per line")
        print("-" * 60)
        return 0
    else:
        print(f"[FAIL] Found {len(errors):,} errors across {record_count:,} records:", file=sys.stderr)
        for err in errors[:20]:
            print(f"  [-] {err}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors.", file=sys.stderr)
        print("-" * 60, file=sys.stderr)
        return 1



if __name__ == "__main__":
    sys.exit(main())
