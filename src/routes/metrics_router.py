"""Prometheus metrics exposition endpoint."""

from fastapi import APIRouter, Response

from src.observability.metrics import render_metrics


metrics_router = APIRouter(tags=["Metrics"])


@metrics_router.get(
    "/metrics",
    include_in_schema=False,
)
async def metrics() -> Response:
    payload, content_type = render_metrics()

    return Response(
        content=payload,
        media_type=content_type,
    )
