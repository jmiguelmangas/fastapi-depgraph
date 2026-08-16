"""Construye el árbol de dependencias de una app FastAPI leyendo
``route.dependant`` — la estructura que FastAPI ya construye internamente
al registrar cada ruta. No reparsea firmas a mano ni toca el motor de
resolución de dependencias.
"""

from __future__ import annotations

import asyncio
import functools
import inspect as pyinspect
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import NamedTuple

from fastapi import FastAPI
from fastapi.routing import APIRoute

_MAX_REPR_LEN = 60


@dataclass
class DependencyNode:
    """Un nodo del árbol: el endpoint (raíz) o una de sus dependencias."""

    name: str
    call: Callable | None
    is_async: bool
    use_cache: bool
    children: list[DependencyNode] = field(default_factory=list)

    def __iter__(self) -> Iterator[DependencyNode]:
        """Recorrido en profundidad incluyéndose a sí mismo."""
        yield self
        for child in self.children:
            yield from child


@dataclass
class RouteDependencyTree:
    path: str
    methods: list[str]
    root: DependencyNode


@dataclass
class DepGraphReport:
    routes: list[RouteDependencyTree]

    def shared_dependencies(self) -> dict[Callable, list[str]]:
        """Callables usados como dependencia en 2+ rutas, con los paths que
        los usan. Compara por identidad de función, no por nombre — dos
        funciones con el mismo nombre en módulos distintos no cuentan como
        la misma dependencia.
        """
        usage: dict[Callable, set[str]] = {}
        for route in self.routes:
            for node in route.root:
                if node is route.root or node.call is None:
                    continue
                usage.setdefault(node.call, set()).add(route.path)
        return {call: sorted(paths) for call, paths in usage.items() if len(paths) > 1}

    def uncached_dependencies(self) -> list[str]:
        """Nombres de dependencias con ``use_cache=False`` — se recomputan
        cada vez que aparecen en el árbol de resolución de un request.
        """
        names: set[str] = set()
        for route in self.routes:
            for node in route.root:
                if node is route.root:
                    continue
                if not node.use_cache:
                    names.add(node.name)
        return sorted(names)


def _node_name(call: Callable | None) -> str:
    if call is None:
        return "<desconocido>"
    if isinstance(call, functools.partial):
        # Depends(functools.partial(check_role, role="admin")) es un patrón
        # común para parametrizar una dependencia. Sin desenvolver, dos
        # partials sobre la misma función de base (role="admin" vs.
        # role="editor") comparten __name__/__qualname__ y se muestran como
        # si fueran la misma dependencia.
        inner = _node_name(call.func)
        bound = [_safe_repr(a) for a in call.args]
        bound += [f"{k}={_safe_repr(v)}" for k, v in call.keywords.items()]
        return f"{inner}({', '.join(bound)})" if bound else inner
    # Funciones y clases tienen __name__ propio. Una dependencia basada en
    # clase (``Depends(SomeClass())``) es una instancia sin __name__: nombrar
    # por repr() incluiría la dirección de memoria y cambiaría en cada
    # corrida, rompiendo la deduplicación de nodos en el export a Mermaid.
    # Se nombra por la clase de la instancia en ese caso.
    target = call if hasattr(call, "__name__") else type(call)
    module = getattr(target, "__module__", "") or ""
    qualname = getattr(target, "__qualname__", None) or target.__name__
    name = f"{module}.{qualname}" if module else qualname
    closure = _closure_repr(target)
    return f"{name}{closure}" if closure else name


def _closure_repr(func: object) -> str:
    """Dependencias generadas por una función factory (patrón común para
    parametrizar límites, roles, etc.) comparten __qualname__
    (``make_rate_limiter.<locals>.check``) aunque sean closures distintos
    con valores capturados distintos. Mostrar las variables capturadas evita
    confundirlos como si fueran la misma dependencia.
    """
    code = getattr(func, "__code__", None)
    cells = getattr(func, "__closure__", None)
    if not code or not cells or not code.co_freevars:
        return ""
    parts = []
    for var_name, cell in zip(code.co_freevars, cells):
        try:
            parts.append(f"{var_name}={_safe_repr(cell.cell_contents)}")
        except ValueError:
            continue  # celda todavía sin asignar
    return "{" + ", ".join(parts) + "}" if parts else ""


