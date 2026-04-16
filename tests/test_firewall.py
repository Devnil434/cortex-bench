"""Tests for Privacy Firewall — no torch, no trf model needed."""
import pytest
from backend.privacy.firewall import PrivacyFirewall


@pytest.fixture(scope="module")
def firewall():
    # Uses en_core_web_lg — safe on Python 3.14
    return PrivacyFirewall(model_name="en_core_web_lg")


def test_email_detection(firewall):
    result = firewall.scan("Contact me at john.doe@gmail.com for details.")
    types = {e["type"] for e in result.entities_found}
    assert "EMAIL_ADDRESS" in types
    assert "<EMAIL_ADDRESS_1>" in result.masked_query
    assert "john.doe@gmail.com" not in result.masked_query


def test_indian_aadhaar(firewall):
    result = firewall.scan("My Aadhaar is 2345 6789 0123")
    types = {e["type"] for e in result.entities_found}
    assert "IN_AADHAAR" in types
    assert result.is_sensitive is True
    assert result.sensitivity_score == 1.0


def test_indian_pan(firewall):
    result = firewall.scan("My PAN card is ABCDE1234F")
    types = {e["type"] for e in result.entities_found}
    assert "IN_PAN" in types
    assert result.is_sensitive is True


def test_clean_query(firewall):
    result = firewall.scan("What is the capital of France?")
    assert result.pii_count == 0
    assert result.is_sensitive is False
    assert result.masked_query == "What is the capital of France?"


def test_reversible_masking(firewall):
    query = "Send invoice to alice@example.com"
    result = firewall.scan(query)
    restored = firewall.restore(result.masked_query, result.entity_map)
    assert restored == query


def test_credit_card_always_sensitive(firewall):
    result = firewall.scan("Pay with card 4111 1111 1111 1111")
    assert result.is_sensitive is True


def test_multiple_pii(firewall):
    query = "I am John Smith, email: j.smith@corp.com, phone: 9876543210"
    result = firewall.scan(query)
    assert result.pii_count >= 2
    assert result.is_sensitive is True