"""FastAPI integration, with reusable handling for custom APIRoute wrappers."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable, Sequence
from typing import TypeAlias

from fastapi import FastAPI
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from .catalog import ErrorCatalog
from .exceptions import AppException
from .mapping import ExceptionMapper, ResolvedError, classify_exception, internal_error
from .renderers import ProblemRenderer, ResponseRenderer

RequestIdProvider: TypeAlias = Callable[[Request], str | None]
InstanceProvider: TypeAlias = Callable[[Request, str], str | None]

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class ExceptionAdapter:
    """Classify and render an exception for one FastAPI application."""

    def __init__(
        self,
        *,
        catalog: ErrorCatalog | None = None,
        renderer: ResponseRenderer | None = None,
        mappers: Sequence[ExceptionMapper] = (),
        request_id_provider: RequestIdProvider | None = None,
        instance_provider: InstanceProvider | None = None,
        logger: logging.Logger | None = None,
        expose_http_detail: bool = False,
    ) -> None:
        self.catalog = catalog if catalog is not None else ErrorCatalog()
        self.renderer = renderer if renderer is not None else ProblemRenderer()
        self.mappers = tuple(mappers)
        self.request_id_provider = request_id_provider
        self.instance_provider = instance_provider
        self.logger = logger if logger is not None else logging.getLogger("pydexception")
        self.expose_http_detail = expose_http_detail

    def _trace_id(self, request: Request) -> str:
        if self.request_id_provider is not None:
            try:
                candidate = self.request_id_provider(request)
            except Exception:
                candidate = None
            if isinstance(candidate, str) and _REQUEST_ID.fullmatch(candidate):
                return candidate
        return f"trn-{uuid.uuid4()}"

    async def response_for(self, request: Request, exc: Exception) -> Response:
        """Use this method from a route wrapper that catches exceptions first."""

        if isinstance(exc, StarletteHTTPException) and not 400 <= exc.status_code <= 599:
            return await http_exception_handler(request, exc)

        trace_id = self._trace_id(request)
        error: ResolvedError
        try:
            resolved = classify_exception(
                exc,
                mappers=self.mappers,
                expose_http_detail=self.expose_http_detail,
            )
            if resolved is None:
                return await http_exception_handler(request, exc)  # type: ignore[arg-type]
            error = resolved
            instance = (
                self.instance_provider(request, trace_id)
                if self.instance_provider is not None
                else None
            )
            response = self.renderer.render(request, error, trace_id=trace_id, instance=instance)
            if not isinstance(response, Response):
                raise TypeError("renderer must return a Response")
            if response.status_code != error.spec.http_status:
                raise ValueError("renderer status does not match resolved error")
        except Exception:
            error = internal_error()
            response = ProblemRenderer().render(request, error, trace_id=trace_id, instance=None)
        response.headers["X-Request-ID"] = trace_id
        level = logging.ERROR if error.spec.http_status >= 500 else logging.WARNING
        self.logger.log(
            level,
            "HTTP error response",
            extra={
                "error_code": error.spec.code,
                "http_status": error.spec.http_status,
                "trace_id": trace_id,
                "exception_type": type(exc).__name__,
            },
        )
        return response


def install_exception_handlers(
    app: FastAPI,
    *,
    catalog: ErrorCatalog | None = None,
    renderer: ResponseRenderer | None = None,
    mappers: Sequence[ExceptionMapper] = (),
    request_id_provider: RequestIdProvider | None = None,
    instance_provider: InstanceProvider | None = None,
    logger: logging.Logger | None = None,
    expose_http_detail: bool = False,
    replace: bool = False,
) -> ExceptionAdapter:
    """Install handlers before the application starts serving requests."""

    if app.middleware_stack is not None:
        raise RuntimeError("install exception handlers before the first request")
    if getattr(app.state, "pydexception", None) is not None:
        raise RuntimeError("pydexception handlers are already installed")

    default_handlers: dict[type[Exception], object] = {
        StarletteHTTPException: http_exception_handler,
        RequestValidationError: request_validation_exception_handler,
    }
    handled_types: tuple[type[Exception], ...] = (
        AppException,
        StarletteHTTPException,
        RequestValidationError,
        Exception,
    )
    for exception_type in handled_types:
        existing = app.exception_handlers.get(exception_type)
        if (
            existing is not None
            and existing is not default_handlers.get(exception_type)
            and not replace
        ):
            raise ValueError(f"custom handler already registered for {exception_type.__name__}")

    adapter = ExceptionAdapter(
        catalog=catalog,
        renderer=renderer,
        mappers=mappers,
        request_id_provider=request_id_provider,
        instance_provider=instance_provider,
        logger=logger,
        expose_http_detail=expose_http_detail,
    )

    async def handle_exception(request: Request, exc: Exception) -> Response:
        return await adapter.response_for(request, exc)

    app.add_exception_handler(AppException, handle_exception)
    app.add_exception_handler(StarletteHTTPException, handle_exception)
    app.add_exception_handler(RequestValidationError, handle_exception)
    app.add_exception_handler(Exception, handle_exception)
    app.state.pydexception = adapter
    return adapter
