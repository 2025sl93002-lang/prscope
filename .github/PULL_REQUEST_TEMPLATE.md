# Pull Request

## Summary

Briefly describe what this PR changes and why. Link any related issues (e.g. `Closes #123`).

## Type of change

Please check all that apply:

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Documentation only
- [ ] Refactor / internal change (no functional change)
- [ ] Build, CI, or tooling change

## How tested

Describe how you verified this change. Include the commands you ran and their results.

- Backend tests: `cd backend && PYTHONPATH=. pytest`
- Backend lint: `cd backend && ruff check .`
- Frontend tests: `cd frontend && npm test`
- Frontend build: `cd frontend && npm run build`
- Manual verification (describe steps, e.g. ran `POST /api/demo/setup` and checked the Evidence Ledger):

```
<paste relevant output here>
```

## Checklist

- [ ] Tests pass (`PYTHONPATH=. pytest` for the backend; `npm test` for the frontend)
- [ ] Lint is clean (`ruff check .`)
- [ ] Documentation updated (README and relevant files under `docs/`, if behavior or usage changed)
- [ ] No secrets, credentials, or private repository contents committed
- [ ] Verification evidence for this change is provided above (test results, CI output, or manual-check notes that let a reviewer confirm the change does what it claims)
