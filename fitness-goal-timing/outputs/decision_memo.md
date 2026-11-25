# When should a fitness app ask for a goal?

**SYNTHETIC PORTFOLIO EXERCISE | V1 | 25 November 2026**

## Decision

Retain the onboarding goal prompt in this simulated case. The first-workout gain accompanies a clear decline in the primary retention metric. Test a shorter onboarding prompt in a separate follow-up experiment.

## Product question and design

Would moving the same optional weekly goal prompt until after the first completed workout improve sustained use? Randomize new eligible accounts before onboarding, with 20,000 per arm and 28 complete days of follow-up. Keep wording, skip option, workouts, prices and reminders identical. Goal capture does not change workout selection.

## Frozen success criteria

Recommend rollout only if retention improves by at least 1.50 percentage points and its 95% interval excludes zero, paid conversion has a lower bound above -1.00 point, and onboarding errors have an upper bound below +0.50 point. Clear retention or guardrail harm takes precedence. Otherwise retain current timing pending more evidence.

| Outcome | Onboarding | Deferred | Difference [95% CI] |
|---|---:|---:|---:|
| Week-four workout retention | 22.67% | 19.89% | -2.78 pp [-3.58, -1.98] |
| First workout by day 7 | 60.02% | 66.26% | +6.24 pp [+5.29, +7.18] |
| Paid conversion by day 28 | 6.04% | 6.11% | +0.07 pp [-0.40, +0.54] |
| Onboarding error by day 7 | 1.58% | 1.50% | -0.09 pp [-0.33, +0.16] |

All rates use 20,000 accounts per arm. pp = percentage points. Newcombe / Wilson 95% intervals.

## What the simulation shows

The primary outcome is a completed workout during days 22-28. All assigned accounts stay in every denominator, including 6,242 treatment accounts that never see the deferred prompt. Paid conversion and error intervals pass the prespecified guardrails. Intervals describe sampling variation within this synthetic model.

## Interpretation and next bet

Earlier goal-setting may support commitment, but this simulation cannot establish that mechanism. Inspect the path from first workout to return visits, then separately test lower-friction goal-setting. Never compare only prompt viewers or first-workout completers as if they remained randomized.

## Scope and provenance

SYNTHETIC educational exercise by Aviv Emanuel. Rates, thresholds and sample size are chosen assumptions. Seed 20261125 was fixed before the first run. This case uses fictional accounts and illustrates growth-experiment decision-making. It reports no real app effect or production rollout. The public source provides framing only.

Context: [Aviv Emanuel’s public retention case](https://www.avivemanuel.com/post/loyal-users-early-behaviors).
