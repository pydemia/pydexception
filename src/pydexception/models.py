"""Validated public error definitions and RFC 9457 response models."""

from __future__ import annotations

import re
from http import HTTPStatus
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ErrorCode = str | int

_URI_CHARACTER = re.compile(r"^(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+$")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")


def validate_uri_reference(value: str) -> str:
    """Validate an ASCII RFC 3986 URI reference used as a problem identifier."""

    if not value or not _URI_CHARACTER.fullmatch(value) or value.count("#") > 1:
        raise ValueError("type URI must be a nonempty URI reference")
    try:
        parts = urlsplit(value)
        if parts.scheme and not _SCHEME.fullmatch(parts.scheme):
            raise ValueError("invalid URI scheme")
        if parts.scheme in {"http", "https"} and not parts.hostname:
            raise ValueError("HTTP type URI requires a host")
        if parts.netloc:
            _ = parts.port
        if not parts.scheme and not value.startswith(("/", "?", "#")):
            first_segment = re.split(r"[/?#]", value, maxsplit=1)[0]
            if ":" in first_segment:
                raise ValueError("relative URI first segment cannot contain a colon")
    except ValueError as exc:
        raise ValueError("type URI must be a valid URI reference") from exc
    return value


class ErrorSpec(BaseModel):
    """Immutable error type owned by the application."""

    model_config = ConfigDict(frozen=True, strict=True)

    code: ErrorCode
    http_status: int = Field(ge=400, le=599)
    type_uri: str
    title: str
    message: str

    @field_validator("code", mode="before")
    @classmethod
    def validate_code(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError("code must be a string or integer, excluding bool")
        if isinstance(value, str) and not value.strip():
            raise ValueError("code must not be blank")
        return value

    @field_validator("type_uri")
    @classmethod
    def validate_type_uri(cls, value: str) -> str:
        return validate_uri_reference(value)

    @field_validator("title", "message")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @model_validator(mode="after")
    def validate_about_blank(self) -> ErrorSpec:
        if self.type_uri == "about:blank":
            try:
                phrase = HTTPStatus(self.http_status).phrase
            except ValueError as exc:
                raise ValueError("about:blank requires a standard HTTP status") from exc
            if self.title != phrase:
                raise ValueError(f"about:blank title must be {phrase!r}")
        return self


class ProblemDetails(BaseModel):
    """RFC 9457 JSON response with stable application extensions."""

    model_config = ConfigDict(frozen=True, strict=True)

    type: str
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    code: ErrorCode
    trace_id: str
    instance: str | None = None

    @field_validator("type", "instance")
    @classmethod
    def validate_uri(cls, value: str | None) -> str | None:
        if value is not None:
            return validate_uri_reference(value)
        return value
