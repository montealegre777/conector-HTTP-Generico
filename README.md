# conector-http-generico

Conector Ruvic **genérico** para cualquier API REST: GET/POST/PUT/DELETE con autenticación configurable (`none`, `basic`, `bearer`, `api_key`), y **protección SSRF incorporada**.

## Capacidades

`get`, `post`, `put`, `delete`, `request` (verbo arbitrario, ej. PATCH). A diferencia de todos los demás conectores de Ruvic, **este sí permite eliminar datos** si la API destino lo soporta — está pensado como una herramienta de propósito general, no acotada a un objeto de negocio específico.

## ⚠️ Diseño de seguridad — leer antes de desplegar

Este conector es más poderoso (y riesgoso) que los demás porque golpea APIs externas configurables. Incluye protecciones activas:

1. **Atado a un solo dominio**: cada instancia configurada solo puede llamar a `base_url` (más los dominios que se agreguen explícitamente en `allowed_domains`). No puede llamar a "cualquier URL" que el agente decida en tiempo real.
2. **Bloqueo de redes privadas por defecto**: si el host configurado (o cualquier host en `allowed_domains`) resuelve a una IP privada, loopback, link-local (incluye el endpoint de metadata de nube `169.254.169.254`) o reservada, la petición se bloquea — salvo que se active `allow_private_networks` explícitamente.
3. **Los errores HTTP de la API destino no son excepciones**: un 404/500 de la API externa se retorna como parte de la respuesta (`status_code`, `ok`), no como una excepción del conector — evita que el agente confunda "la API dijo que no existe" con "el conector falló".

**No actives `allow_private_networks` salvo que haya una necesidad de negocio real y documentada** (ej. integrarse con un sistema interno del cliente mediante VPN/red privada).

## Instalación

Requiere **Python ≥ 3.10**.

```bash
pip install git+https://github.com/tu-org/conector-http-generico.git#subdirectory=lib
```

Para desarrollo local (editable, en un venv limpio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib
```

## Variables de entorno

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_HTTP_GENERIC_BASE_URL` | Sí | URL base de la API destino (con esquema, ej. `https://api.ejemplo.com`) |
| `RUVIC_HTTP_GENERIC_AUTH_MODE` | Sí | `none`, `basic`, `bearer` o `api_key` |
| `RUVIC_HTTP_GENERIC_USERNAME` / `..._PASSWORD` | Si `auth_mode=basic` | Credenciales Basic Auth |
| `RUVIC_HTTP_GENERIC_BEARER_TOKEN` | Si `auth_mode=bearer` | Token Bearer |
| `RUVIC_HTTP_GENERIC_API_KEY_NAME` / `..._VALUE` / `..._LOCATION` | Si `auth_mode=api_key` | Nombre/valor de la API key, y si va en `header` o `query` |
| `RUVIC_HTTP_GENERIC_DEFAULT_HEADERS` | No | JSON de headers a enviar siempre, ej. `{"X-Tenant": "acme"}` |
| `RUVIC_HTTP_GENERIC_ALLOWED_DOMAINS` | No | Dominios extra permitidos, separados por coma |
| `RUVIC_HTTP_GENERIC_ALLOW_PRIVATE_NETWORKS` | No | `true`/`false`, default `false` |
| `RUVIC_HTTP_GENERIC_REQUEST_TIMEOUT` | No | Segundos, default `20` |

## Cómo correr las pruebas locales

Usa [httpbin.org](https://httpbin.org) (servicio público de eco HTTP) para no depender de una API propia:

```bash
export RUVIC_HTTP_GENERIC_BASE_URL="https://httpbin.org"
export RUVIC_HTTP_GENERIC_AUTH_MODE="none"
python test_connection.py
python validate_local.py
```

`validate_local.py` también confirma que la protección SSRF funciona (intenta llamar a un dominio no permitido y a la IP de metadata de nube, y verifica que ambas se bloqueen).

## Limitaciones conocidas

- No tiene noción de paginación, reintentos automáticos, ni rate limiting — es responsabilidad del código que lo use.
- No parsea respuestas que no sean JSON más allá de devolver el texto crudo (`text`).
- Una sola credencial/`auth_mode` por instancia configurada; si una API necesita rotar tokens dinámicamente (OAuth2 con refresh), este conector no lo maneja — usar un conector dedicado en ese caso.

## Notas de integración

- El paquete pip es `ruvic-http-generic-connector`; el import name es `ruvic_http_generic_connector`.
- Única dependencia externa: `requests`.
- Ver `SKILL.md` para los ejemplos de uso que consume el agente.
