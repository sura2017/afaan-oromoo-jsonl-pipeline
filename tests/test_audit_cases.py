"""Strict Pre-Submission Audit Verification Test Suite."""

import json
import tempfile
import unittest
from pathlib import Path

from src.cleaner import TextCleaner
from src.config import PipelineConfig
from src.categorizer import TextCategorizer
from src.output_validator import OutputValidator
from src.pipeline import DatasetPipeline
from src.sentence_processor import SentenceProcessor
from src.spelling_corrector import SpellingCorrector


class TestStrictAuditSuite(unittest.TestCase):
    """Deep quality verification across all supervisor audit requirements."""

    def setUp(self):
        self.config = PipelineConfig()
        self.pipeline = DatasetPipeline(config=self.config)
        self.cleaner = self.pipeline.cleaner
        self.sentence_processor = self.pipeline.sentence_processor
        self.spelling_corrector = self.pipeline.spelling_corrector
        self.categorizer = self.pipeline.categorizer
        self.validator = OutputValidator(controlled_vocabulary=self.config.controlled_vocabulary)

    # ---------------------------------------------------------
    # 1. PHASE 1 AUDIT: Web-Scraping Noise, URLs, Domains, Boilerplate
    # ---------------------------------------------------------
    def test_url_removal_exhaustive(self):
        """Test http, https, www, path, query, embedded, t.me, and fragment checks."""
        samples = [
            ("Odeeffannoo http://example.com argadhaa.", "Odeeffannoo argadhaa."),
            ("Gabaasa https://example.com/ ilaalaa.", "Gabaasa ilaalaa."),
            ("Websaayitii www.example.com daawwadhaa.", "Websaayitii daawwadhaa."),
            ("Fuula https://example.com/path/to/resource ilaalaa.", "Fuula ilaalaa."),
            ("Liinkii http://www.example.com/path?a=1&b=2 cuqaasaa.", "Liinkii cuqaasaa."),
            ("Odeeffannoo dabalataa https://example.com argachuu dandeessu.", "Odeeffannoo dabalataa argachuu dandeessu."),
            ("Teelegiraama t.me/oromia_news hordofaa.", "Teelegiraama hordofaa."),
            ("Karaa telegram.me/oromia_news nu qunnamaa.", "Karaa nu qunnamaa."),
        ]
        forbidden_fragments = ["http", "https", "www", "://", ".com", "/path"]

        for raw, expected in samples:
            cleaned, _ = self.cleaner.clean(raw)
            self.assertEqual(cleaned, expected, f"Failed on URL case: {raw}")
            # Ensure no residue fragments
            for frag in forbidden_fragments:
                self.assertNotIn(frag, cleaned.lower(), f"Forbidden fragment '{frag}' found in: {cleaned}")

    def test_domain_fragments(self):
        """Test removal of domain fragments without damaging legitimate words."""
        raw = "fanabc.com abboota mana kiristaanaa fbc.com qulqulluu"
        cleaned, _ = self.cleaner.clean(raw)
        self.assertEqual(cleaned, "abboota mana kiristaanaa qulqulluu")

        # Legitimate Afaan Oromoo words with apostrophes or similar sounds must NOT be removed
        legit = "waldaan komishinii naannoo Oromiyaa keessatti hojjeta."
        cleaned_legit, _ = self.cleaner.clean(legit)
        self.assertEqual(cleaned_legit, legit)

    def test_boilerplate_exhaustive(self):
        """Test exact, lowercase, UPPERCASE, repeated, and punctuated boilerplate."""
        cases = [
            "Oduu haaraa. Share waliif godhaa.",
            "Oduu haaraa. share waliif godhaa",
            "Oduu haaraa. SHARE WALII GODHAA",
            "Oduu haaraa. Share waliif godhaa! Share waliif godhaa.",
            "Teelegiraama keenya join godhaa! Oduu haaraa.",
        ]
        for raw in cases:
            cleaned, counts = self.cleaner.clean(raw)
            self.assertNotIn("share walii", cleaned.lower())
            self.assertNotIn("join godhaa", cleaned.lower())
            self.assertIn("Oduu haaraa", cleaned)

    def test_broadcast_call_signs_boundary_safety(self):
        """Test FBC, FMC, OBN removal and verify words containing those substrings are NOT damaged."""
        raw = "FBC: Odeeffannoo haaraa Finfinnee irraa. (OBN) gabaase. FMC ifa baase."
        cleaned, counts = self.cleaner.clean(raw)
        self.assertNotIn("FBC:", cleaned)
        self.assertNotIn("(OBN)", cleaned)
        self.assertEqual(cleaned, "Odeeffannoo haaraa Finfinnee irraa. gabaase. ifa baase.")

        # Words with overlapping letter sequences must NOT be damaged
        safe_words = "Dhaabbanni dhiigaa fi qabsoon ifaa dha."
        cleaned_safe, _ = self.cleaner.clean(safe_words)
        self.assertEqual(cleaned_safe, safe_words)

    # ---------------------------------------------------------
    # 2. PLACEHOLDER PROTECTION AUDIT
    # ---------------------------------------------------------
    def test_placeholder_protection_throughout_pipeline(self):
        """Verify [Name], [Phone], [Email], [Organization], [Address] are 100% untouched."""
        cases = [
            "[Name] bilbila [Phone] irratti nu qunnamaa.",
            "Dhaabbata [Organization] keessatti [Email] fayyadamaa.",
            "[Name], teessoo [Address] qabu.",
            "[name] bilbila [phone] qaba.",  # Lowercase placeholder contents must NOT be altered
        ]
        for text in cases:
            processed, _ = self.pipeline.process_record_text(text)
            if "[Name]" in text:
                self.assertIn("[Name]", processed)
            if "[name]" in text:
                self.assertIn("[name]", processed)
            if "[Phone]" in text:
                self.assertIn("[Phone]", processed)
            if "[phone]" in text:
                self.assertIn("[phone]", processed)
            if "[Email]" in text:
                self.assertIn("[Email]", processed)
            if "[Organization]" in text:
                self.assertIn("[Organization]", processed)
            if "[Address]" in text:
                self.assertIn("[Address]", processed)


    # ---------------------------------------------------------
    # 3. SENTENCE-BOUNDARY AND NUMBER / CONVERB INTEGRITY
    # ---------------------------------------------------------
    def test_numbers_dates_decimals_not_corrupted(self):
        """Verify decimal numbers (3.14, 10.5%), dates, and codes are never split with periods."""
        raw = "Gatiin boba'aa 3.14 ture. Bara 2024-10-21 gabaasni 12.5% dabale."
        processed, _ = self.pipeline.process_record_text(raw)
        self.assertIn("3.14", processed)
        self.assertIn("12.5%", processed)
        self.assertIn("2024-10-21", processed)

    def test_converbs_and_subordinate_clauses_not_split(self):
        """Verify verbs ending in converb -ee or subordinate -uuf/-f do not trigger false sentence breaks."""
        # Converb 'dhalatee' connects clause to the next
        raw = "Bara ttii Iskindiriyaatti dhalatee bara dargaggummaa gammoojjii keessatti jiraate."
        processed = self.sentence_processor.process(raw)
        # Should not split after dhalatee
        self.assertNotIn("dhalatee.", processed)
        self.assertIn("dhalatee bara", processed)

        # Subordinate clause 'lakkaa'amuuf'
        raw2 = "wal qixa waan lakkaa'amuuf duuka bu'aa ni jedhama."
        processed2 = self.sentence_processor.process(raw2)
        self.assertNotIn("lakkaa'amuuf.", processed2)
        self.assertIn("lakkaa'amuuf duuka", processed2)

    def test_unpunctuated_multi_sentence_segmentation(self):
        """Verify boundary insertion between finite predicate and sentence starter."""
        raw = "Tapha kubbaa miilaa har'a gaggeeffame barattoonni qormaata isaanii fudhatan"
        # gaggeeffame (predicate) followed by barattoonni (starter)
        processed = self.sentence_processor.process(raw)
        self.assertEqual(processed, "Tapha kubbaa miilaa har'a gaggeeffame. Barattoonni qormaata isaanii fudhatan.")

    def test_question_sentence_detection(self):
        """Verify question intonation and interrogative words get '?'."""
        raw = "Qormaanni yoom kennama isaan eessa jiru"
        processed = self.sentence_processor.process(raw)
        self.assertTrue(processed.endswith("?"))

    # ---------------------------------------------------------
    # 4. SPELLING & HUDHAA (GLOTTAL STOP) INTEGRITY
    # ---------------------------------------------------------
    def test_hudhaa_repair_and_no_guessing(self):
        """Verify safe hudhaa fixes and that ambiguous words are never guessed."""
        # Split hudhaa
        self.assertEqual(self.spelling_corrector.correct("bu ' aa"), "bu'aa")
        self.assertEqual(self.spelling_corrector.correct("lakkaa ' amuuf"), "lakkaa'amuuf")
        self.assertEqual(self.spelling_corrector.correct("duuka bu ' aa"), "duuka bu'aa")
        self.assertEqual(self.spelling_corrector.correct("har’a"), "har'a")

        # Ambiguous word without obvious correction must NOT be modified
        ambiguous = "namni lafaa gabaa dhufe"
        self.assertEqual(self.spelling_corrector.correct(ambiguous), ambiguous)

    # ---------------------------------------------------------
    # 5. MEANING PRESERVATION: 20 REPRESENTATIVE SAMPLES
    # ---------------------------------------------------------
    def test_meaning_preservation_20_samples(self):
        """Audit 20 representative Afaan Oromoo texts to ensure strictly noise removal and format fixes."""
        test_samples = [
            ("barattoonni qormaata fudhatan", "Barattoonni qormaata fudhatan."),
            ("tapha kubbaa miilaa mo'atan", "Tapha kubbaa miilaa mo'atan."),
            ("hospitaala keessatti yaala argatan", "Hospitaala keessatti yaala argatan."),
            ("paarlaamaan marii taasise", "Paarlaamaan marii taasise."),
            ("qonnaan bultoonni midhaan oomishtan", "Qonnaan bultoonni midhaan oomishtan."),
            ("baankiin sharafa qarshii ibse", "Baankiin sharafa qarshii ibse."),
            ("sooftiweerii haaraa uuman", "Sooftiweerii haaraa uuman."),
            ("aadaan oromoo seenaa qaba", "Aadaan Oromoo seenaa qaba."),
            ("haalli qilleensaa rooba qaba", "Haalli qilleensaa rooba qaba."),
            ("poolisiin to'annoo jala oolche", "Poolisiin to'annoo jala oolche."),
            ("manni murtii murteesse", "Manni murtii murteesse."),
            ("saayintistoonni qorannoo dhiyeessan", "Saayintistoonni qorannoo dhiyeessan."),
            ("bosonni eegumsa barbaada", "Bosonni eegumsa barbaada."),
            ("aartii fi sirba haaraa qaban", "Aartii fi sirba haaraa qaban."),
            ("dippilomaasiin idil addunyaa cime", "Dippilomaasiin idil addunyaa cime."),
            ("maatiin nagaa qaba", "Maatiin nagaa qaba."),
            ("jireenyi magaalaa gabbate", "Jireenyi magaalaa gabbate."),
            ("biiroon tajaajila kenne", "Biiroon tajaajila kenne."),
            ("namni hundi nagaan jiraata", "Namni hundi nagaan jiraata."),
            ("odeeffannoon haaraa dhufe", "Odeeffannoon haaraa dhufe."),
        ]
        for raw, expected in test_samples:
            processed, _ = self.pipeline.process_record_text(raw)
            self.assertEqual(processed, expected, f"Meaning or casing drifted for: {raw}")

    # ---------------------------------------------------------
    # 6. CATEGORIZATION AUDIT: MULTI-TOPIC EXAMPLES
    # ---------------------------------------------------------
    def test_multi_topic_core_classification(self):
        """Verify core topic is selected when secondary domains are mentioned."""
        # 1. Political article mentioning schools and hospitals
        text_pol = (
            "Paarlaamaan heera mootummaa fi filannoo naannoo irratti mari'achaa jira. "
            "Pirezidaantichi yaada dhiyeesse. Mootummaan mana barumsaa fi hospitaala ijaaruuf bajata ramade."
        )
        self.assertEqual(self.categorizer.categorize(text_pol), "Politics")

        # 2. Education article mentioning government
        text_edu = (
            "Barattoonni qormaata kutaa 12ffaa yuunivarsiitii keessatti fudhachaa jiru. "
            "Barsiisaan barnoota qulqullina qabu kenne. Mootummaan gargaarsa taasise."
        )
        self.assertEqual(self.categorizer.categorize(text_edu), "Education")

        # 3. Health article discussing economic cost
        text_health = (
            "Hospitaala Finfinnee keessatti yaala fayyaa fi talaallii dhibee koronaa doktoraan kennamaa jira. "
            "Dhukkubsattoonni qoricha argatan. Baasii qarshii baankii dabale."
        )
        self.assertEqual(self.categorizer.categorize(text_health), "Health")

        # 4. Technology article mentioning business
        text_tech = (
            "Teeknooloojii sooftiweerii fi komaapitarra artiifishaal intalijansii haaraa ifoome. "
            "Daldaltoonni daldala isaaniitiif appilikeeshinii fayyadaman."
        )
        self.assertEqual(self.categorizer.categorize(text_tech), "Technology")

    # ---------------------------------------------------------
    # 7. CHECKPOINT / RESUME VERIFICATION
    # ---------------------------------------------------------
    def test_interruption_and_resume(self):
        """Verify pipeline can resume without duplicating records or corrupting files."""
        # Create 10 input records
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".jsonl") as f_in:
            in_path = Path(f_in.name)
            for i in range(1, 11):
                f_in.write(json.dumps({"id": f"res_{i}", "text": f"Oduu haaraa record {i}"}) + "\n")

        out_path = in_path.parent / "test_resume_out.jsonl"
        err_path = in_path.parent / "test_resume_err.jsonl"
        log_path = in_path.parent / "test_resume_log.log"

        try:
            # Simulate partial run: write first 4 records directly to out_path
            with open(out_path, "w", encoding="utf-8") as f_out:
                for i in range(1, 5):
                    f_out.write(json.dumps({"id": f"res_{i}", "text": f"Oduu haaraa record {i}.", "category": "News"}) + "\n")

            # Run with resume=True
            pipeline_res = DatasetPipeline(config=self.config)
            logger = pipeline_res.run(
                input_file=in_path,
                output_file=out_path,
                error_file=err_path,
                log_file=log_path,
                resume=True,
            )

            # Verify that only remaining 6 records were processed, total 10 in output
            is_valid, record_count, val_errors = self.validator.validate_file(out_path)
            self.assertTrue(is_valid, f"Validation errors on resumed file: {val_errors}")
            self.assertEqual(record_count, 10, f"Expected 10 total unique records in resumed output, got {record_count}")

        finally:
            for p in (in_path, out_path, err_path, log_path):
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass


if __name__ == "__main__":
    unittest.main()
