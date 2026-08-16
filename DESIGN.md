# fastapi-depgraph — DESIGN

Introspection of a FastAPI app's `Depends()` tree: which dependencies each
route resolves, in what order, which are cached, and (optionally) how long
each one takes. A public package for the community — not tied to any
internal project.

- **PyPI package:** `fastapi-depgraph`
- **Import:** `fastapi_depgraph`
- **Repo:** own, public

---

## 1. Problem

FastAPI's DI system is implicit by design: nested `Depends()` resolve in an
order that isn't always obvious, and today there's no native way to see the
tree without reading code or setting breakpoints. Teams maintaining large
codebases report that a noticeable share of incident-resolution time goes
into tracing that resolution logic instead of the actual business logic —
and it's a problem that grows with team size, not with domain complexity.

Two concrete symptoms a developer runs into without a tool:

- No way to tell if an expensive dependency (a DB query, an external call)
  is being **recomputed on every sub-dependency** because it isn't cached
  (`use_cache=False`, or unhashable dependencies that break FastAPI's
  automatic cache).
- No way to tell which routes **share** a heavy dependency, so optimizing
  or caching that dependency in one place and not another is easy to miss.

## 2. Scope

**In (v0.1 — static graph, no runtime instrumentation):**

- Introspect `app.routes` and the `Dependant` tree of each `APIRoute`
  (FastAPI already builds it when the route is registered; it's read, not
  reconstructed).
- Report per route: dependency tree with name, sync or async, whether it's
  cached (`use_cache`), and its nesting depth.
- Detect dependencies **repeated across routes** (candidates for shared
  caching/optimization) and dependencies marked `use_cache=False`
  (recomputed on every resolution, even within the same request if they
  appear twice in the tree).
- Export: ASCII tree in the terminal, or a graph in Mermaid/DOT format to
  paste into documentation.
- CLI: `depgraph show app:app` / `depgraph export app:app --format mermaid`.

**In (v0.2 — optional timing, explicit opt-in):**

- A `TimedDepends` as a drop-in replacement for `Depends()` that the user
  chooses to use on the dependencies they care about measuring. Records
  execution time in a per-request contextvar, exposed via an optional debug
  endpoint (`/__depgraph__/last`) or structured logging.

**Out (non-goals):**

