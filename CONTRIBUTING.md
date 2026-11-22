# Contributing to DepLens

Thanks for your interest in improving DepLens — a local-first, open-source
dependency health explorer for Node.js/npm projects. This guide covers how to
set up your environment, run the tests, and get a change merged.

## Development environment

DepLens has a Python + FastAPI backend and a React + TypeScript frontend.

### Backend

Requires **Python 3.9+**.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Frontend

Requires **Node.js 18+**.

```bash
cd frontend
npm install
```

## Running the project

Start the backend and frontend in separate terminals:

```bash
# Backend
cd backend
uvicorn deplens.main:app --reload

# Frontend
cd frontend
npm run dev
```

## Running the tests

Please run and pass the full test suite before opening a pull request.

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## Code style

- **Python** — formatted and linted with [Ruff](https://docs.astral.sh/ruff/).
  Run `ruff check .` and `ruff format .` in `backend/` before committing.
- **TypeScript** — linted with ESLint and formatted with Prettier. Run
  `npm run lint` and `npm run format` in `frontend/`.

CI enforces these checks, so running them locally saves a round trip.

## Branch and pull request workflow

1. Fork the repository (or create a branch if you have write access).
2. Create a topic branch from `main`, e.g. `feat/license-report` or
   `fix/graph-cycle`.
3. Make your change with focused commits and accompanying tests.
4. Push your branch and open a pull request against `main`.
5. Fill out the pull request template and link any related issue.
6. Address review feedback; keep the branch up to date with `main`.

Keep pull requests small and single-purpose where possible — they are easier to
review and merge.

## Commit message conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/). Each
commit message starts with a type:

```
feat: add transitive dependency depth filter
fix: handle missing package-lock.json gracefully
docs: clarify backend setup steps
test: cover usage analyzer edge cases
chore: bump dev tooling versions
refactor: extract license matcher
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`,
`ci`. Use the imperative mood and keep the subject under ~72 characters.

## Dependencies

DepLens is MIT licensed and aims to stay easy to adopt and redistribute. New
dependencies must be licensed under a permissive, MIT-compatible license —
**MIT, BSD (2- or 3-clause), Apache-2.0, or ISC**. Copyleft licenses (GPL,
LGPL, AGPL, etc.) are not acceptable.

When adding a dependency:

- Prefer well-maintained, widely-used packages with minimal transitive weight.
- Note the dependency and its license in your pull request description.
- Explain why it is needed and whether a lighter alternative was considered.

## Reporting bugs and requesting features

Use the issue templates for [bug reports](.github/ISSUE_TEMPLATE/bug_report.md)
and [feature requests](.github/ISSUE_TEMPLATE/feature_request.md). For security
issues, please follow [SECURITY.md](SECURITY.md) instead of opening a public
issue.

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](LICENSE).
