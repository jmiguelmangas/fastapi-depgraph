from fastapi_depgraph import inspect_app
from tests.fixtures.router_app import app, check_rate_limit
from tests.fixtures.websocket_app import app as websocket_app


def test_finds_routes_registered_via_include_router():
    # On recent Starlette versions, routes from an APIRouter included with
    # include_router() no longer show up as flat APIRoute objects in
    # app.routes — without descending into the original router, this
    # returned 0 routes.
    report = inspect_app(app)
    paths = {route.path for route in report.routes}
    assert paths == {"/items/", "/health"}


def test_class_based_dependency_named_by_class_not_repr():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/items/")
    names = [node.name for node in items_route.root]
    assert "tests.fixtures.router_app.RateLimiter" in names
    # An instance's default repr() includes the memory address
    # ("<...RateLimiter object at 0x...>"), which would break node
    # deduplication in the Mermaid export across runs.
    assert not any("0x" in name for name in names)


def test_class_based_dependency_keeps_identity_for_call():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/items/")
    calls = [node.call for node in items_route.root]
    assert check_rate_limit in calls


def test_websocket_routes_are_excluded():
    # APIWebSocketRoute also has .dependant and .path (just like a resolved
    # HTTP route), but no .methods — without that check, it leaks into the
    # tree with an empty methods list.
    report = inspect_app(websocket_app)
    paths = {route.path for route in report.routes}
    assert paths == {"/x"}
