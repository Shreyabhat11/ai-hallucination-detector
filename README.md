# AI Hallucination Detector

### Fact-Checking & Safety Layer for LLMs using Gemini + Web Search + Vector Similarity

An intelligent **AI guardrail system** that audits Large Language Model (LLM) responses and detects hallucinations using:

* Claim extraction
* Web evidence retrieval
* Local knowledge base search
* Logical consistency checks
* Confidence analysis
* Cross-model verification
* Risk scoring dashboard

---

##  Why this project?

LLMs often:

* invent facts
* fabricate sources
* sound overconfident
* contradict themselves

This system acts like an **AI fact-checking firewall** between the model and the user.

Think of it as:

> Grammarly for truthfulness.

---

#  Features

## 🔍 Detection Modules

| Module            | Purpose                                |
| ----------------- | -------------------------------------- |
| Claim Extraction  | Breaks answers into atomic facts       |
| Fact Check        | Verifies with web + local KB           |
| Logic Check       | Finds contradictions                   |
| Citation Check    | Detects fake references                |
| Confidence Score  | Flags overconfident tone               |
| Cross Model Check | Measures answer consistency            |
| Risk Engine       | Combines all signals into final risk % |

---

##  Visual Dashboard (Streamlit)

Interactive UI shows:

* Risk meter
* Module-wise progress bars
* Extracted claims
* Model answer
* Debug JSON (optional)

---

#  Architecture

```
User Prompt
   ↓
Gemini LLM (Answer)
   ↓
Hallucination Detector Pipeline
   ├── Claim Extraction
   ├── Fact Check (Web + Vector Search)
   ├── Logic Check
   ├── Citation Check
   ├── Confidence Check
   ├── Cross Model Agreement
   ↓
Risk Score + Report
   ↓
Streamlit Dashboard
```

---

# ⚙️ Installation

## 1️⃣ Clone

```bash
git clone <repo_url>
cd ai-hallucination-detector
```

---

## 2️⃣ Create virtual env

```bash
python -m venv .venv
source .venv/bin/activate     # mac/linux
.venv\Scripts\activate        # windows
```

---

## 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Setup API Key (Gemini)

Create `.env` in project root:

```
GEMINI_API_KEY=your_api_key_here
```

Get key from:
👉 [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

# ▶️ Run the Project

## Start backend (FastAPI)

```bash
uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

---

## Start dashboard (Streamlit)

```bash
streamlit run streamlit_app.py
```

Open:

```
http://localhost:8501
```

---

# 🧪 Example Test

### Input

```
When was the Eiffel Tower built?
```

### Output

```
Risk Score: 12% (Low)
Claims verified with evidence
```

---

# 🧠 How It Works

## Step 1 — Generate Answer

Gemini produces initial response.

## Step 2 — Extract Claims

Break text into factual statements.

Example:

```
• Eiffel Tower was built in 1889
• Height is 330 meters
```

## Step 3 — Verify

Each claim checked using:

* local knowledge base
* web search evidence
* verifier LLM

## Step 4 — Score

Weighted scoring:

```
Risk = f(fact + logic + citation + confidence + cross)
```

---

# 📦 Tech Stack

* Python
* FastAPI
* Streamlit
* Google Gemini API
* Sentence Transformers
* Vector similarity search
* DuckDuckGo Web Search

---

# 🚀 Future Improvements

* Async parallel checks (faster)
* Highlight risky sentences
* Browser extension
* Chrome plugin
* FAISS / large vector DB
* RAG integration
* PDF/Doc fact verification
* Enterprise guardrail API
