"""Cliente HTTP genérico para cualquier API REST, con auth configurable
(none/basic/bearer/api_key) y protección contra SSRF incorporada.

Capacidades:
- get() / post() / put() / delete():  verbos HTTP estándar.
- request():                          verbo arbitrario (ej. PATCH).

Diseño de seguridad (SSRF):
- El conector está atado a UN dominio configurado (base_url), no a
  "cualquier URL" que se decida en tiempo de ejecución. Las rutas
  relativas ("/algo") siempre se resuelven contra ese dominio.
- Si se pasa una URL absoluta distinta al dominio configurado, se
  rechaza salvo que ese dominio esté explícitamente en `allowed_domains`.
- Por defecto se bloquean IPs privadas/loopback/link-local (incluye el
  endpoint de metadata de nube 169.254.169.254), salvo que el admin
  active `allow_private_networks` explícitamente al configurar el
  conector (uso legítimo: integraciones con sistemas internos).

Diseño de errores (distinto a los conectores de un solo proveedor):
- Una respuesta HTTP 4xx/5xx de la API destino NO lanza una excepción:
  es una respuesta legítima que el llamador debe inspeccionar via
  `status_code`/`ok`. Solo se lanzan excepciones por fallos de red,
  configuración inválida, o destinos bloqueados por seguridad.

Autenticación: las credenciales SIEMPRE provienen de variables de
entorno RUVIC_HTTP_GENERIC_* (ver config.HttpGenericConfig.from_env).
Prohibido hardcodearlas.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from .config import HttpGenericConfig
from .exceptions import (
    HttpGenericConfigError,
    HttpGenericNetworkError,
    HttpGenericSecurityError,
)
from .logging_utils import get_logger


def _hostname_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_private_or_reserved(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # si no se puede interpretar, se trata como no seguro
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


class HttpGenericClient:
    """Cliente HTTP genérico atado a una API destino configurada.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_HTTP_GENERIC_* (comportamiento
            estándar en el runtime de la plataforma).

    Ejemplo:
        >>> client = HttpGenericClient()  # lee RUVIC_HTTP_GENERIC_* del entorno
        >>> client.get("/users/42")
        {'status_code': 200, 'ok': True, 'json': {...}, 'text': None, 'headers': {...}, 'url': '...'}
    """

    def __init__(self, config: HttpGenericConfig | None = None) -> None:
        self.config = config or HttpGenericConfig.from_env()
        self._logger = get_logger()
        self._base_host = _hostname_of(self.config.base_url)
        if not self._base_host:
            raise HttpGenericConfigError(f"No se pudo interpretar el host de base_url: {self.config.base_url!r}")

    # ------------------------------------------------------------------ #
    # Resolución y validación de URL (protección SSRF)
    # ------------------------------------------------------------------ #

    def _resolve_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = urljoin(self.config.base_url + "/", path_or_url.lstrip("/"))
        self._validate_destination(url)
        return url

    def _validate_destination(self, url: str) -> None:
        host = _hostname_of(url)
        if not host:
            raise HttpGenericSecurityError(f"No se pudo interpretar el host de la URL: {url!r}")

        allowed_hosts = {self._base_host, *self.config.allowed_domains}
        if host not in allowed_hosts:
            raise HttpGenericSecurityError(
                f"Destino no permitido: {host!r}. Este conector solo puede llamar a "
                f"{self._base_host!r}" + (
                    f" o a los dominios adicionales autorizados: {', '.join(self.config.allowed_domains)}"
                    if self.config.allowed_domains else ""
                ) + ". Si necesitas llamar a otro dominio, agrégalo a allowed_domains en la configuración."
            )

        if not self.config.allow_private_networks:
            try:
                infos = socket.getaddrinfo(host, None)
            except socket.gaierror as exc:
                raise HttpGenericNetworkError(f"No se pudo resolver el host {host!r}: {exc}") from exc
            for info in infos:
                ip_str = info[4][0]
                if _is_private_or_reserved(ip_str):
                    raise HttpGenericSecurityError(
                        f"Destino bloqueado por seguridad: {host!r} resuelve a una dirección "
                        f"privada/interna ({ip_str}). Esto incluye redes internas y el endpoint "
                        "de metadata de la nube. Si es un uso interno legítimo, activa "
                        "'allow_private_networks' explícitamente en la configuración del conector."
                    )

    # ------------------------------------------------------------------ #
    # Autenticación
    # ------------------------------------------------------------------ #

    def _apply_auth(self, headers: dict[str, str], params: dict[str, Any]) -> tuple:
        auth_mode = self.config.auth_mode
        http_auth = None

        if auth_mode == "basic":
            http_auth = (self.config.username, self.config.password)
        elif auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        elif auth_mode == "api_key":
            if self.config.api_key_location == "header":
                headers[self.config.api_key_name] = self.config.api_key_value
            else:
                params[self.config.api_key_name] = self.config.api_key_value

        return headers, params, http_auth

    # ------------------------------------------------------------------ #
    # Petición central
    # ------------------------------------------------------------------ #

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición HTTP con el verbo indicado.

        Args:
            method: verbo HTTP (GET, POST, PUT, DELETE, PATCH...).
            path: ruta relativa (ej. "/users/42") o URL absoluta dentro
                del dominio permitido.
            params: query params.
            json_body: cuerpo a serializar como JSON.
            data: cuerpo crudo (form-encoded, texto, etc.) — ignorado si
                se pasa json_body.
            headers: headers adicionales para esta llamada (se combinan
                con default_headers y los de autenticación).

        Returns:
            Dict con "status_code", "ok", "json" (o None si la respuesta
            no es JSON), "text" (solo si no es JSON), "headers", "url".
            NO lanza excepción por códigos 4xx/5xx — inspecciona "status_code".

        Ejemplo:
            >>> client.request("GET", "/users", params={"active": "true"})
            {'status_code': 200, 'ok': True, 'json': [...], ...}
        """
        url = self._resolve_url(path)

        req_headers = dict(self.config.default_headers)
        if headers:
            req_headers.update(headers)
        req_params = dict(params or {})
        req_headers, req_params, http_auth = self._apply_auth(req_headers, req_params)

        kwargs: dict[str, Any] = {"params": req_params, "headers": req_headers, "timeout": self.config.timeout}
        if http_auth:
            kwargs["auth"] = http_auth
        if json_body is not None:
            kwargs["json"] = json_body
        elif data is not None:
            kwargs["data"] = data

        try:
            resp = requests.request(method.upper(), url, **kwargs)
        except Timeout as exc:
            raise HttpGenericNetworkError(
                f"Tiempo de espera agotado ({self.config.timeout}s) llamando a {url}."
            ) from exc
        except RequestsConnectionError as exc:
            raise HttpGenericNetworkError(f"No se pudo conectar a {url}: {exc}") from exc
        except RequestException as exc:
            raise HttpGenericNetworkError(f"Error de red llamando a {url}: {exc}") from exc

        parsed_json = None
        text = None
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type.lower():
            try:
                parsed_json = resp.json()
            except ValueError:
                text = resp.text
        else:
            text = resp.text

        self._logger.info("%s %s -> HTTP %s", method.upper(), url, resp.status_code)
        return {
            "status_code": resp.status_code,
            "ok": resp.ok,
            "json": parsed_json,
            "text": text,
            "headers": dict(resp.headers),
            "url": resp.url,
        }

    # ------------------------------------------------------------------ #
    # Verbos HTTP estándar
    # ------------------------------------------------------------------ #

    def get(
        self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Petición GET. Ver request() para el formato del resultado."""
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        json_body: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Petición POST. Ver request() para el formato del resultado."""
        return self.request("POST", path, params=params, json_body=json_body, data=data, headers=headers)

    def put(
        self,
        path: str,
        json_body: Any | None = None,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Petición PUT. Ver request() para el formato del resultado."""
        return self.request("PUT", path, params=params, json_body=json_body, data=data, headers=headers)

    def delete(
        self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Petición DELETE. Ver request() para el formato del resultado.

        ⚠️ A diferencia de los demás conectores de Ruvic, este SÍ ejecuta
        eliminaciones reales si la API destino lo soporta en esa ruta —
        es responsabilidad del agente/usuario confirmar antes de llamarlo
        sobre datos que importen.
        """
        return self.request("DELETE", path, params=params, headers=headers)

    # ------------------------------------------------------------------ #
    # Ping / prueba de conexión
    # ------------------------------------------------------------------ #

    def ping(self) -> bool:
        """Verifica que el host configurado sea alcanzable.

        Cualquier respuesta HTTP (incluido un 404) cuenta como éxito —
        solo falla por problemas de red o de configuración de seguridad.
        """
        result = self.request("GET", "/")
        self._logger.info("Ping a %s -> HTTP %s", self.config.base_url, result["status_code"])
        return True
