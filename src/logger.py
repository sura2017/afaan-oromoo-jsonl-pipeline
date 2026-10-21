"""Logging and metrics tracking for dataset processing pipeline."""

from __future__ import annotations

import json
import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class PipelineMetrics:
    """Tracks running statistics for the pipeline."""

    records_read: int = 0
    records_success: int = 0
    records_skipped: int = 0
    records_malformed: int = 0
    duplicate_ids: int = 0
    urls_removed: int = 0
    domains_removed: int = 0
    boilerplate_removed: int = 0
    broadcast_artifacts_removed: int = 0
    category_counts: Counter[str] = field(default_factory=Counter)
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_time(self) -> float:
        return max(0.001, time.time() - self.start_time)

    @property
    def throughput(self) -> float:
        return self.records_read / self.elapsed_time

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "records_read": self.records_read,
            "records_success": self.records_success,
            "records_skipped": self.records_skipped,
            "records_malformed": self.records_malformed,
            "duplicate_ids": self.duplicate_ids,
            "urls_removed": self.urls_removed,
            "domains_removed": self.domains_removed,
            "boilerplate_removed": self.boilerplate_removed,
            "broadcast_artifacts_removed": self.broadcast_artifacts_removed,
            "elapsed_seconds": round(self.elapsed_time, 2),
            "throughput_rec_per_sec": round(self.throughput, 2),
            "category_distribution": dict(self.category_counts),
        }


class PipelineLogger:
    """Handles structured console/file logging and error log files."""

    def __init__(
        self,
        name: str = "dataset_pipeline",
        log_level: str = "INFO",
        log_file: Optional[Path] = None,
        error_file: Optional[Path] = None,
        error_mode: str = "a",
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        self.logger.handlers.clear()

        # Console handler with UTF-8
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(console_formatter)
            self.logger.addHandler(file_handler)

        self.error_file = error_file
        self.error_fp = None
        if self.error_file:
            self.error_file.parent.mkdir(parents=True, exist_ok=True)
            self.error_fp = open(self.error_file, error_mode, encoding="utf-8")

        self.metrics = PipelineMetrics()

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def debug(self, msg: str) -> None:
        self.logger.debug(msg)

    def log_error_record(
        self,
        line_num: int,
        error_type: str,
        message: str,
        raw_data: Optional[str] = None,
        record_id: Optional[str] = None,
    ) -> None:
        """Write an error record to the dedicated errors file and log warning."""
        self.logger.warning(
            f"Line {line_num} | ID: {record_id or 'UNKNOWN'} | {error_type}: {message}"
        )
        if self.error_fp:
            error_entry = {
                "line": line_num,
                "id": record_id,
                "error_type": error_type,
                "message": message,
                "raw_snippet": (raw_data[:200] if raw_data else None),
            }
            self.error_fp.write(json.dumps(error_entry, ensure_ascii=False) + "\n")
            self.error_fp.flush()

    def report_progress(self, force: bool = False, interval: int = 5000) -> None:
        """Log periodic progress."""
        if force or (self.metrics.records_read > 0 and self.metrics.records_read % interval == 0):
            self.logger.info(
                f"Progress -> Processed: {self.metrics.records_read:,} | "
                f"Successful: {self.metrics.records_success:,} | "
                f"Skipped: {self.metrics.records_skipped:,} | "
                f"Errors/Malformed: {self.metrics.records_malformed:,} | "
                f"Duplicates: {self.metrics.duplicate_ids:,} | "
                f"Rate: {self.metrics.throughput:.1f} rec/sec"
            )

    def print_final_summary(self) -> None:
        """Print full execution summary."""
        m = self.metrics
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE PROCESSING COMPLETE - FINAL SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Records Read:      {m.records_read:,}")
        self.logger.info(f"Successfully Processed:  {m.records_success:,}")
        self.logger.info(f"Skipped / Empty:         {m.records_skipped:,}")
        self.logger.info(f"Malformed Lines:         {m.records_malformed:,}")
        self.logger.info(f"Duplicate IDs:           {m.duplicate_ids:,}")
        self.logger.info(f"URLs Removed:            {m.urls_removed:,}")
        self.logger.info(f"Domains Cleaned:         {m.domains_removed:,}")
        self.logger.info(f"Boilerplates Removed:    {m.boilerplate_removed:,}")
        self.logger.info(f"Broadcast Terms Cleaned: {m.broadcast_artifacts_removed:,}")
        self.logger.info(f"Elapsed Time:            {m.elapsed_time:.2f} seconds")
        self.logger.info(f"Overall Throughput:      {m.throughput:.1f} records/sec")
        self.logger.info("Category Distribution:")
        for cat, count in m.category_counts.most_common():
            self.logger.info(f"  - {cat:16s}: {count:,}")
        self.logger.info("=" * 60)

    def close(self) -> None:
        if self.error_fp:
            self.error_fp.close()
            self.error_fp = None
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)

