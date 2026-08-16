# TASKS

## Done (v0.1)

- [x] `inspect_app()` builds the per-route tree from `route.dependant`
- [x] `DepGraphReport.shared_dependencies()` — compares by identity, not
      by name
- [x] `DepGraphReport.uncached_dependencies()`
- [x] Sync/async detection per node
- [x] ASCII export (`to_ascii`) and Mermaid (`to_mermaid`, with node dedup)
- [x] CLI: `depgraph show [--shared] [--uncached]`, `depgraph export --format mermaid`
- [x] Test fixture with a real case (shared deps + `use_cache=False` +
      async dependency) and 6 passing tests
- [x] Clean lint (`ruff check` + `ruff format`)
- [x] Critical fix: `inspect_app()` returned 0 routes on apps using
      `APIRouter` + `include_router()` on recent Starlette (routes wrapped
      in an internal object, no longer flat in `app.routes`).
- [x] Critical fix: even after fixing the above, the prefix from
      `include_router(prefix=...)` and the dependencies from
      `include_router(dependencies=...)`/`FastAPI(dependencies=...)` never
      reached the tree (path/dependant left unmerged) — reported
      *incorrect* paths, not just incomplete ones. Fixed using
      `effective_candidates()` when available, with a fallback if not.
- [x] Fix: class-based dependencies (`Depends(SomeClass())`) were named
      using `repr()` (memory address included, unstable across runs)
      instead of the class name.
- [x] Fix: dependencies parametrized by factory/closure or
      `functools.partial` (a very common pattern: rate limiting, roles,
      pagination) collapsed into a single indistinguishable name even when
      functionally distinct. Now shown with the captured/bound values
      (`check{times=5}`, `require_role(role='admin')`).
- [x] Fix: WebSocket routes leaked into the tree after the router fix
      (they have `.dependant`/`.path` but no `.methods`).
- [x] Fix: the Mermaid export didn't escape `"`/`<`/`>` in labels — once
      closures/partial dependencies could show captured values, one
      containing those characters broke the syntax or got interpreted as
      HTML (`<locals>`).
- [x] Test coverage for `cli.py` (previously at 0): `show`, `--shared`,
      `--uncached`, `export --format mermaid`, and the three failure modes
      of `_load_app` (malformed path, missing module, missing attribute).
- [x] Test for `app.dependency_overrides` — documents that the graph is
      static and doesn't reflect overrides (expected behavior, see
      DESIGN.md §2).
- [x] See DESIGN.md §7 for details on each fix and the regression fixtures
      (`router_app.py`, `parametrized_app.py`, `websocket_app.py`).
- [x] Whole repo (docs, code comments, CLI output strings, tests)
      translated to English for a public, community-facing package.

## Pending before publishing to PyPI

- [x] CI on GitHub Actions: lint + tests, matrix against 3 FastAPI
      versions (0.110, 0.120, 0.141)
- [x] `.github/workflows/release.yml` (same pattern as errand: build with
      `uv build`, publish via `pypa/gh-action-pypi-publish` + OIDC,
      triggered by `v*` tags) and the `pypi` GitHub environment created on
      the repo.
- [x] PyPI-side trusted publisher registered (pending publisher: owner
      `jmiguelmangas`, repository `fastapi-depgraph`, workflow
      `release.yml`, environment `pypi`).
- [x] `LICENSE` (MIT, consistent with what's declared in `pyproject.toml`)
- [x] A bigger example in `examples/` (10-15 routes) for the README — it's
      what sells the package at a glance
- [ ] Decide and document the community gesture toward `fastapi-di-viz`
      (an issue mentioning this new project — see CLAUDE.md)
- [x] Name confirmed available on PyPI (`fastapi-depgraph`, verified
      2026-08-16 via `pypi.org/pypi/fastapi-depgraph/json` → 404)
- [ ] Tag and push `v0.1.0` to trigger the release workflow and the actual
      publish

## v0.2 (after publishing 0.1)

- [ ] `TimedDepends` — drop-in replacement for `Depends()`, opt-in, without
      touching `solve_dependencies` (see DESIGN.md §3)
- [ ] Optional debug endpoint to expose the timing
