# Health Scoring Model

DepLens assigns each scanned project a **health score** from 0 to 100 and a
letter grade. The score is a **prioritization aid, not a validated risk
probability.** It exists to help you decide where to look first, not to certify
that a project is safe or unsafe.

## Formula

The score starts at **100** and subtracts weighted penalties. Each penalty
category is **capped**, so no single category can dominate the score. After all
penalties are applied the result is **clamped to the range 0–100**.

### Security (vulnerabilities)

| Severity | Penalty each | Category cap |
| --- | --- | --- |
| Critical | −20 | −40 |
| High | −10 | −40 |
| Moderate | −4 | −24 |
| Low | −1 | −10 |

### Outdatedness

| Lag | Penalty each | Category cap |
| --- | --- | --- |
| Major versions behind | −2 | −20 |
| Minor versions behind | −1 | −10 |
| Patch versions behind | −0.5 | −8 |

### Licenses

| Policy outcome | Penalty each | Category cap |
| --- | --- | --- |
| Restricted license | −6 | −24 |
| Review-required license | −1 | −8 |
| Unknown license | −2 | −12 |

### Usage & maintenance

| Signal | Penalty each | Category cap |
| --- | --- | --- |
| Potentially-unused package | −1 | −8 |
| Maintenance concern | −3 | −15 |

## Clamping and grades

```
score = clamp(0, 100, 100 − Σ capped_penalties)
```

| Grade | Range |
| --- | --- |
| A | ≥ 90 |
| B | ≥ 75 |
| C | ≥ 60 |
| D | ≥ 40 |
| F | < 40 |

## Partial confidence

A score is marked **partial** — never silently inflated — when the underlying
data was incomplete, specifically when:

- security advisories were **not checked** (e.g. DepLens ran offline), or
- **registry data was incomplete** for one or more packages.

In partial mode the score reflects only what could be verified. A missing data
source never adds points; it only lowers confidence.

## Worked example

A project with:

- 1 high-severity vulnerability → −10
- 3 moderate vulnerabilities → 3 × −4 = −12
- 2 dependencies a major version behind → 2 × −2 = −4
- 5 dependencies a patch behind → 5 × −0.5 = −2.5
- 1 restricted (copyleft) license → −6
- 2 unknown licenses → 2 × −2 = −4
- 3 potentially-unused packages → 3 × −1 = −3
- 1 maintenance concern → −3

No category exceeds its cap, so:

```
total penalty = 10 + 12 + 4 + 2.5 + 6 + 4 + 3 + 3 = 44.5
score         = 100 − 44.5 = 55.5  →  Grade D
```

If this same project were scanned offline, the two security categories could not
be verified, those penalties would be omitted, and the resulting score would be
flagged **partial** rather than presented as a clean, higher number.

## What the score is not

- It is **not** a probability that the project will be exploited.
- It is **not** legal advice about license compatibility (see `license-policy.md`).
- It is **not** a substitute for review. It points you at the packages worth
  reviewing and shows its work: every penalty traces back to a specific finding.
