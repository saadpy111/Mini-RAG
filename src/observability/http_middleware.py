"""ASGI middleware that records bounded HTTP request metrics."""

from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.observability.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)

KNOWN_METHODS = {
    "DELETE",
    "GET",
    "HEAD",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
}


class PrometheusMiddleware:
    """Record request count, status, route, and latency."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http" or scope.get("path") == "/metrics":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "GET").upper()
        if method not in KNOWN_METHODS:
            method = "OTHER"

        started = perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = int(message["status"])

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = self._route_label(scope)
            duration = perf_counter() - started

            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                route=route,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                route=route,
            ).observe(duration)

    @staticmethod
    def _route_label(scope: Scope) -> str:
        route = scope.get("route")
        route_path = getattr(route, "path", None)

        if route_path:
            return str(route_path)

        endpoint = scope.get("endpoint")
        endpoint_name = getattr(endpoint, "__name__", None)

        if endpoint_name:
            return str(endpoint_name)

        return "unmatched"
