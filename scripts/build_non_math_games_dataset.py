"""
Merge all non-math game CSVs (hanoi, checker_jumping, river_crossing)
into one unified dataset file.

Adds: variant column derived from the source path.
Renames: id -> row_id (parallel to game_cf/build_game_dataset.py).

Usage (from project root):
    python scripts/build_non_math_games_dataset.py
    python scripts/build_non_math_games_dataset.py --out non_math_games/dataset.csv
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import pandas as pd

GAME_PATTERNS = [
    "non_math_games/hanoi/*/data/*.csv",
    "non_math_games/checker_jumping/*/data/*.csv",
    "non_math_games/river_crossing/*/data/*.csv",
]


def _variant_from_path(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
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
            if "variant" not in df.columns:
                df["variant"] = _variant_from_path(path)
            frames.append(df)

    if not frames:
        sys.exit(f"No CSV files found. Run from project root: {project_root!r}")

    combined = pd.concat(frames, ignore_index=True)

    if combined["row_id"].nunique() != len(combined):
        dupes = combined[combined["row_id"].duplicated()]["row_id"].tolist()
        sys.exit(f"Duplicate row_ids: {dupes[:5]} ... fix before continuing.")

    front = [c for c in ["row_id", "game", "variant", "n"] if c in combined.columns]
    rest = [c for c in combined.columns if c not in front]
    combined = combined[front + rest]

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    combined.to_csv(out_path, index=False)

    print(f"Written {len(combined)} rows -> {out_path}")
    print(f"  games    : {sorted(combined['game'].unique())}")
    for game, grp in combined.groupby("game"):
        variants = sorted(grp["variant"].unique())
        print(f"    {game}: {variants}  ({len(grp)} rows)")
    return combined


def main():
    parser = argparse.ArgumentParser(description="Build unified non-math game dataset CSV")
    parser.add_argument("--out", default="non_math_games/dataset.csv")
    parser.add_argument(
        "--root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Project root (default: parent of this script's directory)",
    )
    args = parser.parse_args()
    build(args.root, args.out)


if __name__ == "__main__":
    main()
