from __future__ import annotations

import argparse
import importlib

from .export import to_ascii, to_mermaid
from .inspect import inspect_app


def _load_app(import_path: str):
    if import_path.count(":") != 1:
        raise SystemExit(
            "The argument must have the form 'module:app', e.g. myapp.main:app"
        )
    module_name, attr = import_path.split(":")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise SystemExit(f"Could not import module '{module_name}': {exc}")
    app = getattr(module, attr, None)
    if app is None:
        raise SystemExit(f"Could not find '{attr}' in module '{module_name}'")
    return app


def _cmd_show(args: argparse.Namespace) -> None:
    app = _load_app(args.app)
    report = inspect_app(app)
    print(to_ascii(report), end="")

    if args.shared:
        shared = report.shared_dependencies()
        print("\nDependencies shared across routes:")
        if not shared:
            print("  (none)")
        for call, paths in shared.items():
            name = getattr(call, "__qualname__", getattr(call, "__name__", str(call)))
            print(f"  {name}: {', '.join(paths)}")

    if args.uncached:
        uncached = report.uncached_dependencies()
        print("\nDependencies with use_cache=False:")
        if not uncached:
            print("  (none)")
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
        description="Introspect the Depends() tree of a FastAPI app",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Print the dependency tree as ASCII")
    show.add_argument("app", help="App to inspect, e.g. myapp.main:app")
    show.add_argument(
        "--shared",
        action="store_true",
        help="List dependencies shared across routes",
    )
    show.add_argument(
        "--uncached", action="store_true", help="List dependencies with use_cache=False"
    )
    show.set_defaults(func=_cmd_show)

    export = sub.add_parser("export", help="Export the graph to a format")
    export.add_argument("app", help="App to inspect, e.g. myapp.main:app")
    export.add_argument("--format", choices=["mermaid"], default="mermaid")
    export.set_defaults(func=_cmd_export)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
