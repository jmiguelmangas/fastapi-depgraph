from fastapi_depgraph import inspect_app
from tests.fixtures.sample_app import (
    app,
    get_current_user,
    get_request_id,
    get_settings,
)


def test_finds_all_routes():
    report = inspect_app(app)
    paths = {route.path for route in report.routes}
    assert paths == {"/me", "/items"}


def test_root_node_is_the_endpoint():
    report = inspect_app(app)
    me_route = next(r for r in report.routes if r.path == "/me")
    assert me_route.root.name.endswith(".me") or me_route.root.name == "me"


def test_shared_dependencies_detects_get_settings_across_routes():
    report = inspect_app(app)
    shared = report.shared_dependencies()
    assert get_settings in shared
    assert shared[get_settings] == ["/items", "/me"]


def test_no_false_positive_for_non_shared_dependency():
    report = inspect_app(app)
    shared = report.shared_dependencies()
    # get_db solo aparece en /items, no debería figurar como compartida
    from tests.fixtures.sample_app import get_db

    assert get_db not in shared


def test_uncached_dependencies_flags_use_cache_false():
    report = inspect_app(app)
    uncached = report.uncached_dependencies()
    assert any(get_request_id.__name__ in name for name in uncached)


def test_dependency_overrides_do_not_affect_the_static_graph():
    # inspect_app() lee el árbol declarado en route.dependant, no el que
    # efectivamente correría un request — dependency_overrides es un
    # mecanismo de resolución en tiempo de ejecución (típico en tests) que
    # no lo toca.
    def fake_current_user():
        return {"user": "fake"}

    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        report = inspect_app(app)
        me_route = next(r for r in report.routes if r.path == "/me")
        names = [n.call for n in me_route.root]
        assert get_current_user in names
        assert fake_current_user not in names
    finally:
        app.dependency_overrides.clear()


def test_async_vs_sync_detection():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/items")
    # get_db es una dependencia async (async generator)
    names_async = {n.name: n.is_async for n in items_route.root}
    db_entries = [
        is_async for name, is_async in names_async.items() if "get_db" in name
    ]
    assert db_entries and all(db_entries)
