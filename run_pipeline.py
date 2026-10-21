#!/usr/bin/env python3
"""
CLI entry point for the Afaan Oromoo Dataset Cleaning, Sentence-Boundary Annotation & Categorization Pipeline.

Usage:
    python run_pipeline.py --input input/raw.jsonl --output output/cleaned.jsonl
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import PipelineConfig
from src.pipeline import DatasetPipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Afaan Oromoo Dataset Cleaning, Sentence-Boundary Annotation & Categorization Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to raw input JSONL file (e.g., input/raw.jsonl)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="Path to cleaned output JSONL file (e.g., output/cleaned.jsonl)",
    )
    parser.add_argument(
        "--errors", "-e",
        type=str,
        default=None,
        help="Optional path to write isolated error records JSONL (default: <output_dir>/<output_stem>_errors.jsonl)",
    )
    parser.add_argument(
        "--log", "-l",
        type=str,
        default=None,
        help="Optional path to execution log file (default: <output_dir>/<output_stem>_processing.log)",
    )
    parser.add_argument(
        "--config-dir", "-c",
        type=str,
        default="config",
        help="Directory containing pipeline JSON configuration files",
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume processing from previous checkpoint if interrupted",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console and file logging verbosity level",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=5000,
        help="Number of records between progress status updates",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    config_dir = Path(args.config_dir)

    config = PipelineConfig(
        config_dir=config_dir,
        boilerplate_file=config_dir / "boilerplate_phrases.json",
        broadcast_file=config_dir / "broadcast_terms.json",
        categories_file=config_dir / "categories.json",
        spelling_file=config_dir / "spelling_corrections.json",
        log_level=args.log_level,
        progress_interval=args.progress_interval,
        resume=args.resume,
    )

    error_path = Path(args.errors) if args.errors else None
    log_path = Path(args.log) if args.log else None

    pipeline = DatasetPipeline(config=config)
    logger = pipeline.run(
        input_file=input_path,
        output_file=output_path,
        error_file=error_path,
        log_file=log_path,
        resume=args.resume,
    )

    if logger.metrics.records_success > 0:
        return 0
    elif logger.metrics.records_read == 0:
        print("Warning: Input file was empty.", file=sys.stderr)
        return 0
    else:
        print("Error: No records were successfully processed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
