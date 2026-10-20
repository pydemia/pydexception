"""Runnable FastAPI example: uvicorn examples.minimal_app:app."""

from fastapi import FastAPI

from pydexception import AppException, ErrorSpec, install_exception_handlers, problem_responses

ITEM_NOT_FOUND = ErrorSpec(
    code="item_not_found",
    http_status=404,
    type_uri="https://api.example.com/problems/item-not-found",
    title="Item Not Found",
    message="Item not found.",
)

app = FastAPI()
install_exception_handlers(app)


@app.get("/items/{item_id}", responses=problem_responses(ITEM_NOT_FOUND))
def get_item(item_id: int) -> dict[str, int]:
    if item_id != 1:
        raise AppException(ITEM_NOT_FOUND)
    return {"id": item_id}
