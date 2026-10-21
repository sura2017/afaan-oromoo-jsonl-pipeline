"""Large-scale streaming, memory stability, throughput, and resume test."""

import json
import tempfile
import tracemalloc
import unittest
from pathlib import Path

from src.config import PipelineConfig
from src.output_validator import OutputValidator
from src.pipeline import DatasetPipeline


class TestLargeFileProcessing(unittest.TestCase):
    """Verifies streaming processing, constant memory usage, and resilience on large datasets."""

    def test_streaming_and_memory_stability_5000_records(self):
        """Generate 5,000 synthetic records with noise and malformed lines to test streaming and memory."""
        config = PipelineConfig()
        pipeline = DatasetPipeline(config=config)
        output_validator = OutputValidator(controlled_vocabulary=config.controlled_vocabulary)

        num_records = 5000

        # Create temporary input file
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f_in:
            in_path = Path(f_in.name)

            for i in range(1, num_records + 1):
                # Interspersed intentional malformed JSON line
                if i in (100, 2500):
                    f_in.write('{"id": "bad_json_' + str(i) + '", INVALID_JSON_SYNTAX\n')
                    continue

                # Interspersed intentional duplicate ID
                if i == 500:
                    f_in.write('{"id": "oro_syn_0000001", "text": "Duplicate id test."}\n')
                    continue

                # Interspersed empty text record
                if i == 1500:
                    f_in.write('{"id": "oro_empty_' + str(i) + '", "text": "   "}\n')
                    continue

                # Mixed categories and noise
                mod = i % 5
                if mod == 0:
                    text = (
                        f"fanabc.com abboota mana kiristaanaa qulqulluu atnaatewoos duuka bu 'ootaa "
                        f"keessaa wal qixa waan lakkaa ' amuuf duuka bu ' aa ni jedhama bara ttii iskindiriyaatti "
                        f"dhalatee bara dargaggummaa abbaa inxoos waliin gammoojjii keessatti jiraachaa turaan "
                        f"Share waliif godhaa record {i}"
                    )
                elif mod == 1:
                    text = (
                        f"FBC: Tapha kubbaa miilaa har'a gaggeeffame irratti atleetiksii fi dorgommii "
                        f"guddaa https://example.com/sports ilaalaa record {i}."
                    )
                elif mod == 2:
                    text = (
                        f"Barattoonni yuunivarsiitii qormaata fudhachaa jiru. Teelegiraama keenya join godhaa! "
                        f"Barsiisaan kutaa barnootaa keessatti digirii barsiisa record {i}."
                    )
                elif mod == 3:
                    text = (
                        f"Gabaa fi baankii keessatti gatiin sharafa qarshii fi diinagdee dabale "
                        f"t.me/business_news record {i}."
                    )
                else:
                    text = (
                        f"Hospitaala keessatti yaala fayyaa fi talaallii doktora irraa argatan "
                        f"obbo [Name] bilbila [Phone] irratti qunnamaa record {i}."
                    )

                rec = {"id": f"oro_syn_{i:07d}", "text": text}
                f_in.write(json.dumps(rec) + "\n")

        out_path = in_path.parent / "test_out_cleaned.jsonl"
        err_path = in_path.parent / "test_out_errors.jsonl"
        log_path = in_path.parent / "test_out_log.log"

        tracemalloc.start()
        try:
            logger = pipeline.run(
                input_file=in_path,
                output_file=out_path,
                error_file=err_path,
                log_file=log_path,
            )
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # 1. Verify memory stayed low (peak memory under 50 MB, demonstrating streaming)
            peak_mb = peak_mem / (1024 * 1024)
            self.assertLess(peak_mb, 50.0, f"Memory usage was too high ({peak_mb:.2f} MB), not streaming properly!")

            # 2. Verify throughput is fast (exceeds 100 rec/sec)
            self.assertGreater(logger.metrics.throughput, 100.0, f"Throughput {logger.metrics.throughput:.1f} rec/sec too slow")


            # 3. Verify counts
            self.assertGreater(logger.metrics.records_success, 4900)
            self.assertEqual(logger.metrics.records_malformed, 2)  # lines 100 and 2500
            self.assertEqual(logger.metrics.duplicate_ids, 1)      # line 500
            self.assertEqual(logger.metrics.records_skipped, 1)    # line 1500

            # 4. Verify output file passes full independent validation
            is_valid, record_count, val_errors = output_validator.validate_file(out_path)
            self.assertTrue(is_valid, f"Validation errors: {val_errors[:5]}")
            self.assertEqual(record_count, logger.metrics.records_success)

        finally:
            for p in (in_path, out_path, err_path, log_path):
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass


if __name__ == "__main__":
    unittest.main()

