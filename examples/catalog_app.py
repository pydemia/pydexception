"""Organize service-owned error codes: uvicorn examples.catalog_app:app."""

from fastapi import FastAPI

from pydexception import AppException, ErrorCatalog, ErrorSpec, install_exception_handlers

ENTITY_ERRORS = (
    ErrorSpec(
        code=-1001,
        http_status=500,
        type_uri="https://api.example.com/problems/entity-not-found",
        title="Entity Not Found",
        message="Entity not found.",
    ),
    ErrorSpec(
        code=-1002,
        http_status=409,
        type_uri="https://api.example.com/problems/entity-already-exists",
        title="Entity Already Exists",
        message="Entity already exists.",
    ),
)

AUTH_ERRORS = (
    ErrorSpec(
        code=-2001,
        http_status=403,
        type_uri="https://api.example.com/problems/access-denied",
        title="Access Denied",
        message="Access denied.",
    ),
)

# Building the app catalog checks duplicate codes across domain groups.
ERRORS = ErrorCatalog([*ENTITY_ERRORS, *AUTH_ERRORS])

app = FastAPI()
install_exception_handlers(app, catalog=ERRORS)


@app.get("/entities/{entity_id}")
def get_entity(entity_id: int) -> None:
    raise AppException(ERRORS.get(-1001), detail=f"Entity {entity_id} not found.")
