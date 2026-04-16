"""
Privacy Firewall — main entry point for PII detection and masking.
Uses Presidio Analyzer + spaCy en_core_web_lg (NOT en_core_web_trf).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import spacy
from loguru import logger
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine

from .anonymizer import PrivacyAnonymizer, AnonymizationResult
from .patterns import get_indian_recognizers, get_global_extra_recognizers


# Sensitivity threshold — if combined score exceeds this, mark query sensitive
SENSITIVITY_THRESHOLD = 0.6

# PII types that always trigger SENSITIVE routing regardless of score
ALWAYS_SENSITIVE_TYPES = {
    "IN_AADHAAR", "IN_PAN", "CREDIT_CARD", "US_SSN",
    "MEDICAL_LICENSE", "IN_UPI", "BANK_ACCOUNT",
}


@dataclass
class FirewallResult:
    original_query: str
    masked_query: str
    entity_map: dict[str, str]
    entities_found: list[dict]      # [{type, score, start, end}]
    is_sensitive: bool
    sensitivity_score: float
    processing_time_ms: float
    pii_count: int


class PrivacyFirewall:
    """
    Multi-layer PII detection pipeline:
      1. Fast regex pre-scan (custom patterns)
      2. spaCy NER (en_core_web_lg — no torch)
      3. Presidio full analysis (coordinates both)
      4. Anonymizer (reversible masking)
    """

    # Entities Presidio should detect
    ENTITIES = [
        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
        "US_SSN", "IP_ADDRESS", "URL", "DATE_TIME",
        "NRP",  # Nationality, Religious, Political group
        "MEDICAL_LICENSE", "IBAN_CODE",
        # Custom Indian
        "IN_AADHAAR", "IN_PAN", "IN_UPI", "IN_IFSC", "IN_PHONE",
        # Extra
        "BANK_ACCOUNT",
    ]

    def __init__(self, model_name: str = "en_core_web_lg") -> None:
        logger.info(f"Loading spaCy model: {model_name}")
        try:
            spacy.load(model_name)  # verify it loads before passing to Presidio
        except OSError as e:
            raise RuntimeError(
                f"spaCy model '{model_name}' not found. "
                f"Run: python -m spacy download {model_name}\n"
                f"Do NOT use en_core_web_trf on Python 3.14."
            ) from e

        # Build NLP engine pointing at en_core_web_lg
        nlp_engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": model_name}])
        nlp_engine.load()

        # Build registry with default + custom recognizers
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)
        for recognizer in get_indian_recognizers() + get_global_extra_recognizers():
            registry.add_recognizer(recognizer)

        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            registry=registry,
        )
        self.anonymizer = PrivacyAnonymizer()
        logger.info("PrivacyFirewall initialized successfully.")

    def scan(self, query: str) -> FirewallResult:
        """
        Run the full PII detection and masking pipeline.
        Returns FirewallResult with masked query and metadata.
        """
        t0 = time.perf_counter()

        # Run Presidio analysis
        results = self.analyzer.analyze(
            text=query,
            language="en",
            entities=self.ENTITIES,
            score_threshold=0.4,
        )

        # Anonymize
        anon: AnonymizationResult = self.anonymizer.anonymize(query, results)

        # Build entity list
        entities_found = [
            {
                "type": r.entity_type,
                "score": round(r.score, 3),
                "start": r.start,
                "end": r.end,
                "value": query[r.start:r.end],
            }
            for r in results
        ]

        # Sensitivity scoring
        is_sensitive, sensitivity_score = self._score_sensitivity(results)

        elapsed_ms = (time.perf_counter() - t0) * 1000

        if entities_found:
            logger.info(
                f"Privacy scan: found {len(entities_found)} entities "
                f"[{', '.join(e['type'] for e in entities_found)}] "
                f"sensitive={is_sensitive} ({elapsed_ms:.1f}ms)"
            )

        return FirewallResult(
            original_query=query,
            masked_query=anon.masked_text,
            entity_map=anon.entity_map,
            entities_found=entities_found,
            is_sensitive=is_sensitive,
            sensitivity_score=sensitivity_score,
            processing_time_ms=round(elapsed_ms, 2),
            pii_count=len(results),
        )

    def restore(self, masked_response: str, entity_map: dict[str, str]) -> str:
        """Restore original values in LLM response (if needed)."""
        return self.anonymizer.deanonymize(masked_response, entity_map)

    def _score_sensitivity(self, results) -> tuple[bool, float]:
        if not results:
            return False, 0.0

        # Always-sensitive types override scoring
        found_types = {r.entity_type for r in results}
        if found_types & ALWAYS_SENSITIVE_TYPES:
            return True, 1.0

        # Weighted average of detection scores
        score = sum(r.score for r in results) / len(results)
        is_sensitive = score >= SENSITIVITY_THRESHOLD or len(results) >= 2
        return is_sensitive, round(score, 3)