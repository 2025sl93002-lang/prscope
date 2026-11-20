# Risk Model — Review Attention Scoring

PRScope assigns each analysis a **review-attention level** derived from a set of
independent, deterministic rules. This document explains exactly how that level
is computed, lists every scoring contribution and threshold, walks through a
worked example, and shows how to inspect or configure the model.

> **Important disclaimer — this is review attention, not a bug probability.**
> The attention level tells you *how much reviewer focus a change likely
> warrants*. It is **not** an estimate of the probability that the change
> contains a defect, and it is not an AI score. A high level does not mean the
> change is broken, and a low level does not certify it as correct. Use it to
> prioritize where to look, not as a pass/fail verdict.

---

## How the model works

The model is **additive and deterministic**. There is no machine-learning model,
no API key, and no cloud service involved in producing a level — the same inputs
always produce the same output.

The engine evaluates a fixed set of rules against the analyzed change. Each rule
that fires contributes a fixed number of points. The **attention score** is
simply the sum of all firing contributions:

```
attention_score = Σ (score_contribution of each rule that fired)
```

The score is then mapped to a named **attention level** using fixed thresholds
(see below).

Every rule that fires produces a **finding**, and every finding records the full
reasoning behind it, so nothing is opaque. Each finding stores:

- `title` — short description of what was detected
- `severity`
- `related_files` — the files that triggered the rule
- `explanation` — why this matters for review
- `evidence` — the concrete facts that caused the rule to fire
- `suggested_action` — what a reviewer should do about it
- `rule` — the rule identifier
- `score_contribution` — the exact points this finding added to the total

Because the total is just a sum of these contributions, you can always trace a
level back to the individual findings that produced it.

---

## Score contributions

Each rule contributes the points below when it fires. These values are defined
in the `SCORE` dictionary in `backend/prscope/services/risk_analyzer.py`.

| Rule                 | Points | What it reflects                                             |
| -------------------- | -----: | ----------------------------------------------------------- |
| `security`           |     25 | Changes to security-sensitive code                          |
| `migration`          |     22 | Database or data migrations                                 |
| `very_large_change`  |     22 | Total changed lines at or above the very-large threshold    |
| `api_contract`       |     20 | Changes to an API contract / interface                      |
| `very_high_fan_in`   |     20 | A changed file with a very high number of dependents        |
| `very_many_files`    |     18 | Number of changed files at or above the very-many threshold |
| `missing_tests`      |     15 | A potential test gap was detected for the change            |
| `infrastructure`     |     14 | Infrastructure / deployment changes                         |
| `dependency`         |     12 | Dependency manifest / lockfile changes                      |
| `large_change`       |     12 | Total changed lines at or above the large threshold         |
| `high_fan_in`        |     12 | A changed file with a high number of dependents             |
| `config`             |     10 | Configuration changes                                       |
| `many_files`         |     10 | Number of changed files at or above the many threshold      |
| `build_ci`           |      8 | Build or CI pipeline changes                                |

Rules are independent: more than one can fire for a single change, and their
contributions add together.

---

## Size and fan-in thresholds

The size- and fan-in-based rules fire when a change crosses one of these
thresholds. They are defined alongside the scores in
`backend/prscope/services/risk_analyzer.py`.

| Threshold constant        | Value | Triggers rule       |
| ------------------------- | ----: | ------------------- |
| `LARGE_CHANGE_LINES`      |   400 | `large_change`      |
| `VERY_LARGE_CHANGE_LINES` |  1200 | `very_large_change` |
| `MANY_FILES`              |    20 | `many_files`        |
| `VERY_MANY_FILES`         |    60 | `very_many_files`   |
| `HIGH_FAN_IN`             |     5 | `high_fan_in`       |
| `VERY_HIGH_FAN_IN`        |    15 | `very_high_fan_in`  |

Here, *fan-in* is the number of other intra-repo files that depend on a changed
file (its reverse dependencies), as computed by the dependency and impact
analyzers.

---

## Attention levels

The summed score maps to a level using these thresholds:

| Level        | Score range       |
| ------------ | ----------------- |
| **low**      | `< 20`            |
| **moderate** | `>= 20` and `< 45`|
| **high**     | `>= 45` and `< 75`|
| **critical** | `>= 75`           |

---

## Worked example

Consider a pull request that:

1. Modifies an API contract — fires `api_contract` → **20**
2. Updates a dependency manifest — fires `dependency` → **12**
3. Changes a configuration file — fires `config` → **10**

The attention score is the sum of the firing contributions:

```
20 (api_contract) + 12 (dependency) + 10 (config) = 42
```

A score of **42** falls in the `>= 20` and `< 45` band, so the change is rated
**moderate** attention. The analysis also lists the three findings above, each
with its own explanation, evidence, and `score_contribution`, so a reviewer can
see precisely why the total is 42 and what to verify.

As a second illustration, add a security-sensitive change to the same PR. That
fires `security` → **25**, raising the total to `42 + 25 = 67`, which lands in
the `>= 45` and `< 75` band and rates the change **high**.

---

## Inspecting and configuring the model

The entire model is defined in one file:

```
backend/prscope/services/risk_analyzer.py
```

Both the `SCORE` dictionary (per-rule point contributions) and the size/fan-in
threshold constants live there, in plain Python. This means the model is fully
inspectable — you can read exactly what each rule is worth — and adjustable: edit
the values in that file to tune the scoring for your own project's conventions
(for example, raising `config` points if configuration changes tend to be
high-impact in your codebase, or lowering `large_change` thresholds if your team
prefers smaller diffs).

Because the level is a pure sum of these constants, any change you make is
transparent and reproducible: there is no hidden weighting, no learned model, and
no external service to account for.

---

## Limitations

- The level reflects **review attention, not defect probability.** It helps you
  prioritize review effort; it does not predict or detect bugs.
- Scoring is driven by **file-level static analysis**, which approximates impact
  and does not guarantee runtime behavior.
- The `missing_tests` contribution is based on **potential** test gaps inferred
  from imports and naming, not from coverage data, so it may over- or
  under-report.
- Fan-in is computed over resolved intra-repo dependencies only (Python imports
  and relative JS/TS imports); unresolved edges are not counted toward fan-in
  rules.
- The thresholds and point values are **heuristics**. The defaults are a
  reasonable starting point, not a calibrated standard — tune them for your
  project (see above).
