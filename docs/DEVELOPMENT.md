# Development

How to set up and work on DepLens locally.

## Prerequisites

- **Python 3.9+** (backend).
- **Node.js 18+** (frontend). If you use `nvm`, make sure `node` is on your
  `PATH` in the shell you run these commands from — a login shell that hasn't
  sourced nvm will not find it.

## Backend

From the repository root:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

### Run the server

```bash
# via the DepLens CLI
.venv/bin/python -m deplens serve

# or directly with uvicorn (auto-reload for development)
.venv/bin/uvicorn deplens.main:app --reload
```

The API is served on port **8000**.

### Run a scan from the CLI

```bash
.venv/bin/python -m deplens scan <path-to-project>
```

### Tests

```bash
.venv/bin/python -m pytest
```

### Lint

```bash
.venv/bin/ruff check deplens/
```

## Frontend

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port **5173** and proxies `/api` to the backend on
port **8000**, so run the backend alongside it.

### Build

```bash
npm run build
```

The production build is what `backend/deplens/main.py` serves in a packaged
deployment.

## Demo fixture

A ready-to-scan sample project ships at **`fixtures/demo-project`**. Use it to
try a scan without pointing DepLens at a real repo:

```bash
cd backend
.venv/bin/python -m deplens scan ../fixtures/demo-project
```

## Typical dev loop

1. Start the backend: `.venv/bin/uvicorn deplens.main:app --reload`.
2. Start the frontend: `cd frontend && npm run dev`.
3. Open the Vite dev server (port 5173); API calls proxy to port 8000.
4. Before committing: `ruff check deplens/` and `python -m pytest` in `backend/`.
