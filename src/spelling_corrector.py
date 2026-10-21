"""Phase 2: Afaan Oromoo spelling normalization, hudhaa handling, and proper noun casing."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


class SpellingCorrector:
    """Corrects unambiguous Afaan Oromoo spelling artifacts, hudhaa tokens, and proper nouns."""

    # Matches split apostrophes like "bu ' aa" or "ta 'e" or "har' a"
    SPLIT_HUDHAA_REGEX = re.compile(
        r"(\b[a-zA-Z]+)\s*['’`´]\s*([a-zA-Z]+\b)"
    )

    # Unicode curly quotes or backticks acting as hudhaa inside words
    UNICODE_HUDHAA_REGEX = re.compile(
        r"([a-zA-Z])[’`´]([a-zA-Z])"
    )

    def __init__(
        self,
        proper_nouns: Optional[Dict[str, str]] = None,
        unambiguous_replacements: Optional[Dict[str, str]] = None,
    ) -> None:
        self.proper_nouns = proper_nouns or {}
        self.unambiguous_replacements = unambiguous_replacements or {}

        # Compile regex for proper nouns with word boundaries (case-insensitive)
        self._compiled_proper_nouns = []
        for lower_form, target_casing in self.proper_nouns.items():
            pattern = re.compile(rf"\b{re.escape(lower_form)}\b", re.IGNORECASE)
            self._compiled_proper_nouns.append((pattern, target_casing))

        # Compile unambiguous phrase replacements
        self._compiled_unambiguous = []
        for raw_err, corrected in self.unambiguous_replacements.items():
            pattern = re.compile(rf"\b{re.escape(raw_err)}\b", re.IGNORECASE)
            self._compiled_unambiguous.append((pattern, corrected))

    def correct_hudhaa(self, text: str) -> str:
        """
        Normalize and repair Afaan Oromoo hudhaa (glottal stop apostrophe).
        Ensures words like bu'aa, duuka bu'aa, lakkaa'amuuf are properly formed.
        """
        # Step 1: Normalize unicode quote variants inside words to standard apostrophe
        res = self.UNICODE_HUDHAA_REGEX.sub(r"\1'\2", text)

        # Step 2: Fix split hudhaa patterns e.g. "bu ' aa" -> "bu'aa"
        res = self.SPLIT_HUDHAA_REGEX.sub(r"\1'\2", res)

        return res

    def apply_unambiguous_corrections(self, text: str) -> str:
        """Apply unambiguous dictionary-based token fixes without guessing."""
        res = text
        for pattern, replacement in self._compiled_unambiguous:
            res = pattern.sub(replacement, res)
        return res

    def apply_proper_noun_casing(self, text: str) -> str:
        """Ensure established proper nouns and names have correct capitalization."""
        res = text
        for pattern, target in self._compiled_proper_nouns:
            res = pattern.sub(target, res)
        return res

    def correct(self, text: str) -> str:
        """
        Run safe spelling and hudhaa correction pipeline.
        Only unambiguous, meaning-preserving corrections are applied.
        """
        if not text:
            return ""

        # 1. Unambiguous phrase corrections (e.g. "duuka bu ' aa" -> "duuka bu'aa")
        text = self.apply_unambiguous_corrections(text)

        # 2. Hudhaa repair and normalization
        text = self.correct_hudhaa(text)

        # 3. Proper noun capitalization
        text = self.apply_proper_noun_casing(text)

        return text
