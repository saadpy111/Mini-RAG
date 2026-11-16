"""Prometheus metric definitions shared by the API and RAG pipeline."""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

P = ParamSpec("P")
R = TypeVar("R")

HTTP_DURATION_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
)

RAG_DURATION_BUCKETS = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    30.0,
    60.0,
    120.0,
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests.",
    ("method", "route", "status"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    buckets=HTTP_DURATION_BUCKETS,
)

RAG_QUESTIONS_TOTAL = Counter(
    "rag_questions_total",
    "RAG questions accepted for processing.",
    ("language",),
)

RAG_ANSWERS_GENERATED_TOTAL = Counter(
    "rag_answers_generated_total",
    "RAG answers successfully generated.",
    ("language",),
)

RAG_NO_RELEVANT_CHUNKS_TOTAL = Counter(
    "rag_no_relevant_chunks_total",
    "RAG requests that found no usable context chunks.",
    ("language",),
)

RAG_ERRORS_TOTAL = Counter(
    "rag_errors_total",
    "RAG requests that failed during a pipeline stage.",
    ("stage",),
)

RAG_PIPELINE_DURATION_SECONDS = Histogram(
    "rag_pipeline_duration_seconds",
    "End-to-end RAG pipeline duration in seconds.",
    buckets=RAG_DURATION_BUCKETS,
)

RAG_EMBEDDING_DURATION_SECONDS = Histogram(
    "rag_embedding_duration_seconds",
    "Question embedding duration in seconds.",
    ("operation",),
    buckets=RAG_DURATION_BUCKETS,
)

RAG_VECTOR_SEARCH_DURATION_SECONDS = Histogram(
    "rag_vector_search_duration_seconds",
    "Vector database search duration in seconds.",
    ("operation",),
    buckets=RAG_DURATION_BUCKETS,
)

RAG_LLM_DURATION_SECONDS = Histogram(
    "rag_llm_duration_seconds",
    "Chat completion duration in seconds.",
    buckets=RAG_DURATION_BUCKETS,
)


def track_duration(
    histogram: Histogram,
) -> Callable[
    [Callable[P, Awaitable[R]]],
    Callable[P, Awaitable[R]],
]:
    """Record an async function's duration on ``histogram``."""

    def decorator(
        function: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]:
        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with histogram.time():
                return await function(*args, **kwargs)

        return wrapper

    return decorator


def render_metrics() -> tuple[bytes, str]:
    """Return the current Prometheus exposition payload and content type."""

    return generate_latest(), CONTENT_TYPE_LATEST


__all__ = [
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUESTS_TOTAL",
    "RAG_ANSWERS_GENERATED_TOTAL",
    "RAG_EMBEDDING_DURATION_SECONDS",
    "RAG_ERRORS_TOTAL",
    "RAG_LLM_DURATION_SECONDS",
    "RAG_NO_RELEVANT_CHUNKS_TOTAL",
    "RAG_PIPELINE_DURATION_SECONDS",
    "RAG_QUESTIONS_TOTAL",
    "RAG_VECTOR_SEARCH_DURATION_SECONDS",
    "render_metrics",
    "track_duration",
]
