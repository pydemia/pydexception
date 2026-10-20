"""An APIRoute can reuse the installed adapter when it catches errors first."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

from pydexception import ExceptionAdapter, install_exception_handlers


class HandlingRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await original(request)
            except Exception as exc:
                adapter: ExceptionAdapter = request.app.state.pydexception
                return await adapter.response_for(request, exc)

        return handle


class Input(BaseModel):
    count: int


router = APIRouter(route_class=HandlingRoute)


@router.post("/wrapped")
def wrapped(body: Input) -> dict[str, int]:
    return {"count": body.count}


app = FastAPI()
install_exception_handlers(app)
app.include_router(router)
