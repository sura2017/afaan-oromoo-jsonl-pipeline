"""Phase 1: Web-scraping noise and artifact removal with placeholder protection."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


class TextCleaner:
    """Removes web-scraping noise, URLs, domain fragments, boilerplate, and broadcast artifacts."""

    # Match bracketed placeholders like [Name], [Phone], [Email], [Organization], etc.
    PLACEHOLDER_REGEX = re.compile(r"(\[[a-zA-Z0-9_\-\s]+\])")

    # Full URLs: http://, https://, ftp://, www.
    URL_REGEX = re.compile(
        r"(?:https?://|ftp://|www\.)[^\s/$.?#].[^\s]*",
        re.IGNORECASE,
    )

    # Social media short links: t.me/..., telegram.me/...
    TELEGRAM_URL_REGEX = re.compile(
        r"\b(?:https?://)?(?:t\.me|telegram\.me)/[a-zA-Z0-9_+/-]+",
        re.IGNORECASE,
    )

    # Common domain artifacts like fanabc.com, fbc.com, example.com/path
    DOMAIN_FRAGMENT_REGEX = re.compile(
        r"\b[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|org|net|me|info|tv|edu|et|io|gov)(?:/[^\s]*)?",
        re.IGNORECASE,
    )

    def __init__(
        self,
        boilerplate_phrases: Optional[List[str]] = None,
        broadcast_terms: Optional[List[str]] = None,
    ) -> None:
        self.boilerplate_phrases = boilerplate_phrases or []
        self.broadcast_terms = broadcast_terms or []

        # Compile boilerplate patterns with punctuation flexibility
        self._compiled_boilerplate = []
        for phrase in self.boilerplate_phrases:
            phrase_esc = re.escape(phrase.strip())
            # Match phrase with optional trailing punctuation (. ? !) without broken \b
            pattern = re.compile(
                rf"\b{phrase_esc}(?:[\.?!]+|\b)",
                re.IGNORECASE,
            )
            self._compiled_boilerplate.append(pattern)

        # Compile broadcast call-signs with word boundaries
        self._compiled_broadcast = []
        for term in self.broadcast_terms:
            term_esc = re.escape(term.strip())
            # Match e.g. "FBC - ", "FBC: ", "(FBC)", or standalone "FBC "
            pattern = re.compile(
                rf"(?:\({term_esc}\)|\[{term_esc}\]|\b{term_esc}\b(?:\s*[:\-\u2013\u2014])?)",
                re.IGNORECASE,
            )
            self._compiled_broadcast.append(pattern)

    def protect_placeholders(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace bracketed placeholders (e.g. [Name], [Phone]) with unique tokens.
        """
        protected_map: Dict[str, str] = {}

        def repl(match: re.Match) -> str:
            ph = match.group(0)
            token = f"__PROTECTED_PH_{len(protected_map)}__"
            protected_map[token] = ph
            return token

        masked_text = self.PLACEHOLDER_REGEX.sub(repl, text)
        return masked_text, protected_map

    def restore_placeholders(self, text: str, protected_map: Dict[str, str]) -> str:
        """Restore protected placeholder tokens to their original text."""
        restored = text
        for token, original in protected_map.items():
            restored = restored.replace(token, original)
        return restored

    def clean(
        self, text: str, restore: bool = True
    ) -> Tuple[str, Dict[str, int]]:
        """
        Clean text of web-scraping noise, URLs, boilerplate, and broadcast artifacts.

        Returns:
            (cleaned_text, removal_counts_dict)
        """
        counts = {
            "urls_removed": 0,
            "domains_removed": 0,
            "boilerplate_removed": 0,
            "broadcast_artifacts_removed": 0,
        }

        if not text or not text.strip():
            return "", counts

        # Step 1: Protect placeholders
        masked_text, placeholder_map = self.protect_placeholders(text)

        # Step 2: Remove full URLs
        url_matches = len(self.URL_REGEX.findall(masked_text))
        telegram_matches = len(self.TELEGRAM_URL_REGEX.findall(masked_text))
        counts["urls_removed"] += (url_matches + telegram_matches)
        cleaned = self.TELEGRAM_URL_REGEX.sub(" ", masked_text)
        cleaned = self.URL_REGEX.sub(" ", cleaned)

        # Step 3: Remove embedded domain fragments (e.g., fanabc.com, fbc.com)
        domain_matches = len(self.DOMAIN_FRAGMENT_REGEX.findall(cleaned))
        counts["domains_removed"] += domain_matches
        cleaned = self.DOMAIN_FRAGMENT_REGEX.sub(" ", cleaned)

        # Step 4: Remove broadcast call-signs (e.g. FBC, FMC)
        for b_pat in self._compiled_broadcast:
            b_matches = len(b_pat.findall(cleaned))
            if b_matches > 0:
                counts["broadcast_artifacts_removed"] += b_matches
                cleaned = b_pat.sub(" ", cleaned)

        # Step 5: Remove configurable web-scraping boilerplate phrases
        for bp_pat in self._compiled_boilerplate:
            bp_matches = len(bp_pat.findall(cleaned))
            if bp_matches > 0:
                counts["boilerplate_removed"] += bp_matches
                cleaned = bp_pat.sub(" ", cleaned)

        # Step 6: Normalize whitespace and orphaned separated punctuation
        cleaned = re.sub(r"\s+([.,?!])", r"\1", cleaned)
        cleaned = re.sub(r"([.?!])\s+([.?!])+", r"\1", cleaned)
        cleaned = re.sub(r"[\t\r\n]+", " ", cleaned)
        cleaned = re.sub(r" +", " ", cleaned).strip()

        # Step 7: Restore placeholders if requested
        if restore:
            cleaned = self.restore_placeholders(cleaned, placeholder_map)

        return cleaned, counts


