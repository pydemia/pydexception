from __future__ import annotations

from fastapi.testclient import TestClient

from examples.catalog_app import ERRORS
from examples.catalog_app import app as catalog_app
from examples.legacy_envelope import app as legacy_app
from examples.route_wrapper import app as wrapped_app


def test_legacy_example_preserves_string_code_and_old_http_status() -> None:
    with TestClient(legacy_app) as client:
        response = client.get("/entities/42")
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]["status"] == "-1001"


def test_route_wrapper_example_handles_validation() -> None:
    with TestClient(wrapped_app) as client:
        response = client.post("/wrapped", json={"count": "wrong"})
    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"


def test_catalog_example_registers_multiple_codes() -> None:
    assert len(ERRORS) == 3
    assert {spec.code for spec in ERRORS} == {-1001, -1002, -2001}
    with TestClient(catalog_app, raise_server_exceptions=False) as client:
        response = client.get("/entities/42")
    assert response.status_code == 500
    assert response.json()["code"] == -1001
