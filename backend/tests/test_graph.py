from deplens.parsers.lockfile import parse_lockfile_text
from deplens.services.graph import build_graph

SMALL_LOCK = """
{"name":"app","version":"1.0.0","lockfileVersion":3,
 "packages":{
   "":{"name":"app","version":"1.0.0","dependencies":{"a":"^1.0.0","b":"^1.0.0"}},
   "node_modules/a":{"version":"1.0.0","dependencies":{"shared":"^1.0.0"}},
   "node_modules/b":{"version":"1.0.0","dependencies":{"shared":"^1.0.0","only-b":"^1.0.0"}},
   "node_modules/shared":{"version":"1.5.0"},
   "node_modules/only-b":{"version":"1.0.0"}
 }}
"""


def _graph():
    return build_graph(parse_lockfile_text(SMALL_LOCK))


def test_direct_and_transitive():
    g = _graph()
    assert set(n.name for n in g.nodes.values() if n.is_direct) == {"a", "b"}
    assert set(n.name for n in g.nodes.values() if not n.is_direct) == {"shared", "only-b"}


def test_depth():
    g = _graph()
    assert g.nodes["a@1.0.0"].depth == 1
    assert g.nodes["shared@1.5.0"].depth == 2


def test_multiple_dependency_paths():
    g = _graph()
    # shared is reached via a and via b -> two paths, two dependents.
    shared = g.nodes["shared@1.5.0"]
    assert shared.dependents == 2
    assert shared.path_count == 2
    paths = g.dependency_paths("shared@1.5.0")
    assert len(paths) == 2


def test_upstream_downstream():
    g = _graph()
    assert g.downstream("b@1.0.0") == {"shared@1.5.0", "only-b@1.0.0"}
    assert "b@1.0.0" in g.upstream("only-b@1.0.0")


def test_direct_dependents():
    g = _graph()
    deps = set(g.direct_dependents("shared@1.5.0"))
    assert deps == {"a@1.0.0", "b@1.0.0"}
