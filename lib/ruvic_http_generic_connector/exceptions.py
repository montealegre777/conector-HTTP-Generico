"""Excepciones propias del conector HTTP genérico.

Separan los tipos de fallo que el usuario debe distinguir: configuración
inválida, red, y destino bloqueado por seguridad (SSRF). A diferencia de
los conectores de un solo proveedor (Salesforce, HubSpot...), las
respuestas HTTP de error (4xx/5xx) de la API destino NO son excepciones
aquí — son respuestas legítimas que el llamador debe inspeccionar.
"""


class HttpGenericConnectorError(Exception):
    """Error base del conector."""


class HttpGenericConfigError(HttpGenericConnectorError):
    """Configuración inválida: falta base_url, falta una credencial
    requerida por el auth_mode elegido, o el auth_mode no es válido."""


class HttpGenericNetworkError(HttpGenericConnectorError):
    """No se pudo alcanzar el host (DNS, timeout, TLS, conexión rechazada)."""


class HttpGenericSecurityError(HttpGenericConnectorError):
    """La petición fue bloqueada por una protección de seguridad: el
    destino está fuera del dominio permitido, o apunta a una dirección
    privada/interna/de metadata de nube no autorizada explícitamente."""