def _safe_repr(value: object) -> str:
    text = repr(value)
    if len(text) > _MAX_REPR_LEN:
        text = text[: _MAX_REPR_LEN - 1] + "…"
    return text


def _is_async(call: Callable | None) -> bool:
    if call is None:
        return False
    return bool(asyncio.iscoroutinefunction(call) or pyinspect.isasyncgenfunction(call))


def _build_node(dependant) -> DependencyNode:
    node = DependencyNode(
        name=_node_name(dependant.call),
        call=dependant.call,
        is_async=_is_async(dependant.call),
        use_cache=getattr(dependant, "use_cache", True),
    )
    for sub in getattr(dependant, "dependencies", None) or []:
        node.children.append(_build_node(sub))
    return node


class _ResolvedRoute(NamedTuple):
    dependant: object
    path: str
    methods: list[str]


def _iter_resolved_routes(routes) -> Iterator[_ResolvedRoute]:
    """Recorre ``routes`` en busca de rutas HTTP reales, bajando por routers
    incluidos con ``include_router()`` — sin importar cuántos niveles de
    anidamiento haya.

    En Starlette/FastAPI históricos, ``app.routes`` es una lista plana de
    ``APIRoute`` con ``path``/``dependant`` ya resueltos con el prefijo
    acumulado. En versiones más nuevas, un router incluido queda envuelto en
    un objeto interno sin tipo público, y la fusión de prefijo y de
    dependencias declaradas en ``include_router(..., dependencies=[...])``
    se difiere hasta el momento de resolver cada request — el ``APIRoute``
    original (accesible vía ``original_router.routes``) queda con el path
    *sin* prefijo y el dependant *sin* esas dependencias adicionales.

    Ese objeto expone igual el resultado ya fusionado a través de un método
    (``effective_candidates()``); se usa cuando está disponible, con
    fallback silencioso al router original si no existe o cambia de forma
    — se pierde el prefijo/las dependencias de inclusión en ese caso, pero
    nunca se rompe la introspección por completo.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield _ResolvedRoute(
                route.dependant, route.path, sorted(route.methods or [])
            )
            continue

        effective_candidates = getattr(route, "effective_candidates", None)
        if callable(effective_candidates):
            try:
                candidates = list(effective_candidates())
            except Exception:  # noqa: BLE001 — API interna sin contrato, fallback intencional
                candidates = None
            if candidates is not None:
                yield from _iter_resolved_routes(candidates)
                continue

        dependant = getattr(route, "dependant", None)
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if dependant is not None and path is not None and methods is not None:
            # _EffectiveRouteContext-like: ya resuelto (path con prefijo,
            # dependant fusionado). ``methods`` (a diferencia de una
            # APIWebSocketRoute, que también tiene ``dependant``/``path``
            # pero no rutas HTTP) confirma que es una ruta HTTP real.
            yield _ResolvedRoute(dependant, path, sorted(methods))
            continue

        nested = getattr(route, "routes", None)
        if nested is None:
            original_router = getattr(route, "original_router", None)
            nested = getattr(original_router, "routes", None)
        if nested:
            yield from _iter_resolved_routes(nested)


def inspect_app(app: FastAPI) -> DepGraphReport:
    """Punto de entrada principal: recorre las rutas de ``app`` y construye
    un árbol de dependencias por cada una, a partir de ``route.dependant``.
    """
    routes: list[RouteDependencyTree] = []
    for resolved in _iter_resolved_routes(app.routes):
        root = _build_node(resolved.dependant)
        routes.append(
            RouteDependencyTree(path=resolved.path, methods=resolved.methods, root=root)
        )
    return DepGraphReport(routes=routes)
