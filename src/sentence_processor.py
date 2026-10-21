"""Phase 2: Sentence-boundary detection, punctuation annotation, and sentence capitalization for Afaan Oromoo."""

from __future__ import annotations

import re
from typing import List, Set


class SentenceProcessor:
    """
    Analyzes complete Afaan Oromoo text context to identify natural sentence
    boundaries, inject punctuation, enforce spacing, and ensure correct sentence capitalization.
    """

    # Interrogative indicators in Afaan Oromoo
    INTERROGATIVE_WORDS = {
        "akkam", "akkamitti", "maaliif", "maali", "maal", "eenyu", "eenyuf",
        "eessa", "eessatti", "eessaa", "yoom", "meeqa", "kam", "kamiyyuu",
        "moo", "maaliifis"
    }

    # Finite main verb predicates & copulas that typically conclude a statement
    FINITE_PREDICATES = {
        "jedhama", "jedhame", "jedhan", "jedhani", "jedheen", "jedhe", "jette",
        "dha", "miti", "ture", "turani", "turaan", "turte",
        "jira", "jiru", "jiraata", "jiraatti", "jiraate", "jiraatan",
        "ta'e", "ta'a", "ta'an", "ta'ani", "ta'aniiru", "ta'eera",
        "gaggeeffame", "gaggeeffama", "gaggeeffameera", "gaggeeffamaniiru",
        "kenne", "kennan", "kennite", "kennaniiru",
        "beeksise", "beeksifte", "beeksifteetti", "beeksifame", "beeksifaniiru",
        "ibse", "ibsaniiru", "ibsite", "ibsame",
        "argate", "argatan", "argatti", "argatte", "argataniiru",
        "danda'a", "dandeessu", "danda'an", "dandeetti",
        "mo'ate", "mo'atan", "mo'atte", "mo'ataniiru",
        "dhufe", "dhufan", "dhufte", "deeme", "deeman", "deemte",
        "qaba", "qabu", "qabdi", "qabna", "qabuuf"  # Note: qabuuf handled by subordinate check
    }

    # Sentence-initial discourse markers, pronouns, and time nouns in Afaan Oromoo
    SENTENCE_STARTERS = {
        # Pronouns & demonstratives
        "kun", "kunis", "kuni", "inni", "innis", "isheen", "isheens", "isaan",
        "isaanis", "nuyi", "nu'i", "sun", "sunis", "suni",
        # Discourse markers / conjunctions
        "garuu", "kanaaf", "kanaafuu", "kana malees", "haa ta'u malee", "haata'u malee",
        "haa ta'u malees", "akkasumas", "akkasumatti", "dabalataan", "waliigalatti",
        "booda", "erga", "yeroo", "osoo", "utuu", "yoo",
        # Time words & subjects
        "bara", "har'a", "guyyaa", "waggaa", "amma", "dura", "bariisaa",
        # Common subject initial terms
        "mootummaan", "barattoonni", "abboota", "poolisiin", "kantiibaan",
        "pirezidaantichi", "ministeerichi", "koreen", "waldaan", "hawaasni"
    }

    def __init__(self) -> None:
        pass

    def is_interrogative_clause(self, clause_text: str) -> bool:
        """Check if clause is a question based on interrogatives."""
        tokens = [t.lower() for t in re.findall(r"\b[a-zA-Z']+\b", clause_text)]
        if not tokens:
            return False
        # Check if last word is alternative question marker 'moo'
        if tokens[-1] == "moo":
            return True
        # Check presence of interrogative words
        for t in tokens:
            if t in self.INTERROGATIVE_WORDS:
                return True
        return False

    def insert_boundaries_in_unpunctuated_text(self, text: str) -> str:
        """
        Detect clause boundaries in unpunctuated running text based on
        morphosyntactic structures, predicate endings, and clause transitions.
        """
        words = text.split()
        if len(words) < 3:
            return text

        annotated_words: List[str] = []
        i = 0
        n = len(words)

        while i < n:
            word = words[i]
            annotated_words.append(word)

            if i < n - 1:
                next_word = words[i + 1]
                word_clean = word.lower().strip(".,;:?!'\"")
                next_clean = next_word.lower().strip(".,;:?!'\"")

                # Subordinate clauses ending with -f, -uuf, -iif or converb -ee do NOT break sentence
                is_subordinate = (
                    word_clean.endswith("uuf")
                    or word_clean.endswith("iif")
                    or word_clean.endswith("dhaaf")
                    or (word_clean.endswith("f") and len(word_clean) > 3 and not word_clean in {"fbc", "fmc"})
                    or (word_clean.endswith("ee") and len(word_clean) > 4)  # Converb form e.g. dhalatee, deemee
                )

                # Check if current word is a finite predicate
                is_predicate = (word_clean in self.FINITE_PREDICATES) and not is_subordinate

                # Multi-word predicate checks e.g. "ni jedhama", "jiraachaa turaan"
                if i >= 1:
                    prev_clean = words[i - 1].lower().strip(".,;:?!'\"")
                    if prev_clean == "ni" and word_clean in {"jedhama", "ta'a", "danda'ama", "beekama"}:
                        is_predicate = True
                    elif word_clean in {"turaan", "turani", "jira", "jiru"} and prev_clean.endswith("aa"):
                        is_predicate = True

                # Check if next word is a recognized sentence starter
                is_starter = (
                    next_clean in self.SENTENCE_STARTERS
                    or next_word[0].isupper()  # Already capitalized word / proper noun
                    or next_word.startswith("__PROTECTED_PH_")
                )

                # If word doesn't already have punctuation and we hit a boundary
                if is_predicate and is_starter and not word.endswith((".", "?", "!")):
                    # Check if the preceding clause is interrogative
                    current_clause = " ".join(annotated_words)
                    punct = "?" if self.is_interrogative_clause(current_clause) else "."
                    annotated_words[-1] = word + punct

            i += 1

        return " ".join(annotated_words)

    def normalize_sentence_spacing_and_punct(self, text: str) -> str:
        """
        Clean punctuation spacing: exactly one space after '.' or '?' when another word follows.
        Disallow arbitrary ! ; : as sentence-ending unless needed.
        """
        # Replace semicolons with period
        res = re.sub(r";\s*", ". ", text)

        # Normalize 4 or more repeated periods to standard ellipsis
        res = re.sub(r"\.{4,}", "...", res)

        # Ensure exactly one space after sentence period when followed by a word/bracket (never inside decimal numbers like 3.14 or 10.5%)
        res = re.sub(r"([a-zA-Z'’])\.([a-zA-Z\[])", r"\1. \2", res)
        # Ensure exactly one space after question mark if followed by a letter/bracket
        res = re.sub(r"\?([a-zA-Z\[])", r"? \1", res)

        # Normalize multiple spaces after punctuation while preserving single space
        res = re.sub(r"([.?])\s+", r"\1 ", res)

        return res


    def capitalize_sentences(self, text: str) -> str:
        """
        Capitalize the first letter of each sentence while preserving valid internal
        proper nouns, established names, and abbreviations.
        """
        if not text:
            return ""

        # Split into sentence chunks separated by (. ) or (? )
        chunks = re.split(r"([.?]\s+)", text)
        processed_chunks: List[str] = []

        for idx, chunk in enumerate(chunks):
            # Delimiters like ". " or "? " remain as-is
            if re.match(r"^[.?]\s+$", chunk):
                processed_chunks.append(chunk)
                continue

            stripped = chunk.strip()
            if not stripped:
                processed_chunks.append(chunk)
                continue

            # Capitalize the first alphabetic character if not already capitalized
            # e.g. "bara ttii ..." -> "Bara ttii ..."
            # Be careful with leading brackets e.g. "[Name] ..."
            first_match = re.search(r"[a-zA-Z]", chunk)
            if first_match:
                pos = first_match.start()
                char = chunk[pos]
                capitalized_chunk = chunk[:pos] + char.upper() + chunk[pos + 1 :]
                processed_chunks.append(capitalized_chunk)
            else:
                processed_chunks.append(chunk)

        result = "".join(processed_chunks).strip()
        return result

    def ensure_final_punctuation(self, text: str) -> str:
        """Ensure the complete text ends with valid sentence-ending punctuation (. or ?)."""
        text = text.strip()
        if not text:
            return ""

        if text.endswith((".", "?")):
            return text

        # Strip dangling punctuation like comma, dash, colon
        while text and text[-1] in (",", ";", ":", "-", "–", "—", " "):
            text = text[:-1].strip()

        if text.endswith((".", "?")):
            return text

        # Check if entire text or final clause is a question
        punct = "?" if self.is_interrogative_clause(text) else "."
        return text + punct

    def process(self, text: str) -> str:
        """
        Run complete sentence processing:
        1. Natural boundary detection
        2. Normalization of punctuation & spacing
        3. Sentence capitalization
        4. Final punctuation guarantee
        """
        if not text or not text.strip():
            return ""

        # Step 1: Detect and annotate boundaries in text
        annotated = self.insert_boundaries_in_unpunctuated_text(text)

        # Step 2: Normalize punctuation and spacing (exactly one space after sentence punctuation)
        normalized = self.normalize_sentence_spacing_and_punct(annotated)

        # Step 3: Ensure valid final punctuation
        with_final = self.ensure_final_punctuation(normalized)

        # Step 4: Capitalize each sentence
        capitalized = self.capitalize_sentences(with_final)

        # Step 5: Final spacing verification
        cleaned = re.sub(r" +", " ", capitalized).strip()

        return cleaned
