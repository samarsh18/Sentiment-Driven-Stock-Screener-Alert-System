# Sentiment-Driven Stock Screener + Alert System

An AI-powered stock monitoring and alert system that continuously monitors available
financial news and market data for stocks selected by users.

---

## High-Level Pipeline

```
User Watchlist
      ↓
24/7 Background Monitoring
      ↓
Financial News + Market Data
      ↓
Relevance Filtering
      ↓
Deduplication
      ↓
Open-Source Financial Sentiment Model
      ↓
Gemini LLM
      ↓
Decision Engine
      ↓
Database
      ↓
Alert Service
      ↓
User Notification
```

---

## Key Design Principles

**Independent monitoring service**
The monitoring service runs independently from the frontend.
Closing the frontend does **not** stop monitoring. Background workers continue to
ingest and analyze data as long as the server process is running.

**Provider-bound data timeliness**
The system processes information when it becomes available from supported data providers.
It does not claim to receive information before a provider publishes it.

---

## Team Responsibilities

### Person 1 — Data Ingestion & 24/7 Monitoring
- Financial news ingestion
- Market-data ingestion
- Provider integrations
- News normalization
- News deduplication
- Background monitoring worker
- Monitoring pipeline

### Person 2 — Backend & Database
- FastAPI application
- PostgreSQL database
- SQLAlchemy ORM
- User APIs
- Watchlist APIs
- Database persistence
- Alert persistence

### Person 3 — AI & Decision Engine
- Open-source financial sentiment model (FinBERT / equivalent)
- Gemini LLM integration
- Prompt engineering
- Structured AI output
- AI output validation
- Decision engine

---

## Project Structure

```
Sentiment-Driven-Stock-Screener-Alert-System/
│
├── backend/          # FastAPI app (Person 2)
│   └── app/
│
├── worker/           # Background monitoring workers (Person 1)
│
├── ai/               # AI pipeline and decision engine (Person 3)
│
├── tests/            # Shared test suite
│
├── docs/             # Project documentation
│   └── PROJECT_CONTEXT.md
│
├── .gitignore
├── .env.example      # Template — copy to .env and fill in secrets
├── requirements.txt
└── README.md
```

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/samarsh18/Sentiment-Driven-Stock-Screener-Alert-System.git
cd Sentiment-Driven-Stock-Screener-Alert-System

# Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment template and fill in your secrets
cp .env.example .env
```

> **Never commit `.env`.** It is listed in `.gitignore`.

---

## Branch Strategy

```
main
└── develop
    ├── feature/data-monitoring    ← Person 1
    ├── feature/backend-database   ← Person 2
    └── feature/hybrid-ai          ← Person 3
```
