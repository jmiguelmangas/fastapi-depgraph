# fastapi-depgraph — DESIGN

Introspección del árbol de `Depends()` de una app FastAPI: qué dependencias
resuelve cada ruta, en qué orden, cuáles se cachean, y (opcional) cuánto
tarda cada una. Paquete público para la comunidad — no ligado a ningún
proyecto interno.

- **Paquete PyPI:** `fastapi-depgraph`
- **Import:** `fastapi_depgraph`
- **Repo:** propio, público

---

## 1. Problema

El sistema de DI de FastAPI es implícito por diseño: `Depends()` anidados se
resuelven en orden no siempre obvio, y hoy no hay forma nativa de ver el
árbol sin leer código o poner breakpoints. Los equipos que mantienen
codebases grandes reportan que una parte notable del tiempo de resolución de
incidentes se va en rastrear esa lógica de resolución en vez de la lógica de
negocio en sí — y es un problema que crece con el tamaño del equipo, no con
la complejidad del dominio.

Dos síntomas concretos que un desarrollador se encuentra sin herramienta:

- No sabe si una dependencia cara (una query a DB, una llamada externa) se
  está **recomputando en cada sub-dependencia** por no estar cacheada
  (`use_cache=False`, o dependencias no-hasheables que rompen el caché
  automático de FastAPI).
- No sabe qué rutas **comparten** una dependencia pesada, así que optimizar
  o cachear esa dependencia en un sitio y no en otro es fácil de pasar por
  alto.

## 2. Alcance

**Dentro (v0.1 — grafo estático, sin tocar runtime):**

- Introspeccionar `app.routes` y el árbol `Dependant` de cada `APIRoute`
  (FastAPI ya lo construye al registrar la ruta; se lee, no se reconstruye).
- Reportar por ruta: árbol de dependencias con nombre, si es sync o async,
  si está cacheada (`use_cache`), y su profundidad de anidamiento.
- Detectar dependencias **repetidas entre rutas** (candidatas a compartir
  caché u optimización) y dependencias marcadas `use_cache=False` (recompute
  en cada resolución, incluso dentro del mismo request si aparecen dos veces
  en el árbol).
- Exportar: árbol ASCII en terminal, o grafo en formato Mermaid/DOT para
  pegarlo en documentación.
- CLI: `depgraph show app:app` / `depgraph export app:app --format mermaid`.

**Dentro (v0.2 — timing opcional, opt-in explícito):**

- Un `TimedDepends` como reemplazo drop-in de `Depends()` que el usuario elige
  usar en las dependencias que le interesa medir. Registra tiempo de
  ejecución en una contextvar por request, expuesto vía endpoint de debug
  opcional (`/__depgraph__/last`) o log estructurado.

**Fuera (no-goals):**

- No hace profiling general de la app (para eso ya hay APMs con OpenTelemetry).
- No detecta llamadas bloqueantes dentro de un `async def` — es un problema
  relacionado pero distinto (bloqueo del event loop vs. visibilidad del
  grafo de DI); mezclar los dos alcances en un paquete lo complica sin
  necesidad.
- No modifica el comportamiento de resolución de dependencias de FastAPI —
  es de solo lectura en v0.1, y opt-in explícito en v0.2.

## 3. Decisión de diseño: nada de monkeypatching de `solve_dependencies`

La forma "fácil" de medir timing sería parchear la función interna de
FastAPI que resuelve dependencias. Se descarta para v0.1 y se limita en v0.2:

- Es API interna no pública (`fastapi.dependencies.utils`), cambia entre
  versiones sin aviso en el changelog público, y un parche roto en
  producción es peor que no tener la herramienta.
- La introspección estática (leer `route.dependant` después del registro) es
  mucho más estable: es la misma estructura que FastAPI ya usa internamente
  para servir requests, solo se lee después de construida.
- Para timing, `TimedDepends` es explícito y no toca nada interno — el
  usuario decide qué medir, envolviendo la dependencia él mismo. Menos mágico,
  más mantenible, y sigue funcionando si FastAPI cambia su motor de DI.

## 4. API pública

```python
from fastapi_depgraph import inspect_app

report = inspect_app(app)

report.routes                      # lista de RouteDependencyTree
report.shared_dependencies()       # deps usadas en 2+ rutas
report.uncached_dependencies()     # use_cache=False, candidatas a revisar

for route in report.routes:
    route.path                     # "/users/{id}"
    route.tree                     # nodo raíz: nombre, sync/async, hijos, cached
```

```python
# v0.2 — timing opt-in
from fastapi_depgraph import TimedDepends

async def get_current_user(token: str = Depends(oauth2_scheme)):
    ...

@app.get("/me")
async def me(user = TimedDepends(get_current_user)):
    ...
# el timing queda disponible en el contexto del request, sin tocar
# el motor de resolución de FastAPI
```

## 5. Estructura del repo

