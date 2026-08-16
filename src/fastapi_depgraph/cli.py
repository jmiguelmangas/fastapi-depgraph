from __future__ import annotations

import argparse
import importlib

from .export import to_ascii, to_mermaid
from .inspect import inspect_app


def _load_app(import_path: str):
    if import_path.count(":") != 1:
        raise SystemExit(
            "El argumento debe tener forma 'modulo:app', ej. myapp.main:app"
        )
    module_name, attr = import_path.split(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise SystemExit(f"No se pudo importar el módulo '{module_name}': {exc}")
    app = getattr(module, attr, None)
    if app is None:
        raise SystemExit(f"No se encontró '{attr}' en el módulo '{module_name}'")
    return app


def _cmd_show(args: argparse.Namespace) -> None:
    app = _load_app(args.app)
    report = inspect_app(app)
    print(to_ascii(report), end="")

    if args.shared:
        shared = report.shared_dependencies()
        print("\nDependencias compartidas entre rutas:")
        if not shared:
            print("  (ninguna)")
        for call, paths in shared.items():
            name = getattr(call, "__qualname__", getattr(call, "__name__", str(call)))
            print(f"  {name}: {', '.join(paths)}")

    if args.uncached:
        uncached = report.uncached_dependencies()
        print("\nDependencias con use_cache=False:")
        if not uncached:
            print("  (ninguna)")
        for name in uncached:
            print(f"  {name}")


def _cmd_export(args: argparse.Namespace) -> None:
    app = _load_app(args.app)
    report = inspect_app(app)
    if args.format == "mermaid":
        print(to_mermaid(report), end="")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Introspección del árbol de Depends() de una app FastAPI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Imprime el árbol de dependencias en ASCII")
    show.add_argument("app", help="App a inspeccionar, ej. myapp.main:app")
    show.add_argument(
        "--shared",
        action="store_true",
        help="Lista dependencias compartidas entre rutas",
    )
    show.add_argument(
        "--uncached", action="store_true", help="Lista dependencias con use_cache=False"
    )
    show.set_defaults(func=_cmd_show)

    export = sub.add_parser("export", help="Exporta el grafo a un formato")
    export.add_argument("app", help="App a inspeccionar, ej. myapp.main:app")
    export.add_argument("--format", choices=["mermaid"], default="mermaid")
    export.set_defaults(func=_cmd_export)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
