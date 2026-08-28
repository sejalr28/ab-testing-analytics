# Data Dictionary — `cookie_cats.csv`

Source: Cookie Cats mobile game A/B test (public dataset, originally distributed
via DataCamp; 90,189 players who installed the game during the live test).
Real random assignment, real outcomes — not simulated.

| Column | Type | Description |
|---|---|---|
| `userid` | int | Unique player identifier |
| `version` | string | Experiment arm: `gate_30` (control — original gate at level 30) or `gate_40` (treatment — gate moved to level 40) |
| `sum_gamerounds` | int | Number of game rounds played in the first 14 days after install |
| `retention_1` | bool | Did the player return to the game 1 day after install? |
| `retention_7` | bool | Did the player return to the game 7 days after install? |

No missing values, no duplicate `userid`s. `sum_gamerounds` is heavily
right-skewed (median 16, max 49,854 — one extreme outlier account), handled via
outlier-sensitivity analysis and a non-parametric test rather than exclusion by
default. See `notebooks/01_eda_and_experiment_analysis.ipynb`.
