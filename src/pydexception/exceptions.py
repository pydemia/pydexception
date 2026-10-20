"""Application exception independent of FastAPI's HTTPException."""

from __future__ import annotations

import re
from collections.abc import Mapping
from types import MappingProxyType

from .models import ErrorSpec

_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


def validated_headers(headers: Mapping[str, str] | None) -> Mapping[str, str]:
    result: dict[str, str] = {}
    for name, value in (headers or {}).items():
        if not isinstance(name, str) or not _HEADER_NAME.fullmatch(name):
            raise ValueError("invalid response header name")
        if not isinstance(value, str) or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("invalid response header value")
        try:
            value.encode("latin-1")
        except UnicodeEncodeError as exc:
            raise ValueError("response header must be Latin-1 encodable") from exc
        result[name] = value
    return MappingProxyType(result)


class AppException(Exception):
    """Raise a declared error with an optional safe request-specific detail."""

    def __init__(
        self,
        spec: ErrorSpec,
        *,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(spec, ErrorSpec):
            raise TypeError("spec must be an ErrorSpec")
        if detail is not None and (not isinstance(detail, str) or not detail.strip()):
            raise ValueError("detail must be a nonblank string")
        self.spec = spec
        self.detail = detail
        self.headers = validated_headers(headers)
        super().__init__(detail if detail is not None else spec.message)
