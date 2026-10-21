"""Tests for text categorization and controlled vocabulary enforcement."""

import unittest

from src.config import PipelineConfig
from src.categorizer import TextCategorizer


class TestCategorization(unittest.TestCase):
    """Test suite for Afaan Oromoo topic categorization."""

    def setUp(self):
        config = PipelineConfig()
        self.categorizer = TextCategorizer(
            controlled_vocabulary=config.controlled_vocabulary,
            normalization_map=config.category_normalization,
            category_keywords=config.category_keywords,
        )

    def test_religion_categorization(self):
        text = "Abboota mana kiristaanaa qulqulluu Atnaatewoos duuka bu'ootaa keessaa wal qixa waan lakkaa'amuuf."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Religion")

    def test_sports_categorization(self):
        text = "Tapha kubbaa miilaa har'a gaggeeffame irratti gareen keenya mo'ate."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Sports")

    def test_education_categorization(self):
        text = "Barattoonni yuunivarsiitii qormaata isaanii kutaa barnootaa keessatti fudhatan."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Education")

    def test_politics_categorization(self):
        text = "Paartileen siyaasaa filannoo heera mootummaa irratti mari'atan."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Politics")

    def test_health_categorization(self):
        text = "Hospitaala keessatti doktora irraa qoricha fi yaala fayyaa argatan."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Health")

    def test_technology_categorization(self):
        text = "Sooftiweerii haaraa fi teeknooloojii komaapitarra artiifishaal intalijansii uuman."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Technology")

    def test_economy_categorization(self):
        text = "Gabaa fi baankii keessatti gatiin sharafa qarshii fi diinagdee dabale."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Economy")

    def test_agriculture_categorization(self):
        text = "Qonnaan bultoonni sanyii filatamaa fi midhaan callaa qonnaa oomishtan."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Agriculture")

    def test_fallback_to_other(self):
        text = "Namni tokko gara gandaatti dhufe."
        cat = self.categorizer.categorize(text)
        self.assertEqual(cat, "Other")

    def test_category_normalization_variants(self):
        """Verify normalization of variants into standard vocabulary."""
        self.assertEqual(self.categorizer.normalize_category("religious"), "Religion")
        self.assertEqual(self.categorizer.normalize_category("sport"), "Sports")
        self.assertEqual(self.categorizer.normalize_category("sports"), "Sports")
        self.assertEqual(self.categorizer.normalize_category("tech"), "Technology")
        self.assertEqual(self.categorizer.normalize_category("non_existent_category"), "Other")
        self.assertEqual(self.categorizer.normalize_category(""), "Other")
        self.assertEqual(self.categorizer.normalize_category(None), "Other")


if __name__ == "__main__":
    unittest.main()
