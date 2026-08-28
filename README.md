# A/B Testing & Experimentation Analytics

A full experimentation workflow — pre-registered experiment design, SQL,
statistical testing, and a stakeholder recommendation — built on a real mobile
game A/B test (Cookie Cats, 90,189 players). This is not a dashboard project;
the dashboard is the last 10%. The point is demonstrating the actual DA
workflow: frame a question, design the test properly, test it rigorously,
recommend a decision.

## Why this project, not just another dashboard

Most DA portfolios show a chart wall. What Data Analyst interviews at
experimentation-heavy companies (Amazon, Netflix, Meta, Google, and consumer
brands like Nike running constant site/app tests) actually screen for is
whether you can **design and reason about an experiment**: pick the right
metric, size the test correctly, catch a broken randomizer, choose the right
statistical test for the data's shape, and turn a p-value into a business
recommendation. This project is built around that loop.

## Quick look — no install needed

**Open `reports/executive_report.html` directly in any browser.** It's a
standalone, self-contained results readout — no Streamlit, no Python, no
setup. This is the piece to link or screenshot for a resume/LinkedIn; the
Streamlit app below is for interactively exploring the analysis and running
the significance calculator on your own numbers.

## What's inside

```
ABTest-Experimentation-Analytics/
├── experiment_design.md         # Pre-registered plan: hypothesis, metrics,
│                                 # MDE, sample size — written BEFORE results
├── executive_memo.md            # Ship/no-ship recommendation for stakeholders
├── data/
│   ├── cookie_cats.csv          # Real A/B test data, 90,189 players
│   ├── ab_test.db               # SQLite DB (via sql/build_db.py)
│   ├── data_dictionary.md
│   └── chart_engagement_distribution.png
├── sql/
│   ├── build_db.py
│   └── ab_test_analysis.sql     # 7 SQL queries: SRM inputs, retention, guardrails
├── analysis/
│   ├── ab_test_stats.py         # Reusable stats toolkit (SRM, z-test, sample
│   │                             # size, MDE, Mann-Whitney, Bonferroni)
│   └── test_ab_test_stats.py    # Unit tests, validated against scipy
├── reports/
│   └── executive_report.html    # Standalone polished report — open directly,
│                                 # no install required
├── notebooks/
│   └── 01_eda_and_experiment_analysis.ipynb   # Full analysis, pre-run
└── dashboard/
    └── app.py                   # Results readout + reusable significance
                                  # calculator (works on ANY experiment's numbers)
```

## How to run

```bash
pip install -r requirements.txt

# 1. Build the SQLite database
python sql/build_db.py

# 2. Run the SQL queries (any SQLite client, or):
sqlite3 data/ab_test.db < sql/ab_test_analysis.sql

# 3. Run the unit tests on the stats toolkit
cd analysis && pytest test_ab_test_stats.py -v && cd ..

# 4. Open the notebook (already executed, but you can re-run it)
jupyter notebook notebooks/01_eda_and_experiment_analysis.ipynb

# 5. Launch the dashboard + calculator
streamlit run dashboard/app.py
```

## Key findings

| Finding | Detail |
|---|---|
| **Primary result** | Moving the gate to level 40 **decreased** Day-7 retention by 0.82pp (19.02% → 18.20%), statistically significant (p=0.0016) |
| **Recommendation** | Do not ship — keep the gate at level 30 (see `executive_memo.md`) |
| **Guardrail** | No significant engagement (game rounds) difference — the retention loss isn't offset by an engagement gain, it's a clean loss |
| **SRM check** | Minor imbalance detected (p=0.0086) but passes the strict experimentation-platform threshold (p<0.001) — flagged as a caveat, not a blocker |
| **Practical vs. statistical significance** | Effect (0.82pp) is real but under the pre-registered 1.0pp minimum effect size that was decided to matter |
| **Power check** | At the actual sample size, the test could detect effects as small as 0.74pp — the non-significant secondary/guardrail results are meaningful nulls, not underpowered noise |

## Design notes (why it's built this way)

- **Real data, real assignment, not simulated.** No synthetic treatment effect
  to defend — the outcome is what actually happened when this game ran the test.
- **Pre-registered design (`experiment_design.md`) written before the analysis,
  not after.** This is what prevents p-hacking, and it's the answer to "how do
  you avoid fooling yourself" in an interview.
- **SRM check runs first, always.** A broken randomizer invalidates every
  result downstream — checking is standard practice at any company running
  experiments at scale, and skipping it is a common mistake.
- **Mann-Whitney, not a t-test, for the engagement guardrail.** The metric is
  heavily right-skewed with extreme outliers; a t-test's normality assumption
  doesn't hold, and its result would be dominated by a few extreme accounts
  instead of the typical player.
- **Bonferroni correction** applied because three metrics are tested on one
  dataset — without it, the false-positive rate across the whole readout is
  higher than the nominal 5%.
- **The stats toolkit (`analysis/ab_test_stats.py`) is dataset-agnostic** and
  unit-tested against scipy — it's built to be reused on the next experiment,
  which is what a real internal DA tool looks like, not a one-off notebook.
- **The dashboard is a calculator, not just a chart wall** — the second tab
  works on any control/treatment numbers, independent of this dataset.

## Suggested resume framing

> **A/B Testing & Experimentation Analytics** (SQL, Python, SciPy, Streamlit)
> Designed and ran a full experimentation workflow — pre-registered hypothesis,
> sample-size/power calculation, SRM validation, and statistical testing — on a
> 90K-player mobile game A/B test; identified a statistically significant 0.82pp
> retention regression missed by the original "later gate = better retention"
> assumption, and delivered a ship/no-ship recommendation via executive memo.
> Built a reusable, unit-tested A/B significance-testing toolkit (SRM checks,
> two-proportion z-tests, MDE calculations, non-parametric testing for skewed
> metrics) deployed as an interactive Streamlit calculator.
