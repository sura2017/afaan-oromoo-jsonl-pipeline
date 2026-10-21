"""Tests for Web-Scraping Noise & Artifact Cleaner."""

import unittest

from src.cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    """Test suite for TextCleaner."""

    def setUp(self):
        self.cleaner = TextCleaner(
            boilerplate_phrases=[
                "Share waliif godhaa",
                "Teelegiraama keenya join godhaa",
                "Like fi Share gochuu hin dagatinaa",
                "Follow us",
            ],
            broadcast_terms=["FBC", "FMC", "OBN"],
        )

    def test_url_removal_http_https_www(self):
        """Verify removal of http, https, and www URLs."""
        # Standard https URL
        text1 = "Odeeffannoo dabalataa https://example.com argachuu dandeessu."
        cleaned1, c1 = self.cleaner.clean(text1)
        self.assertEqual(cleaned1, "Odeeffannoo dabalataa argachuu dandeessu.")
        self.assertEqual(c1["urls_removed"], 1)

        # http with query path
        text2 = "Liinkii kana http://www.example.com/path?a=1 ilaalaa."
        cleaned2, c2 = self.cleaner.clean(text2)
        self.assertEqual(cleaned2, "Liinkii kana ilaalaa.")
        self.assertEqual(c2["urls_removed"], 1)

        # www URL
        text3 = "Websaayitii www.example.org/news daawwadhaa."
        cleaned3, c3 = self.cleaner.clean(text3)
        self.assertEqual(cleaned3, "Websaayitii daawwadhaa.")
        self.assertEqual(c3["urls_removed"], 1)

    def test_telegram_and_short_urls(self):
        """Verify removal of t.me and telegram links."""
        text = "Teelegiraama keenya t.me/oromia_news irratti hordofaa."
        cleaned, c = self.cleaner.clean(text)
        self.assertEqual(cleaned, "Teelegiraama keenya irratti hordofaa.")
        self.assertEqual(c["urls_removed"], 1)

    def test_embedded_domain_fragments(self):
        """Verify removal of domain fragments like fanabc.com, fbc.com."""
        text = "fanabc.com abboota mana kiristaanaa qulqulluu"
        cleaned, c = self.cleaner.clean(text)
        self.assertEqual(cleaned, "abboota mana kiristaanaa qulqulluu")
        self.assertEqual(c["domains_removed"], 1)

    def test_boilerplate_phrases_exact_and_case_insensitive(self):
        """Verify boilerplate removal with case variations and punctuation."""
        # Exact with period
        text1 = "Barattoonni qormaata fudhachaa jiru. Share waliif godhaa."
        cleaned1, c1 = self.cleaner.clean(text1)
        self.assertEqual(cleaned1, "Barattoonni qormaata fudhachaa jiru.")
        self.assertEqual(c1["boilerplate_removed"], 1)

        # Case-insensitive with exclamation mark
        text2 = "Oduu haaraa share waliif godhaa! OBN gabaase."
        cleaned2, c2 = self.cleaner.clean(text2)
        self.assertIn("Oduu haaraa", cleaned2)
        self.assertNotIn("share waliif godhaa", cleaned2.lower())

        # Telegram join prompt
        text3 = "Teelegiraama keenya join godhaa! Oduu guyyaa argaa."
        cleaned3, c3 = self.cleaner.clean(text3)
        self.assertEqual(cleaned3, "Oduu guyyaa argaa.")

    def test_broadcast_call_signs(self):
        """Verify removal of broadcast station prefixes without damaging inside words."""
        # Call-sign at start
        text1 = "FBC: Odeeffannoo haaraa Finfinnee irraa."
        cleaned1, c1 = self.cleaner.clean(text1)
        self.assertEqual(cleaned1, "Odeeffannoo haaraa Finfinnee irraa.")
        self.assertEqual(c1["broadcast_artifacts_removed"], 1)

        # Call-sign in parentheses
        text2 = "Gabaasni dhiyaate (OBN) akka ibsetti..."
        cleaned2, c2 = self.cleaner.clean(text2)
        self.assertEqual(cleaned2, "Gabaasni dhiyaate akka ibsetti...")

        # Ensure valid word containing abbreviation letters is NOT damaged
        text3 = "FMC qabsoo ifaa"
        cleaned3, _ = self.cleaner.clean(text3)
        self.assertEqual(cleaned3, "qabsoo ifaa")

    def test_placeholder_preservation(self):
        """Verify placeholders like [Name], [Phone], [Email] are 100% preserved."""
        text = "[Name] bilbila [Phone] fi email [Email] irratti qunnamaa."
        cleaned, _ = self.cleaner.clean(text)
        self.assertIn("[Name]", cleaned)
        self.assertIn("[Phone]", cleaned)
        self.assertIn("[Email]", cleaned)
        self.assertEqual(cleaned, "[Name] bilbila [Phone] fi email [Email] irratti qunnamaa.")

    def test_whitespace_normalization(self):
        """Verify multiple spaces, tabs, and newlines become single space."""
        text = "  Dubbii    bal'aa\t\tbaay'ee\n\nqaba.   "
        cleaned, _ = self.cleaner.clean(text)
        self.assertEqual(cleaned, "Dubbii bal'aa baay'ee qaba.")
        # Ensure hudhaa apostrophe is preserved
        self.assertIn("bal'aa", cleaned)
        self.assertIn("baay'ee", cleaned)


if __name__ == "__main__":
    unittest.main()
