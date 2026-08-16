# CLAUDE.md

Project context for Claude Code. See `DESIGN.md` for the full design
(problem, scope, decisions, roadmap, risks).

## What this is

`fastapi-depgraph`: introspection of a FastAPI app's `Depends()` tree,
reading `route.dependant` (FastAPI's internal structure, already built when
each route is registered — signatures are never reparsed by hand).

Public, standalone package, not tied to any internal project.

## Prior art

`fastapi-di-viz` (PyPI, dotcs/fastapi-di-viz) already exists — stalled
since Dec. 2024, reparses signatures instead of using `route.dependant`,
has no shared/uncached dependency detection, and has a name-collision bug
(uses `__name__` without the module). This package was written from
scratch for exactly that reason, not as a fork. Worth opening an issue
there mentioning this project as a community gesture, without blocking
anything.

## Conventions

- Think before coding; reuse what already exists before writing something
  new.
- Prioritize readability over cleverness.
- Lint (`ruff check` + `ruff format`) and tests (`pytest`) after any
  change, before calling it done.
- Compare dependencies by function identity (`is`), never by name — that's
  the cause of the `fastapi-di-viz` bug this package deliberately avoids.
- No runtime dependencies beyond `fastapi` itself. `pytest` is dev-only.
- No monkeypatching of FastAPI's internal resolution APIs
  (`solve_dependencies` and similar) — see DESIGN.md §3. Only
  `route.dependant` is read, after FastAPI has already built it.

## Structure

```
src/fastapi_depgraph/
├── inspect.py   # inspect_app() + DepGraphReport — the core
├── export.py    # to_ascii(), to_mermaid()
└── cli.py       # depgraph show / depgraph export
tests/
├── fixtures/       # toy FastAPI apps covering routers, parametrized deps,
│                   # class-based deps, WebSocket routes
└── test_*.py
```

## Commands

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/ tests/ --fix && ruff format src/ tests/
PYTHONPATH=. depgraph show tests.fixtures.sample_app:app --shared --uncached
```

## Current status

Published on PyPI as `fastapi-depgraph` v0.1.0
(https://pypi.org/project/fastapi-depgraph/). `inspect_app`,
`shared_dependencies()`, `uncached_dependencies()`, ASCII and Mermaid
export, CLI with `show`/`export`. 23 tests passing, including regressions
for `APIRouter`/`include_router()` nesting, parametrized (factory/closure,
`functools.partial`) dependencies, and WebSocket route exclusion. See
TASKS.md for what's left (v0.2 timing, the `fastapi-di-viz` community
gesture).
