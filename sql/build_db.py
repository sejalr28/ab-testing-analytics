"""
Loads data/cookie_cats.csv into a local SQLite database (ab_test.db) so the
core aggregation lives in SQL, not just pandas.

Usage:
    python sql/build_db.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "cookie_cats.csv"
DB_PATH = ROOT / "data" / "ab_test.db"


def main():
    df = pd.read_csv(CSV_PATH)
    df["retention_1"] = df["retention_1"].astype(int)  # SQLite has no native bool
    df["retention_7"] = df["retention_7"].astype(int)

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("experiment_users", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_version ON experiment_users(version)")
    conn.commit()
    conn.close()
    print(f"Loaded {len(df):,} rows into {DB_PATH}")


if __name__ == "__main__":
    main()
