-- A/B Test Analysis — Core SQL Queries
-- Run against data/ab_test.db (SQLite). Build it first with: python sql/build_db.py

-- =========================================================
-- 1. Sample sizes per arm (input to the SRM check)
-- =========================================================
SELECT
    version,
    COUNT(*) AS n_users
FROM experiment_users
GROUP BY version;

-- =========================================================
-- 2. Primary metric: Day-7 retention by arm
-- =========================================================
SELECT
    version,
    COUNT(*)                                    AS n_users,
    SUM(retention_7)                            AS retained_d7,
    ROUND(100.0 * SUM(retention_7) / COUNT(*), 2) AS retention_7_pct
FROM experiment_users
GROUP BY version;

-- =========================================================
-- 3. Secondary metric: Day-1 retention by arm
-- =========================================================
SELECT
    version,
    COUNT(*)                                    AS n_users,
    SUM(retention_1)                            AS retained_d1,
    ROUND(100.0 * SUM(retention_1) / COUNT(*), 2) AS retention_1_pct
FROM experiment_users
GROUP BY version;

-- =========================================================
-- 4. Guardrail metric: engagement (game rounds) distribution by arm
--    Median is reported alongside mean because the metric is heavily skewed
--    (see notebook / experiment_design.md for why a t-test on the mean alone
--    would be misleading here).
-- =========================================================
SELECT
    version,
    COUNT(*)                          AS n_users,
    ROUND(AVG(sum_gamerounds), 1)     AS mean_rounds,
    MIN(sum_gamerounds)               AS min_rounds,
    MAX(sum_gamerounds)               AS max_rounds
FROM experiment_users
GROUP BY version;

-- =========================================================
-- 5. Retention funnel: D1 -> D7 by arm
--    (of users who came back on D1, how many were still active on D7?)
-- =========================================================
SELECT
    version,
    SUM(retention_1)                                        AS d1_returners,
    SUM(CASE WHEN retention_1 = 1 AND retention_7 = 1 THEN 1 ELSE 0 END) AS d1_and_d7_returners,
    ROUND(100.0 * SUM(CASE WHEN retention_1 = 1 AND retention_7 = 1 THEN 1 ELSE 0 END)
          / NULLIF(SUM(retention_1), 0), 2)                  AS d1_to_d7_carry_pct
FROM experiment_users
GROUP BY version;

-- =========================================================
-- 6. Outlier scan: users with extreme engagement (candidate bots/QA accounts)
--    Flagged for the sensitivity analysis in experiment_design.md
-- =========================================================
SELECT
    userid,
    version,
    sum_gamerounds,
    retention_1,
    retention_7
FROM experiment_users
ORDER BY sum_gamerounds DESC
LIMIT 10;

-- =========================================================
-- 7. Zero-engagement installs (never played a single round) by arm
--    A different failure mode than "played but didn't return" -- worth
--    separating install-time drop-off from mid-funnel churn.
-- =========================================================
SELECT
    version,
    SUM(CASE WHEN sum_gamerounds = 0 THEN 1 ELSE 0 END)              AS zero_round_users,
    ROUND(100.0 * SUM(CASE WHEN sum_gamerounds = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS zero_round_pct
FROM experiment_users
GROUP BY version;
