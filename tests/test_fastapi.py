from __future__ import annotations

import logging

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pydexception import (
    AppException,
    ErrorCatalog,
    ErrorSpec,
    ResolvedError,
    install_exception_handlers,
)

ITEM_NOT_FOUND = ErrorSpec(
    code=-1001,
    http_status=404,
    type_uri="https://api.example.com/problems/item-not-found",
    title="Item Not Found",
    message="Item not found.",
)


def make_app(**handler_options: object) -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app, **handler_options)  # type: ignore[arg-type]

    @app.get("/items/{item_id}")
    def get_item(item_id: int) -> dict[str, int]:
        raise AppException(ITEM_NOT_FOUND, detail=f"Item {item_id} is missing.")

    @app.get("/auth")
    def auth() -> None:
        raise HTTPException(401, detail="private token", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/limited")
    def limited() -> None:
        raise HTTPException(429, detail="slow down", headers={"Retry-After": "30"})

    @app.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("secret database password")

    @app.post("/body-error")
    def body_error(body: dict[str, str]) -> None:
        del body
        raise RuntimeError("secret database password")

    @app.get("/internal-validation")
    def internal_validation() -> None:
        class InternalModel(BaseModel):
            number: int

        InternalModel(number="wrong")  # type: ignore[arg-type]

    @app.get("/redirect")
    def redirect() -> None:
        raise HTTPException(307, detail="go", headers={"Location": "/items/1"})

    return app


def test_application_error_uses_rfc_body_and_matching_trace_header() -> None:
    app = make_app()
    with TestClient(app) as client:
        first = client.get("/items/1")
        second = client.get("/items/2")
    assert first.status_code == second.status_code == 404
    assert first.headers["content-type"] == "application/problem+json"
    assert first.json()["status"] == 404
    assert first.json()["code"] == -1001
    assert first.json()["detail"] == "Item 1 is missing."
    assert second.json()["detail"] == "Item 2 is missing."
    assert first.json()["trace_id"] == first.headers["x-request-id"]
    assert first.json()["trace_id"] != second.json()["trace_id"]
    assert "instance" not in first.json()
    assert ITEM_NOT_FOUND.message == "Item not found."


def test_framework_404_405_and_headers() -> None:
    app = make_app()
    with TestClient(app) as client:
        not_found = client.get("/missing")
        method = client.post("/auth")
        auth = client.get("/auth")
        limited = client.get("/limited")
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "http_404"
    assert method.status_code == 405
    assert method.headers["allow"] == "GET"
    assert method.json()["status"] == 405
    assert auth.status_code == 401
    assert auth.headers["www-authenticate"] == "Bearer"
    assert "private token" not in auth.text
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "30"
    for response in (not_found, method, auth, limited):
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["trace_id"] == response.headers["x-request-id"]


def test_request_validation_and_internal_error_hide_inputs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = make_app()
    caplog.set_level(logging.WARNING, logger="pydexception")
    with TestClient(app, raise_server_exceptions=False) as client:
        invalid = client.get("/items/not-an-integer", headers={"Authorization": "secret header"})
        unexpected = client.get("/unexpected", headers={"Authorization": "secret header"})
        body_error = client.post("/body-error", json={"secret": "private request content"})
        internal_validation = client.get("/internal-validation")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "request_validation_error"
    assert invalid.json()["status"] == 422
    assert "not-an-integer" not in invalid.text
    assert unexpected.status_code == 500
    assert unexpected.json()["detail"] == "Internal server error."
    assert "secret" not in unexpected.text
    assert body_error.status_code == 500
    assert "private request content" not in body_error.text
    assert internal_validation.status_code == 500
    assert internal_validation.json()["code"] == "internal_server_error"
    assert "secret" not in caplog.text
    assert "Authorization" not in caplog.text
    assert "private request content" not in caplog.text


def test_provider_ids_are_validated_and_instance_is_optional() -> None:
    app = make_app(
        request_id_provider=lambda request: request.headers.get("x-request-id"),
        instance_provider=lambda request, trace_id: f"urn:uuid:{trace_id}",
    )
    with TestClient(app) as client:
        valid = client.get("/items/1", headers={"X-Request-ID": "trn-valid"})
        invalid = client.get("/items/1", headers={"X-Request-ID": "invalid value"})
    assert valid.json()["trace_id"] == valid.headers["x-request-id"] == "trn-valid"
    assert valid.json()["instance"] == "urn:uuid:trn-valid"
    assert invalid.json()["trace_id"].startswith("trn-")
    assert invalid.json()["trace_id"] != "invalid value"


def test_exception_request_id_header_is_replaced_with_response_id() -> None:
    app = make_app()

    @app.get("/header-conflict")
    def conflict() -> None:
        raise AppException(ITEM_NOT_FOUND, headers={"X-Request-ID": "wrong-id"})

    with TestClient(app) as client:
        response = client.get("/header-conflict")
    assert response.headers["x-request-id"] == response.json()["trace_id"]
    assert response.headers["x-request-id"] != "wrong-id"


def test_mapper_and_custom_renderer_are_used() -> None:
    class LegacyRenderer:
        def render(
            self,
            request: Request,
            error: ResolvedError,
            *,
            trace_id: str,
            instance: str | None,
        ) -> Response:
            del request, instance
            return JSONResponse(
                status_code=error.spec.http_status,
                content={"detail": {"status": str(error.spec.code)}, "trace_id": trace_id},
                headers={"X-Request-ID": "wrong"},
            )

    def map_lookup(exc: Exception) -> AppException | None:
        return AppException(ITEM_NOT_FOUND) if isinstance(exc, LookupError) else None

    app = make_app(renderer=LegacyRenderer(), mappers=[map_lookup])

    @app.get("/lookup")
    def lookup() -> None:
        raise LookupError("private record")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/lookup")
    assert response.status_code == 404
    assert response.json()["detail"]["status"] == "-1001"
    assert response.headers["x-request-id"] == response.json()["trace_id"]
    assert response.headers["content-type"].startswith("application/json")


def test_renderer_failure_falls_back_to_safe_500() -> None:
    class BrokenRenderer:
        def render(
            self,
            request: Request,
            error: ResolvedError,
            *,
            trace_id: str,
            instance: str | None,
        ) -> Response:
            raise ValueError("internal rendering secret")

    app = make_app(renderer=BrokenRenderer())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/items/1")
    assert response.status_code == 500
    assert response.json()["code"] == "internal_server_error"
    assert "secret" not in response.text


def test_renderer_wrong_status_falls_back_to_safe_500() -> None:
    class WrongStatusRenderer:
        def render(
            self,
            request: Request,
            error: ResolvedError,
            *,
            trace_id: str,
            instance: str | None,
        ) -> Response:
            del request, error, trace_id, instance
            return JSONResponse({"detail": "wrong"}, status_code=200)

    app = make_app(renderer=WrongStatusRenderer())
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/items/1")
    assert response.status_code == 500
    assert response.json()["code"] == "internal_server_error"


def test_catalog_is_held_per_app() -> None:
    first = make_app(catalog=ErrorCatalog([ITEM_NOT_FOUND]))
    second = make_app()
    assert first.state.pydexception.catalog.get(-1001) is ITEM_NOT_FOUND
    assert len(second.state.pydexception.catalog) == 0


def test_install_conflicts_and_repeated_install() -> None:
    app = FastAPI()

    @app.exception_handler(StarletteHTTPException)
    async def custom(request: Request, exc: StarletteHTTPException) -> Response:
        return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)

    with pytest.raises(ValueError, match="custom handler"):
        install_exception_handlers(app)
    install_exception_handlers(app, replace=True)
    with pytest.raises(RuntimeError, match="already installed"):
        install_exception_handlers(app)


def test_nonerror_http_exception_uses_fastapi_handler() -> None:
    app = make_app()
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/redirect")
    assert response.status_code == 307
    assert response.headers["location"] == "/items/1"
    assert response.headers["content-type"].startswith("application/json")


def test_route_wrapper_reuses_adapter_for_validation_error() -> None:
    class CatchingRoute(APIRoute):
        def get_route_handler(self):  # type: ignore[no-untyped-def]
            original = super().get_route_handler()

            async def handler(request: Request) -> Response:
                try:
                    return await original(request)
                except Exception as exc:
                    return await request.app.state.pydexception.response_for(request, exc)

            return handler

    class Payload(BaseModel):
        count: int

    router = APIRouter(route_class=CatchingRoute)

    @router.post("/wrapped")
    def wrapped(payload: Payload) -> dict[str, int]:
        return {"count": payload.count}

    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post("/wrapped", json={"count": "wrong"})
    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"


def test_handler_installation_after_first_request_is_rejected() -> None:
    app = FastAPI()
    with TestClient(app) as client:
        assert client.get("/missing").status_code == 404
    with pytest.raises(RuntimeError, match="before the first request"):
        install_exception_handlers(app)