- No general app profiling (that's what APMs with OpenTelemetry are for).
- No detection of blocking calls inside an `async def` — a related but
  distinct problem (event-loop blocking vs. DI graph visibility); mixing
  the two scopes in one package complicates it needlessly.
- Doesn't modify FastAPI's dependency-resolution behavior — read-only in
  v0.1, explicit opt-in in v0.2.

## 3. Design decision: no monkeypatching `solve_dependencies`

The "easy" way to measure timing would be to patch FastAPI's internal
dependency-resolution function. Ruled out for v0.1 and constrained in v0.2:

- It's non-public internal API (`fastapi.dependencies.utils`), changes
  between versions without notice in the public changelog, and a broken
  patch in production is worse than not having the tool at all.
- Static introspection (reading `route.dependant` after registration) is
  far more stable: it's the same structure FastAPI already uses internally
  to serve requests, only read after it's been built.
- For timing, `TimedDepends` is explicit and touches nothing internal — the
  user decides what to measure by wrapping the dependency themselves. Less
  magic, more maintainable, and keeps working even if FastAPI changes its
  DI engine.

## 4. Public API

```python
from fastapi_depgraph import inspect_app

report = inspect_app(app)

report.routes                      # list of RouteDependencyTree
report.shared_dependencies()       # deps used in 2+ routes
report.uncached_dependencies()     # use_cache=False, worth a look

for route in report.routes:
    route.path                     # "/users/{id}"
    route.tree                     # root node: name, sync/async, children, cached
```

```python
# v0.2 — opt-in timing
from fastapi_depgraph import TimedDepends

async def get_current_user(token: str = Depends(oauth2_scheme)):
    ...

@app.get("/me")
async def me(user = TimedDepends(get_current_user)):
    ...
# timing is available in the request context, without touching
# FastAPI's resolution engine
```

## 5. Repo structure

```
fastapi-depgraph/
├── src/fastapi_depgraph/
│   ├── __init__.py        # inspect_app, TimedDepends
│   ├── inspect.py         # reads route.dependant, builds the report
│   ├── report.py          # RouteDependencyTree, shared_dependencies, etc.
│   ├── export.py          # ASCII, Mermaid, DOT
│   ├── timing.py          # TimedDepends + contextvar (v0.2)
│   └── cli.py
├── tests/
│   └── fixtures/           # toy FastAPI apps with varied dependency trees
├── examples/
├── CLAUDE.md
├── DESIGN.md
└── .github/workflows/      # lint, tests against several FastAPI versions
```

Tests: toy FastAPI apps with known cases (shared deps, `use_cache=False`,
deep nesting) and assertions on the resulting tree. CI matrix against 2-3
recent FastAPI versions, because `route.dependant` is the only internal
surface touched and it's worth detecting early if its shape changes.

## 6. Roadmap

**0.1 — the defensible minimum (this afternoon/this week)**
`inspect_app`, `shared_dependencies()`, `uncached_dependencies()`, ASCII and
Mermaid export, basic CLI. No timing. A medium-sized example app (10-15
routes, nested deps) for the README — that's what sells the package at a
glance.

**0.2 — opt-in timing**
`TimedDepends`, optional debug endpoint, clear documentation that it's
opt-in and instruments nothing automatically.

**Later:** Mermaid embedded in `/docs` (an extra tab in Swagger UI via
`app.mount` isn't trivial but would be the visual differentiator);
evaluate exporting to OpenTelemetry spans if there's real demand.

## 7. Risks

- **`route.dependant` is internal API, not public.** Mitigation: minimal
  contact surface (a single attribute read), CI matrix against several
  FastAPI versions, and a clear fallback (explicit error, not silent) if
  the structure changes shape unexpectedly.

  This risk already materialized twice, before publishing, both on recent
  Starlette versions (the same ones already in the CI matrix — the test
  fixture simply never exercised the broken pattern):

  1. Routes included with `include_router()` stopped being flattened into
     `app.routes` — they get wrapped in an object with no public type.
     `inspect_app()` silently returned 0 routes for any app using
     `APIRouter`, i.e. almost any real app.
  2. Even after descending into the original router, each `APIRoute`'s
     `path` and its `dependant` were left *without* the prefix and without
     the dependencies passed to
     `include_router(..., dependencies=[...])`/`FastAPI(dependencies=[...])`
     — that merge is now deferred until a request is resolved instead of
     being applied when the route is registered. Left unfixed, the report
     showed *incorrect* paths (`/x` instead of `/v1/x`) — worse than 0
     routes, because it isn't obvious at a glance.

  Fixed with `_iter_resolved_routes()` in `inspect.py`: it recursively
  descends into any object exposing `.routes` or `.original_router.routes`
  (duck typing, regardless of the internal type), and when the router
  exposes an `effective_candidates()` method — the same computation
  Starlette uses to resolve real requests — it uses that to get the
  already-merged path and dependant. If that call fails or the method
  doesn't exist (older Starlette, or a different future shape), it falls
  back to the original router without the prefix/inclusion dependencies
  instead of breaking introspection. Regression coverage in
  `tests/fixtures/router_app.py`, `tests/fixtures/parametrized_app.py`,
  `tests/test_router_discovery.py` and
  `tests/test_parametrized_dependencies.py`.

  Along the way, that same more permissive introspection path (duck typing
  on `.dependant`/`.path`) started letting WebSocket routes leak through
  (`APIWebSocketRoute` also has `.dependant` and `.path`, but no
  `.methods`) — closed by requiring a non-`None` `.methods` to accept
  something as an HTTP route. See `tests/fixtures/websocket_app.py`.
- **False positives in "shared dependencies".** Two dependencies with the
  same function name but defined in different modules aren't the same —
  compare by function identity (`id()`/reference), not by name, from the
  initial design.
- **Something similar already exists: `fastapi-di-viz`.** It covers exactly
  the base part of v0.1 (walks the tree and exports to Mermaid/DOT), but
  has been stalled since December 2024, single maintainer, no
  `shared_dependencies()`, `uncached_dependencies()`, or timing. Two honest
  paths: (a) start from scratch with the real differentiator (shared/
  uncached dependency detection + opt-in timing), presenting it as a
  successor with broader scope, or (b) contact the author and propose those
  features as a PR/fork before fragmenting the ecosystem with a new name.
  (b) is slower but healthier for the community; (a) is faster and gives
  full control over the roadmap.
