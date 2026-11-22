"""Usage analysis: find evidence of whether a dependency is actually used.

This is deliberately conservative. A dependency can be used indirectly (plugins,
CLI binaries invoked from scripts, framework conventions, dynamic requires), so
DepLens never *confidently* declares a package unused from a text search alone.
It reports evidence, a detection method, and a calibrated confidence level, and
leaves the judgement to the developer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from deplens.parsers.manifest import Manifest
from deplens.services.safety import iter_source_files, read_text_capped

SOURCE_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte"}
CONFIG_EXTENSIONS = {".json", ".yml", ".yaml", ".toml"}
CONFIG_FILENAMES = {
    "babel.config.js",
    ".babelrc",
    ".eslintrc",
    ".eslintrc.js",
    ".eslintrc.json",
    ".prettierrc",
    "webpack.config.js",
    "vite.config.js",
    "vite.config.ts",
    "rollup.config.js",
    "jest.config.js",
    "tsconfig.json",
    "postcss.config.js",
    "tailwind.config.js",
}

# Statuses, from strongest to weakest evidence.
CONFIRMED = "confirmed"
POTENTIAL = "potential"
NONE = "none"
INCOMPLETE = "incomplete"


@dataclass
class UsageEvidence:
    file: str  # path relative to project root
    line: int
    method: str  # import | require | dynamic-import | config | script-bin
    snippet: str


@dataclass
class UsageResult:
    package: str
    status: str
    confidence: str  # high | medium | low
    explanation: str
    evidence: List[UsageEvidence] = field(default_factory=list)


def _escape(pkg: str) -> str:
    return re.escape(pkg)


def _build_patterns(pkg: str):
    """Regexes that match an import/require of ``pkg`` or a subpath of it."""
    p = _escape(pkg)
    # name or name/subpath, as a quoted string.
    quoted = rf"['\"]{p}(?:/[^'\"]*)?['\"]"
    return {
        "require": re.compile(rf"require\(\s*{quoted}\s*\)"),
        "import": re.compile(rf"""(?:import\b[^;\n]*?\bfrom\s*{quoted}|import\s*{quoted})"""),
        "dynamic-import": re.compile(rf"import\(\s*{quoted}\s*\)"),
        "export-from": re.compile(rf"export\b[^;\n]*?\bfrom\s*{quoted}"),
    }


def analyze_usage(
    root: Path,
    manifest: Manifest,
    target_packages: Optional[List[str]] = None,
) -> Dict[str, UsageResult]:
    """Scan source files for usage evidence of each declared dependency.

    Only direct dependencies are analysed — transitive packages are pulled in by
    other packages, so project-source usage is not a meaningful signal for them.
    """
    declared = manifest.declared()
    packages = target_packages if target_packages is not None else list(declared.keys())
    results: Dict[str, UsageResult] = {
        pkg: UsageResult(package=pkg, status=NONE, confidence="low", explanation="", evidence=[])
        for pkg in packages
    }
    patterns = {pkg: _build_patterns(pkg) for pkg in packages}

    scanned_any = False
    # 1) Source files — strongest evidence.
    for path in iter_source_files(root, SOURCE_EXTENSIONS):
        scanned_any = True
        text = read_text_capped(path)
        if not text:
            continue
        rel = str(path.relative_to(root))
        lines = text.splitlines()
        for pkg in packages:
            pats = patterns[pkg]
            if pkg not in text:
                continue  # fast reject
            for lineno, line in enumerate(lines, start=1):
                for method, rx in pats.items():
                    if rx.search(line):
                        res = results[pkg]
                        if len(res.evidence) < 25:
                            res.evidence.append(
                                UsageEvidence(
                                    file=rel,
                                    line=lineno,
                                    method="import" if method in ("import", "export-from")
                                    else method,
                                    snippet=line.strip()[:200],
                                )
                            )

    # 2) Config files and scripts — weaker evidence (plugins, presets, binaries).
    for path in iter_source_files(root, CONFIG_EXTENSIONS):
        name = path.name
        # package.json is not usage evidence: its dependency block is a declaration,
        # and its scripts are handled separately in step 3.
        if name == "package.json":
            continue
        is_config = name in CONFIG_FILENAMES or name.endswith(
            ("rc", ".yml", ".yaml", ".toml")
        )
        if not is_config:
            continue
        text = read_text_capped(path)
        if not text:
            continue
        rel = str(path.relative_to(root))
        lines = text.splitlines()
        for pkg in packages:
            if pkg not in text:
                continue
            for lineno, line in enumerate(lines, start=1):
                if pkg in line:
                    res = results.get(pkg)
                    if res is None:
                        continue
                    if len(res.evidence) < 25:
                        res.evidence.append(
                            UsageEvidence(
                                file=rel, line=lineno, method="config",
                                snippet=line.strip()[:200],
                            )
                        )

    # 3) package.json scripts: a package's bin name used in a script command.
    for pkg in packages:
        for script_name, command in manifest.scripts.items():
            if re.search(rf"(^|\s|&&|\|){_escape(pkg)}(\s|$|/)", command):
                res = results[pkg]
                if len(res.evidence) < 25:
                    res.evidence.append(
                        UsageEvidence(
                            file="package.json", line=0, method="script-bin",
                            snippet=f"scripts.{script_name}: {command[:160]}",
                        )
                    )

    # Classify.
    for res in results.values():
        _classify(res, scanned_any)
    return results


def _classify(res: UsageResult, scanned_any: bool) -> None:
    if not scanned_any:
        res.status = INCOMPLETE
        res.confidence = "low"
        res.explanation = "No source files were found to analyse."
        return
    strong = [e for e in res.evidence if e.method in ("import", "require", "dynamic-import")]
    weak = [e for e in res.evidence if e.method in ("config", "script-bin")]
    if strong:
        res.status = CONFIRMED
        res.confidence = "high"
        res.explanation = (
            f"Imported/required directly in {len({e.file for e in strong})} source file(s)."
        )
    elif weak:
        res.status = POTENTIAL
        res.confidence = "medium"
        res.explanation = (
            "Referenced only in configuration or scripts. The package may be a plugin, "
            "preset, or CLI tool used indirectly rather than imported in source."
        )
    else:
        res.status = NONE
        res.confidence = "low"
        res.explanation = (
            "No import, require, config, or script reference was found. This does NOT "
            "prove the package is unused — it may be loaded dynamically, via a framework "
            "convention, or by a build tool. Verify before removing."
        )
