"""
Query complexity estimation — used to decide if a heavier model is warranted.
Fast heuristics only — no model calls.
"""

import re
from enum import Enum


class Complexity(str, Enum):
    LOW = "low"       # simple, one-shot query
    MEDIUM = "medium" # moderate context or multi-part
    HIGH = "high"     # long context, multi-step, documents


# Complexity → model tier bump (0 = no change, 1 = one tier up)
COMPLEXITY_TIER_BUMP = {
    Complexity.LOW: 0,
    Complexity.MEDIUM: 0,
    Complexity.HIGH: 1,
}


def estimate_complexity(query: str) -> tuple[Complexity, dict]:
    """
    Returns (complexity, signals) where signals is a dict of detected features.
    """
    signals = {}

    # Word count
    word_count = len(query.split())
    signals["word_count"] = word_count

    # Character count
    char_count = len(query)
    signals["char_count"] = char_count

    # Multi-step indicators
    multi_step = bool(re.search(
        r"\b(step by step|multiple|several|all of|each|compare|contrast|analyze)\b",
        query, re.IGNORECASE
    ))
    signals["multi_step"] = multi_step

    # Code blocks or technical content
    has_code = bool(re.search(r"```|def |function |class |import |SELECT |FROM ", query))
    signals["has_code"] = has_code

    # Document/article input (long text with newlines)
    has_document = char_count > 600 and query.count("\n") >= 3
    signals["has_document"] = has_document

    # Number of distinct questions
    question_count = query.count("?")
    signals["question_count"] = question_count

    # Score complexity
    if has_document or (word_count > 150 and multi_step) or question_count >= 3:
        complexity = Complexity.HIGH
    elif multi_step or word_count > 60 or has_code or question_count >= 2:
        complexity = Complexity.MEDIUM
    else:
        complexity = Complexity.LOW

    signals["complexity"] = complexity.value
    return complexity, signals