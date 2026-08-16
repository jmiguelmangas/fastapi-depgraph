# CLAUDE.md

Contexto de proyecto para Claude Code. Ver `DESIGN.md` para el diseño
completo (problema, alcance, decisiones, roadmap, riesgos).

## Qué es

`fastapi-depgraph`: introspección del árbol de `Depends()` de una app
FastAPI, leyendo `route.dependant` (estructura interna de FastAPI, ya
construida al registrar cada ruta — no se reparsean firmas a mano).

Paquete público, independiente, sin relación con ningún proyecto interno.

## Prior art

Existe `fastapi-di-viz` (PyPI, dotcs/fastapi-di-viz) — parado desde dic.
2024, reparsea firmas en vez de usar `route.dependant`, sin detección de
dependencias compartidas/no-cacheadas, y con un bug de colisión de nombres
(usa `__name__` sin el módulo). Este paquete se escribió desde cero por eso
mismo, no como fork. Vale la pena abrir un issue allí mencionando este
proyecto como gesto de comunidad, sin que bloquee nada.

## Convenciones

- Pensar antes de codear; reusar lo que ya exista antes de escribir algo
  nuevo.
- Priorizar legibilidad sobre cleverness.
- Lint (`ruff check` + `ruff format`) y tests (`pytest`) después de
  cualquier cambio, antes de darlo por terminado.
- Comparar dependencias por identidad de función (`is`), nunca por nombre —
  es la causa del bug de `fastapi-di-viz` que este paquete evita a propósito.
- Sin dependencias de runtime más allá de `fastapi` en sí. `pytest` es
  dev-only.
- Sin monkeypatching de APIs internas de resolución de FastAPI
  (`solve_dependencies` y similares) — ver DESIGN.md §3. Solo se lee
  `route.dependant` después de que FastAPI ya lo construyó.

## Estructura

```
src/fastapi_depgraph/
├── inspect.py   # inspect_app() + DepGraphReport — el core
├── export.py    # to_ascii(), to_mermaid()
└── cli.py       # depgraph show / depgraph export
tests/
├── fixtures/sample_app.py   # app FastAPI de juguete con deps compartidas y no-cacheadas
└── test_inspect.py
```

## Comandos

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/ --fix && ruff format src/ tests/
PYTHONPATH=. depgraph show tests.fixtures.sample_app:app --shared --uncached
```

## Estado actual

v0.1 funcional: `inspect_app`, `shared_dependencies()`,
`uncached_dependencies()`, export ASCII y Mermaid, CLI con `show`/`export`.
6 tests pasando. Ver TASKS.md para lo pendiente antes de publicar.
