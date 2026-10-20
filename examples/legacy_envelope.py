"""Illustrative service adapter; compare exact fields with the real service first."""

from datetime import datetime, timezone

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pydexception import (
    AppException,
    ErrorSpec,
    ResolvedError,
    install_exception_handlers,
)


class LegacyEnvelopeRenderer:
    def render(
        self,
        request: Request,
        error: ResolvedError,
        *,
        trace_id: str,
        instance: str | None,
    ) -> Response:
        del instance
        return JSONResponse(
            status_code=error.spec.http_status,
            content={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": {
                    "type": error.spec.type_uri,
                    "title": error.spec.title,
                    "status": str(error.spec.code),
                    "detail": error.detail,
                    "instance": request.url.path,
                    "system_message": None,
                },
                "trace_id": trace_id,
                "data": None,
                "payload": None,
            },
        )


# The old service returns HTTP 500 for this code unless the caller overrides it.
LEGACY_ENTITY_NOT_FOUND = ErrorSpec(
    code=-1001,
    http_status=500,
    type_uri="https://api.example.com/problems/entity-not-found",
    title="Entity Not Found",
    message="Entity not found.",
)

app = FastAPI()
install_exception_handlers(app, renderer=LegacyEnvelopeRenderer())


@app.get("/entities/{entity_id}")
def get_entity(entity_id: int) -> None:
    raise AppException(LEGACY_ENTITY_NOT_FOUND, detail=f"Entity {entity_id} not found.")
