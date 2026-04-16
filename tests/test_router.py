import pytest
from unittest.mock import patch
from backend.router import SmartRouter
from backend.intent_classifier import Intent, IntentResult


def make_intent(intent: Intent, model: str = "phi3:mini") -> IntentResult:
    return IntentResult(
        intent=intent, confidence=0.9, method="keyword",
        preferred_model=model, reasoning="test", latency_ms=1.0,
    )


@pytest.fixture
def router():
    return SmartRouter()


def test_sensitive_always_phi3(router):
    result = router.route(make_intent(Intent.SENSITIVE), "my aadhaar is 1234")
    assert result.selected_model == "phi3:mini"


def test_reasoning_prefers_mistral(router):
    with patch("backend.router.SmartRouter._get_free_memory_gb", return_value=8.0):
        result = router.route(make_intent(Intent.REASONING), "Prove that P != NP")
    assert result.selected_model == "mistral:7b"


def test_coding_prefers_phi3(router):
    with patch("backend.router.SmartRouter._get_free_memory_gb", return_value=8.0):
        result = router.route(make_intent(Intent.CODING), "Write a bubble sort")
    assert result.selected_model == "phi3:mini"


def test_low_memory_forces_phi3(router):
    with patch("backend.router.SmartRouter._get_free_memory_gb", return_value=2.5):
        result = router.route(make_intent(Intent.REASONING), "Complex math problem")
    assert result.selected_model == "phi3:mini"


def test_routing_decision_has_scores(router):
    with patch("backend.router.SmartRouter._get_free_memory_gb", return_value=8.0):
        result = router.route(make_intent(Intent.FACTUAL_QA), "What is Python?")
    assert len(result.scores) == 3
    assert all(0.0 <= s <= 1.0 for s in result.scores.values())