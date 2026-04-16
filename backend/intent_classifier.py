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

class KeywordClassifier:
    """
    Stage 1: Fast classification using keyword matching.
    Uses rapidfuzz partial ratio for typo tolerance.
    Zero LLM calls — sub-millisecond.
    """

    CONFIDENCE_DIRECT = 0.85    # exact substring found
    CONFIDENCE_FUZZY = 0.65     # fuzzy match above threshold
    FUZZY_THRESHOLD = 80        # rapidfuzz score 0-100

    def classify(self, query: str) -> Optional[tuple[Intent, float]]:
        """
        Returns (intent, confidence) or None if too ambiguous.
        """
        q_lower = query.lower()
        scores: dict[Intent, float] = {}

        for intent, keywords in INTENT_KEYWORDS.items():
            best_score = 0.0
            for kw in keywords:
                # Direct substring match (fastest)
                if kw in q_lower:
                    best_score = max(best_score, self.CONFIDENCE_DIRECT)
                    break
                # Fuzzy match for typos and variations
                ratio = fuzz.partial_ratio(kw, q_lower) / 100.0
                if ratio >= self.FUZZY_THRESHOLD / 100.0:
                    best_score = max(best_score, ratio * self.CONFIDENCE_FUZZY)

            if best_score > 0:
                scores[intent] = best_score

        if not scores:
            return None

        best_intent = max(scores, key=lambda k: scores[k])
        best_score = scores[best_intent]

        # Only return if score is unambiguous (no close second)
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and (sorted_scores[0] - sorted_scores[1]) < 0.1:
            return None  # ambiguous — defer to LLM

        return best_intent, best_score

    def detect_code_markers(self, query: str) -> bool:
        """Detect code blocks or error tracebacks."""
        patterns = [
            r"```[\s\S]*```",       # code block
            r"def \w+\(",           # Python function
            r"function \w+\(",      # JS function
            r"class \w+",           # class definition
            r"import \w+",          # import statement
            r"Traceback \(most",    # Python traceback
            r"Error: ",             # generic error
            r"line \d+",            # error line reference
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in patterns)

    def detect_length_hint(self, query: str) -> Optional[Intent]:
        """Long multi-paragraph text usually needs summarization."""
        if len(query) > 800 and "\n" in query:
            return Intent.SUMMARIZATION
        return None
    
class OllamaIntentClassifier:
    """
    Stage 2: Zero-shot classification via local Ollama.
    Called only when keyword classifier is ambiguous.
    Uses phi3:mini (fastest model) for meta-classification.
    """

    SYSTEM_PROMPT = """You are a query intent classifier. 
Classify the user query into EXACTLY ONE of these categories:
coding, reasoning, summarization, factual_qa, creative, unknown

Rules:
- coding: any request involving writing, fixing, explaining code
- reasoning: logic puzzles, math, multi-step analysis, comparisons
- summarization: condense, summarize, extract key points from text
- factual_qa: simple factual questions, definitions, lookups
- creative: stories, poems, brainstorming, imaginative tasks
- unknown: cannot determine clearly

Respond with ONLY the category name, nothing else. No explanation."""

    def __init__(self, model: str = "phi3:mini") -> None:
        self.model = model

    def classify(self, query: str) -> tuple[Intent, float]:
        """Call Ollama to classify intent. Returns (intent, confidence)."""
        import ollama

        # Truncate long queries for faster classification
        truncated = query[:500] if len(query) > 500 else query

        try:
            response = ollama.generate(
                model=self.model,
                prompt=f"Query: {truncated}",
                system=self.SYSTEM_PROMPT,
                options={"temperature": 0.0, "num_predict": 10},
            )
            raw = response["response"].strip().lower()

            # Parse the response
            for intent in Intent:
                if intent.value in raw:
                    return intent, 0.75
            return Intent.UNKNOWN, 0.3

        except Exception as e:
            logger.warning(f"Ollama intent classification failed: {e}")
            return Intent.FACTUAL_QA, 0.3   # safe default
        
# -------------------Main Classifier Orchestrator----------------------------------

class IntentClassifier:
    """
    Orchestrates the two-stage classification pipeline.
    Stage 1 (keyword) → fast, always tried first.
    Stage 2 (LLM) → only called when stage 1 is ambiguous.
    """

    def __init__(self) -> None:
        self.keyword_clf = KeywordClassifier()
        self.llm_clf = OllamaIntentClassifier(model="phi3:mini")

    def classify(
        self,
        query: str,
        is_sensitive: bool = False,
    ) -> IntentResult:
        """
        Classify query intent and return routing recommendation.
        If privacy firewall flagged the query as sensitive, override intent.
        """
        t0 = time.perf_counter()

        # Privacy override — always comes first
        if is_sensitive:
            return IntentResult(
                intent=Intent.SENSITIVE,
                confidence=1.0,
                method="privacy_override",
                preferred_model=MODEL_ROUTING[Intent.SENSITIVE],
                reasoning="Privacy firewall detected PII — routing to minimal model",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

        # Stage 1: Heuristic checks
        if self.keyword_clf.detect_code_markers(query):
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return IntentResult(
                intent=Intent.CODING,
                confidence=0.9,
                method="heuristic",
                preferred_model=MODEL_ROUTING[Intent.CODING],
                reasoning="Code markers detected in query",
                latency_ms=elapsed,
            )

        length_hint = self.keyword_clf.detect_length_hint(query)
        if length_hint:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return IntentResult(
                intent=length_hint,
                confidence=0.8,
                method="heuristic",
                preferred_model=MODEL_ROUTING[length_hint],
                reasoning="Long text detected — likely summarization task",
                latency_ms=elapsed,
            )

        # Stage 1: Keyword matching
        keyword_result = self.keyword_clf.classify(query)
        if keyword_result is not None:
            intent, confidence = keyword_result
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return IntentResult(
                intent=intent,
                confidence=confidence,
                method="keyword",
                preferred_model=MODEL_ROUTING[intent],
                reasoning=f"Keyword match for '{intent.value}'",
                latency_ms=elapsed,
            )

        # Stage 2: LLM fallback
        logger.debug("Keyword classifier ambiguous — falling back to LLM classification")
        intent, confidence = self.llm_clf.classify(query)
        elapsed = round((time.perf_counter() - t0) * 1000, 2)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            method="llm",
            preferred_model=MODEL_ROUTING[intent],
            reasoning="LLM zero-shot classification",
            latency_ms=elapsed,
        )