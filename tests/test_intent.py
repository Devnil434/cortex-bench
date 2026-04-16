import pytest
from backend.intent_classifier import IntentClassifier, Intent


@pytest.fixture(scope="module")
def clf():
    return IntentClassifier()


@pytest.mark.parametrize("query,expected_intent", [
    ("Write a Python function to sort a list", Intent.CODING),
    ("Fix this bug: TypeError: list index out of range", Intent.CODING),
    ("def fibonacci(n): pass — complete this", Intent.CODING),
    ("Summarize this article for me", Intent.SUMMARIZATION),
    ("What is the capital of France?", Intent.FACTUAL_QA),
    ("Write a poem about the moon", Intent.CREATIVE),
    ("Step by step, prove that sqrt(2) is irrational", Intent.REASONING),
    ("Compare and contrast REST vs GraphQL", Intent.REASONING),
])
def test_intent_classification(clf, query, expected_intent):
    result = clf.classify(query)
    assert result.intent == expected_intent, (
        f"Expected {expected_intent}, got {result.intent} for: '{query}'"
    )


def test_sensitive_override(clf):
    result = clf.classify("What is 2+2?", is_sensitive=True)
    assert result.intent == Intent.SENSITIVE
    assert result.method == "privacy_override"
    assert result.confidence == 1.0


def test_code_marker_detection(clf):
    query = "```python\ndef hello():\n    pass\n```\nFix this function"
    result = clf.classify(query)
    assert result.intent == Intent.CODING
    assert result.method == "heuristic"


def test_routing_model_assigned(clf):
    result = clf.classify("Write a quicksort in C++")
    assert result.preferred_model == "phi3:mini"   # coding → phi3


def test_latency_fast(clf):
    import time
    t0 = time.perf_counter()
    clf.classify("What is Python?")
    elapsed = (time.perf_counter() - t0) * 1000
    assert elapsed < 100, f"Keyword classification took {elapsed:.1f}ms — too slow"