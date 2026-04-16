"""
Async Ollama client wrapper with streaming and metrics capture.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import AsyncIterator

import ollama
from loguru import logger


@dataclass
class InferenceMetrics:
    model: str
    tokens_generated: int
    tokens_per_sec: float
    time_to_first_token_ms: float
    total_latency_ms: float


async def stream_generate(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
) -> AsyncIterator[tuple[str, InferenceMetrics | None]]:
    """
    Async generator yielding (token_chunk, metrics_or_None).
    metrics is only set on the final chunk.
    """
    t_start = time.perf_counter()
    first_token_time: float | None = None
    total_tokens = 0

    options = {"temperature": temperature, "num_predict": 1024}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async for chunk in await ollama.AsyncClient().chat(
            model=model,
            messages=messages,
            stream=True,
            options=options,
        ):
            token = chunk["message"]["content"]
            total_tokens += 1

            if first_token_time is None:
                first_token_time = (time.perf_counter() - t_start) * 1000

            if chunk.get("done", False):
                elapsed = time.perf_counter() - t_start
                tps = total_tokens / elapsed if elapsed > 0 else 0
                metrics = InferenceMetrics(
                    model=model,
                    tokens_generated=total_tokens,
                    tokens_per_sec=round(tps, 2),
                    time_to_first_token_ms=round(first_token_time or 0, 2),
                    total_latency_ms=round(elapsed * 1000, 2),
                )
                yield token, metrics
            else:
                yield token, None

    except Exception as e:
        logger.error(f"Ollama streaming error (model={model}): {e}")
        raise


async def generate_sync(
    model: str,
    prompt: str,
    system: str = "",
    temperature: float = 0.7,
) -> tuple[str, InferenceMetrics]:
    """Non-streaming generation for internal use (e.g. intent classification)."""
    t_start = time.perf_counter()
    response = ollama.generate(
        model=model,
        prompt=prompt,
        system=system,
        options={"temperature": temperature, "num_predict": 512},
    )
    elapsed = time.perf_counter() - t_start
    text = response["response"]
    tokens = response.get("eval_count", len(text.split()))
    tps = tokens / elapsed if elapsed > 0 else 0

    metrics = InferenceMetrics(
        model=model,
        tokens_generated=tokens,
        tokens_per_sec=round(tps, 2),
        time_to_first_token_ms=0.0,
        total_latency_ms=round(elapsed * 1000, 2),
    )
    return text, metrics
