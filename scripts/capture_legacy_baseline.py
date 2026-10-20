"""Capture a synthetic error-response baseline from skax-successionX-backend.

Run this with that backend's Python environment and its repository root on
PYTHONPATH. It makes only in-process TestClient requests with synthetic input.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from shared.exception.exception_handlers import set_global_exception_handlers
from shared.exception.exceptions import HandledException
from shared.exception.types.error_catalog import ErrorCatalog
from shared.logging.routes import RequestLoggingRoute

logging.disable(logging.CRITICAL)


class Item(BaseModel):
    count: int


router = APIRouter(route_class=RequestLoggingRoute)


@router.post("/items")
def create_item(item: Item) -> None:
    raise HandledException(ErrorCatalog.ENTITY_NOT_FOUND.value)


@router.get("/protected")
def protected() -> None:
    raise HTTPException(401, detail="synthetic denial", headers={"WWW-Authenticate": "Bearer"})


app = FastAPI()
app.include_router(router)
set_global_exception_handlers(app)


def summarize(label: str, response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    detail = body.get("detail")
    headers = response.headers  # type: ignore[attr-defined]
    return {
        "case": label,
        "http_status": response.status_code,  # type: ignore[attr-defined]
        "body_keys": sorted(body),
        "body_detail_status": detail.get("status") if isinstance(detail, dict) else None,
        "body_detail_status_type": (
            type(detail.get("status")).__name__ if isinstance(detail, dict) else None
        ),
        "body_detail_title": detail.get("title") if isinstance(detail, dict) else None,
        "body_detail_text": detail.get("detail") if isinstance(detail, dict) else detail,
        "body_detail_instance": detail.get("instance") if isinstance(detail, dict) else None,
        "body_detail_keys": sorted(detail) if isinstance(detail, dict) else None,
        "body_timestamp_type": type(body.get("timestamp")).__name__,
        "body_data_is_null": body.get("data") is None,
        "body_payload_is_null": body.get("payload") is None,
        "body_trace_prefix": str(body.get("trace_id", "")).split("-", 1)[0],
        "header_request_id_prefix": str(headers.get("x-request-id", "")).split("-", 1)[0],
        "content_type": headers.get("content-type"),
        "www_authenticate": headers.get("www-authenticate"),
        "allow": headers.get("allow"),
        "has_request_time_header": "x-request-time" in headers,
        "has_response_duration_header": "x-response-duration" in headers,
    }


with TestClient(app, raise_server_exceptions=False) as client:
    cases = (
        ("route_validation", client.post("/items", json={"count": "wrong"})),
        ("route_not_found_code", client.post("/items", json={"count": 1})),
        ("route_http_401", client.get("/protected")),
        ("unmatched_404", client.get("/missing")),
        ("method_405", client.post("/protected")),
    )
    for label, response in cases:
        print(json.dumps(summarize(label, response), ensure_ascii=False))