```
fastapi-depgraph/
├── src/fastapi_depgraph/
│   ├── __init__.py        # inspect_app, TimedDepends
│   ├── inspect.py         # lectura de route.dependant, construcción del reporte
│   ├── report.py          # RouteDependencyTree, shared_dependencies, etc.
│   ├── export.py          # ASCII, Mermaid, DOT
│   ├── timing.py          # TimedDepends + contextvar (v0.2)
│   └── cli.py
├── tests/
│   └── fixtures/           # apps FastAPI de juguete con árboles de deps variados
├── examples/
├── CLAUDE.md
├── DESIGN.md
└── .github/workflows/      # lint, tests contra varias versiones de FastAPI
```

Tests: apps FastAPI de juguete con casos conocidos (deps compartidas,
`use_cache=False`, anidamiento profundo) y aserciones sobre el árbol
resultante. Matriz de CI contra 2-3 versiones recientes de FastAPI, porque
`route.dependant` es la única superficie interna que se toca y conviene
detectar pronto si cambia de forma.

## 6. Roadmap

**0.1 — el mínimo defendible (esta tarde/esta semana)**
`inspect_app`, `shared_dependencies()`, `uncached_dependencies()`, export
ASCII y Mermaid, CLI básico. Sin timing. Un ejemplo con una app de tamaño
medio (10-15 rutas, deps anidadas) para el README — es lo que vende el
paquete de un vistazo.

**0.2 — timing opt-in**
`TimedDepends`, endpoint de debug opcional, documentación clara de que es
opt-in y no instrumenta nada automáticamente.

**Después:** integración con Mermaid embebido en `/docs` (un tab extra en
Swagger UI vía `app.mount` no es trivial pero sería el diferencial visual);
evaluar exportar a OpenTelemetry spans si hay demanda real.

## 7. Riesgos

- **`route.dependant` es API interna, no pública.** Mitigación: superficie de
  contacto mínima (un solo atributo leído), matriz de CI contra varias
  versiones de FastAPI, y fallback claro (error explícito, no silencioso) si
  la estructura cambia de forma inesperada.

  Este riesgo ya se materializó dos veces, antes de publicar, ambas en
  versiones recientes de Starlette (las mismas que ya estaban en la matriz
  de CI — el fixture de test simplemente nunca ejercitaba el patrón roto):

  1. Las rutas incluidas con `include_router()` dejaron de aplanarse en
     `app.routes` — quedan envueltas en un objeto interno sin tipo público.
     `inspect_app()` devolvía silenciosamente 0 rutas para cualquier app
     que usara `APIRouter`, es decir, casi cualquier app real.
  2. Incluso bajando al router original, el `path` de cada `APIRoute` y su
     `dependant` quedaban *sin* el prefijo y sin las dependencias pasadas a
     `include_router(..., dependencies=[...])`/`FastAPI(dependencies=[...])`
     — esa fusión se difiere ahora hasta el momento de resolver un request
     en vez de aplicarse al registrar la ruta. Sin corregirlo, el reporte
     mostraba paths *incorrectos* (`/x` en vez de `/v1/x`) — peor que 0
     rutas, porque no se nota a simple vista.

  Se corrigió con `_iter_resolved_routes()` en `inspect.py`: baja
  recursivamente por cualquier objeto que exponga `.routes` o
  `.original_router.routes` (duck typing, sin importar el tipo interno), y
  cuando el router expone un método `effective_candidates()` — el mismo
  cálculo que Starlette usa para resolver requests reales — lo usa para
  obtener el path y el dependant ya fusionados. Si esa llamada falla o el
  método no existe (Starlette viejo, o una forma futura distinta), cae de
  vuelta al router original sin prefijo/dependencias de inclusión en vez de
  romper la introspección. Regresión en `tests/fixtures/router_app.py`,
  `tests/fixtures/parametrized_app.py`, `tests/test_router_discovery.py` y
  `tests/test_parametrized_dependencies.py`.

  De paso, el mismo camino de introspección más permisivo (duck typing por
  `.dependant`/`.path`) empezó a colar rutas WebSocket (`APIWebSocketRoute`
  también tiene `.dependant` y `.path`, pero no `.methods`) — se cerró
  exigiendo `.methods` no-`None` para aceptar algo como ruta HTTP. Ver
  `tests/fixtures/websocket_app.py`.
- **Falsos positivos en "dependencias compartidas".** Dos dependencias con el
  mismo nombre de función pero definidas en módulos distintos no son la
  misma — comparar por identidad de la función (`id()`/referencia), no por
  nombre, desde el diseño inicial.
- **Ya existe algo similar: `fastapi-di-viz`.** Cubre justo la parte base de
  v0.1 (camina el árbol y exporta a Mermaid/DOT), pero está parado desde
  diciembre 2024, un solo mantenedor, sin `shared_dependencies()`,
  `uncached_dependencies()` ni timing. Dos caminos honestos: (a) partir de
  cero con el diferencial real (detección de deps compartidas/no-cacheadas +
  timing opt-in), presentándolo como sucesor con alcance mayor, o (b)
  contactar al autor y proponer esas features como PR/fork antes de
  fragmentar el ecosistema con un nombre nuevo. (b) es más lento pero más
  sano para la comunidad; (a) es más rápido y da control total del roadmap.
