"""
CLI benchmark runner — measures latency, throughput, and quality per model.
Run: python -m benchmarks.runner
"""

import asyncio
import json
import time
from pathlib import Path

import ollama
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from .prompts import BENCHMARK_PROMPTS

console = Console()
MODELS = ["phi3:mini", "llama3.2:3b", "mistral:7b"]
RESULTS_FILE = Path("data/benchmark_results.json")


def run_single(model: str, prompt: str) -> dict:
    t0 = time.perf_counter()
    first_token_time = None
    tokens = 0
    response_text = ""

    try:
        for chunk in ollama.generate(model=model, prompt=prompt, stream=True):
            if first_token_time is None:
                first_token_time = (time.perf_counter() - t0) * 1000
            response_text += chunk.get("response", "")
            tokens += 1
            if chunk.get("done"):
                break
    except Exception as e:
        return {"error": str(e), "model": model}

    elapsed = time.perf_counter() - t0
    return {
        "model": model,
        "latency_ms": round(elapsed * 1000, 2),
        "ttft_ms": round(first_token_time or 0, 2),
        "tokens": tokens,
        "tps": round(tokens / elapsed, 2),
        "response_length": len(response_text),
    }


def run_benchmarks():
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_results = {}

    console.rule("[bold blue]AI Routing System — Benchmark Suite[/bold blue]")

    for category, prompts in BENCHMARK_PROMPTS.items():
        console.print(f"\n[bold yellow]Category: {category.upper()}[/bold yellow]")
        category_results = {m: [] for m in MODELS}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            for model in MODELS:
                task = progress.add_task(f"  {model}", total=len(prompts))
                # Warmup
                try:
                    ollama.generate(model=model, prompt="Hi", options={"num_predict": 1})
                except Exception:
                    pass

                for prompt in prompts:
                    result = run_single(model, prompt)
                    category_results[model].append(result)
                    progress.advance(task)

        # Print summary table for this category
        table = Table(title=f"Results — {category}", show_header=True)
        table.add_column("Model", style="cyan")
        table.add_column("Avg Latency (ms)", justify="right")
        table.add_column("Avg TPS", justify="right")
        table.add_column("Avg TTFT (ms)", justify="right")

        for model in MODELS:
            results = [r for r in category_results[model] if "error" not in r]
            if not results:
                table.add_row(model, "ERROR", "-", "-")
                continue
            avg_lat = sum(r["latency_ms"] for r in results) / len(results)
            avg_tps = sum(r["tps"] for r in results) / len(results)
            avg_ttft = sum(r["ttft_ms"] for r in results) / len(results)
            table.add_row(model, f"{avg_lat:.0f}", f"{avg_tps:.1f}", f"{avg_ttft:.0f}")

        console.print(table)
        all_results[category] = category_results

    # Save results
    RESULTS_FILE.write_text(json.dumps(all_results, indent=2))
    console.print(f"\n[green]Results saved to {RESULTS_FILE}[/green]")


if __name__ == "__main__":
    run_benchmarks()