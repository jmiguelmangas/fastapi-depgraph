# TASKS

## Hecho (v0.1)

- [x] `inspect_app()` construye el árbol por ruta desde `route.dependant`
- [x] `DepGraphReport.shared_dependencies()` — comparación por identidad, no
      por nombre
- [x] `DepGraphReport.uncached_dependencies()`
- [x] Detección sync/async por nodo
- [x] Export ASCII (`to_ascii`) y Mermaid (`to_mermaid`, con dedup de nodos)
- [x] CLI: `depgraph show [--shared] [--uncached]`, `depgraph export --format mermaid`
- [x] Fixture de test con caso real (deps compartidas + `use_cache=False` +
      dependencia async) y 6 tests pasando
- [x] Lint limpio (`ruff check` + `ruff format`)
- [x] Fix crítico: `inspect_app()` devolvía 0 rutas en apps que usan
      `APIRouter` + `include_router()` sobre Starlette reciente (rutas
      envueltas en un objeto interno, ya no planas en `app.routes`).
- [x] Fix crítico: incluso resolviendo lo anterior, el prefijo de
      `include_router(prefix=...)` y las dependencias de
      `include_router(dependencies=...)`/`FastAPI(dependencies=...)` no
      llegaban al árbol (path/dependant sin fusionar) — reportaba paths
      *incorrectos*, no solo incompletos. Corregido usando
      `effective_candidates()` cuando está disponible, con fallback si no.
- [x] Fix: dependencias basadas en clase (`Depends(AlgunaClase())`) se
      nombraban con `repr()` (dirección de memoria incluida, inestable
      entre corridas) en vez del nombre de la clase.
- [x] Fix: dependencias parametrizadas por factory/closure o
      `functools.partial` (patrón muy común: rate limiting, roles,
      paginación) colapsaban en un solo nombre indistinguible aunque fueran
      funcionalmente distintas. Ahora se muestran con las variables
      capturadas/bindeadas (`check{times=5}`, `require_role(role='admin')`).
- [x] Fix: rutas WebSocket se colaban en el árbol tras el fix de routers
      (tienen `.dependant`/`.path` pero no `.methods`).
- [x] Fix: el export a Mermaid no escapaba `"`/`<`/`>` en los labels — con
      el fix de closures/partial, un valor capturado con esos caracteres
      rompía la sintaxis o se interpretaba como HTML (`<locals>`).
- [x] Cobertura de test para `cli.py` (antes en 0): `show`, `--shared`,
      `--uncached`, `export --format mermaid`, y los tres modos de fallo de
      `_load_app` (path malformado, módulo inexistente, atributo
      inexistente).
- [x] Test de `app.dependency_overrides` — documenta que el grafo es
      estático y no refleja overrides (comportamiento esperado, ver
      DESIGN.md §2).
- [x] Ver DESIGN.md §7 para el detalle de cada fix y los fixtures de
      regresión (`router_app.py`, `parametrized_app.py`, `websocket_app.py`).

## Pendiente antes de publicar en PyPI

- [x] CI en GitHub Actions: lint + tests, matriz contra 3 versiones de
      FastAPI (0.110, 0.120, 0.141)
- [x] `.github/workflows/release.yml` (mismo patrón que errand: build con
      `uv build`, publish vía `pypa/gh-action-pypi-publish` + OIDC,
      disparado por tag `v*`) y entorno de GitHub `pypi` creado en el repo.
      Falta el lado de PyPI: registrar el "pending publisher" en
      https://pypi.org/manage/account/publishing/ (Owner `jmiguelmangas`,
      Repository `fastapi-depgraph`, Workflow `release.yml`, Environment
      `pypi`) — requiere login interactivo, no se puede hacer por CLI/API.
- [x] `LICENSE` (MIT, coherente con lo declarado en `pyproject.toml`)
- [x] Un ejemplo más grande en `examples/` (10-15 rutas) para el README —
      es lo que vende el paquete de un vistazo
- [ ] Decidir y documentar el gesto de comunidad hacia `fastapi-di-viz`
      (issue mencionando el proyecto nuevo — ver CLAUDE.md)
- [x] Nombre confirmado libre en PyPI (`fastapi-depgraph`, verificado
      2026-08-16 vía `pypi.org/pypi/fastapi-depgraph/json` → 404)

## v0.2 (después de publicar 0.1)

- [ ] `TimedDepends` — reemplazo drop-in de `Depends()`, opt-in, sin tocar
      `solve_dependencies` (ver DESIGN.md §3)
- [ ] Endpoint de debug opcional para exponer el timing
