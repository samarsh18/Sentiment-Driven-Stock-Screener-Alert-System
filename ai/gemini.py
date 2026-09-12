"""
Gemini LLM integration (Stage 2).

Gemini receives the news + the Stage 1 open-source sentiment result and
returns a structured analysis (impact, severity, confidence, reason,
summary). The raw response is always validated with Pydantic
(`ai.schemas.GeminiAnalysis`) before anything downstream trusts it.

Credentials:
    Read exclusively from the `GEMINI_API_KEY` environment variable.
    Never hardcoded, never logged, never committed. See `.env.example`.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Callable, Optional

from pydantic import ValidationError

from ai.prompts import build_analysis_prompt
from ai.schemas import GeminiAnalysis, NewsInput, SentimentResult

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"

# Injectable type: takes a fully-built prompt string, returns the raw text
# response from the model. This is the only seam needed to mock Gemini in
# tests -- no network, no SDK, no real API key required.
GenerateFn = Callable[[str], str]

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


class GeminiError(Exception):
    """Base class for all Gemini-related failures."""


class GeminiConfigError(GeminiError):
    """Raised when Gemini cannot be configured (e.g. missing API key)."""


class GeminiRequestError(GeminiError):
    """Raised when the request to Gemini itself fails (network, quota, etc.)."""


class GeminiOutputError(GeminiError):
    """Raised when Gemini's response is not valid JSON or fails schema
    validation. We never silently accept invalid AI data."""


def _strip_code_fences(text: str) -> str:
    """Gemini sometimes wraps JSON in ```json ... ``` fences despite
    instructions not to. Strip them defensively before parsing."""
    return _CODE_FENCE_RE.sub("", text.strip()).strip()


def _lazy_load_generate_fn(model_name: str, api_key: str) -> GenerateFn:
    """Loads the real google-generativeai SDK on first use."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without the SDK installed
        raise GeminiConfigError(
            "The 'google-generativeai' package is required to call the "
            "real Gemini API. Install it with `pip install google-generativeai`, "
            "or inject a `generate_fn` (e.g. for tests)."
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    def _generate(prompt: str) -> str:
        response = model.generate_content(prompt)
        return response.text

    return _generate


class GeminiClient:
    """Wraps Gemini calls for Stage 2 contextual news analysis.

    Usage:
        client = GeminiClient()  # reads GEMINI_API_KEY from env
        analysis = client.analyze(news, sentiment_result)

    For tests, inject `generate_fn` so no real API key or network call is
    required:
        client = GeminiClient(
            api_key="unused-in-tests",
            generate_fn=lambda prompt: '{"news_id": "...", ...}',
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_GEMINI_MODEL,
        generate_fn: Optional[GenerateFn] = None,
    ) -> None:
        # Credentials come exclusively from the environment unless a
        # generate_fn is injected (test mode), in which case no real key
        # is ever required.
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._model_name = model_name
        self._generate_fn = generate_fn

        if self._generate_fn is None and not self._api_key:
            raise GeminiConfigError(
                "GEMINI_API_KEY is not set. Set it as an environment variable "
                "(see .env.example) — never hardcode it in source."
            )

    def _get_generate_fn(self) -> GenerateFn:
        if self._generate_fn is None:
            # self._api_key is guaranteed non-None here (checked in __init__).
            self._generate_fn = _lazy_load_generate_fn(self._model_name, self._api_key)  # type: ignore[arg-type]
        return self._generate_fn

    def analyze(self, news: NewsInput, sentiment_result: SentimentResult) -> GeminiAnalysis:
        """Sends the news + Stage 1 sentiment to Gemini and returns a
        validated GeminiAnalysis.

        Raises:
            GeminiRequestError: the call to Gemini itself failed.
            GeminiOutputError: Gemini's response was not valid JSON, or
                failed Pydantic validation (malformed/out-of-range fields,
                missing keys, wrong types, etc).
        """
        prompt = build_analysis_prompt(news, sentiment_result)
        generate_fn = self._get_generate_fn()

        try:
            raw_text = generate_fn(prompt)
        except GeminiError:
            raise
        except Exception as exc:  # noqa: BLE001 - any SDK/network failure is wrapped uniformly
            logger.exception("Gemini request failed.")
            raise GeminiRequestError(str(exc)) from exc

        if raw_text is None:
            raise GeminiOutputError("Gemini returned an empty response.")

        cleaned = _strip_code_fences(raw_text)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("Gemini returned non-JSON output.")
            raise GeminiOutputError(f"Gemini output was not valid JSON: {exc}") from exc

        # Defensive: make sure identifiers weren't hallucinated/mismatched;
        # override with the values we actually sent, since these should be
        # pass-through, not model-generated.
        if isinstance(payload, dict):
            payload["news_id"] = news.news_id
            payload["symbol"] = news.symbol

        try:
            return GeminiAnalysis.model_validate(payload)
        except ValidationError as exc:
            logger.warning("Gemini output failed schema validation.")
            raise GeminiOutputError(f"Gemini output failed validation: {exc}") from exc
