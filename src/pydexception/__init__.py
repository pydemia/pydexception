"""Typed errors and RFC 9457 responses for FastAPI."""

from .catalog import ErrorCatalog
from .exceptions import AppException
from .fastapi import ExceptionAdapter, install_exception_handlers
from .mapping import ExceptionMapper, ResolvedError, classify_exception
from .models import ErrorCode, ErrorSpec, ProblemDetails
from .openapi import problem_responses
from .renderers import ProblemRenderer, ResponseRenderer

__all__ = [
    "AppException",
    "ErrorCatalog",
    "ErrorCode",
    "ErrorSpec",
    "ExceptionAdapter",
    "ExceptionMapper",
    "ProblemDetails",
    "ProblemRenderer",
    "ResolvedError",
    "ResponseRenderer",
    "classify_exception",
    "install_exception_handlers",
    "problem_responses",
]
