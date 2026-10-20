"""Explicit OpenAPI problem response declarations for FastAPI routes."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import ErrorSpec, ProblemDetails


def problem_responses(*specs: ErrorSpec) -> dict[int | str, dict[str, Any]]:
    """Build FastAPI's `responses` argument, grouping errors by HTTP status."""

    grouped: dict[int, list[ErrorSpec]] = defaultdict(list)
    for spec in specs:
        grouped[spec.http_status].append(spec)

    result: dict[int | str, dict[str, Any]] = {}
    for status, status_specs in grouped.items():
        examples: dict[str, dict[str, Any]] = {}
        for spec in status_specs:
            name = f"{type(spec.code).__name__}_{spec.code}"
            if name in examples:
                raise ValueError(f"duplicate error code in OpenAPI responses: {spec.code!r}")
            examples[name] = {
                "summary": spec.title,
                "value": ProblemDetails(
                    type=spec.type_uri,
                    title=spec.title,
                    status=spec.http_status,
                    detail=spec.message,
                    code=spec.code,
                    trace_id="trn-example",
                ).model_dump(exclude_none=True),
            }
        result[status] = {
            "description": ", ".join(spec.title for spec in status_specs),
            "content": {
                "application/problem+json": {
                    "schema": ProblemDetails.model_json_schema(),
                    "examples": examples,
                }
            },
        }
    return result
