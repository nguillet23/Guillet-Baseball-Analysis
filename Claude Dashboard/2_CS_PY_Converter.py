"""
csv_to_js.py
============
Converts expected_2025_stats.csv (output of the Python pipeline) into the
JavaScript PLAYERS array used by all four HTML files.

Usage
-----
    python csv_to_js.py expected_2025_stats.csv

Output
------
Prints the JS array to stdout. Redirect to a file or copy-paste into
the PLAYERS constant at the top of each HTML file.

    python csv_to_js.py expected_2025_stats.csv > players_data.js
"""

import sys
import json
import pandas as pd

# ── Required columns ─────────────────────────────────────────────────────────
REQUIRED = ["Name", "MB", "xMB", "TB", "xTB", "BB", "xBB",
            "AB", "xAB", "H", "xH", "SB", "xSB", "CS", "xCS"]

INT_COLS  = ["MB", "xMB", "TB", "xTB", "BB", "xBB",
             "AB", "xAB", "H",  "xH",  "SB", "xSB", "CS", "xCS"]


def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Keep only rows that have a name and the two MB columns
    df = df.dropna(subset=["Name", "MB", "xMB"])

    # Fill missing component columns with the corresponding actual stat
    fallbacks = {"xTB": "TB", "xBB": "BB", "xAB": "AB",
                 "xH":  "H",  "xSB": "SB", "xCS": "CS"}
    for xcol, col in fallbacks.items():
        if xcol not in df.columns:
            df[xcol] = df.get(col, 0)
        else:
            df[xcol] = df[xcol].fillna(df.get(col, 0))

    # Round integer columns
    for col in INT_COLS:
        if col in df.columns:
            df[col] = df[col].round(0).astype(int)

    return df


def df_to_js_array(df: pd.DataFrame) -> str:
    cols = [c for c in REQUIRED if c in df.columns]
    records = df[cols].to_dict(orient="records")

    lines = []
    for r in records:
        # Build each player object on one line for readability
        parts = []
        for k, v in r.items():
            if isinstance(v, str):
                parts.append(f'{k}:"{v}"')
            else:
                parts.append(f"{k}:{v}")
        lines.append("  {" + ", ".join(parts) + "}")

    return "const PLAYERS = [\n" + ",\n".join(lines) + "\n];"


def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_to_js.py expected_2025_stats.csv")
        sys.exit(1)

    path = sys.argv[1]
    df = load_and_clean(path)

    if df.empty:
        print("// No rows found after cleaning.", file=sys.stderr)
        sys.exit(1)

    js = df_to_js_array(df)
    print(js)
    print(f"\n// {len(df)} players exported.", file=sys.stderr)


if __name__ == "__main__":
    main()