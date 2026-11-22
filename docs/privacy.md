# Privacy

DepLens is **local-first**. It is designed so that analyzing your project does
not require handing your code to anyone.

## What stays on your machine

- Your source code. DepLens reads it to analyze imports and dependencies, but it
  **never uploads source code** anywhere.
- Your `package.json` and `package-lock.json`.
- All scan results, decisions, and settings — stored in a local SQLite database.
- The health score and every finding behind it.

## What leaves your machine, and why

DepLens contacts exactly two public services, and sends the **minimum** needed:

| Destination | What is sent | Why |
| --- | --- | --- |
| **npm registry** | Package **names** only | To look up published versions and metadata (latest version, dist-tags) for update analysis. |
| **OSV.dev** | Package **name + version** | To check for known security advisories affecting the installed version. |

That is the entire outbound data boundary. In particular, DepLens does **not**
send file contents, directory layouts, source code, project identity, or any
personal information.

## Offline mode

DepLens supports running fully **offline**. With no network access it still
parses manifests and lockfiles, resolves the graph, analyzes licenses and usage,
and produces a report. The steps that need the network (registry metadata and
OSV advisories) are **skipped and clearly marked**, and the health score is
flagged **partial** rather than presented as if everything were checked (see
`scoring-model.md`).

## No telemetry, no account

- **No telemetry.** DepLens does not phone home, collect analytics, or report
  usage.
- **No account, no login.** There is nothing to sign up for.
- **No background uploads.** The only network calls are the registry and OSV
  lookups described above, made during a scan.

## Safety alongside privacy

DepLens also never executes your project's code, npm lifecycle scripts, or
`npm install` — it only reads files. See `security.md` for how it safely handles
untrusted project contents.
