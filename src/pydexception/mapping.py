"""Classify exceptions without creating an HTTP response."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import AppException, validated_headers
from .models import ErrorSpec

ExceptionMapper = Callable[[Exception], AppException | None]

_VALIDATION_SPEC = ErrorSpec(
    code="request_validation_error",
    http_status=422,
    type_uri="about:blank",
    title=HTTPStatus(422).phrase,
    message="Request validation failed.",
)
_INTERNAL_SPEC = ErrorSpec(
    code="internal_server_error",
    http_status=500,
    type_uri="about:blank",
    title=HTTPStatus(500).phrase,
    message="Internal server error.",
)


@dataclass(frozen=True)
class ResolvedError:
    """One response-ready error, independent of response serialization."""

    spec: ErrorSpec
    detail: str
    headers: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", validated_headers(self.headers))


def internal_error() -> ResolvedError:
    return ResolvedError(_INTERNAL_SPEC, _INTERNAL_SPEC.message, {})


def classify_exception(
    exc: Exception,
    *,
    mappers: Sequence[ExceptionMapper] = (),
    expose_http_detail: bool = False,
) -> ResolvedError | None:
    """Return None only for HTTP exceptions outside the 4xx/5xx range."""

    if isinstance(exc, AppException):
        return ResolvedError(exc.spec, exc.detail or exc.spec.message, exc.headers)

    for mapper in mappers:
        mapped = mapper(exc)
        if mapped is not None:
            if not isinstance(mapped, AppException):
                raise TypeError("exception mapper must return AppException or None")
            return ResolvedError(mapped.spec, mapped.detail or mapped.spec.message, mapped.headers)

    if isinstance(exc, RequestValidationError):
        return ResolvedError(_VALIDATION_SPEC, _VALIDATION_SPEC.message, {})

    if isinstance(exc, StarletteHTTPException):
        status = exc.status_code
        if not 400 <= status <= 599:
            return None
        try:
            title = HTTPStatus(status).phrase
            type_uri = "about:blank"
        except ValueError:
            title = "HTTP Error"
            type_uri = f"urn:pydexception:http-status:{status}"
        public_detail = title
        if expose_http_detail and status < 500 and isinstance(exc.detail, str):
            public_detail = exc.detail
        spec = ErrorSpec(
            code=f"http_{status}",
            http_status=status,
            type_uri=type_uri,
            title=title,
            message=public_detail,
        )
        return ResolvedError(spec, public_detail, exc.headers or {})

    return internal_error()
