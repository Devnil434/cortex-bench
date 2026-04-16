"""
Custom PII pattern recognizers for Indian and global identifiers.
Uses Presidio PatternRecognizer — no torch, no transformers.
"""

from presidio_analyzer import PatternRecognizer, Pattern


def get_indian_recognizers() -> list[PatternRecognizer]:
    """Return custom recognizers for Indian PII types."""

    # Aadhaar: 12-digit number, often spaced as 4-4-4
    aadhaar = PatternRecognizer(
        supported_entity="IN_AADHAAR",
        patterns=[
            Pattern(
                name="aadhaar_spaced",
                regex=r"\b\d{4}\s\d{4}\s\d{4}\b",
                score=0.9,
            ),
            Pattern(
                name="aadhaar_plain",
                regex=r"\b[2-9]\d{11}\b",
                score=0.75,
            ),
        ],
        context=["aadhaar", "uid", "unique identification"],
    )

    # PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)
    pan = PatternRecognizer(
        supported_entity="IN_PAN",
        patterns=[
            Pattern(
                name="pan_card",
                regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
                score=0.95,
            ),
        ],
        context=["pan", "permanent account number", "income tax"],
    )

    # UPI ID: user@bank format
    upi = PatternRecognizer(
        supported_entity="IN_UPI",
        patterns=[
            Pattern(
                name="upi_id",
                regex=r"\b[\w.\-]{3,}@[a-zA-Z]{3,}\b",
                score=0.85,
            ),
        ],
        context=["upi", "gpay", "phonepe", "paytm", "payment"],
    )

    # IFSC code: 4 letters + 0 + 6 chars
    ifsc = PatternRecognizer(
        supported_entity="IN_IFSC",
        patterns=[
            Pattern(
                name="ifsc",
                regex=r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
                score=0.9,
            ),
        ],
        context=["ifsc", "bank", "transfer", "neft", "rtgs"],
    )

    # Indian mobile: 10-digit starting with 6-9
    mobile = PatternRecognizer(
        supported_entity="IN_PHONE",
        patterns=[
            Pattern(
                name="indian_mobile",
                regex=r"\b[6-9]\d{9}\b",
                score=0.8,
            ),
            Pattern(
                name="indian_mobile_with_code",
                regex=r"\+91[-\s]?[6-9]\d{9}\b",
                score=0.95,
            ),
        ],
    )

    return [aadhaar, pan, upi, ifsc, mobile]


def get_global_extra_recognizers() -> list[PatternRecognizer]:
    """Additional global patterns not in Presidio defaults."""

    # Generic account number pattern
    account = PatternRecognizer(
        supported_entity="BANK_ACCOUNT",
        patterns=[
            Pattern(
                name="account_number",
                regex=r"\b\d{9,18}\b",
                score=0.5,
            ),
        ],
        context=["account", "acc no", "acct", "account number"],
    )

    return [account]