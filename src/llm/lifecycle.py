"""Application lifespan wiring for the shared LLM HTTP client."""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.helpers.config import settings


def build_http_client() -> httpx.AsyncClient:
    """Build the generic client owned by the application lifespan."""

    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.llm_connect_timeout,
            read=settings.llm_read_timeout,
            write=settings.llm_read_timeout,
            pool=settings.llm_connect_timeout,
        )
    )


@asynccontextmanager
async def llm_lifespan(app: FastAPI):
    client = build_http_client()
    app.state.llm_http_client = client

    try:
        yield
    finally:
        await client.aclose()
