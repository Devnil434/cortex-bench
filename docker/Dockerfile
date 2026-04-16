FROM python:3.14-slim

WORKDIR /app

# Install spaCy model dependencies (system-level)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install all deps with pip — no uv
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m spacy download en_core_web_lg

COPY . .

# Create data directory for SQLite
RUN mkdir -p data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]