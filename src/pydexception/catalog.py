"""Application-scoped error definition catalog."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from urllib.parse import urlsplit

from .models import ErrorCode, ErrorSpec


@dataclass(frozen=True, slots=True)
class ErrorCatalog:
    """An immutable index of error definitions keyed by application code."""

    _by_code: Mapping[ErrorCode, ErrorSpec]

    def __init__(self, specs: Iterable[ErrorSpec] = ()) -> None:
        by_code: dict[ErrorCode, ErrorSpec] = {}
        by_type: dict[str, ErrorSpec] = {}
        for spec in specs:
            if spec.code in by_code:
                raise ValueError(f"duplicate error code: {spec.code!r}")
            if spec.type_uri != "about:blank" and urlsplit(spec.type_uri).scheme:
                prior = by_type.get(spec.type_uri)
                if prior is not None and (
                    prior.title != spec.title or prior.http_status != spec.http_status
                ):
                    raise ValueError(f"conflicting definitions for type URI: {spec.type_uri}")
                by_type[spec.type_uri] = spec
            by_code[spec.code] = spec
        object.__setattr__(self, "_by_code", MappingProxyType(by_code))

    def get(self, code: ErrorCode) -> ErrorSpec:
        if isinstance(code, bool):
            raise KeyError(code)
        return self._by_code[code]

    def __iter__(self) -> Iterator[ErrorSpec]:
        return iter(self._by_code.values())

    def __len__(self) -> int:
        return len(self._by_code)

    def __contains__(self, code: object) -> bool:
        if isinstance(code, bool):
            return False
        return code in self._by_code
