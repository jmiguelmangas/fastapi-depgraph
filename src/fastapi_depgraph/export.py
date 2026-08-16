"""Report exporters: an ASCII tree for the terminal and a Mermaid graph."""

from __future__ import annotations

import hashlib

from .inspect import DependencyNode, DepGraphReport


def to_ascii(report: DepGraphReport) -> str:
    lines: list[str] = []
    for route in report.routes:
        header = f"{','.join(route.methods)} {route.path}"
        lines.append(header)
        _ascii_node(route.root, prefix="  ", lines=lines, is_root=True)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _ascii_node(
    node: DependencyNode,
    prefix: str,
    lines: list[str],
    is_root: bool,
    is_last: bool = True,
) -> None:
    kind = "async" if node.is_async else "sync"
    marker = "" if node.use_cache else " [no-cache]"
    if is_root:
        lines.append(f"{prefix}{node.name} ({kind}){marker}")
        child_prefix = prefix
    else:
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.name} ({kind}){marker}")
        child_prefix = prefix + ("    " if is_last else "│   ")

    for i, child in enumerate(node.children):
        _ascii_node(
            child,
            child_prefix,
            lines,
            is_root=False,
            is_last=(i == len(node.children) - 1),
        )


def _safe_id(name: str) -> str:
    # id stable across runs (hash() of a str has a per-process random seed)
    return "n" + hashlib.md5(name.encode()).hexdigest()[:8]


def _mermaid_escape(text: str) -> str:
    # The name of a parametrized dependency (functools.partial or a
    # closure) may include the repr() of an arbitrary value — with quotes,
    # "<"/">", etc. Left unescaped, it either breaks the label's syntax
    # (quote-delimited) or gets interpreted as an HTML tag.
    return (
        text.replace("&", "#amp;")
        .replace('"', "#quot;")
        .replace("<", "#lt;")
        .replace(">", "#gt;")
    )


def to_mermaid(report: DepGraphReport) -> str:
    lines = ["graph TD;"]
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()

    def declare(node: DependencyNode) -> None:
        node_id = _safe_id(node.name)
        if node_id not in seen_nodes:
            seen_nodes.add(node_id)
            label = node.name if node.use_cache else f"{node.name} [no-cache]"
            lines.append(f'    {node_id}["{_mermaid_escape(label)}"]')

    def walk(node: DependencyNode) -> None:
        declare(node)
        for child in node.children:
            declare(child)
            edge = (_safe_id(node.name), _safe_id(child.name))
            if edge not in seen_edges:
                seen_edges.add(edge)
                lines.append(f"    {edge[0]} --> {edge[1]}")
            walk(child)

    for route in report.routes:
        walk(route.root)

    return "\n".join(lines) + "\n"
