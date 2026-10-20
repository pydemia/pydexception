"""HTTP rendering of classified errors."""

from __future__ import annotations

from typing import Protocol

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .mapping import ResolvedError
from .models import ProblemDetails


class ResponseRenderer(Protocol):
    """An application can replace the default response envelope."""

    def render(
        self,
        request: Request,
        error: ResolvedError,
        *,
        trace_id: str,
        instance: str | None,
    ) -> Response: ...


class ProblemRenderer:
    """Render the package's RFC 9457 response."""

    def render(
        self,
        request: Request,
        error: ResolvedError,
        *,
        trace_id: str,
        instance: str | None,
    ) -> Response:
        del request
        problem = ProblemDetails(
            type=error.spec.type_uri,
            title=error.spec.title,
            status=error.spec.http_status,
            detail=error.detail,
            code=error.spec.code,
            trace_id=trace_id,
            instance=instance,
        )
        headers = {
            key: value for key, value in error.headers.items() if key.lower() != "x-request-id"
        }
        headers["X-Request-ID"] = trace_id
        return JSONResponse(
            status_code=error.spec.http_status,
            content=problem.model_dump(exclude_none=True),
            headers=headers,
            media_type="application/problem+json",
        )
