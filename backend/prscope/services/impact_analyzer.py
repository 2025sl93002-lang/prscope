"""Change-impact analyzer.

Given the dependency graph and the set of changed files, determines which files
are directly or indirectly affected. Impact propagates along **reverse**
dependency edges: if a changed file ``A`` is imported by ``B``, then ``B`` is
potentially affected, and anything importing ``B`` is affected indirectly.

Every relationship is labelled by how it was detected (direct edge vs. inferred
multi-hop path). Static analysis approximates — it never guarantees — runtime
impact. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class ImpactResult:
    nodes: list[dict] = field(default_factory=list)  # {path, impact_type, distance, category}
    affected_direct: list[str] = field(default_factory=list)
    affected_indirect: list[str] = field(default_factory=list)


def build_adjacency(
    edges: list[tuple[str, str, str]]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (forward, reverse) adjacency maps.

    forward[a] = files that *a imports*.
    reverse[a] = files that *import a*.
    """
    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for src, dst, _rel in edges:
        forward[src].add(dst)
        reverse[dst].add(src)
    return forward, reverse


def compute_impact(
    changed_paths: list[str],
    edges: list[tuple[str, str, str]],
    categories: dict[str, str] | None = None,
) -> ImpactResult:
    categories = categories or {}
    _forward, reverse = build_adjacency(edges)
    changed = set(changed_paths)

    distance: dict[str, int] = {p: 0 for p in changed}
    queue: deque[str] = deque(changed)
    while queue:
        node = queue.popleft()
        d = distance[node]
        for importer in reverse.get(node, ()):  # files that depend on `node`
            if importer not in distance or distance[importer] > d + 1:
                distance[importer] = d + 1
                queue.append(importer)

    result = ImpactResult()
    for path, dist in sorted(distance.items(), key=lambda kv: (kv[1], kv[0])):
        if dist == 0:
            impact_type = "changed"
        elif dist == 1:
            impact_type = "direct"
            result.affected_direct.append(path)
        else:
            impact_type = "indirect"
            result.affected_indirect.append(path)
        result.nodes.append(
            {
                "path": path,
                "impact_type": impact_type,
                "distance": dist,
                "category": categories.get(path),
            }
        )
    return result


def _looks_like_test(path: str) -> bool:
    p = path.lower()
    base = p.rsplit("/", 1)[-1]
    return (
        "/test" in p
        or "/tests/" in p
        or "/__tests__/" in p
        or "/spec/" in p
        or base.startswith("test_")
        or base.endswith(("_test.py", "_test.go", ".test.ts", ".test.tsx", ".test.js",
                          ".test.jsx", ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx"))
    )


def file_impact(
    path: str,
    edges: list[tuple[str, str, str]],
    categories: dict[str, str] | None = None,
) -> dict:
    """Per-file impact view used by the Impact Explorer."""
    categories = categories or {}
    forward, reverse = build_adjacency(edges)
    direct_deps = sorted(forward.get(path, set()))
    reverse_deps = sorted(reverse.get(path, set()))

    # Downstream = reverse-dependency closure beyond the direct importers.
    downstream: set[str] = set()
    queue: deque[str] = deque(reverse_deps)
    seen = set(reverse_deps) | {path}
    while queue:
        node = queue.popleft()
        for importer in reverse.get(node, ()):
            if importer not in seen:
                seen.add(importer)
                downstream.add(importer)
                queue.append(importer)

    related_tests = sorted(d for d in reverse_deps if _looks_like_test(d))

    explanations: list[str] = []
    for dep in reverse_deps[:25]:
        rel = "tests" if _looks_like_test(dep) else "imports"
        explanations.append(f"{dep} {rel} {path} (direct dependency).")
    for dep in sorted(downstream)[:25]:
        explanations.append(
            f"{dep} transitively depends on {path} (indirect potential impact)."
        )

    return {
        "path": path,
        "category": categories.get(path),
        "direct_dependencies": direct_deps,
        "reverse_dependencies": reverse_deps,
        "downstream_impact": sorted(downstream),
        "related_tests": related_tests,
        "path_explanations": explanations,
    }


def build_graph_payload(
    all_paths: set[str],
    edges: list[tuple[str, str, str]],
    impact: ImpactResult,
    categories: dict[str, str] | None = None,
    changed_paths: list[str] | None = None,
) -> dict:
    """Assemble nodes+edges for the frontend graph.

    Only includes files that participate in an edge or are changed/affected, to
    keep the graph legible for large repositories.
    """
    categories = categories or {}
    changed = set(changed_paths or [])
    impact_by_path = {n["path"]: n for n in impact.nodes}

    relevant: set[str] = set(changed) | set(impact_by_path)
    for src, dst, _ in edges:
        if src in relevant or dst in relevant:
            relevant.add(src)
            relevant.add(dst)

    nodes = []
    for p in sorted(relevant):
        node = impact_by_path.get(p)
        impact_type = node["impact_type"] if node else "unaffected"
        distance = node["distance"] if node else -1
        nodes.append(
            {
                "id": p,
                "label": p.rsplit("/", 1)[-1],
                "impact_type": impact_type,
                "category": categories.get(p),
                "distance": distance,
            }
        )
    graph_edges = [
        {"source": s, "target": d, "relation_type": rel, "detection": "direct"}
        for s, d, rel in edges
        if s in relevant and d in relevant
    ]
    return {"nodes": nodes, "edges": graph_edges}
