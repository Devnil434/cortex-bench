"""
health_check.py — Verifies every component of the AI Routing System.
Run: python health_check.py
"""

import sys
import importlib
import httpx
from rich.console import Console
from rich.table import Table

console = Console()
OLLAMA_BASE = "http://localhost:11434"
REQUIRED_MODELS = ["phi3:mini", "llama3.2:3b", "mistral:7b"]
REQUIRED_PACKAGES = [
    "spacy", "presidio_analyzer", "presidio_anonymizer",
    "fastapi", "streamlit", "aiosqlite", "plotly", "pandas",
    "rapidfuzz", "sklearn", "psutil", "loguru",
]


def check_python_version() -> bool:
    major, minor = sys.version_info[:2]
    ok = (major == 3 and minor >= 14)
    console.print(
        f"  Python {major}.{minor}",
        style="green" if ok else "red",
    )
    return ok


def check_packages() -> bool:
    table = Table(title="Python Packages", show_header=True)
    table.add_column("Package", style="cyan")
    table.add_column("Status", style="green")
    all_ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            table.add_row(pkg, "[green]OK[/green]")
        except ImportError:
            table.add_row(pkg, "[red]MISSING[/red]")
            all_ok = False
    console.print(table)
    return all_ok


def check_spacy_model() -> bool:
    try:
        import spacy
        nlp = spacy.load("en_core_web_lg")
        console.print("  spaCy en_core_web_lg: [green]OK[/green]")
        return True
    except OSError:
        console.print(
            "  spaCy en_core_web_lg: [red]NOT FOUND[/red]\n"
            "  Run: python -m spacy download en_core_web_lg"
        )
        return False


def check_ollama() -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = {m["name"] for m in resp.json().get("models", [])}
        all_ok = True
        for m in REQUIRED_MODELS:
            found = any(m in name for name in models)
            console.print(
                f"  {m}: {'[green]FOUND[/green]' if found else '[red]MISSING[/red]'}"
            )
            if not found:
                all_ok = False
        return all_ok
    except Exception as e:
        console.print(f"  [red]Ollama not reachable: {e}[/red]")
        console.print("  Make sure 'ollama serve' is running.")
        return False


def check_ollama_inference() -> bool:
    try:
        import ollama
        resp = ollama.generate(model="phi3:mini", prompt="Reply with just: OK")
        ok = "ok" in resp["response"].lower() or len(resp["response"]) > 0
        console.print(f"  Inference test: {'[green]OK[/green]' if ok else '[yellow]WARN[/yellow]'}")
        return ok
    except Exception as e:
        console.print(f"  [red]Inference failed: {e}[/red]")
        return False


if __name__ == "__main__":
    console.rule("[bold blue]AI Routing System — Health Check[/bold blue]")

    results = {
        "Python 3.14+": check_python_version(),
        "Python Packages": check_packages(),
        "spaCy Model": check_spacy_model(),
        "Ollama Models": check_ollama(),
        "Ollama Inference": check_ollama_inference(),
    }

    console.rule()
    all_pass = all(results.values())
    if all_pass:
        console.print("[bold green]All checks passed! Ready to build.[/bold green]")
    else:
        failed = [k for k, v in results.items() if not v]
        console.print(f"[bold red]Failed: {', '.join(failed)}[/bold red]")
        sys.exit(1)