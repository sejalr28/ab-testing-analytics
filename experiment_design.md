# Experiment Design — Progress Gate Placement (Level 30 vs Level 40)

Written before looking at outcome data. This is the pre-registered analysis plan —
it defines what "success" means and how we'll test for it *before* results can bias
those decisions. In an interview, this document is the answer to "how do you avoid
p-hacking?"

## 1. Background & business question

Cookie Cats is a mobile puzzle game. Players hit a "gate" that pauses progress
(wait or pay to continue) at level 30. Product wants to know: **if we move the
first gate from level 30 to level 40, does it help or hurt the business?**

Two competing hypotheses product has heard:
- "A later gate keeps players in the core loop longer before the first friction
  point → higher retention."
- "A later gate means players invest more time before hitting a paywall, and the
  eventual gate feels more punishing → could hurt retention or increase churn."

We don't assume either is true. That's what the test is for.

## 2. Hypothesis

- **H0:** Moving the gate from level 30 to level 40 has no effect on Day-7 retention.
- **H1:** Moving the gate from level 30 to level 40 changes Day-7 retention.
- Two-sided test — we have a real prior belief in both directions, so a one-sided
  test would be inappropriate here.

## 3. Metrics

| Role | Metric | Why |
|---|---|---|
| **Primary (OEC)** | `retention_7` — did the player return 7 days after install | Longer-horizon retention is a better proxy for genuine engagement than Day-1, which is noisier and more prone to novelty effects |
| **Secondary** | `retention_1` — Day-1 retention | Sanity check / early read; not the ship decision on its own |
| **Guardrail** | `sum_gamerounds` — rounds played in first 14 days | A gate change could win on retention while quietly tanking engagement (e.g. if the later gate makes the early game feel like a slog). We must not ship a retention win that comes at the cost of engagement collapsing. |

Only one metric (`retention_7`) drives the ship decision. `retention_1` and
`sum_gamerounds` are read for context and as guardrails, not cherry-picked after
the fact — which is why they're written down here, in advance.

## 4. Statistical parameters (decided before seeing data)

- **α (significance level):** 0.05
- **Power:** 0.80
- **Baseline D7 retention (industry-typical mobile puzzle game):** ~19%
- **Minimum detectable effect (MDE):** 1 percentage point absolute (19% → 20%),
  the smallest change product considers worth the engineering cost of moving
  the gate
- **Required sample size per arm** (two-proportion test, α=0.05, power=0.80,
  baseline 19%, MDE 1pp): ~15,300 users per arm — see
  `analysis/ab_test_stats.py::required_sample_size`

We are testing **three metrics** on the same dataset (D1, D7, guardrail), so we
apply a **Bonferroni correction** (α/3 ≈ 0.017) when interpreting the secondary
and guardrail results, to control the family-wise error rate. The primary metric
(D7 retention) is the pre-registered ship decision and is evaluated at α=0.05.

## 5. Pre-registered analysis plan

1. **Sample Ratio Mismatch (SRM) check first.** If assignment isn't ~50/50 within
   statistical noise, we do not trust any downstream result until we understand why.
2. Two-proportion z-test (with Wilson score confidence interval) on `retention_7`.
3. Two-proportion z-test on `retention_1` (secondary, Bonferroni-adjusted).
4. Mann-Whitney U test on `sum_gamerounds` (guardrail) — a **non-parametric** test
   because in-game engagement is heavily right-skewed with extreme outliers
   (bots/QA accounts), so a t-test's normality assumption doesn't hold and its
   result would be dominated by a handful of extreme values, not the typical player.
5. Outlier sensitivity check: report the guardrail result with and without extreme
   outliers, and justify any exclusion criteria explicitly rather than silently
   dropping rows.
6. Ship decision is made on the primary metric result alone, guardrails permitting.

## 6. What would make us NOT ship, even with a "winning" primary metric

- SRM flags a broken randomization (result isn't trustworthy either direction).
- Guardrail (`sum_gamerounds`) drops significantly — a retention win isn't worth
  an engagement collapse.
- Effect size is statistically significant but below the pre-registered MDE
  (statistically significant ≠ practically significant).
