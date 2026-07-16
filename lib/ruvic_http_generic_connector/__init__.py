"""Conector Ruvic HTTP genérico para cualquier API REST."""

from .client import HttpGenericClient
from .config import ENV_PREFIX, HttpGenericConfig
from .exceptions import (
    HttpGenericConfigError,
    HttpGenericConnectorError,
    HttpGenericNetworkError,
    HttpGenericSecurityError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "HttpGenericClient",
    "HttpGenericConfig",
    "HttpGenericConfigError",
    "HttpGenericConnectorError",
    "HttpGenericNetworkError",
    "HttpGenericSecurityError",
    "setup_logging",
]

__version__ = "1.0.0"
