# Synthetic account data dictionary

**SYNTHETIC PORTFOLIO EXERCISE. One row per randomized account.**

The main file is `outputs/synthetic_accounts.csv`, with 40,000 rows plus a header. All IDs are fictional. The file has no direct identifiers, real timestamps or source-system records. Days are elapsed days relative to assignment, which occurs before onboarding on day 0. Blank numeric cells mean the event did not occur within the modeled window. Never drop these rows.

| Field | Type | Definition |
|---|---|---|
| account_id | string | Unique fictional ID, SYN-000001 through SYN-040000 |
| scenario | string | main_conflict for the delivered account file |
| arm | string | onboarding or after_workout, permanently assigned before outcomes |
| assignment_day | integer | Always 0 |
| followup_days | integer | Always 28, ensuring complete observation |
| prompt_seen | 0/1 | Whether the prompt was rendered by day 28. This does not record acceptance |
| prompt_day | integer or blank | 0 in control; first_workout_day in treatment; blank if never exposed |
| first_workout_day | integer or blank | First completed workout on days 1-7 or 8-21; blank if absent |
| week4_workout_day | integer or blank | One representative completed workout on days 22-28; blank if absent |
| first_paid_day | integer or blank | First paid conversion on days 1-28; blank if absent |
| onboarding_error_day | integer or blank | One representative logged onboarding error on days 0-7; blank if absent |

The file is an account-level sufficient summary of the modeled events. Counts of workouts, payments and errors are intentionally outside this v1. A real event pipeline would use event IDs, versioned event definitions, UTC assignment timestamps, late-arrival handling and account/device identity resolution before constructing this table.

## Metric contracts

Every metric divides the number of assigned accounts with the qualifying event by **all 20,000 assigned accounts in that arm**. The estimand is the effect of assignment to the timing policy. There are no post-assignment exclusions.

- `retention_w4` is a workout during days 22-28 inclusive. It can be 1 only after a modeled first workout. This is week-four activity retention, rather than requiring activity in every previous week.
- `first_workout_d7` is first_workout_day <= 7. It is a diagnostic and cannot override the primary decision.
- `paid_d28` is first_paid_day <= 28. The tolerated loss is 1.00 percentage point.
- `error_d7` is onboarding_error_day <= 7. The tolerated increase is 0.50 percentage point. Lower is preferable.

`results.csv` has one row per scenario and metric. `control_count` and `treatment_count` are event counts; `control_n` and `treatment_n` are assigned denominators. `*_pct` are percentages. `difference_pp`, `ci_low_pp`, and `ci_high_pp` express the deferred-minus-onboarding effect and 95% interval in percentage points. Full precision is stored. Displayed values are rounded to two decimals.

## Data-generating assumptions

Control first-workout probability is 0.60. Treatment is 0.66 in the main and aligned-benefit scenarios and 0.60 under the null. Conditional week-four return among early completers is 0.36 in control, 0.29 in the main treatment, 0.36 under the null and 0.38 with aligned benefit. Among people without an early workout, 8% first complete one on days 8-21, with a 25% week-four return probability. Paid conversion is 6% and onboarding errors 1.5% independently of workout outcomes in both arms. These simplifications make the assumed conflict transparent. They are not estimated from users.

The expected main primary rates are 22.40% for control and 19.82% for treatment. Realized finite-sample rates differ. All scenarios reuse fixed random draws and permanent assignment. This is a sensitivity comparison across assumptions, not three independent trials or evidence about mechanism.
