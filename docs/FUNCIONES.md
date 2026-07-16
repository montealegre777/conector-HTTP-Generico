# Conector HTTP Genérico — Qué hace cada función

Este documento explica, en lenguaje simple, qué hace cada una de las 5 funciones del conector `ruvic_http_generic_connector`.

**Nota importante:** a diferencia de los otros conectores, este habla con **cualquier API REST** que se configure — pero solo con **una** a la vez, la que quede fijada al configurarlo. No es un conector que pueda llamar a cualquier URL improvisada.

---

## 1. `get()` — Consultar datos

**¿Qué hace?** Pide información a la API, sin modificar nada (equivalente a "leer").

**Ejemplo:**
```python
client.get("/usuarios/42")
```

**Analogía:** preguntar algo, sin cambiar nada.

---

## 2. `post()` — Crear algo nuevo

**¿Qué hace?** Envía datos a la API para crear un registro nuevo.

**Ejemplo:**
```python
client.post("/usuarios", json_body={"nombre": "Ana"})
```

**Analogía:** llenar un formulario y enviarlo por primera vez.

---

## 3. `put()` — Actualizar/reemplazar algo

**¿Qué hace?** Envía datos para actualizar un registro que ya existe.

**Ejemplo:**
```python
client.put("/usuarios/42", json_body={"nombre": "Ana Actualizada"})
```

**Analogía:** corregir un formulario que ya habías llenado antes.

---

## 4. `delete()` — Eliminar algo ⚠️

**¿Qué hace?** Le pide a la API que elimine un registro.

**Ejemplo:**
```python
client.delete("/usuarios/42")
```

**⚠️ Diferencia importante con los demás conectores de Ruvic:** todos los demás conectores (Salesforce, HubSpot, GitHub, SAP) tienen la eliminación **bloqueada a propósito**. Este es el único que sí la permite, porque su propósito es ser una herramienta genérica de propósito general. Úsalo con cuidado — no hay red de seguridad extra aquí, más allá de que confirmes bien antes de llamarlo.

---

## 5. `request()` — Cualquier otro verbo (ej. PATCH)

**¿Qué hace?** Igual que las anteriores, pero te deja elegir el verbo HTTP exacto — útil para `PATCH` (actualización parcial) u otros verbos menos comunes.

**Ejemplo:**
```python
client.request("PATCH", "/usuarios/42", json_body={"activo": False})
```

---

## Cómo leer lo que devuelve cada función

Todas devuelven un diccionario con:
- `status_code`: el código de respuesta (200 = éxito, 404 = no encontrado, etc.)
- `ok`: `True` si el código está entre 200-299
- `json`: los datos, si la respuesta es JSON
- `text`: el texto crudo, si la respuesta NO es JSON
- `headers`: los headers de la respuesta
- `url`: la URL final que se llamó

**Importante:** que la función no lance un error **no significa** que la API dijo "sí" — siempre hay que revisar `status_code`/`ok`, porque un 404 o 500 de la API destino es una respuesta normal, no un fallo del conector.

---

## Las protecciones de seguridad (no son funciones, pero debes saber que existen)

- **No puede llamar a cualquier URL**: solo al dominio que se configuró, salvo que se agreguen otros explícitamente.
- **No puede llamar a direcciones internas/privadas** (como la red interna de Ruvic, o el "endpoint de metadata" de servidores en la nube) a menos que un administrador lo autorice explícitamente.

Si alguna de estas protecciones bloquea una llamada, verás un error claro explicando por qué — no es un bug, es la protección funcionando.

---

## Resumen rápido — ¿cuál función usar según lo que pida el usuario?

| El usuario pide... | Función a usar |
|---|---|
| "Consulta/trae datos de X" | `get()` |
| "Crea un registro nuevo en X" | `post()` |
| "Actualiza este registro en X" | `put()` |
| "Elimina este registro en X" | `delete()` (⚠️ confirma antes) |
| "Actualiza parcialmente / usa PATCH" | `request("PATCH", ...)` |
