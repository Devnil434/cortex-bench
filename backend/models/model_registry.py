"""
Model Registry — capability scores and metadata for each Ollama model.
Scores are 0.0 to 1.0 per capability dimension.
"""

from dataclasses import dataclass


@dataclass
class ModelProfile:
    name: str           # Ollama model tag
    display_name: str
    size_gb: float      # approximate VRAM/RAM footprint
    # Capability scores per intent (higher = better fit)
    coding_score: float
    reasoning_score: float
    summarization_score: float
    factual_qa_score: float
    creative_score: float
    # Performance characteristics
    avg_tokens_per_sec: float   # baseline on CPU (updated at runtime)
    max_context_tokens: int


MODEL_REGISTRY: dict[str, ModelProfile] = {
    "phi3:mini": ModelProfile(
        name="phi3:mini",
        display_name="Phi-3 Mini (3.8B)",
        size_gb=2.3,
        coding_score=0.90,
        reasoning_score=0.65,
        summarization_score=0.60,
        factual_qa_score=0.75,
        creative_score=0.60,
        avg_tokens_per_sec=35.0,
        max_context_tokens=4096,
    ),
    "llama3.2:3b": ModelProfile(
        name="llama3.2:3b",
        display_name="Llama 3.2 (3B)",
        size_gb=2.0,
        coding_score=0.72,
        reasoning_score=0.75,
        summarization_score=0.78,
        factual_qa_score=0.85,
        creative_score=0.82,
        avg_tokens_per_sec=28.0,
        max_context_tokens=8192,
    ),
    "mistral:7b": ModelProfile(
        name="mistral:7b",
        display_name="Mistral 7B",
        size_gb=4.1,
        coding_score=0.78,
        reasoning_score=0.92,
        summarization_score=0.95,
        factual_qa_score=0.88,
        creative_score=0.85,
        avg_tokens_per_sec=18.0,
        max_context_tokens=8192,
    ),
}


def get_profile(model_name: str) -> ModelProfile:
    if model_name not in MODEL_REGISTRY:
        raise KeyError(f"Model '{model_name}' not in registry. Available: {list(MODEL_REGISTRY)}")
    return MODEL_REGISTRY[model_name]


def get_capability_score(model_name: str, intent: str) -> float:
    profile = get_profile(model_name)
    score_map = {
        "coding": profile.coding_score,
        "reasoning": profile.reasoning_score,
        "summarization": profile.summarization_score,
        "factual_qa": profile.factual_qa_score,
        "creative": profile.creative_score,
        "sensitive": 1.0 - profile.size_gb / 5.0,  # smaller = safer for sensitive
        "unknown": 0.5,
    }
    return score_map.get(intent, 0.5)