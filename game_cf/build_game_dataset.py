"""
Merge all game CF CSVs into one unified dataset file.

Adds columns: game (sudoku / cryptarithmetic / entropy_jugs / game24 / countdown),
              variant (baseline / cf1 / cf2 / …)
Renames: id → row_id

Usage (from project root)
─────────────────────────
python game_cf/build_game_dataset.py
python game_cf/build_game_dataset.py --out game_cf/dataset.csv
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pandas as pd

GAME_PATTERNS = [
    "game_cf/sudoku/*/data/*.csv",
    "game_cf/cryptarithmetic/*/data/*.csv",
    "game_cf/entropy_jugs/*/data/*.csv",
    "game_cf/game24/*/data/*.csv",
    "game_cf/countdown/*/data/*.csv",
]

_GAME_PREFIXES = [
    "cryptarithmetic",   # check before shorter prefixes
    "entropy_jugs",
    "countdown",
    "game24",
    "sudoku",
]


def _game_from_rule(rule: str) -> str:
    for prefix in _GAME_PREFIXES:
        if rule.startswith(prefix):
            return prefix
    return "unknown"


def _variant_from_path(path: str) -> str:
    """Extract variant name from CSV path, e.g. '.../cf1_base9/data/…' → 'cf1_base9'."""
    parts = path.replace("\\", "/").split("/")
    # data/ is the last directory before the filename
    data_idx = next((i for i, p in enumerate(parts) if p == "data"), None)
    if data_idx and data_idx >= 1:
        return parts[data_idx - 1]
    return "unknown"


def build(project_root: str, out_path: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for pattern in GAME_PATTERNS:
        for path in sorted(glob.glob(os.path.join(project_root, pattern))):
            df = pd.read_csv(path)
            if "id" in df.columns and "row_id" not in df.columns:
                df = df.rename(columns={"id": "row_id"})
            df["game"] = df["rule"].apply(_game_from_rule)
            df["variant"] = _variant_from_path(path)
            frames.append(df)

    if not frames:
        sys.exit(f"No CSV files found. Run from project root: {project_root!r}")

    combined = pd.concat(frames, ignore_index=True)

    if combined["row_id"].nunique() != len(combined):
        dupes = combined[combined["row_id"].duplicated()]["row_id"].tolist()
        sys.exit(f"Duplicate row_ids: {dupes[:5]} … fix before continuing.")

    # Reorder columns: identifiers first, then content
    front = ["row_id", "game", "variant", "rule", "state"]
    rest = [c for c in combined.columns if c not in front]
    combined = combined[front + rest]

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    combined.to_csv(out_path, index=False)

    print(f"Written {len(combined)} rows → {out_path}")
    print(f"  games    : {sorted(combined['game'].unique())}")
    print(f"  variants : {len(combined['variant'].unique())} total")
    for game, grp in combined.groupby("game"):
        variants = sorted(grp["variant"].unique())
        print(f"    {game}: {variants}  ({len(grp)} rows)")
    return combined


def main():
    parser = argparse.ArgumentParser(description="Build unified game CF dataset CSV")
    parser.add_argument("--out", default="game_cf/dataset.csv")
    parser.add_argument(
        "--root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Project root (default: parent of this script)",
    )
    args = parser.parse_args()
    build(args.root, args.out)


if __name__ == "__main__":
    main()
