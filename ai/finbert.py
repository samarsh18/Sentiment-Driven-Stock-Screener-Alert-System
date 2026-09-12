"""
Open-source financial sentiment model integration (Stage 1).

We use an EXISTING, PRETRAINED, open-source model — we do not train or
fine-tune anything here. See the "Open-source model" section of the
project README for full documentation (model name, repo, license,
download/execution method, input/output format).

Model: ProsusAI/finbert
    https://huggingface.co/ProsusAI/finbert
    (training code / paper: https://github.com/ProsusAI/finBERT)

This module is deliberately decoupled from the `transformers` library at
import time: the actual Hugging Face pipeline is loaded lazily, and a
`predict_fn` can be injected for testing so unit tests never need to
download the ~440MB model or hit the network.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from ai.schemas import SentimentResult

logger = logging.getLogger(__name__)

# ProsusAI/finbert emits these three labels. Anything else is treated as
# an invalid/unexpected model output.
_VALID_LABELS = {"positive", "negative", "neutral"}

# BERT-family models (including finbert) have a 512 sub-word-token limit.
# We also cap raw characters before tokenization so pathologically long
# articles don't blow up latency/memory before we ever reach the tokenizer.
DEFAULT_MAX_INPUT_CHARS = 4000

# Type of the injectable prediction function: raw text in, a list of
# {"label": str, "score": float} dicts out (this matches the shape the
# Hugging Face `pipeline("sentiment-analysis", ...)` call returns).
PredictFn = Callable[[str], List[dict]]


class FinBertError(Exception):
    """Base class for all FinBERT-related failures."""


class FinBertInferenceError(FinBertError):
    """Raised when the underlying model call itself fails (e.g. runtime
    error, OOM, network failure while lazily downloading weights)."""


class FinBertInvalidOutputError(FinBertError):
    """Raised when the model returns output we cannot normalize (e.g. an
    unexpected label, missing score, or malformed structure)."""


def _lazy_load_pipeline() -> PredictFn:
    """Loads the real Hugging Face pipeline on first use.

    Imported lazily so importing this module (and running the test suite)
    never requires `transformers`/`torch` to be installed unless someone
    actually exercises the real model.
    """
    try:
        from transformers import pipeline  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without transformers installed
        raise FinBertInferenceError(
            "The 'transformers' package is required to run the real "
            "FinBERT model. Install it with `pip install transformers torch`, "
            "or inject a `predict_fn` (e.g. for tests)."
        ) from exc

    nlp = pipeline("sentiment-analysis", model="ProsusAI/finbert", tokenizer="ProsusAI/finbert")

    def _predict(text: str) -> List[dict]:
        # truncation=True + max_length=512 respects the model's context
        # window regardless of how long `text` is.
        return nlp(text, truncation=True, max_length=512)

    return _predict


def normalize_finbert_output(raw: List[dict]) -> SentimentResult:
    """Normalizes a raw Hugging Face pipeline result into our contract.

    Raises FinBertInvalidOutputError if the shape or label is unexpected.
    Never silently accepts invalid AI data.
    """
    if not raw or not isinstance(raw, list):
        raise FinBertInvalidOutputError(f"Expected a non-empty list, got: {raw!r}")

    top = raw[0]
    if not isinstance(top, dict) or "label" not in top or "score" not in top:
        raise FinBertInvalidOutputError(f"Malformed model output: {top!r}")

    label = str(top["label"]).lower().strip()
    try:
        score = float(top["score"])
    except (TypeError, ValueError) as exc:
        raise FinBertInvalidOutputError(f"Non-numeric score: {top.get('score')!r}") from exc

    if label not in _VALID_LABELS:
        raise FinBertInvalidOutputError(f"Unexpected sentiment label: {label!r}")

    if not (0.0 <= score <= 1.0):
        raise FinBertInvalidOutputError(f"Score out of expected [0,1] range: {score!r}")

    # Map the model's (label, confidence) pair onto our signed -1..1 scale.
    # Positive confidence pushes toward +1, negative confidence toward -1,
    # neutral has no direction so it maps to 0.0 regardless of confidence.
    if label == "positive":
        sentiment_score = score
    elif label == "negative":
        sentiment_score = -score
    else:
        sentiment_score = 0.0

    return SentimentResult(sentiment=label, sentiment_score=round(sentiment_score, 4))


class FinBertSentimentAnalyzer:
    """Thin wrapper around the open-source financial sentiment model.

    Usage:
        analyzer = FinBertSentimentAnalyzer()
        result = analyzer.analyze("Acme Corp beats earnings estimates")

    For tests, inject a fake `predict_fn` so no real model is loaded:
        analyzer = FinBertSentimentAnalyzer(
            predict_fn=lambda text: [{"label": "positive", "score": 0.91}]
        )
    """

    def __init__(
        self,
        predict_fn: Optional[PredictFn] = None,
        max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    ) -> None:
        self._predict_fn = predict_fn
        self._max_input_chars = max_input_chars

    def _get_predict_fn(self) -> PredictFn:
        if self._predict_fn is None:
            self._predict_fn = _lazy_load_pipeline()
        return self._predict_fn

    def analyze(self, text: str) -> SentimentResult:
        """Classifies financial-news text as positive/negative/neutral.

        Handles:
            - empty/whitespace-only text -> neutral, 0.0, no model call
            - extremely long text -> truncated before hitting the model
            - model runtime errors -> FinBertInferenceError
            - invalid/unexpected model output -> FinBertInvalidOutputError
        """
        if text is None or not text.strip():
            logger.info("Empty text passed to FinBERT; returning neutral without model call.")
            return SentimentResult(sentiment="neutral", sentiment_score=0.0)

        truncated = text[: self._max_input_chars]
        if len(text) > self._max_input_chars:
            logger.info(
                "Truncated input from %d to %d characters before FinBERT inference.",
                len(text),
                self._max_input_chars,
            )

        predict_fn = self._get_predict_fn()
        try:
            raw_output = predict_fn(truncated)
        except FinBertError:
            raise
        except Exception as exc:  # noqa: BLE001 - any model failure is wrapped uniformly
            logger.exception("FinBERT inference failed.")
            raise FinBertInferenceError(str(exc)) from exc

        return normalize_finbert_output(raw_output)
