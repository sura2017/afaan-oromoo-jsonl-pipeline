"""Phase 3: Topic classification for Afaan Oromoo text."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set


class TextCategorizer:
    """Classifies Afaan Oromoo text into standardized controlled categories."""

    DEFAULT_CONTROLLED_VOCABULARY = [
        "News", "Politics", "Sports", "Religion", "Education", "Health",
        "Economy", "Entertainment", "Technology", "Business", "Agriculture",
        "Science", "Environment", "Culture", "Crime", "Law", "Government",
        "International", "Society", "Lifestyle", "Weather", "Other"
    ]

    def __init__(
        self,
        controlled_vocabulary: Optional[List[str]] = None,
        normalization_map: Optional[Dict[str, str]] = None,
        category_keywords: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.controlled_vocabulary = (
            controlled_vocabulary or self.DEFAULT_CONTROLLED_VOCABULARY
        )
        self.allowed_set: Set[str] = set(self.controlled_vocabulary)
        self.normalization_map = normalization_map or {}
        self.category_keywords = category_keywords or {}

        # Compile word and phrase patterns for efficient matching
        self._compiled_keywords: Dict[str, List[re.Pattern]] = {}
        for cat, keywords in self.category_keywords.items():
            self._compiled_keywords[cat] = []
            for kw in keywords:
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                # Phrase or token match with word boundaries
                pattern = re.compile(rf"\b{re.escape(kw_clean)}\b", re.IGNORECASE)
                self._compiled_keywords[cat].append(pattern)

    def normalize_category(self, raw_category: Optional[str]) -> str:
        """
        Normalize raw category string against controlled vocabulary and normalization map.
        Guarantees returned category is in self.allowed_set.
        """
        if not raw_category or not str(raw_category).strip():
            return "Other"

        cat_clean = str(raw_category).strip()

        # Direct match in allowed set
        if cat_clean in self.allowed_set:
            return cat_clean

        # Check normalization map
        cat_lower = cat_clean.lower()
        if cat_lower in self.normalization_map:
            normalized = self.normalization_map[cat_lower]
            if normalized in self.allowed_set:
                return normalized

        # Title case check
        cat_title = cat_clean.capitalize()
        if cat_title in self.allowed_set:
            return cat_title

        # Safe fallback
        return "Other"

    def predict_category(self, text: str) -> str:
        """
        Predict the core category of the cleaned Afaan Oromoo text.
        Uses keyword, phrase, and morphosyntactic topical indicators.
        """
        if not text or not text.strip():
            return "Other"

        scores: Dict[str, float] = {cat: 0.0 for cat in self.controlled_vocabulary}
        text_lower = text.lower()

        # Score matching keywords/phrases
        # The lead clause (first ~30 words) provides strong thematic anchoring for news/web text
        words = text_lower.split()
        lead_text = " ".join(words[:30])

        for cat, patterns in self._compiled_keywords.items():
            for pat in patterns:
                matches = len(pat.findall(text_lower))
                if matches > 0:
                    phrase_weight = 2.5 if " " in pat.pattern else 1.0
                    lead_bonus = 1.5 if pat.search(lead_text) else 1.0
                    scores[cat] += matches * phrase_weight * lead_bonus


        # Find category with maximum score
        best_cat = "Other"
        max_score = 0.0

        for cat, score in scores.items():
            if score > max_score:
                max_score = score
                best_cat = cat

        # Require a minimal threshold score of 1.0 to assign specific category, else Other
        if max_score < 1.0:
            return "Other"

        return self.normalize_category(best_cat)

    def categorize(self, text: str) -> str:
        """Assign standardized single category to text."""
        raw_pred = self.predict_category(text)
        return self.normalize_category(raw_pred)
