from __future__ import annotations

from dataclasses import FrozenInstanceError
from http import HTTPStatus

import pytest
from pydantic import ValidationError

from pydexception import AppException, ErrorCatalog, ErrorSpec


def spec(**changes: object) -> ErrorSpec:
    values: dict[str, object] = {
        "code": -1001,
        "http_status": 404,
        "type_uri": "https://api.example.com/problems/missing",
        "title": "Missing",
        "message": "An item is missing.",
    }
    values.update(changes)
    return ErrorSpec.model_validate(values)


@pytest.mark.parametrize(
    "value",
    [
        "https://api.example.com/problems/missing",
        "urn:example:missing",
        "/problems/missing",
        "about:blank",
    ],
)
def test_type_uri_accepts_uri_references(value: str) -> None:
    title = HTTPStatus(404).phrase if value == "about:blank" else "Missing"
    assert spec(type_uri=value, title=title).type_uri == value


@pytest.mark.parametrize(
    "value",
    ["", "has a space", "https://", "https://api.example.com:invalid/a", "bad%zz", "a#b#c"],
)
def test_type_uri_rejects_invalid_references(value: str) -> None:
    with pytest.raises(ValidationError):
        spec(type_uri=value)


@pytest.mark.parametrize("value", [True, False, "", "   ", 1.5, None])
def test_code_rejects_ambiguous_values(value: object) -> None:
    with pytest.raises(ValidationError):
        spec(code=value)


@pytest.mark.parametrize("value", [399, 600, True, "404"])
def test_http_status_is_a_strict_error_status(value: object) -> None:
    with pytest.raises(ValidationError):
        spec(http_status=value)


def test_about_blank_title_follows_status() -> None:
    with pytest.raises(ValidationError):
        spec(type_uri="about:blank", title="Missing")


def test_spec_is_frozen() -> None:
    item = spec()
    with pytest.raises(ValidationError):
        item.message = "Changed"  # type: ignore[misc]


def test_catalog_checks_codes_and_shared_type_contract() -> None:
    first = spec()
    second = spec(code=-1002, message="Another missing item.")
    catalog = ErrorCatalog([first, second])
    assert len(catalog) == 2
    assert catalog.get(-1001) is first
    assert -1002 in catalog
    with pytest.raises(ValueError, match="duplicate error code"):
        ErrorCatalog([first, first])
    with pytest.raises(ValueError, match="conflicting definitions"):
        ErrorCatalog([first, spec(code=-1002, title="Other")])
    with pytest.raises(ValueError, match="conflicting definitions"):
        ErrorCatalog([first, spec(code=-1002, http_status=409)])
    with pytest.raises(FrozenInstanceError):
        catalog._by_code = {}  # type: ignore[misc]


def test_about_blank_catalog_allows_different_statuses() -> None:
    catalog = ErrorCatalog(
        [
            spec(type_uri="about:blank", title=HTTPStatus(404).phrase),
            spec(
                code="bad_request",
                http_status=400,
                type_uri="about:blank",
                title=HTTPStatus(400).phrase,
            ),
        ]
    )
    assert len(catalog) == 2


def test_bool_does_not_find_integer_code() -> None:
    catalog = ErrorCatalog([spec(code=1)])
    assert True not in catalog
    with pytest.raises(KeyError):
        catalog.get(True)


def test_app_exception_copies_and_validates_headers() -> None:
    headers = {"Retry-After": "30"}
    error = AppException(spec(), detail="Item 42 is missing.", headers=headers)
    headers["Retry-After"] = "60"
    assert error.headers["Retry-After"] == "30"
    with pytest.raises(TypeError):
        error.headers["Retry-After"] = "60"  # type: ignore[index]
    with pytest.raises(ValueError):
        AppException(spec(), detail=" ")
    with pytest.raises(ValueError):
        AppException(spec(), headers={"X-Test": "bad\r\nInjected: 1"})
