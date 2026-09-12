"""
AI subsystem for the Sentiment-Driven Stock Screener + Alert System.

Ownership (Developer 3):
    - Open-source financial sentiment model integration (FinBERT-based)
    - Gemini LLM integration
    - Prompt engineering
    - Structured AI output + Pydantic validation
    - Deterministic decision engine
    - Risk / opportunity / watch / informational classification

This package does NOT implement GDELT ingestion, market-data ingestion,
PostgreSQL models, FastAPI routes, the frontend, or push notifications.
Other developers should import `analyze_news` from `ai.analyzer` and
`evaluate` from `ai.decision_engine` as the integration points.
"""
