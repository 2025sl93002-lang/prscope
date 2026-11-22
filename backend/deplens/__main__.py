"""Command-line entry point: ``python -m deplens`` / ``deplens``.

Subcommands:
  serve   Run the API server (default).
  scan    Scan a project from the CLI and print a short summary.
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def _serve(args):
    import uvicorn

    uvicorn.run("deplens.main:app", host=args.host, port=args.port, reload=args.reload)


def _scan(args):
    from deplens.db import get_db
    from deplens.scanner import ScanError, run_scan
    from deplens.services.safety import PathSafetyError

    db = get_db()
    try:
        scan_id = asyncio.run(run_scan(db, args.path, online=not args.offline))
    except (ScanError, PathSafetyError) as exc:
        print(f"Scan failed: {exc}", file=sys.stderr)
        sys.exit(1)
    scan = db.query_one("SELECT * FROM scans WHERE id=?", (scan_id,))
    print(f"Scan #{scan_id} complete.")
    print(f"  Health: {scan['health_score']}/100 "
          f"({scan['health_grade']}, {scan['health_confidence']})")
    import json

    summary = json.loads(scan["summary_json"])
    print(f"  Dependencies: {summary['total']} ({summary['direct']} direct, "
          f"{summary['transitive']} transitive)")
    print(f"  Vulnerable packages: {summary['vulnerable_packages']}")
    print(f"  Outdated: {summary['outdated']}  License warnings: {summary['license_warnings']}")
    print(f"  Potentially unused: {summary['potentially_unused']}")
    print("Run 'deplens serve' and open the UI to explore the full results.")


def main():
    parser = argparse.ArgumentParser(prog="deplens", description="DepLens dependency explorer")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Run the API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_serve)

    scan = sub.add_parser("scan", help="Scan a project and print a summary")
    scan.add_argument("path", help="Path to the npm project directory")
    scan.add_argument("--offline", action="store_true", help="Skip registry/OSV network calls")
    scan.set_defaults(func=_scan)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        args.func = _serve
        args.host, args.port, args.reload = "127.0.0.1", 8000, False
    args.func(args)


if __name__ == "__main__":
    main()
