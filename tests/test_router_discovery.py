from fastapi_depgraph import inspect_app
from tests.fixtures.router_app import app, check_rate_limit
from tests.fixtures.websocket_app import app as websocket_app


def test_finds_routes_registered_via_include_router():
    # En versiones recientes de Starlette, las rutas de un APIRouter
    # incluido con include_router() ya no aparecen como APIRoute planas en
    # app.routes — sin bajar por el router original, esto devolvía 0 rutas.
    report = inspect_app(app)
    paths = {route.path for route in report.routes}
    assert paths == {"/items/", "/health"}


def test_class_based_dependency_named_by_class_not_repr():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/items/")
    names = [node.name for node in items_route.root]
    assert "tests.fixtures.router_app.RateLimiter" in names
    # repr() por defecto de una instancia incluye la dirección de memoria
    # ("<...RateLimiter object at 0x...>"), lo que rompería la
    # deduplicación de nodos en el export a Mermaid entre corridas.
    assert not any("0x" in name for name in names)


def test_class_based_dependency_keeps_identity_for_call():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/items/")
    calls = [node.call for node in items_route.root]
    assert check_rate_limit in calls


def test_websocket_routes_are_excluded():
    # APIWebSocketRoute también tiene .dependant y .path (igual que una ruta
    # HTTP resuelta), pero no .methods — sin ese chequeo, se cuela en el
    # árbol con una lista de métodos vacía.
    report = inspect_app(websocket_app)
    paths = {route.path for route in report.routes}
    assert paths == {"/x"}
