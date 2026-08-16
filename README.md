# fastapi-depgraph

<p align="center">
  <img src="https://raw.githubusercontent.com/jmiguelmangas/fastapi-depgraph/main/assets/logo.png" alt="fastapi-depgraph logo" width="200">
</p>

<p align="center">
  <a href="https://pypi.org/project/fastapi-depgraph/"><img src="https://img.shields.io/pypi/v/fastapi-depgraph.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/fastapi-depgraph/"><img src="https://img.shields.io/pypi/pyversions/fastapi-depgraph.svg" alt="Supported Python versions"></a>
  <a href="https://github.com/jmiguelmangas/fastapi-depgraph/actions/workflows/ci.yml"><img src="https://github.com/jmiguelmangas/fastapi-depgraph/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <a href="https://github.com/jmiguelmangas/fastapi-depgraph/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/fastapi-depgraph.svg" alt="License"></a>
</p>

Introspection of a FastAPI app's `Depends()` tree: which dependencies each
route resolves, which are shared across routes, which aren't cached, and
export to ASCII or Mermaid.

Reads `route.dependant` — the structure FastAPI already builds internally
when each route is registered — instead of reparsing signatures by hand.

## Install

```bash
pip install fastapi-depgraph
```

## Usage — CLI

```bash
depgraph show myapp.main:app
depgraph show myapp.main:app --shared --uncached
depgraph export myapp.main:app --format mermaid > graph.mmd
```

## Usage — API

```python
from fastapi_depgraph import inspect_app

report = inspect_app(app)

report.shared_dependencies()    # {callable: ["/route1", "/route2"]}
report.uncached_dependencies()  # ["module.get_request_id", ...]

for route in report.routes:
    print(route.path, route.root.name)
```

## Example

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

Dependencies shared across routes:
  get_current_user: /orders, /orders/{order_id}, /users/me
  get_db: /orders, /orders/{order_id}, /users, /users/me
  get_settings: /orders, /orders/{order_id}, /users, /users/me
  get_request_id: /orders, /orders/{order_id}, /users/me
  get_orders_service: /orders, /orders/{order_id}

Dependencies with use_cache=False:
  basic_app.get_request_id
```

At a glance: `get_db` and `get_settings` get resolved on four different
routes — if one gets expensive, that's where to look first. And
`get_request_id` is intentionally marked as uncached (it comes from a
per-request header), but in a real case that's the flag that warns you
about a `use_cache=False` someone forgot or added by mistake.

## What patterns it handles

Tested, with regression coverage, against the real patterns that broke
early versions of this package:

- `APIRouter` + `include_router()`, at any level of nesting and with any
  prefix (`/api` → `/v1` → `/items` correctly accumulates in the path).
- Dependencies declared on `include_router(router, dependencies=[...])` or
  `FastAPI(dependencies=[...])` — an auth guard for an entire router shows
  up in the tree of every route it covers.
- Apps mounted with `app.mount(sub_app)` (path caveat below).
- Dependencies parametrized by a factory (`def make_limiter(n): def
  check(): ...; return check`) or `functools.partial(fn, role="admin")`:
  two instances with different captured/bound values show up as distinct
  nodes (`check{n=5}` vs. `check{n=10}`, `require_role(role='admin')` vs.
  `require_role(role='editor')`) instead of collapsing into one name.
- `Depends(SomeClass())` (instance) and `Depends(SomeClass)` (the class
  itself) — both "class as a dependency" patterns documented by FastAPI.

## Known limitations

- **Apps mounted with `app.mount(sub_app)`** are walked (Starlette exposes
  the sub-app's routes through `Mount.routes`), but the reported `path` is
  relative to the sub-app, without the mount's prefix.
- Only HTTP routes are inspected; WebSocket routes aren't part of the tree
  (intentionally — `Depends()` on WebSocket doesn't have per-request
  caching or the same resolution model, see DESIGN.md §2).
- If two different instances of the same class are used as dependencies on
  different routes, `shared_dependencies()` correctly treats them as not
  shared (it compares by identity), but they're shown with the same label
  in the tree/Mermaid unless the class itself is a closure — there's no
  generic way to give an arbitrary instance a readable name.
- `app.dependency_overrides` (the standard mechanism for injecting test
  doubles) isn't reflected: the tree shows the dependency as declared in
  the code, not the one that would actually run under an active override —
  it's a static graph, see DESIGN.md §2.
- The name of a parametrized dependency includes the `repr()` of its
  captured/bound values — if those values are secrets (tokens, API keys
  passed as defaults), they'll show up in `depgraph show`/`export` output.
  Don't paste that output into public channels without checking what
  parametrized dependencies your app has.
- Merging the path/dependencies for included routers (`include_router`)
  uses, when available, an internal method with no public contract that
  Starlette exposes to resolve routes at request time; if that shape
  changes in a future version, the package silently degrades to the
  previous behavior (no accumulated prefix or inclusion dependencies)
  instead of failing — the CI matrix runs against several FastAPI versions
  to catch it early if that happens.

## Why

FastAPI's DI system is implicit: nested `Depends()` resolve with no native
way to see the tree. Two questions this package answers that today have no
direct way to answer:

- Which expensive dependencies are being **recomputed** instead of cached
  (`use_cache=False`)?
- Which routes **share** an expensive dependency, so you know where to
  optimize once instead of in five different places?

See `DESIGN.md` for the rest of the scope and design decisions.
