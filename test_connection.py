"""Prueba de conexión estándar del conector http_generic.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_HTTP_GENERIC_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica que el host configurado en base_url sea alcanzable."""
    try:
        from ruvic_http_generic_connector import (
            HttpGenericClient,
            HttpGenericConfigError,
            HttpGenericNetworkError,
            HttpGenericSecurityError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-http-generic-connector no está instalada. "
            "Instala con: pip install git+https://github.com/tu-org/"
            "conector-http-generico.git#subdirectory=lib",
        )

    try:
        client = HttpGenericClient()  # valida config y credenciales del auth_mode elegido
    except (ValueError, HttpGenericConfigError) as exc:
        return False, str(exc)

    try:
        client.ping()
    except HttpGenericNetworkError as exc:
        return False, f"Error de red: {exc}"
    except HttpGenericSecurityError as exc:
        return False, f"Bloqueado por seguridad: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a {client.config.base_url} (auth_mode={client.config.auth_mode})"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
