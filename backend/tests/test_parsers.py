import pytest

from deplens.parsers import parse_manifest_text
from deplens.parsers.lockfile import ROOT_ID, parse_lockfile_text

# --- manifest ---------------------------------------------------------------


def test_manifest_parses_all_scopes():
    m = parse_manifest_text(
        """{"name":"app","version":"1.0.0",
            "dependencies":{"a":"^1.0.0"},
            "devDependencies":{"b":"~2.0.0"},
            "optionalDependencies":{"c":"3.0.0"},
            "peerDependencies":{"d":"*"},
            "scripts":{"build":"tsc"}}"""
    )
    assert m.name == "app"
    scopes = {d.name: d.scope for d in m.dependencies}
    assert scopes == {"a": "prod", "b": "dev", "c": "optional", "d": "peer"}
    assert m.scripts["build"] == "tsc"


def test_manifest_declared_prefers_prod():
    m = parse_manifest_text(
        '{"dependencies":{"x":"^1.0.0"},"devDependencies":{"x":"^2.0.0"}}'
    )
    assert m.declared()["x"].scope == "prod"


def test_manifest_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_manifest_text("{not json")


def test_manifest_non_object_raises():
    with pytest.raises(ValueError):
        parse_manifest_text("[1,2,3]")


def test_manifest_malformed_deps_warns():
    m = parse_manifest_text('{"dependencies":"oops"}')
    assert m.dependencies == []
    assert m.warnings


# --- lockfile (v3 real fixture) ---------------------------------------------


def test_lockfile_v3_fixture(demo_project):
    lock = parse_lockfile_text((demo_project / "package-lock.json").read_text())
    assert lock.fmt == "v3"
    assert lock.root_name == "deplens-demo"
    # The fixture pins old versions on purpose.
    assert "lodash@4.17.11" in lock.packages
    assert "express@4.17.1" in lock.packages
    # Direct deps are flagged.
    directs = {p.name for p in lock.packages.values() if p.is_direct}
    assert {"lodash", "express", "minimist", "moment"} <= directs
    # Edges exist from the root and between packages.
    assert any(e.source == ROOT_ID for e in lock.edges)
    assert any(e.source != ROOT_ID for e in lock.edges)


def test_lockfile_v2_packages_format():
    lock = parse_lockfile_text(
        """{"name":"app","version":"1.0.0","lockfileVersion":2,
            "packages":{
              "":{"name":"app","version":"1.0.0","dependencies":{"a":"^1.0.0"}},
              "node_modules/a":{"version":"1.1.0","dependencies":{"b":"^2.0.0"}},
              "node_modules/b":{"version":"2.3.0"}
            }}"""
    )
    assert lock.fmt == "v2"
    assert lock.packages["a@1.1.0"].is_direct
    assert not lock.packages["b@2.3.0"].is_direct
    # a -> b edge resolved via node_modules walk-up.
    assert any(e.source == "a@1.1.0" and e.target == "b@2.3.0" for e in lock.edges)


def test_lockfile_v1_dependencies_format():
    lock = parse_lockfile_text(
        """{"name":"app","version":"1.0.0","lockfileVersion":1,
            "dependencies":{
              "a":{"version":"1.1.0","requires":{"b":"^2.0.0"},
                   "dependencies":{"b":{"version":"2.3.0"}}},
              "b":{"version":"2.0.0"}
            }}"""
    )
    assert lock.fmt == "v1"
    # Nested b@2.3.0 (under a) and top-level b@2.0.0 are distinct nodes.
    assert "b@2.3.0" in lock.packages
    assert "b@2.0.0" in lock.packages
    # a requires b -> resolves to the nested 2.3.0 (nearest scope wins).
    assert any(e.source == "a@1.1.0" and e.target == "b@2.3.0" for e in lock.edges)


def test_lockfile_unsupported_structure_raises():
    with pytest.raises(ValueError):
        parse_lockfile_text('{"lockfileVersion": 99, "something": {}}')


def test_lockfile_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_lockfile_text("}{")
