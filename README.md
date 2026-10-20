# pydexception

FastAPI applications can define typed errors with Pydantic 2 and return RFC 9457 Problem Details responses. Application error codes are separate from HTTP status codes.

## Install

From this checkout, install an editable copy with `pip install -e .` or build a wheel with `uv build` and install the wheel. This repository has not been published as a package release.

## Minimal application

```python
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
```

A missing item returns HTTP 404 with `Content-Type: application/problem+json`:

```json
{
  "type": "https://api.example.com/problems/item-not-found",
  "title": "Item Not Found",
  "status": 404,
  "detail": "Item not found.",
  "code": "item_not_found",
  "trace_id": "trn-..."
}
```

`AppException(spec, detail="...")` replaces the default public `detail` for that occurrence. Internal exception text is not included in the response. A chained cause can be kept with `raise AppException(spec) from exc`.

## Managing error codes

Keep error definitions in the service that owns them. Group them by domain, then assemble one app catalog so code collisions fail during startup:

```python
ENTITY_ERRORS = (ENTITY_NOT_FOUND, ENTITY_ALREADY_EXISTS)
AUTH_ERRORS = (ACCESS_DENIED,)
ERRORS = ErrorCatalog([*ENTITY_ERRORS, *AUTH_ERRORS])

install_exception_handlers(app, catalog=ERRORS)
raise AppException(ERRORS.get(-1001))
```

The [catalog example](examples/catalog_app.py) defines `-1001`, `-1002`, and `-2001` with their messages and HTTP statuses. Treat each `code` as a stable public identifier: document its meaning, do not reuse it for a different error, and keep `http_status` as a separate field. For compatibility with the referenced backend, the example maps `-1001` to HTTP 500; changing it to 404 is an explicit API contract change.

The catalog detects duplicates among its registered definitions. Registration is currently organizational: `AppException` can still receive an unregistered `ErrorSpec`, so a service that requires every code to be registered should consistently raise errors through `ERRORS.get(code)` and review direct `ErrorSpec` uses.

## Behavior and integration

- Register application definitions with `ErrorCatalog([...])` and pass it to `install_exception_handlers(app, catalog=catalog)` to keep the catalog with that app and reject duplicate codes. `AppException` also accepts an unregistered `ErrorSpec`; duplicate detection then applies only to definitions explicitly included in the catalog.
- The default handler returns 422 for FastAPI request validation errors, preserves valid `HTTPException` headers, and returns a generic 500 response for unexpected errors. The default does not expose the original `HTTPException.detail`; set `expose_http_detail=True` only when 4xx details are intended to be public.
- The generated `trace_id` is also set in the `X-Request-ID` response header. An application can supply `request_id_provider` to use its validated request context. An `X-Request-ID` carried by an exception is replaced with the response ID.
- `instance_provider` may supply a URI reference identifying an individual problem occurrence. Without it, `instance` is absent.
- The return value of `install_exception_handlers` is an `ExceptionAdapter`. A custom `APIRoute` that catches errors before FastAPI's global handlers can call `await adapter.response_for(request, exc)` to use the same conversion.
- A service can supply exception `mappers` and a `ResponseRenderer` for its own exceptions and response envelope. A renderer must return the resolved HTTP status. Its integration should compare both HTTP status and body fields against the existing API contract.

Install handlers before the application serves its first request. Registering over a service's custom handler requires `replace=True`. WebSocket, already started streaming responses, and background task failures are outside the HTTP response conversion contract.

For an executable application and integration examples, see [examples](examples/). For implementation and migration boundaries, see [the plan](docs/implementation-plan.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
