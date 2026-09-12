"""
Prompt templates for the Gemini LLM stage.

Kept separate from ai/gemini.py and ai/analyzer.py on purpose: prompts are
content, not control flow, and should be editable/reviewable without
touching business logic (and without hunting for a giant string inside a
route handler).
"""

from __future__ import annotations

from ai.schemas import NewsInput, SentimentResult

SYSTEM_PROMPT = """You are a financial news analyst assistant embedded in a stock \
screener and alert system. You analyze one financial news item at a time \
in the context of a preliminary sentiment signal, and return a single, \
strictly-structured JSON object describing its likely market impact.

Rules you must always follow:
- Focus only on the actual, stated financial event in the article. Do not \
invent facts that are not present in the text.
- Clearly distinguish confirmed facts from your own inferences or \
assumptions. If you are inferring something, treat it as lower-confidence.
- Do NOT predict exact future stock prices, price targets, or percentage \
moves.
- Do NOT provide financial advice (no "buy", "sell", or "hold" \
recommendations).
- Be concise. `reason` and `summary` should each be at most 2-3 sentences.
- Return ONLY a single JSON object. No markdown code fences, no \
preamble, no trailing commentary.
"""

# The exact JSON schema we require back from Gemini. Keeping this as a
# literal, explicit shape in the prompt (rather than just describing it in
# prose) meaningfully reduces malformed-output rates.
RESPONSE_SCHEMA_HINT = """Respond with ONLY a JSON object of this exact shape:
{
  "news_id": "<same news_id as given below>",
  "symbol": "<same symbol as given below>",
  "sentiment": "positive | negative | neutral",
  "sentiment_score": <float between -1 and 1>,
  "impact": "low | medium | high",
  "severity": <integer between 1 and 10>,
  "confidence": <float between 0 and 1>,
  "reason": "<short explanation grounded in the article text>",
  "summary": "<concise, neutral summary of the news>"
}
"""


def build_analysis_prompt(news: NewsInput, sentiment_result: SentimentResult) -> str:
    """Builds the full user-turn prompt sent to Gemini for Stage 2 analysis.

    Includes: news title, news content, stock symbol, company, and the
    open-source sentiment result, per the project's Stage 2 contract.
    """
    return f"""{SYSTEM_PROMPT}

Here is the news item and a preliminary open-source sentiment signal to \
use as context (you may agree, refine, or override it based on your own \
reading of the article, but explain your reasoning if you diverge):

news_id: {news.news_id}
symbol: {news.symbol}
company_name: {news.company_name}
source: {news.source}
published_at: {news.published_at.isoformat()}

title: {news.title}

content:
\"\"\"
{news.content}
\"\"\"

preliminary_sentiment: {sentiment_result.sentiment}
preliminary_sentiment_score: {sentiment_result.sentiment_score}

{RESPONSE_SCHEMA_HINT}
"""
