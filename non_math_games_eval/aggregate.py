#!/usr/bin/env python3
"""
Aggregate per-run scored results into pass@k and consistency metrics.

Input : scored CSV produced by evaluate.py  (columns include: id, run, game,
        variant, n, model, correct, valid, valid_but_wrong, goal_reached)

Output: two CSVs
  --problem-csv : one row per (id, model) — pass@k, consistency
  --summary-csv : one row per (game, variant, n, model) — group-level averages

Metrics computed:
  pass@1        — mean individual-run accuracy  (correct / total runs)
  pass@k_any    — problem solved in ≥1 of k runs
  pass@k_maj    — problem solved in >k/2 of k runs  (majority vote)
  consistency   — all runs identical (all-correct or all-wrong)
  valid_but_wrong_rate — fraction of runs with valid moves but wrong final state

Usage:
  python aggregate.py --input scored.csv --k 5 \\
      --problem-csv per_problem.csv --summary-csv summary.csv
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from math import comb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Core aggregation ──────────────────────────────────────────────────────────

def _pass_at_k_unbiased(n, c, k):
    """
    Unbiased pass@k estimator from Chen et al. (Codex paper):
      pass@k = 1 - C(n-c, k) / C(n, k)
    n = total runs, c = correct runs, k = target k.
    Returns 0 if k > n.
    """
    if k > n:
        return None  # not enough runs
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def aggregate_problem(runs: list[dict], k: int) -> dict:
    """
    runs: list of scored rows for the same (id, model)
    Returns aggregated metrics for that problem.
    """
    n = len(runs)
    c = sum(1 for r in runs if r.get("correct") in (True, "True", "true", "1", 1))
    vbw = sum(1 for r in runs if r.get("valid_but_wrong") in (True, "True", "true", "1", 1))

    pass1 = c / n if n > 0 else 0.0
    passk_any = _pass_at_k_unbiased(n, c, k)
    passk_maj = _pass_at_k_unbiased(n, c, k // 2 + 1) if k >= 2 else pass1
    consistent = (c == 0 or c == n)  # always right or always wrong

    first = runs[0]
    return {
        "id": first.get("id", ""),
        "game": first.get("game", ""),
        "variant": first.get("variant", ""),
        "n": first.get("n", ""),
        "model": first.get("model", ""),
        "num_runs": n,
        "num_correct": c,
        "pass@1": round(pass1, 4),
        f"pass@{k}_any": round(passk_any, 4) if passk_any is not None else "",
        f"pass@{k}_majority": round(passk_maj, 4) if passk_maj is not None else "",
        "consistent": consistent,
        "valid_but_wrong_rate": round(vbw / n, 4) if n > 0 else 0.0,
    }


def aggregate_group(problems: list[dict], k: int) -> dict:
    """
    problems: list of per-problem dicts for the same (game, variant, n, model)
    Returns group-level averages.
    """
    if not problems:
        return {}

    def mean(key):
        vals = [p[key] for p in problems if isinstance(p.get(key), (int, float))]
        return round(sum(vals) / len(vals), 4) if vals else ""

    first = problems[0]
    return {
        "game": first["game"],
        "variant": first["variant"],
        "n": first["n"],
        "model": first["model"],
        "num_problems": len(problems),
        "total_runs": sum(p["num_runs"] for p in problems),
        "pass@1": mean("pass@1"),
        f"pass@{k}_any": mean(f"pass@{k}_any"),
        f"pass@{k}_majority": mean(f"pass@{k}_majority"),
        "consistency_rate": round(
            sum(1 for p in problems if p["consistent"]) / len(problems), 4
        ),
        "valid_but_wrong_rate": mean("valid_but_wrong_rate"),
    }


# ── I/O ───────────────────────────────────────────────────────────────────────

def run(input_csv: str, k: int, problem_csv: str | None, summary_csv: str | None):
    # Load all scored rows
    rows = []
    with open(input_csv, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    if not rows:
        print("No rows in input CSV.")
        return

    # Group by (id, model)
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        key = (row.get("id", ""), row.get("model", ""))
        groups[key].append(row)

    problem_rows = [aggregate_problem(runs, k) for runs in groups.values()]

    if problem_csv:
        _write_csv(problem_rows, problem_csv)
        print(f"Per-problem aggregates → {problem_csv}  ({len(problem_rows)} rows)")

    if summary_csv:
        # Group problem_rows by (game, variant, n, model)
        summary_groups: dict[tuple, list] = defaultdict(list)
        for p in problem_rows:
            key = (p["game"], p["variant"], p["n"], p["model"])
            summary_groups[key].append(p)

        summary_rows = [
            aggregate_group(probs, k)
            for probs in summary_groups.values()
        ]
        # Sort by game, variant, n
        summary_rows.sort(key=lambda r: (r.get("game",""), r.get("variant",""), str(r.get("n",""))))
        _write_csv(summary_rows, summary_csv)
        print(f"Group summary           → {summary_csv}  ({len(summary_rows)} rows)")

    # Print summary table to stdout
    print(f"\n{'game':<20} {'variant':<25} {'n':>3}  {'pass@1':>6}  {'pass@{k}_any':>10}  {'pass@{k}_maj':>10}  {'consist':>7}  {'valid≠goal':>10}")
    print("-" * 100)
    for r in sorted(problem_rows, key=lambda x: (x.get("game",""), x.get("variant",""), str(x.get("n","")))):
        any_k = r.get(f"pass@{k}_any", "")
        maj_k = r.get(f"pass@{k}_majority", "")
        print(
            f"  {r.get('game',''):<18} {r.get('variant',''):<24} {str(r.get('n','')):>3}"
            f"  {r.get('pass@1',''):>6}  {str(any_k):>10}  {str(maj_k):>10}"
            f"  {'yes' if r.get('consistent') else 'no':>7}  {r.get('valid_but_wrong_rate',''):>10}"
        )


def _write_csv(rows: list[dict], path: str):
    if not rows:
        return
    all_keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Aggregate pass@k metrics from scored responses")
    ap.add_argument("--input", required=True, help="Scored CSV from evaluate.py")
    ap.add_argument("--k", type=int, default=5, help="k for pass@k (default: 5)")
    ap.add_argument("--problem-csv", default=None, help="Output: one row per problem")
    ap.add_argument("--summary-csv", default=None, help="Output: one row per (game, variant, n)")
    args = ap.parse_args()

    run(args.input, args.k, args.problem_csv, args.summary_csv)


if __name__ == "__main__":
    main()
