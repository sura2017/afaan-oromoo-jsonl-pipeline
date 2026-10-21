"""Configuration management for the dataset pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class PipelineConfig:
    """Holds configuration settings for the entire pipeline."""

    # Paths
    config_dir: Path = field(default_factory=lambda: Path("config"))
    boilerplate_file: Path = field(default_factory=lambda: Path("config/boilerplate_phrases.json"))
    broadcast_file: Path = field(default_factory=lambda: Path("config/broadcast_terms.json"))
    categories_file: Path = field(default_factory=lambda: Path("config/categories.json"))
    spelling_file: Path = field(default_factory=lambda: Path("config/spelling_corrections.json"))

    # Processing options
    batch_size: int = 1000
    progress_interval: int = 5000
    log_level: str = "INFO"
    resume: bool = False
    error_log_path: Optional[Path] = None

    # Loaded configurations
    boilerplate_phrases: List[str] = field(default_factory=list)
    broadcast_terms: List[str] = field(default_factory=list)
    controlled_vocabulary: List[str] = field(default_factory=list)
    category_normalization: Dict[str, str] = field(default_factory=dict)
    category_keywords: Dict[str, List[str]] = field(default_factory=dict)
    proper_nouns: Dict[str, str] = field(default_factory=dict)
    unambiguous_spelling: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Load JSON configuration files if present."""
        self.load_configs()

    def load_configs(self) -> None:
        """Load configuration files from disk."""
        # 1. Boilerplate phrases
        if self.boilerplate_file.exists():
            with open(self.boilerplate_file, "r", encoding="utf-8") as f:
                self.boilerplate_phrases = json.load(f)

        # 2. Broadcast terms
        if self.broadcast_file.exists():
            with open(self.broadcast_file, "r", encoding="utf-8") as f:
                self.broadcast_terms = json.load(f)

        # 3. Categories
        if self.categories_file.exists():
            with open(self.categories_file, "r", encoding="utf-8") as f:
                cat_data = json.load(f)
                self.controlled_vocabulary = cat_data.get("controlled_vocabulary", [])
                self.category_normalization = cat_data.get("normalization_map", {})
                self.category_keywords = cat_data.get("category_keywords", {})

        # 4. Spelling & proper nouns
        if self.spelling_file.exists():
            with open(self.spelling_file, "r", encoding="utf-8") as f:
                sp_data = json.load(f)
                self.proper_nouns = sp_data.get("proper_nouns", {})
                self.unambiguous_spelling = sp_data.get("unambiguous_replacements", {})

    @property
    def allowed_categories_set(self) -> Set[str]:
        """Return a set of allowed categories for O(1) lookup."""
        return set(self.controlled_vocabulary)
