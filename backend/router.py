"""
Smart Router — selects the optimal Ollama model for each query.
Considers: intent, complexity, system memory, model performance history.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import psutil
from loguru import logger

from .intent_classifier import Intent, IntentResult
from .models.model_registry import MODEL_REGISTRY, get_capability_score, ModelProfile
from .models.complexity import Complexity, estimate_complexity


# Minimum free RAM (in GB) required to load each model
MEMORY_REQUIREMENTS = {
    "phi3:mini": 3.0,
    "llama3.2:3b": 3.5,
    "mistral:7b": 5.5,
}

# Model priority order (lightest to heaviest)
MODEL_TIERS = ["phi3:mini", "llama3.2:3b", "mistral:7b"]


@dataclass
class RoutingDecision:
    selected_model: str
    fallback_model: str
    intent: str
    complexity: str
    capability_score: float
    memory_ok: bool
    reasoning: str
    latency_ms: float
    scores: dict[str, float] = field(default_factory=dict)


class SmartRouter:
    """
    Multi-criteria model selection engine.
    Scoring formula:
      final_score = capability_score * 0.6
                  + speed_score * 0.25
                  + memory_score * 0.15
    """

    def __init__(self) -> None:
        # Runtime latency history: model → list of observed tok/s
        self._latency_history: dict[str, list[float]] = {m: [] for m in MODEL_REGISTRY}

    def route(self, intent_result: IntentResult, query: str) -> RoutingDecision:
        """
        Given intent + query, select the best model.
        Returns RoutingDecision with primary + fallback.
        """
        t0 = time.perf_counter()
        intent = intent_result.intent
        complexity, complexity_signals = estimate_complexity(query)
        free_gb = self._get_free_memory_gb()

        # Compute score for each model
        model_scores: dict[str, float] = {}
        for model_name, profile in MODEL_REGISTRY.items():
            cap = get_capability_score(model_name, intent.value)
            spd = self._speed_score(profile)
            mem = self._memory_score(model_name, free_gb)
            total = cap * 0.60 + spd * 0.25 + mem * 0.15
            model_scores[model_name] = round(total, 4)

        # High complexity: boost heavier model scores
        if complexity == Complexity.HIGH:
            model_scores["mistral:7b"] = min(1.0, model_scores["mistral:7b"] + 0.15)
            logger.debug("Complexity=HIGH: boosting mistral:7b score")

        # Reasoning intent: prefer mistral
        if intent == Intent.REASONING:
            model_scores["mistral:7b"] = min(1.0, model_scores["mistral:7b"] + 0.3)
            logger.debug("Intent=REASONING: boosting mistral:7b score")

        # Sensitive queries: force smallest model
        if intent == Intent.SENSITIVE:
            selected = "phi3:mini"
            fallback = "llama3.2:3b"
            reasoning = "Sensitive query — routed to smallest model to minimize data exposure"
        else:
            # Filter out models that don't have enough memory
            viable = {
                m: s for m, s in model_scores.items()
                if self._has_memory(m, free_gb)
            }

            if not viable:
                # Emergency fallback — always run phi3:mini
                logger.warning("No model fits in available memory — forcing phi3:mini")
                selected = "phi3:mini"
            else:
                selected = max(viable, key=lambda m: viable[m])

            # Fallback = next tier down from selected
            fallback = self._get_fallback(selected)
            reasoning = self._build_reasoning(
                selected, intent, complexity, free_gb, model_scores
            )

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        decision = RoutingDecision(
            selected_model=selected,
            fallback_model=fallback,
            intent=intent.value,
            complexity=complexity.value,
            capability_score=model_scores.get(selected, 0.0),
            memory_ok=self._has_memory(selected, free_gb),
            reasoning=reasoning,
            latency_ms=elapsed_ms,
            scores=model_scores,
        )

        logger.info(
            f"Routed: intent={intent.value} complexity={complexity.value} "
            f"model={selected} (score={decision.capability_score:.3f}) "
            f"free_mem={free_gb:.1f}GB"
        )
        return decision

    def record_inference(self, model: str, tokens_per_sec: float) -> None:
        """Update runtime latency history for adaptive scoring."""
        history = self._latency_history[model]
        history.append(tokens_per_sec)
        if len(history) > 20:
            history.pop(0)  # keep rolling window of 20

    def _speed_score(self, profile: ModelProfile) -> float:
        """Normalize speed: phi3 fastest = 1.0, mistral slowest = 0.0."""
        speeds = [p.avg_tokens_per_sec for p in MODEL_REGISTRY.values()]
        min_s, max_s = min(speeds), max(speeds)
        if max_s == min_s:
            return 0.5
        return (profile.avg_tokens_per_sec - min_s) / (max_s - min_s)

    def _memory_score(self, model_name: str, free_gb: float) -> float:
        """Score based on how much headroom remains after loading model."""
        required = MEMORY_REQUIREMENTS.get(model_name, 4.0)
        headroom = free_gb - required
        if headroom <= 0:
            return 0.0
        return min(1.0, headroom / 4.0)   # 4GB headroom = perfect score

    def _has_memory(self, model_name: str, free_gb: float) -> bool:
        required = MEMORY_REQUIREMENTS.get(model_name, 4.0)
        return free_gb >= required

    def _get_free_memory_gb(self) -> float:
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 3)

    def _get_fallback(self, selected: str) -> str:
        idx = MODEL_TIERS.index(selected) if selected in MODEL_TIERS else 1
        return MODEL_TIERS[max(0, idx - 1)]   # one tier lighter

    def _build_reasoning(
        self,
        model: str,
        intent: Intent,
        complexity: Complexity,
        free_gb: float,
        scores: dict[str, float],
    ) -> str:
        lines = [
            f"Selected {model} for intent={intent.value}, complexity={complexity.value}.",
            f"Available memory: {free_gb:.1f}GB.",
            f"Model scores: " + ", ".join(f"{m}={s:.3f}" for m, s in scores.items()),
        ]
        return " | ".join(lines)