"""
Intent Classifier — two-stage pipeline:
  Stage 1: Fast keyword + heuristic matching (no LLM call)
  Stage 2: Ollama zero-shot classification (fallback for ambiguous)
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger
from rapidfuzz import fuzz


class Intent(str, Enum):
    CODING = "coding"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    FACTUAL_QA = "factual_qa"
    CREATIVE = "creative"
    SENSITIVE = "sensitive"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    intent: Intent
    confidence: float           # 0.0 to 1.0
    method: str                 # "keyword" | "heuristic" | "llm" | "privacy_override"
    preferred_model: str        # suggested model name
    reasoning: Optional[str]    # brief explanation
    latency_ms: float


# Keyword maps per intent — case-insensitive substring match
INTENT_KEYWORDS: dict[Intent, list[str]] = {
    Intent.CODING: [
        "write code", "write a function", "implement", "debug", "fix the bug",
        "python script", "javascript", "typescript", "java ", "c++", "golang",
        "sql query", "regex", "algorithm", "data structure", "class ",
        "unit test", "api endpoint", "dockerfile", "bash script", "shell",
        "error:", "traceback", "syntaxerror", "valueerror", "null pointer",
        "compile", "build", "deploy", "git ", "github",
    ],
    Intent.REASONING: [
        "why ", "explain why", "what causes", "how does", "prove that",
        "compare and contrast", "analyze", "evaluate", "what would happen",
        "logical", "step by step", "think through", "solve this",
        "math problem", "calculate", "probability", "statistics",
        "hypothesis", "argument", "evidence", "because",
    ],
    Intent.SUMMARIZATION: [
        "summarize", "summary", "tldr", "tl;dr", "in brief",
        "key points", "main ideas", "condense", "shorten",
        "what are the highlights", "give me an overview",
        "abstract", "digest",
    ],
    Intent.FACTUAL_QA: [
        "what is", "what are", "who is", "when did", "where is",
        "define ", "definition of", "tell me about", "what does",
        "how many", "list of", "examples of", "name the",
    ],
    Intent.CREATIVE: [
        "write a story", "write a poem", "brainstorm", "generate ideas",
        "imagine ", "creative ", "fictional", "invent", "design a",
        "suggest ", "recommend ", "come up with", "make up",
        "roleplay", "pretend", "fantasy", "narrative",
    ],
}

# Model routing table
MODEL_ROUTING: dict[Intent, str] = {
    Intent.CODING: "phi3:mini",
    Intent.REASONING: "mistral:7b",
    Intent.SUMMARIZATION: "mistral:7b",
    Intent.FACTUAL_QA: "llama3.2:3b",
    Intent.CREATIVE: "llama3.2:3b",
    Intent.SENSITIVE: "phi3:mini",   # smallest model for sensitive — least data retained
    Intent.UNKNOWN: "llama3.2:3b",
}