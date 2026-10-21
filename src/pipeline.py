"""Production-grade streaming pipeline orchestrator for Afaan Oromoo dataset processing."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple

from src.cleaner import TextCleaner
from src.config import PipelineConfig
from src.categorizer import TextCategorizer
from src.jsonl_reader import stream_jsonl
from src.logger import PipelineLogger
from src.output_validator import OutputValidator
from src.sentence_processor import SentenceProcessor
from src.spelling_corrector import SpellingCorrector
from src.validator import RecordValidator


class DatasetPipeline:
    """
    Orchestrates the complete dataset processing pipeline:
    JSONL Stream -> Validation -> Cleaning -> Hudhaa/Spelling -> Sentence Annotation -> Categorization -> Output Validation -> JSONL Writer
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self.config = config or PipelineConfig()

        # Initialize pipeline stages once to avoid repeated expensive overhead
        self.validator = RecordValidator(check_duplicates=True)
        self.cleaner = TextCleaner(
            boilerplate_phrases=self.config.boilerplate_phrases,
            broadcast_terms=self.config.broadcast_terms,
        )
        self.spelling_corrector = SpellingCorrector(
            proper_nouns=self.config.proper_nouns,
            unambiguous_replacements=self.config.unambiguous_spelling,
        )
        self.sentence_processor = SentenceProcessor()
        self.categorizer = TextCategorizer(
            controlled_vocabulary=self.config.controlled_vocabulary,
            normalization_map=self.config.category_normalization,
            category_keywords=self.config.category_keywords,
        )
        self.output_validator = OutputValidator(
            controlled_vocabulary=self.config.controlled_vocabulary
        )

    def process_record_text(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Run text through:
        1. Noise and artifact cleaning (with placeholder protection)
        2. Safe spelling & hudhaa correction
        3. Sentence-boundary detection, spacing, and capitalization
        """
        # Step 1: Protect placeholders across the entire text pipeline
        masked_text, placeholder_map = self.cleaner.protect_placeholders(text)

        # Step 2: Clean web noise (keeping placeholders masked)
        cleaned_text, clean_counts = self.cleaner.clean(masked_text, restore=False)
        if not cleaned_text:
            return "", clean_counts

        # Step 3: Safe hudhaa and spelling normalization
        corrected_text = self.spelling_corrector.correct(cleaned_text)

        # Step 4: Sentence boundary annotation and capitalization
        annotated_text = self.sentence_processor.process(corrected_text)

        # Step 5: Restore placeholders exactly
        final_text = self.cleaner.restore_placeholders(annotated_text, placeholder_map)

        return final_text, clean_counts

    def load_checkpoint(self, checkpoint_file: Path) -> Set[str]:
        """Load set of already processed record IDs from checkpoint if resuming."""
        processed_ids: Set[str] = set()
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    processed_ids = set(data.get("processed_ids", []))
            except Exception:
                processed_ids = set()
        return processed_ids

    def save_checkpoint(self, checkpoint_file: Path, processed_ids: Set[str], last_line: int) -> None:
        """Save checkpoint data atomically."""
        tmp_cp = checkpoint_file.with_suffix(".tmp")
        try:
            with open(tmp_cp, "w", encoding="utf-8") as f:
                json.dump({"last_line": last_line, "processed_ids": list(processed_ids)}, f)
            if tmp_cp.exists():
                tmp_cp.replace(checkpoint_file)
        except Exception:
            pass

    def run(
        self,
        input_file: Path,
        output_file: Path,
        error_file: Optional[Path] = None,
        log_file: Optional[Path] = None,
        resume: bool = False,
    ) -> PipelineLogger:
        """
        Execute streaming end-to-end dataset processing.
        """
        input_path = Path(input_file)
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if error_file is None:
            error_file = output_path.parent / f"{output_path.stem}_errors.jsonl"
        error_path = Path(error_file)

        if log_file is None:
            log_file = output_path.parent / f"{output_path.stem}_processing.log"
        log_path = Path(log_file)

        logger = PipelineLogger(
            name="afaan_oromoo_pipeline",
            log_level=self.config.log_level,
            log_file=log_path,
            error_file=error_path,
            error_mode="a" if resume else "w",
        )

        logger.info(f"Starting Afaan Oromoo Dataset Pipeline")
        logger.info(f"Input file:  {input_path}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Error log:   {error_path}")
        logger.info(f"Resume mode: {resume}")

        checkpoint_file = output_path.parent / f".checkpoint_{output_path.stem}.json"
        resumed_ids: Set[str] = set()
        if resume:
            resumed_ids = self.load_checkpoint(checkpoint_file)
            if output_path.exists():
                try:
                    with open(output_path, "r", encoding="utf-8") as rf:
                        for line in rf:
                            line_s = line.strip()
                            if line_s:
                                obj = json.loads(line_s)
                                if "id" in obj:
                                    resumed_ids.add(str(obj["id"]))
                except Exception:
                    pass

            if resumed_ids:
                logger.info(f"Resuming execution: {len(resumed_ids)} IDs previously processed")
                self.validator.seen_ids.update(resumed_ids)


        # Atomic writing setup: write to .tmp unless resuming existing output
        if resume and output_path.exists():
            target_out_path = output_path
            write_mode = "a"
        else:
            target_out_path = output_path.with_suffix(".jsonl.tmp")
            write_mode = "w"

        out_fp = open(target_out_path, write_mode, encoding="utf-8", buffering=65536)

        try:
            for raw_record in stream_jsonl(input_path):
                line_num = raw_record.line_number
                logger.metrics.records_read += 1

                # 1. Handle Reader / JSON decoding errors
                if raw_record.error:
                    logger.metrics.records_malformed += 1
                    logger.log_error_record(
                        line_num=line_num,
                        error_type="MALFORMED_JSON",
                        message=raw_record.error,
                        raw_data=raw_record.raw_text,
                    )
                    continue

                record_data = raw_record.data
                if record_data is None:
                    continue

                # 2. Validate input record structure and uniqueness
                is_valid, rec_id, raw_text, val_err = self.validator.validate_record(record_data)
                if not is_valid:
                    if val_err and "Duplicate ID" in val_err:
                        logger.metrics.duplicate_ids += 1
                        logger.log_error_record(
                            line_num=line_num,
                            error_type="DUPLICATE_ID",
                            message=val_err,
                            record_id=rec_id,
                            raw_data=raw_record.raw_text,
                        )
                    else:
                        logger.metrics.records_skipped += 1
                        logger.log_error_record(
                            line_num=line_num,
                            error_type="INVALID_RECORD",
                            message=val_err or "Unknown validation error",
                            record_id=rec_id,
                            raw_data=raw_record.raw_text,
                        )
                    continue

                # Check if already processed in resume mode
                if resume and rec_id in resumed_ids:
                    continue

                # 3. Process text (Clean -> Hudhaa/Spelling -> Sentence boundaries)
                try:
                    processed_text, clean_counts = self.process_record_text(raw_text)

                    # Update cleaning metrics
                    logger.metrics.urls_removed += clean_counts["urls_removed"]
                    logger.metrics.domains_removed += clean_counts["domains_removed"]
                    logger.metrics.boilerplate_removed += clean_counts["boilerplate_removed"]
                    logger.metrics.broadcast_artifacts_removed += clean_counts["broadcast_artifacts_removed"]

                    if not processed_text or not processed_text.strip():
                        logger.metrics.records_skipped += 1
                        logger.log_error_record(
                            line_num=line_num,
                            error_type="EMPTY_AFTER_CLEANING",
                            message="Text became empty after removing web scraping noise",
                            record_id=rec_id,
                        )
                        continue

                    # 4. Categorize text
                    category = self.categorizer.categorize(processed_text)

                    # 5. Build final record with strict 3 keys in order: id, text, category
                    final_obj = {
                        "id": rec_id,
                        "text": processed_text,
                        "category": category,
                    }

                    # 6. Validate output compliance
                    out_valid, out_err = self.output_validator.validate_record(final_obj)
                    if not out_valid:
                        logger.metrics.records_skipped += 1
                        logger.log_error_record(
                            line_num=line_num,
                            error_type="OUTPUT_VALIDATION_FAILURE",
                            message=out_err or "Output validation failed",
                            record_id=rec_id,
                        )
                        continue

                    # 7. Write line immediately (buffered)
                    json_line = json.dumps(final_obj, ensure_ascii=False)
                    out_fp.write(json_line + "\n")

                    logger.metrics.records_success += 1
                    logger.metrics.category_counts[category] += 1
                    if resume and rec_id:
                        resumed_ids.add(rec_id)

                except Exception as ex:
                    # Isolate errors to this single record
                    logger.metrics.records_malformed += 1
                    logger.log_error_record(
                        line_num=line_num,
                        error_type="PROCESSING_EXCEPTION",
                        message=str(ex),
                        record_id=rec_id,
                        raw_data=raw_record.raw_text,
                    )
                    continue

                # Periodic progress reporting
                logger.report_progress(interval=self.config.progress_interval)

                # Periodic checkpointing
                if resume and logger.metrics.records_read % 10000 == 0:
                    self.save_checkpoint(checkpoint_file, resumed_ids, line_num)

            # Flush output stream
            out_fp.flush()
            out_fp.close()

            # Atomic rename if temporary file was used
            if not resume or not output_path.exists():
                if target_out_path.exists():
                    target_out_path.replace(output_path)

            # Clean up checkpoint on complete run
            if checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                except Exception:
                    pass

            logger.report_progress(force=True)
            logger.print_final_summary()

        finally:
            if not out_fp.closed:
                out_fp.close()
            logger.close()

        return logger
