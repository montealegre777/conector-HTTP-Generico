"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_HTTP_GENERIC_.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

ENV_PREFIX = "RUVIC_HTTP_GENERIC_"

_VALID_AUTH_MODES = ("none", "basic", "bearer", "api_key")
_VALID_API_KEY_LOCATIONS = ("header", "query")


@dataclass(frozen=True)
class HttpGenericConfig:
    """Parámetros de conexión de un conector HTTP genérico apuntando a
    UNA API destino configurada (no a URLs arbitrarias por llamada)."""

    base_url: str
    auth_mode: str = "none"
    username: str = ""
    password: str = ""
    bearer_token: str = ""
    api_key_name: str = ""
    api_key_value: str = ""
    api_key_location: str = "header"
    default_headers: dict = field(default_factory=dict)
    allowed_domains: tuple = ()
    allow_private_networks: bool = False
    timeout: int = 20

    @classmethod
    def from_env(cls) -> "HttpGenericConfig":
        """Construye la configuración desde las variables RUVIC_HTTP_GENERIC_*.

        Raises:
            ValueError: si falta base_url, el auth_mode no es válido, o
                faltan las credenciales requeridas por el auth_mode elegido.
        """
        base_url = os.environ.get(f"{ENV_PREFIX}BASE_URL", "").strip()
        if not base_url:
            raise ValueError(
                f"Falta la variable de entorno del conector http_generic: "
                f"{ENV_PREFIX}BASE_URL. Configura el conector en Settings → Conectores."
            )
        if not (base_url.startswith("https://") or base_url.startswith("http://")):
            raise ValueError(
                f"{ENV_PREFIX}BASE_URL debe incluir el esquema (https:// o http://): {base_url!r}"
            )

        auth_mode = os.environ.get(f"{ENV_PREFIX}AUTH_MODE", "none").strip().lower()
        if auth_mode not in _VALID_AUTH_MODES:
            raise ValueError(
                f"{ENV_PREFIX}AUTH_MODE inválido: {auth_mode!r}. "
                f"Debe ser uno de: {', '.join(_VALID_AUTH_MODES)}."
            )

        username = os.environ.get(f"{ENV_PREFIX}USERNAME", "")
        password = os.environ.get(f"{ENV_PREFIX}PASSWORD", "")
        bearer_token = os.environ.get(f"{ENV_PREFIX}BEARER_TOKEN", "")
        api_key_name = os.environ.get(f"{ENV_PREFIX}API_KEY_NAME", "")
        api_key_value = os.environ.get(f"{ENV_PREFIX}API_KEY_VALUE", "")
        api_key_location = os.environ.get(f"{ENV_PREFIX}API_KEY_LOCATION", "header").strip().lower()

        if auth_mode == "basic" and (not username or not password):
            raise ValueError(f"auth_mode 'basic' requiere {ENV_PREFIX}USERNAME y {ENV_PREFIX}PASSWORD.")
        if auth_mode == "bearer" and not bearer_token:
            raise ValueError(f"auth_mode 'bearer' requiere {ENV_PREFIX}BEARER_TOKEN.")
        if auth_mode == "api_key":
            if not api_key_name or not api_key_value:
                raise ValueError(
                    f"auth_mode 'api_key' requiere {ENV_PREFIX}API_KEY_NAME y {ENV_PREFIX}API_KEY_VALUE."
                )
            if api_key_location not in _VALID_API_KEY_LOCATIONS:
                raise ValueError(
                    f"{ENV_PREFIX}API_KEY_LOCATION inválido: {api_key_location!r}. "
                    f"Debe ser uno de: {', '.join(_VALID_API_KEY_LOCATIONS)}."
                )

        headers_raw = os.environ.get(f"{ENV_PREFIX}DEFAULT_HEADERS", "").strip()
        default_headers = {}
        if headers_raw:
            try:
                parsed = json.loads(headers_raw)
                if not isinstance(parsed, dict):
                    raise ValueError("debe ser un objeto JSON de {clave: valor}")
                default_headers = {str(k): str(v) for k, v in parsed.items()}
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(
                    f"{ENV_PREFIX}DEFAULT_HEADERS no es JSON válido: {exc}"
                ) from exc

        allowed_domains_raw = os.environ.get(f"{ENV_PREFIX}ALLOWED_DOMAINS", "").strip()
        allowed_domains = tuple(
            d.strip().lower() for d in allowed_domains_raw.split(",") if d.strip()
        )

        allow_private_raw = os.environ.get(f"{ENV_PREFIX}ALLOW_PRIVATE_NETWORKS", "false").strip().lower()

        return cls(
            base_url=base_url.rstrip("/"),
            auth_mode=auth_mode,
            username=username,
            password=password,
            bearer_token=bearer_token,
            api_key_name=api_key_name,
            api_key_value=api_key_value,
            api_key_location=api_key_location,
            default_headers=default_headers,
            allowed_domains=allowed_domains,
            allow_private_networks=allow_private_raw in ("true", "1", "yes"),
            timeout=int(os.environ.get(f"{ENV_PREFIX}REQUEST_TIMEOUT", "20")),
        )
