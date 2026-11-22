# License Policy

DepLens classifies each dependency's license into a **family** and maps that
family to a **policy outcome**. This helps you spot licenses that may need review
before you ship. It drives the license portion of the health score (see
`scoring-model.md`).

> **This is not legal advice.** License classification is **heuristic**. It is a
> prioritization aid to tell you where to look, not a legal determination of
> compatibility or obligation. Consult a qualified professional for legal
> questions.

## License families

| Family | Example licenses |
| --- | --- |
| **Permissive** | MIT, ISC, BSD (2/3-clause), Apache-2.0, 0BSD, Unlicense, CC0 |
| **Weak-copyleft** | MPL-2.0, LGPL, EPL |
| **Copyleft** | GPL, AGPL |
| **Proprietary** | Non-OSS / commercial |
| **Unknown** | Missing or unrecognized license field |

## Default policy

| Family | Outcome |
| --- | --- |
| Permissive | **allowed** |
| Weak-copyleft | **review** |
| Copyleft | **restricted** |
| Proprietary | **restricted** |
| Unknown | **review** |

- **allowed** — no license penalty.
- **review** — flagged for a human to look at; small score penalty.
- **restricted** — flagged as likely incompatible with a permissive project;
  larger score penalty.

The score penalties attached to these outcomes are documented in
`scoring-model.md`.

## Configuring the policy

The policy is **configurable**. Overrides are persisted in the `settings` table
(see `architecture.md`) and can be adjusted so that, for example, weak-copyleft
is treated as `allowed` for an internal project, or a specific license is pinned
to a particular outcome. The family → outcome mapping above is the default used
when no override is set.

## Why "unknown" is review, not allowed

A missing or unrecognized license is treated as **review**, never silently
allowed. An absent license is not the same as a permissive one — it may carry no
grant of rights at all — so DepLens surfaces it for a human decision rather than
assuming the best case.
