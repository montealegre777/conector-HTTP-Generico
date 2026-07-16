---
name: http-generic
description: Usa la librería ruvic_http_generic_connector para hacer peticiones HTTP a la API REST configurada para este conector - GET, POST, PUT, DELETE, y verbos arbitrarios vía request(). Úsala cuando el usuario pida integrarse con una API externa que no tiene un conector dedicado en Ruvic (no es Salesforce, HubSpot, GitHub, SAP...). El conector está atado a UN dominio configurado; no puede llamar a cualquier URL arbitraria.
triggers:
- api rest
- llamar api
- petición http
- webhook
- integración genérica
---

# Conector HTTP Genérico (ruvic_http_generic_connector)

Librería Python para hacer peticiones a **una API REST específica ya configurada** (no a cualquier URL que se te ocurra en el momento). Cada instancia de este conector está atada a un `base_url` fijo, definido cuando se configuró en Ruvic. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/tu-org/conector-http-generico.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `http_generic` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_HTTP_GENERIC_BASE_URL` | URL base de la API destino |
| `RUVIC_HTTP_GENERIC_AUTH_MODE` | `none`, `basic`, `bearer` o `api_key` |
| `RUVIC_HTTP_GENERIC_USERNAME` / `..._PASSWORD` | (si auth_mode=basic) |
| `RUVIC_HTTP_GENERIC_BEARER_TOKEN` | (si auth_mode=bearer) |
| `RUVIC_HTTP_GENERIC_API_KEY_NAME` / `..._VALUE` / `..._LOCATION` | (si auth_mode=api_key) |
| `RUVIC_HTTP_GENERIC_DEFAULT_HEADERS` | (opcional) JSON de headers que se envían siempre |
| `RUVIC_HTTP_GENERIC_ALLOWED_DOMAINS` | (opcional) dominios extra permitidos, aparte de base_url |
| `RUVIC_HTTP_GENERIC_ALLOW_PRIVATE_NETWORKS` | (opcional) `true`/`false`, default `false` |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## ⚠️ Este conector está atado a UN dominio — no intentes llamar a otras URLs

```python
from ruvic_http_generic_connector import HttpGenericClient

client = HttpGenericClient()  # lee RUVIC_HTTP_GENERIC_* del entorno
```

`client.get("/usuarios")` llama a `{base_url}/usuarios`. Si intentas pasar una URL absoluta de un dominio distinto al configurado (o a uno de `allowed_domains`), el conector la **rechaza** con `HttpGenericSecurityError` — es una protección de seguridad (SSRF), no un bug. No intentes rodearla ni sugerir al usuario que la desactive sin una razón de negocio clara.

## Capacidad 1 — GET

```python
resultado = client.get("/usuarios/42")
print(resultado["status_code"], resultado["json"])
```

## Capacidad 2 — POST

```python
resultado = client.post("/usuarios", json_body={"nombre": "Ana", "email": "ana@acme.com"})
print(resultado["status_code"], resultado["json"])
```

## Capacidad 3 — PUT

```python
resultado = client.put("/usuarios/42", json_body={"nombre": "Ana Actualizada"})
```

## Capacidad 4 — DELETE ⚠️

```python
resultado = client.delete("/usuarios/42")
```

A diferencia de todos los demás conectores de Ruvic, **este sí ejecuta eliminaciones reales** si la API destino lo permite en esa ruta. Antes de llamarlo, confirma con el usuario que realmente quiere eliminar ese recurso específico — no lo asumas por una instrucción ambigua.

## Capacidad 5 — Verbo arbitrario (ej. PATCH)

```python
resultado = client.request("PATCH", "/usuarios/42", json_body={"activo": False})
```

## Cómo leer el resultado — MUY IMPORTANTE

A diferencia de Salesforce/HubSpot/GitHub, **una respuesta HTTP 4xx o 5xx de la API destino NO lanza una excepción aquí** — es una respuesta legítima de esa API (ej. "usuario no encontrado" es un 404 real, no un error del conector). Siempre revisa `status_code`/`ok`:

```python
resultado = client.get("/usuarios/999")
if resultado["ok"]:
    print("Encontrado:", resultado["json"])
else:
    print(f"La API respondió {resultado['status_code']}: {resultado['json'] or resultado['text']}")
```

## Manejo de errores reales (red, configuración, seguridad)

```python
from ruvic_http_generic_connector import (
    HttpGenericNetworkError, HttpGenericSecurityError, HttpGenericConfigError,
)

try:
    resultado = client.get("/usuarios")
except HttpGenericNetworkError:
    print("No se pudo conectar a la API — revisa la red o si el servicio está caído")
except HttpGenericSecurityError as e:
    print(f"Petición bloqueada por seguridad: {e}")
except HttpGenericConfigError:
    print("El conector no está bien configurado — revisa Settings → Conectores")
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_HTTP_GENERIC_*` (el constructor de `HttpGenericClient` ya lo hace).
2. Nunca imprimas `RUVIC_HTTP_GENERIC_BEARER_TOKEN`, `..._PASSWORD`, ni `..._API_KEY_VALUE` en logs ni en la salida.
3. Siempre revisa `status_code`/`ok` en el resultado — nunca asumas que una llamada fue exitosa solo porque no lanzó excepción.
4. No intentes llamar a dominios fuera de `base_url`/`allowed_domains`: es una protección de seguridad activa, no una limitación a evadir.
5. Antes de usar `delete()` o `request("DELETE", ...)`, confirma la intención del usuario — es la única operación irreversible que este conector permite.
6. No sugieras activar `allow_private_networks` salvo que el usuario tenga una necesidad clara de integrarse con un sistema interno — es una superficie de riesgo real (SSRF).
