"""Standard benchmark prompts covering all 5 intent categories."""

BENCHMARK_PROMPTS = {
    "coding": [
        "Write a Python function to find the nth Fibonacci number using memoization.",
        "Fix this bug: def add(a, b): return a - b",
        "Write a FastAPI endpoint that returns a list of users from SQLite.",
        "Implement a binary search algorithm in Python with type hints.",
        "Write a regex to validate an email address.",
    ],
    "reasoning": [
        "If all cats are animals and some animals are pets, can we say all cats are pets? Explain.",
        "A train travels 60 mph for 2 hours then 80 mph for 3 hours. What is the average speed?",
        "Compare and contrast REST API and GraphQL. Which should I choose for a mobile app?",
        "Step by step: how does a Python dictionary handle hash collisions?",
        "Why does Python's GIL exist and what are its implications for multi-threading?",
    ],
    "summarization": [
        "Summarize the key points: Large Language Models are trained on massive datasets...",
        "Give me a TL;DR of the concept of gradient descent in machine learning.",
        "What are the main takeaways from the CAP theorem in distributed systems?",
        "Briefly summarize what Docker containers are and why they are useful.",
        "Condense this: The Internet Protocol Suite (TCP/IP) is the conceptual model...",
    ],
    "factual_qa": [
        "What is the difference between RAM and ROM?",
        "What year was Python created and by whom?",
        "Define 'idempotent' in the context of HTTP methods.",
        "What is the time complexity of quicksort in the worst case?",
        "What does ACID stand for in database transactions?",
    ],
    "creative": [
        "Write a short haiku about machine learning.",
        "Suggest 5 creative names for a privacy-focused AI startup.",
        "Write a one-paragraph story about a robot learning to code.",
        "Brainstorm 5 innovative uses for local LLMs in healthcare.",
        "Come up with a catchy tagline for an offline AI assistant.",
    ],
}