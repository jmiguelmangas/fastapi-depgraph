# fastapi-depgraph

Introspección del árbol de `Depends()` de una app FastAPI: qué dependencias
resuelve cada ruta, cuáles se comparten entre rutas, cuáles no están
cacheadas, y export a ASCII o Mermaid.

Lee `route.dependant` — la estructura que FastAPI ya construye internamente
al registrar cada ruta — en vez de reparsear firmas a mano.

## Instalación

```bash
pip install fastapi-depgraph
```

## Uso — CLI

```bash
depgraph show myapp.main:app
depgraph show myapp.main:app --shared --uncached
depgraph export myapp.main:app --format mermaid > graph.mmd
```

## Uso — API

```python
from fastapi_depgraph import inspect_app

report = inspect_app(app)

report.shared_dependencies()    # {callable: ["/ruta1", "/ruta2"]}
report.uncached_dependencies()  # ["modulo.get_request_id", ...]

for route in report.routes:
    print(route.path, route.root.name)
```

## Ejemplo

```bash
$ depgraph show examples/basic_app.py:app --shared --uncached
```

```
GET /users/me
  basic_app.read_current_user (sync)
  └── basic_app.get_current_user (sync)
      ├── basic_app.get_db (async)
      │   └── basic_app.get_settings (sync)
      └── basic_app.get_request_id (sync) [no-cache]
...

Dependencias compartidas entre rutas:
  get_current_user: /orders, /orders/{order_id}, /users/me
  get_db: /orders, /orders/{order_id}, /users, /users/me
  get_settings: /orders, /orders/{order_id}, /users, /users/me
  get_request_id: /orders, /orders/{order_id}, /users/me
  get_orders_service: /orders, /orders/{order_id}

Dependencias con use_cache=False:
  basic_app.get_request_id
```

De un vistazo: `get_db` y `get_settings` se resuelven en cuatro rutas
distintas — si una se vuelve cara, es ahí donde conviene mirar primero. Y
`get_request_id` está marcada como no-cacheada a propósito (viene de un
header por request), pero en un caso real esa marca es la que te avisa de
un `use_cache=False` que alguien olvidó o puso sin querer.

## Qué patrones soporta

Probado, con test de regresión, contra los patrones reales que rompían
versiones tempranas de este paquete:

- `APIRouter` + `include_router()`, con cualquier nivel de anidamiento y
  prefijo (`/api` → `/v1` → `/items` se acumula correctamente en el path).
- Dependencias declaradas en `include_router(router, dependencies=[...])` o
  `FastAPI(dependencies=[...])` — un guard de auth para todo un router se ve
  en el árbol de cada ruta que cubre.
- Apps montadas con `app.mount(sub_app)` (nota de path abajo).
- Dependencias parametrizadas por factory (`def make_limiter(n): def
  check(): ...; return check`) o `functools.partial(fn, role="admin")`: dos
  instancias con distinto valor capturado/bindeado se muestran como nodos
  distintos (`check{n=5}` vs. `check{n=10}`, `require_role(role='admin')`
  vs. `require_role(role='editor')`) en vez de colapsar en un solo nombre.
- `Depends(AlgunaClase())` (instancia) y `Depends(AlgunaClase)` (la clase
  misma) — ambos patrones de "clase como dependencia" documentados en
  FastAPI.

## Limitaciones conocidas

- **Apps montadas con `app.mount(sub_app)`** se recorren (Starlette expone
  las rutas del sub-app en `Mount.routes`), pero el `path` reportado es
  relativo al sub-app, sin el prefijo del mount.
- Solo se inspeccionan rutas HTTP; rutas WebSocket no forman parte del
  árbol (a propósito — `Depends()` en WebSocket no tiene caché de request
  ni el mismo modelo de resolución, ver DESIGN.md §2).
- Si dos instancias distintas de la misma clase se usan como dependencias
  en rutas distintas, `shared_dependencies()` las trata correctamente como
  no compartidas (compara por identidad), pero se muestran con el mismo
  label en el árbol/Mermaid salvo que la clase misma sea una closure — no
  hay forma genérica de nombrar una instancia arbitraria de forma legible.
- `app.dependency_overrides` (el mecanismo estándar para inyectar test
  doubles) no se refleja: el árbol muestra la dependencia tal como está
  declarada en el código, no la que efectivamente correría bajo un
  override activo — es un grafo estático, ver DESIGN.md §2.
- El nombre de una dependencia parametrizada incluye el `repr()` de los
  valores capturados/bindeados — si esos valores son secretos (tokens,
  API keys pasados como default), van a aparecer en la salida de `depgraph
  show`/`export`. No pegues ese output en canales públicos sin revisar qué
  dependencias parametrizadas tiene tu app.
- La fusión de path/dependencias para routers incluidos (`include_router`)
  usa, cuando está disponible, un método interno sin contrato público que
  Starlette expone para resolver rutas en tiempo real; si esa forma cambia
  en una versión futura, el paquete degrada de forma silenciosa al
  comportamiento anterior (sin prefijo acumulado ni dependencias de
  inclusión) en vez de fallar — la matriz de CI corre contra varias
  versiones de FastAPI para detectarlo pronto si pasa.

## Por qué

El sistema de DI de FastAPI es implícito: `Depends()` anidados se resuelven
sin que haya forma nativa de ver el árbol. Dos preguntas que este paquete
responde y que hoy no tienen forma directa de contestarse:

- ¿Qué dependencias pesadas se están **recomputando** en vez de cachearse
  (`use_cache=False`)?
- ¿Qué rutas **comparten** una dependencia cara, para saber dónde optimizar
  una vez y no en cinco sitios distintos?

Ver `DESIGN.md` para el resto del alcance y las decisiones de diseño.
