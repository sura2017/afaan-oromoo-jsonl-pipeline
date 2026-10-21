"""Tests for sentence boundary detection, Afaan Oromoo hudhaa, and spelling normalization."""

import unittest

from src.cleaner import TextCleaner
from src.sentence_processor import SentenceProcessor
from src.spelling_corrector import SpellingCorrector


class TestSentenceProcessing(unittest.TestCase):
    """Test suite for sentence boundary annotation, hudhaa, and capitalization."""

    def setUp(self):
        self.cleaner = TextCleaner(
            boilerplate_phrases=["Share waliif godhaa"],
            broadcast_terms=["FBC"],
        )
        self.spelling_corrector = SpellingCorrector(
            proper_nouns={
                "atnaatewoos": "Atnaatewoos",
                "iskindiriyaa": "Iskindiriyaa",
                "iskindiriyaatti": "Iskindiriyaatti",
                "inxoos": "Inxoos",
                "finfinnee": "Finfinnee",
                "oromiyaa": "Oromiyaa",
                "itoophiyaa": "Itoophiyaa",
            },
            unambiguous_replacements={
                "bu ' aa": "bu'aa",
                "duuka bu ' aa": "duuka bu'aa",
                "duuka bu 'ootaa": "duuka bu'ootaa",
                "lakkaa ' amuuf": "lakkaa'amuuf",
                "ta ' e": "ta'e",
                "har ' a": "har'a",
            },
        )
        self.sentence_processor = SentenceProcessor()

    def test_prompt_reference_example(self):
        """
        Verify the exact benchmark example provided in Section 26 of the prompt:
        Input:
            fanabc.com abboota mana kiristaanaa qulqulluu atnaatewoos duuka bu'ootaa keessaa
            wal qixa waan lakkaa'amuuf duuka bu'aa ni jedhama bara ttii iskindiriyaatti
            dhalatee bara dargaggummaa abbaa inxoos waliin gammoojjii keessatti jiraachaa
            turaan Share waliif godhaa
        Expected:
            Abboota mana kiristaanaa qulqulluu Atnaatewoos duuka bu'ootaa keessaa wal qixa
            waan lakkaa'amuuf duuka bu'aa ni jedhama. Bara ttii Iskindiriyaatti dhalatee
            bara dargaggummaa abbaa Inxoos waliin gammoojjii keessatti jiraachaa turaan.
        """
        raw_text = (
            "fanabc.com abboota mana kiristaanaa qulqulluu atnaatewoos duuka bu'ootaa keessaa "
            "wal qixa waan lakkaa'amuuf duuka bu'aa ni jedhama bara ttii iskindiriyaatti "
            "dhalatee bara dargaggummaa abbaa inxoos waliin gammoojjii keessatti jiraachaa "
            "turaan Share waliif godhaa"
        )
        expected = (
            "Abboota mana kiristaanaa qulqulluu Atnaatewoos duuka bu'ootaa keessaa wal qixa "
            "waan lakkaa'amuuf duuka bu'aa ni jedhama. Bara ttii Iskindiriyaatti dhalatee "
            "bara dargaggummaa abbaa Inxoos waliin gammoojjii keessatti jiraachaa turaan."
        )

        cleaned, _ = self.cleaner.clean(raw_text)
        corrected = self.spelling_corrector.correct(cleaned)
        final_text = self.sentence_processor.process(corrected)

        self.assertEqual(final_text, expected)

    def test_question_detection(self):
        """Verify questions receive '?' ending punctuation."""
        text = "Barattoonni qormaata eessa fudhatu"
        processed = self.sentence_processor.process(text)
        self.assertTrue(processed.endswith("?"))
        self.assertEqual(processed, "Barattoonni qormaata eessa fudhatu?")

        # Alternative question with 'moo'
        text_alt = "Inni har'a dhufa moo"
        processed_alt = self.sentence_processor.process(text_alt)
        self.assertTrue(processed_alt.endswith("?"))

    def test_single_spacing_after_punctuation(self):
        """Verify exactly one space follows period and no missing/double spaces."""
        text = "Kun odeeffannoo dha.Kunis fakkeenya dha.   Sunis dhugaa dha."
        processed = self.sentence_processor.process(text)
        self.assertEqual(processed, "Kun odeeffannoo dha. Kunis fakkeenya dha. Sunis dhugaa dha.")

    def test_sentence_capitalization(self):
        """Verify first letter of each sentence is capitalized."""
        text = "oduun har'aa kunooti. barattoonni gara mana barumsaa deeman."
        processed = self.sentence_processor.process(text)
        self.assertEqual(processed, "Oduun har'aa kunooti. Barattoonni gara mana barumsaa deeman.")

    def test_hudhaa_preservation_and_repair(self):
        """Verify valid hudhaa is preserved and split apostrophes are repaired."""
        # Split hudhaa
        text1 = "bu ' aa guddaa argate"
        corrected1 = self.spelling_corrector.correct(text1)
        self.assertEqual(corrected1, "bu'aa guddaa argate")

        # Curly quotes acting as hudhaa
        text2 = "har’a dhufe"
        corrected2 = self.spelling_corrector.correct(text2)
        self.assertEqual(corrected2, "har'a dhufe")

        # Complex hudhaa tokens
        text3 = "lakkaa ' amuuf duuka bu 'ootaa"
        corrected3 = self.spelling_corrector.correct(text3)
        self.assertEqual(corrected3, "lakkaa'amuuf duuka bu'ootaa")

    def test_placeholder_retention(self):
        """Verify placeholders like [Name] remain untouched through sentence processing."""
        text = "obbo [Name] bilbila [Phone] qabu. isaan [Address] jiraatu."
        processed = self.sentence_processor.process(text)
        self.assertIn("[Name]", processed)
        self.assertIn("[Phone]", processed)
        self.assertIn("[Address]", processed)


if __name__ == "__main__":
    unittest.main()
