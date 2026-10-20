from __future__ import annotations

from fastapi import FastAPI

from pydexception import ErrorSpec, problem_responses


def spec(code: str, status: int) -> ErrorSpec:
    return ErrorSpec(
        code=code,
        http_status=status,
        type_uri=f"https://api.example.com/problems/{code}",
        title=code.replace("_", " ").title(),
        message="A public explanation.",
    )


def test_openapi_declares_problem_media_type_and_grouped_examples() -> None:
    missing = spec("missing", 404)
    hidden = spec("hidden", 404)
    app = FastAPI()

    @app.get("/items", responses=problem_responses(missing, hidden))
    def items() -> dict[str, list[str]]:
        return {"items": []}

    response = app.openapi()["paths"]["/items"]["get"]["responses"]["404"]
    assert set(response["content"]) == {"application/problem+json"}
    problem = response["content"]["application/problem+json"]
    assert set(problem["examples"]) == {"str_missing", "str_hidden"}
    assert problem["examples"]["str_missing"]["value"]["status"] == 404
    assert problem["schema"]["properties"]["code"]


def test_openapi_keeps_integer_and_string_codes_distinct() -> None:
    integer = spec("1", 404).model_copy(update={"code": 1})
    string = spec("1", 404)
    examples = problem_responses(integer, string)[404]["content"]["application/problem+json"][
        "examples"
    ]
    assert set(examples) == {"int_1", "str_1"}
