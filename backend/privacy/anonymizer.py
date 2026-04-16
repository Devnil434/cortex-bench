"""
Wrapper around Presidio Anonymizer for consistent placeholder generation.
"""

from dataclasses import dataclass, field
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


@dataclass
class AnonymizationResult:
    masked_text: str
    entity_map: dict[str, str]  # placeholder → original value
    entity_types_found: list[str]


class PrivacyAnonymizer:
    """
    Replaces PII entities with reversible indexed placeholders.
    Example: "John" → "<PERSON_1>", email → "<EMAIL_ADDRESS_1>"
    """

    def __init__(self) -> None:
        self.engine = AnonymizerEngine()
        self._counters: dict[str, int] = {}

    def _make_placeholder(self, entity_type: str) -> str:
        self._counters[entity_type] = self._counters.get(entity_type, 0) + 1
        return f"<{entity_type}_{self._counters[entity_type]}>"

    def anonymize(
        self,
        text: str,
        analyzer_results: list,
    ) -> AnonymizationResult:
        """
        Anonymize text using analyzer results.
        Returns masked text and a map from placeholder → original.
        """
        self._counters.clear()
        entity_map: dict[str, str] = {}
        entity_types: list[str] = []

        # Build operator config with custom placeholders
        operators: dict[str, OperatorConfig] = {}
        for result in analyzer_results:
            placeholder = self._make_placeholder(result.entity_type)
            original = text[result.start:result.end]
            entity_map[placeholder] = original
            if result.entity_type not in entity_types:
                entity_types.append(result.entity_type)
            operators[result.entity_type] = OperatorConfig(
                "replace",
                {"new_value": placeholder},
            )

        anonymized = self.engine.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=operators,
        )

        return AnonymizationResult(
            masked_text=anonymized.text,
            entity_map=entity_map,
            entity_types_found=entity_types,
        )

    def deanonymize(self, masked_text: str, entity_map: dict[str, str]) -> str:
        """Restore original values from placeholder map."""
        result = masked_text
        # Sort by placeholder index descending to avoid substring conflicts
        for placeholder, original in sorted(entity_map.items(), reverse=True):
            result = result.replace(placeholder, original)
        return result