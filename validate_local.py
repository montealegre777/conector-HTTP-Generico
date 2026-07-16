"""Validación local del conector http_generic: ejercita las 5 capacidades.

Por defecto usa httpbin.org (servicio público gratuito de prueba, que
hace "eco" de lo que le envíes) para no depender de una API propia del
usuario. Configura las env vars antes de correr:

    export RUVIC_HTTP_GENERIC_BASE_URL="https://httpbin.org"
    export RUVIC_HTTP_GENERIC_AUTH_MODE="none"
    python validate_local.py
"""

from ruvic_http_generic_connector import HttpGenericClient, setup_logging

setup_logging("INFO")
client = HttpGenericClient()

print("== 1. GET ==")
resultado = client.get("/get", params={"hola": "mundo"})
print(f"  status={resultado['status_code']} ok={resultado['ok']}")
print(f"  json.args={resultado['json'].get('args') if resultado['json'] else None}")

print("== 2. POST ==")
resultado = client.post("/post", json_body={"nombre": "Ruvic", "prueba": True})
print(f"  status={resultado['status_code']} ok={resultado['ok']}")
print(f"  json.json={resultado['json'].get('json') if resultado['json'] else None}")

print("== 3. PUT ==")
resultado = client.put("/put", json_body={"actualizado": True})
print(f"  status={resultado['status_code']} ok={resultado['ok']}")

print("== 4. DELETE ==")
resultado = client.delete("/delete")
print(f"  status={resultado['status_code']} ok={resultado['ok']}")

print("== 5. request() con verbo arbitrario (PATCH) ==")
resultado = client.request("PATCH", "/patch", json_body={"campo": "valor"})
print(f"  status={resultado['status_code']} ok={resultado['ok']}")

print("== 6. Confirmar que un dominio distinto al configurado se bloquea (SSRF) ==")
try:
    client.get("https://evil-example.com/robar-datos")
    print("  ERROR: debió bloquearse y no lo hizo")
except Exception as exc:
    print(f"  OK, bloqueado correctamente: {exc}")

print("== 7. Confirmar que una IP de metadata de nube se bloquea (aunque sea por la lista de dominios) ==")
try:
    client.get("http://169.254.169.254/latest/meta-data/")
    print("  ERROR: debió bloquearse y no lo hizo")
except Exception as exc:
    print(f"  OK, bloqueado correctamente: {exc}")
    print(
        "  (nota: aquí se bloqueó porque el dominio no coincide con base_url; "
        "si base_url mismo resolviera a una IP privada, se bloquearía por esa razón en su lugar)"
    )
