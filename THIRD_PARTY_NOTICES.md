# Third-Party Notices

DepLens is distributed under the MIT License. It depends on the third-party
open-source software listed below. All of these are **OSI-approved** and
**compatible with the MIT License**.

This file is a human-maintained summary. A **machine-generated inventory** of the
exact installed packages and their licenses is produced by the
`license-check` CI workflow (`.github/workflows/license-check.yml`), which also
enforces the project's permissive-license policy.

## Backend (runtime)

| Package | License |
| --- | --- |
| FastAPI | MIT |
| Starlette (via FastAPI) | BSD-3-Clause |
| Uvicorn | BSD-3-Clause |
| Pydantic | MIT |
| httpx | BSD-3-Clause |
| NetworkX | BSD-3-Clause |

## Frontend (runtime)

These are the intended frontend libraries (the frontend is built separately).

| Package | License |
| --- | --- |
| React | MIT |
| ReactDOM | MIT |
| React Router | MIT |
| Cytoscape.js | MIT |
| cytoscape-fcose | MIT |
| Recharts | MIT |
| lucide-react | ISC |

## Notes

- Each license above is OSI-approved and compatible with MIT.
- Licenses and their full texts are included with the respective packages as
  installed from their registries (PyPI and npm).
- For the authoritative, version-specific list, consult the inventory generated
  by the license-check CI workflow against the pinned dependencies.
