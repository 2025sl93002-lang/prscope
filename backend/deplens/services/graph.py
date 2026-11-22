"""Dependency graph construction and analysis, backed by NetworkX.

Given the normalised packages and edges from a lockfile, this builds a directed
graph rooted at the project and answers the questions the UI needs: depth of
each package, how many packages depend on it, the concrete dependency paths
from the root, and upstream/downstream reachability for the impact simulator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import networkx as nx

from deplens.parsers.lockfile import ROOT_ID, Lockfile


@dataclass
class GraphNode:
    id: str
    name: str
    version: str
    scopes: List[str]
    is_direct: bool
    depth: int  # shortest number of hops from the root (direct deps are depth 1)
    dependents: int  # number of distinct packages that depend on this one
    path_count: int  # number of distinct dependency paths from the root
    resolved: Optional[str] = None


@dataclass
class DependencyGraph:
    root_id: str
    nodes: Dict[str, GraphNode]
    graph: nx.DiGraph = field(repr=False)

    def direct_ids(self) -> List[str]:
        return [n.id for n in self.nodes.values() if n.is_direct]

    def transitive_ids(self) -> List[str]:
        return [n.id for n in self.nodes.values() if not n.is_direct]

    def dependency_paths(self, node_id: str, limit: int = 25) -> List[List[str]]:
        """All simple paths from the root to ``node_id`` (capped at ``limit``)."""
        if node_id not in self.graph or node_id == self.root_id:
            return []
        paths: List[List[str]] = []
        try:
            for path in nx.all_simple_paths(self.graph, self.root_id, node_id, cutoff=40):
                paths.append(path)
                if len(paths) >= limit:
                    break
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return []
        return paths

    def downstream(self, node_id: str) -> Set[str]:
        """Everything the given package (transitively) depends on."""
        if node_id not in self.graph:
            return set()
        return set(nx.descendants(self.graph, node_id))

    def upstream(self, node_id: str) -> Set[str]:
        """Everything that (transitively) depends on the given package."""
        if node_id not in self.graph:
            return set()
        ancestors = set(nx.ancestors(self.graph, node_id))
        ancestors.discard(self.root_id)
        return ancestors

    def direct_dependents(self, node_id: str) -> List[str]:
        """Packages that depend on ``node_id`` directly (excluding the root)."""
        if node_id not in self.graph:
            return []
        return [p for p in self.graph.predecessors(node_id) if p != self.root_id]


def build_graph(lockfile: Lockfile) -> DependencyGraph:
    g = nx.DiGraph()
    g.add_node(ROOT_ID)
    for pkg in lockfile.packages.values():
        g.add_node(pkg.id, name=pkg.name, version=pkg.version)
    for edge in lockfile.edges:
        if edge.source in (ROOT_ID,) or edge.source in lockfile.packages:
            if edge.target in lockfile.packages:
                g.add_edge(edge.source, edge.target, edge_type=edge.edge_type, spec=edge.spec)

    # Shortest-path depth from the root for every reachable node.
    try:
        depths = nx.single_source_shortest_path_length(g, ROOT_ID)
    except nx.NodeNotFound:
        depths = {ROOT_ID: 0}

    nodes: Dict[str, GraphNode] = {}
    for pkg in lockfile.packages.values():
        dependents = len([p for p in g.predecessors(pkg.id) if p != ROOT_ID])
        nodes[pkg.id] = GraphNode(
            id=pkg.id,
            name=pkg.name,
            version=pkg.version,
            scopes=sorted(pkg.scopes) or ["prod"],
            is_direct=pkg.is_direct,
            depth=depths.get(pkg.id, -1),
            dependents=dependents,
            path_count=0,  # filled lazily below for direct+shallow nodes
            resolved=pkg.resolved,
        )

    dep_graph = DependencyGraph(root_id=ROOT_ID, nodes=nodes, graph=g)

    # Precompute path counts only for nodes with multiple predecessors (the
    # interesting "multiple dependency paths" case); others have exactly one.
    for node in nodes.values():
        preds = [p for p in g.predecessors(node.id)]
        if len(preds) <= 1:
            node.path_count = 1 if node.depth > 0 else 0
        else:
            node.path_count = len(dep_graph.dependency_paths(node.id, limit=100))

    return dep_graph
