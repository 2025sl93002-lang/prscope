---
name: Feature request
about: Suggest an idea or improvement for PRScope
title: "[Feature]: "
labels: enhancement
assignees: ''
---

## Problem

A clear and concise description of the problem or need this feature would address. What are you trying to accomplish, and where does PRScope fall short today?

For example: "When reviewing a PR, I want ... but PRScope currently ..."

## Proposed solution

A clear and concise description of what you want to happen. Describe the behavior, UI, API route, or analysis output you have in mind.

If your request relates to PRScope's core workflow (change → affected components → potential impact → required verification → available evidence → review readiness), explain where in that chain it fits.

## Alternatives

A clear and concise description of any alternative solutions or features you have considered, including existing PRScope features or external tools that partially address the need.

## Additional context

Add any other context, mockups, or examples here.

Please keep in mind PRScope's guiding principles when proposing features:

- **Local-first and deterministic.** Core analysis runs with no AI model, no API keys, and no paid/cloud services. AI is optional via a local Ollama runtime, with a deterministic fallback.
- **Explainable over opaque.** PRScope explains how every finding is derived rather than emitting a single opaque score.
- **Privacy-preserving.** Repository source code is never uploaded anywhere, and there is no telemetry.

Note: GitHub integration is not implemented in this proof of concept. It is tracked as a roadmap item, so related requests are welcome.
