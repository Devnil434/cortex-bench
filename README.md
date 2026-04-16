# 🔀 Cortex-Bench: AI Routing System with Privacy Firewall

> Intelligent offline AI system that dynamically selects the best local LLM while protecting sensitive user data.

---

## 🚀 Overview

This project is a **privacy-first, fully local AI routing system** that:

* Runs multiple Small Language Models (SLMs) using **Ollama**
* Dynamically selects the best model based on query intent
* Detects and masks sensitive data before inference
* Benchmarks model performance (speed vs quality)

💡 Built to address real-world constraints:

* 🔒 Privacy (no external API calls)
* ⚡ Latency (local inference)
* 💰 Cost (zero API usage)

---

## 🧠 Key Features

### 🔀 Intelligent Model Routing

* Classifies query intent (coding, reasoning, creative, etc.)
* Routes to optimal model:

  * ⚡ `phi3:mini` → fast coding tasks
  * ⚖️ `llama3.2:3b` → balanced responses
  * 🧠 `mistral:7b` → deep reasoning

---

### 🛡️ Privacy Firewall (Core Innovation)

* Built using **Microsoft Presidio** + spaCy
* Detects and masks:

  * Emails, phone numbers, credit cards
  * Aadhaar, PAN, UPI (custom Indian patterns 🇮🇳)
* Reversible anonymization:

  ```
  John → <PERSON_1>
  test@gmail.com → <EMAIL_1>
  ```

---

### 📊 Benchmarking Engine

* Compare models on:

  * ⏱ Latency
  * 🔤 Tokens/sec
  * 🧠 Response quality
* CLI runner generates structured results

---

### 🌐 Full-Stack System

* ⚙️ Backend: **FastAPI**
* 🎨 Frontend: **Streamlit**
* 🗄️ Database: SQLite (audit logs)
* 🔁 Streaming: SSE (real-time token output)

---

## 🏗️ Architecture

```
User Query
   │
   ▼
🛡️ Privacy Firewall
   │
   ▼
🧠 Intent Classifier
   │
   ▼
🔀 Smart Router
   │
   ▼
🤖 Local LLM (Ollama)
   │
   ▼
📊 Metrics + Audit Logs
```

---

## ⚙️ Tech Stack

| Layer       | Technology    |
| ----------- | ------------- |
| LLM Runtime | Ollama        |
| Backend     | FastAPI       |
| Frontend    | Streamlit     |
| NLP         | spaCy         |
| Privacy     | Presidio      |
| Database    | SQLite        |
| Benchmark   | Python + Rich |

---

## 📦 Installation

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

---

### 2. Pull Models

```bash
ollama pull phi3:mini
ollama pull llama3.2:3b
ollama pull mistral:7b
```

---

### 3. Setup Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

### 4. Install spaCy Model

```bash
python -m spacy download en_core_web_lg
```

---

### 5. Run Health Check

```bash
python health_check.py
```

---

## ▶️ Running the Project

### Start Backend

```bash
uvicorn backend.server:app --reload
```

### Start Frontend

```bash
streamlit run frontend/app.py
```

---

## 📊 Benchmarking

Run:

```bash
python -m benchmarks.runner
```

Outputs:

* Latency comparison
* Tokens/sec
* Model efficiency tradeoffs

---

## 📈 Example Tradeoffs

| Model       | Speed ⚡ | Quality 🧠 | Memory 💾 |
| ----------- | ------- | ---------- | --------- |
| phi3:mini   | High    | Medium     | Low       |
| llama3.2:3b | Medium  | Medium+    | Medium    |
| mistral:7b  | Low     | High       | High      |

---

## 🔒 Privacy First Design

* ❌ No external APIs
* ✅ All inference runs locally
* ✅ PII masked before processing
* ✅ Sensitive queries routed to smaller models

---

## 🧪 Example Flow

**Input:**

```
My Aadhaar is 1234 5678 9123, explain recursion
```

**Processed:**

```
My Aadhaar is <IN_AADHAAR_1>, explain recursion
```

---

## 📊 Dashboard Features

* Routing decision logs
* Privacy audit history
* Model performance charts

---

## 🐳 Docker Support

```bash
docker compose up --build
```

Includes:

* Ollama
* Backend
* Frontend

---

## 📌 Future Improvements

* GPU acceleration support
* Fine-tuned routing model
* Multi-language PII detection
* RAG integration (local vector DB)

---

## 🤝 Contributing

Contributions are welcome!

* Fork the repo
* Create a feature branch
* Submit a PR

---

## 📜 License

MIT License

---

## 💡 Why This Project Matters

This project demonstrates:

* Real-world AI system design
* Privacy-aware architecture
* Performance benchmarking
* Intelligent model orchestration

---

## 👨‍💻 Author

**Nilanjan Saha**

* Passionate about AI, MLOps, and system design
* Building real-world AI infrastructure projects

---

## ⭐ If you like this project

Give it a star ⭐ and share!
