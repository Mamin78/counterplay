"""
Strip MCQ-specific columns and prose from every game_cf CSV.

The generators emit MCQ-shaped CSVs (option_A..D, correct_option, plus a
question that ends with "Which of the following ...?"). The evaluation used
in the thesis is open-ended: the model sees the puzzle and produces an answer
directly, which is verified against `correct_answer`.

This script rewrites every per-variant CSV in place, dropping:
  - option_A, option_B, option_C, option_D
  - correct_option
And rewrites the `question` column with the MCQ-prompting lines removed,
matching the runtime strip performed by llm_eval/evaluate_games_open.py.

Run from the project root:
    python scripts/strip_mcq_from_game_cf.py
Idempotent: re-running has no effect once the columns are gone.
"""
from __future__ import annotations

import glob
import os
import re
import sys

import pandas as pd

DROP_COLS = ["option_A", "option_B", "option_C", "option_D", "correct_option"]

# Matches MCQ-prompting lines.
# First four are kept verbatim from llm_eval/evaluate_games_open.py.
# The "Each answer option" line is an entropy_jugs-only residue that the
# runtime evaluator left in by oversight; we strip it here for the public data.
_MCQ_STRIP_RE = re.compile(
    r"\n(?:"
    r"Which of the following[^\n]*"
    r"|Which option[^\n]*"
    r"|Which expression[^\n]*"
    r"|Note: one option[^\n]*"
    r"|Each answer option[^\n]*"
    r")",
    re.MULTILINE,
)


def _strip_mcq(q: str) -> str:
    return _MCQ_STRIP_RE.sub("", q).rstrip()


def clean_csv(path: str) -> dict:
    df = pd.read_csv(path)
    before = set(df.columns)

    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    if "question" in df.columns:
        df["question"] = df["question"].astype(str).map(_strip_mcq)

    df.to_csv(path, index=False)
    dropped = before & set(DROP_COLS)
    return {"rows": len(df), "dropped": sorted(dropped)}


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = os.path.join(root, "game_cf/*/*/data/*.csv")
    paths = sorted(glob.glob(pattern))
    if not paths:
        print(f"No CSVs matched {pattern!r}", file=sys.stderr)
        return 1

    total_rows = 0
    for path in paths:
        info = clean_csv(path)
        rel = os.path.relpath(path, root)
        dropped = ",".join(info["dropped"]) if info["dropped"] else "(already clean)"
        print(f"  {rel}: {info['rows']} rows  dropped=[{dropped}]")
        total_rows += info["rows"]

    print(f"\nDone. {len(paths)} CSVs, {total_rows} total rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
