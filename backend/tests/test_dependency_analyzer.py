"""Tests for dependency extraction & resolution. SPDX-License-Identifier: MIT"""
from prscope.services import dependency_analyzer as dep


def test_extract_python_imports():
    src = "import os\nfrom a.b import c\nfrom . import d\nfrom ..e import f\n"
    imports = dep.extract_python_imports(src)
    modules = [m for m, _lvl, _names in imports]
    assert "os" in modules
    assert "a.b" in modules
    levels = {m: lvl for m, lvl, _ in imports}
    assert levels.get("e") == 2  # from ..e


def test_extract_js_imports():
    src = (
        "import x from './x';\n"
        "import {y} from '../lib/y';\n"
        "const z = require('./z');\n"
        "import('./lazy');\n"
        "import React from 'react';\n"
    )
    specs = dep.extract_js_imports(src)
    assert "./x" in specs
    assert "../lib/y" in specs
    assert "./z" in specs
    assert "./lazy" in specs
    assert "react" in specs  # bare specifier extracted (resolved as external later)


def test_js_relative_resolution():
    files = {"src/a.ts", "src/lib/y.ts", "src/lib/index.ts"}
    assert dep._resolve_js_relative("src/a.ts", "./lib/y", files) == "src/lib/y.ts"
    assert dep._resolve_js_relative("src/a.ts", "./lib", files) == "src/lib/index.ts"
    assert dep._resolve_js_relative("src/a.ts", "react", files) is None


def test_demo_graph_edges(demo_repo):
    from prscope.services import git_diff
    diff = git_diff.compute_diff(demo_repo, "main", "feature/payment-refactor")
    graph = dep.build_dependency_graph(demo_repo, diff.target_sha)
    edges = graph.edge_set()
    assert ("src/payment/checkout_controller.py", "src/payment/payment_service.py") in edges
    assert ("src/payment/order_processor.py", "src/payment/payment_service.py") in edges
    assert ("tests/test_payment_service.py", "src/payment/payment_service.py") in edges
    assert graph.python_files >= 4
