from fastapi_depgraph import inspect_app
from fastapi_depgraph.export import to_mermaid
from tests.fixtures.parametrized_app import app, limiter_5, limiter_10


def test_nested_router_prefixes_accumulate_in_path():
    # api_router (prefix=/api) incluye v1_router (prefix=/v1) incluye
    # items_router (prefix=/items) — el path final debe acumular los tres.
    report = inspect_app(app)
    paths = {route.path for route in report.routes}
    assert paths == {"/api/v1/items/", "/api/ping"}


def test_closures_with_different_captured_values_get_distinct_names():
    report = inspect_app(app)
    items_route = next(r for r in report.routes if r.path == "/api/v1/items/")
    names = [node.name for node in items_route.root]
    assert any("times=5" in name for name in names)
    assert any("times=10" in name for name in names)


def test_closures_with_different_captured_values_are_not_shared():
    report = inspect_app(app)
    shared = report.shared_dependencies()
    assert limiter_5 not in shared
    assert limiter_10 not in shared


def test_functools_partial_dependencies_get_distinct_names():
    report = inspect_app(app)
    ping_route = next(r for r in report.routes if r.path == "/api/ping")
    names = [node.name for node in ping_route.root]
    assert any("role='admin'" in name for name in names)
    assert any("role='editor'" in name for name in names)


def test_mermaid_export_escapes_angle_brackets_in_closure_labels():
    report = inspect_app(app)
    mermaid = to_mermaid(report)
    # <locals> sin escapar se interpreta como una etiqueta HTML en Mermaid.
    assert "<locals>" not in mermaid
    assert "#lt;locals#gt;" in mermaid
