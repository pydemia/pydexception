from __future__ import annotations

from fastapi import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

from pydexception import AppException, ErrorSpec, classify_exception


def item_spec() -> ErrorSpec:
    return ErrorSpec(
        code=-1001,
        http_status=404,
        type_uri="https://api.example.com/problems/missing",
        title="Missing",
        message="Item not found.",
    )


def test_application_error_uses_public_detail_and_headers() -> None:
    error = classify_exception(
        AppException(item_spec(), detail="Item 42 is missing.", headers={"Retry-After": "30"})
    )
    assert error is not None
    assert error.spec.code == -1001
    assert error.detail == "Item 42 is missing."
    assert error.headers["Retry-After"] == "30"


def test_mapper_precedes_framework_fallback() -> None:
    def mapper(exc: Exception) -> AppException | None:
        if isinstance(exc, LookupError):
            return AppException(item_spec())
        return None

    mapped = classify_exception(LookupError("private database key"), mappers=[mapper])
    assert mapped is not None
    assert mapped.spec.code == -1001
    assert "private" not in mapped.detail


def test_http_exception_hides_detail_by_default_and_preserves_headers() -> None:
    error = classify_exception(
        HTTPException(401, detail={"token": "private"}, headers={"WWW-Authenticate": "Bearer"})
    )
    assert error is not None
    assert error.spec.http_status == 401
    assert error.detail == "Unauthorized"
    assert error.headers["WWW-Authenticate"] == "Bearer"


def test_http_detail_requires_opt_in_and_still_hides_5xx() -> None:
    public = classify_exception(
        StarletteHTTPException(404, detail="Public missing item"), expose_http_detail=True
    )
    private = classify_exception(
        StarletteHTTPException(500, detail="database password"), expose_http_detail=True
    )
    assert public is not None and public.detail == "Public missing item"
    assert private is not None and "password" not in private.detail


def test_non_error_http_status_is_delegated() -> None:
    assert classify_exception(StarletteHTTPException(307, detail="redirect")) is None


def test_unexpected_error_never_exposes_original_text() -> None:
    error = classify_exception(ValueError("secret card number"))
    assert error is not None
    assert error.spec.http_status == 500
    assert error.spec.code == "internal_server_error"
    assert "secret" not in error.detail
