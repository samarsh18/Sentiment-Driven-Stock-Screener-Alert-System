# Project Context — Sentiment-Driven Stock Screener + Alert System

---

## Goal

Users create profiles and select stocks that they want to monitor.

The system continuously monitors available financial news and market data for
those stocks. Relevant events are normalized, deduplicated, analyzed using a
hybrid AI pipeline, classified by a deterministic decision engine, stored, and
eventually sent as personalized alerts.

---

## Team Ownership

### Person 1 — Data Ingestion & 24/7 Monitoring
- Financial news ingestion
- Market-data ingestion
- Provider integrations
- News normalization
- News deduplication
- Background monitoring worker
- Monitoring pipeline

### Person 2 — Backend & Database
- PostgreSQL database
- SQLAlchemy ORM
- FastAPI application
- User APIs
- Watchlist APIs
- Database persistence
- Alert persistence

### Person 3 — AI & Decision Engine
- Open-source financial sentiment model (FinBERT / equivalent)
- Gemini LLM integration
- AI prompts
- AI output validation
- AI analyzer
- Decision engine

---

## Normalized News Contract

Person 1 must produce normalized news objects that conform to this schema.
All downstream consumers (Person 3 AI pipeline, Person 2 persistence) depend on it.

```json
{
  "news_id": "string",
  "symbol": "string",
  "company_name": "string",
  "title": "string",
  "content": "string",
  "source": "string",
  "url": "string",
  "published_at": "ISO-8601 timestamp"
}
```

---

## Monitoring Architecture

The monitoring service runs independently from the frontend.
Closing the frontend does **not** stop monitoring.
Background workers continue to ingest and analyze data as long as the server
process is running.

The system processes information when it becomes available from supported data
providers. It does not claim to receive information before a provider publishes it.

---

## Security Policy

**Never commit:**
- API keys
- Passwords
- Database credentials
- `.env` files

Use `.env.example` as a template. Copy it to `.env` locally and fill in your
secrets. The `.env` file is listed in `.gitignore` and must never be staged or
committed.

---

## Branch Strategy

```
main
└── develop
    ├── feature/data-monitoring    ← Person 1
    ├── feature/backend-database   ← Person 2
    └── feature/hybrid-ai          ← Person 3
```

Each developer works exclusively on their own feature branch. No developer should
commit to `main`, `develop`, or another developer's feature branch.
