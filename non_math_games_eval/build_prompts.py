#!/usr/bin/env python3
"""
Generate evaluation prompts from data CSVs.

Usage:
  # One dataset:
  python build_prompts.py --data ../non_math_games/hanoi/baseline/data/hanoi_baseline.csv \\
                          --output prompts/hanoi_baseline_prompts.csv

  # All datasets at once:
  python build_prompts.py --all --output-dir prompts/

Output CSV columns: id, game, variant, n, prompt
(The 'solution' column is intentionally omitted — never shown to the model.)
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from non_math_games_eval.prompts import build_prompt

_ROOT = os.path.join(os.path.dirname(__file__), "..", "non_math_games")

ALL_DATA_CSVS = {
    "hanoi_baseline":         "hanoi/baseline/data/hanoi_baseline.csv",
    "hanoi_cf1_four_pegs":    "hanoi/cf1_four_pegs/data/hanoi_cf1_four_pegs.csv",
    "hanoi_cf2_adjacent":     "hanoi/cf2_adjacent/data/hanoi_cf2_adjacent.csv",
    "checker_baseline":       "checker_jumping/baseline/data/checker_baseline.csv",
    "checker_cf1_asymmetric": "checker_jumping/cf1_asymmetric/data/checker_cf1_asymmetric.csv",
    "checker_cf2_jump_two":   "checker_jumping/cf2_jump_two/data/checker_cf2_jump_two.csv",
    "checker_cf3_two_empty":  "checker_jumping/cf3_two_empty/data/checker_cf3_two_empty.csv",
    "river_baseline":         "river_crossing/baseline/data/river_baseline.csv",
    "river_cf1_neutral":      "river_crossing/cf1_neutral/data/river_cf1_neutral.csv",
}

FIELDNAMES = ["id", "game", "variant", "n", "prompt"]


def build_file(data_csv: str, output_csv: str):
    os.makedirs(os.path.dirname(output_csv) or ".", exist_ok=True)
    count = 0
    with open(data_csv, newline="") as fin, open(output_csv, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in reader:
            prompt = build_prompt(row)
            writer.writerow({
                "id": row["id"],
                "game": row["game"],
                "variant": row["variant"],
                "n": row.get("n", ""),
                "prompt": prompt,
            })
            count += 1
    print(f"  {count} prompts → {output_csv}")


def main():
    ap = argparse.ArgumentParser(description="Build evaluation prompts from data CSVs")
    ap.add_argument("--data", help="Path to a single data CSV")
    ap.add_argument("--output", help="Output prompt CSV path")
    ap.add_argument("--all", action="store_true", help="Build prompts for all known datasets")
    ap.add_argument("--output-dir", default="prompts", help="Output directory when using --all")
    args = ap.parse_args()

    if args.all:
        os.makedirs(args.output_dir, exist_ok=True)
        for name, rel_path in ALL_DATA_CSVS.items():
            src = os.path.join(_ROOT, rel_path)
            if not os.path.exists(src):
                print(f"  SKIP {name}: not found")
                continue
            dst = os.path.join(args.output_dir, f"{name}_prompts.csv")
            build_file(src, dst)
        return

    if args.data:
        output = args.output or args.data.replace(".csv", "_prompts.csv")
        build_file(args.data, output)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
