#!/usr/bin/env python3
"""
Evaluate model responses on non-math game datasets.

Two modes:
  --self-test   : Validate ground-truth solutions stored in the data CSV.
                  Confirms every grader works correctly. No model responses needed.

  --responses   : Score pre-generated model responses.
                  Input:  --data <data_csv>  --responses <responses_csv>
                  The responses CSV must have columns: id, response
                  (plus optional: model, prompt)
                  Output: --output <scored_csv>  (defaults to <responses_csv>_scored.csv)

Usage examples:
  python evaluate.py --self-test --data ../non_math_games/hanoi/baseline/data/hanoi_baseline.csv
  python evaluate.py --self-test --all
  python evaluate.py --responses responses.csv --data hanoi_baseline.csv --output scored.csv
"""
import argparse
import csv
import json
import os
import sys

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from non_math_games_eval import graders, parsers

# ── All data CSV paths relative to the non_math_games folder ──────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..", "non_math_games")

ALL_DATA_CSVS = {
    "hanoi_baseline":        "hanoi/baseline/data/hanoi_baseline.csv",
    "hanoi_cf1_four_pegs":   "hanoi/cf1_four_pegs/data/hanoi_cf1_four_pegs.csv",
    "hanoi_cf2_adjacent":    "hanoi/cf2_adjacent/data/hanoi_cf2_adjacent.csv",
    "checker_baseline":      "checker_jumping/baseline/data/checker_baseline.csv",
    "checker_cf1_asymmetric":"checker_jumping/cf1_asymmetric/data/checker_cf1_asymmetric.csv",
    "checker_cf2_jump_two":  "checker_jumping/cf2_jump_two/data/checker_cf2_jump_two.csv",
    "checker_cf3_two_empty": "checker_jumping/cf3_two_empty/data/checker_cf3_two_empty.csv",
    "river_baseline":        "river_crossing/baseline/data/river_baseline.csv",
    "river_cf1_neutral":     "river_crossing/cf1_neutral/data/river_cf1_neutral.csv",
}


# ── Core: parse + grade one row ───────────────────────────────────────────────

def score_response(row: dict, response_text: str) -> dict:
    """Parse model text and grade it. Returns a result dict."""
    game = row["game"]

    # Path-based games: parse moves first, then grade
    moves = parsers.parse(game, response_text)
    result = graders.grade(row, moves)

    expected = row.get("num_moves")
    result["parsed_moves"] = json.dumps(moves) if moves else None
    result["expected_move_count"] = int(expected) if expected else None
    return result


# ── Self-test: validate ground-truth solutions ─────────────────────────────────

def self_test(data_csv: str) -> dict:
    """
    Run every ground-truth solution through the grader.
    Returns summary: {total, passed, failed, errors}.
    """
    total = passed = failed = 0
    errors = []

    with open(data_csv, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            solution = json.loads(row["solution"])
            result = graders.grade(row, solution)

            if result["valid"] and result["goal_reached"]:
                passed += 1
            else:
                failed += 1
                errors.append({
                    "id": row["id"],
                    "error": result.get("error"),
                    "error_at_move": result.get("error_at_move"),
                })

    return {"total": total, "passed": passed, "failed": failed, "errors": errors}


# ── Scoring: model responses ───────────────────────────────────────────────────

_SCORE_FIELDS = [
    "id", "run", "game", "variant", "n",
    "parsed_moves", "expected_move_count",
    "valid", "goal_reached", "correct", "valid_but_wrong",
    "move_count", "error", "error_at_move",
    # passthrough
    "model", "response",
]


def score_file(data_csv: str, responses_csv: str, output_csv: str):
    """
    Score a responses CSV.  Responses must have columns: id, response[, run, model].
    'run' is optional — if present, multiple rows with the same id are treated as
    repeated trials and scored individually.  Pass@k aggregation is done separately
    by aggregate.py (or --aggregate mode).
    """
    # Load data rows indexed by id
    data = {}
    with open(data_csv, newline="") as f:
        for row in csv.DictReader(f):
            data[row["id"]] = row

    results = []
    missing = []

    with open(responses_csv, newline="") as f:
        reader = csv.DictReader(f)
        for resp_row in reader:
            rid = resp_row.get("id", "").strip()
            if rid not in data:
                missing.append(rid)
                continue

            data_row = data[rid]
            response_text = resp_row.get("response", "")
            model = resp_row.get("model", "")
            run = resp_row.get("run", "1")

            result = score_response(data_row, response_text)
            result["id"] = rid
            result["run"] = run
            result["game"] = data_row["game"]
            result["variant"] = data_row["variant"]
            result["n"] = data_row.get("n", "")
            result["model"] = model
            result["response"] = response_text
            # valid_but_wrong: all moves legal but goal not reached
            result["valid_but_wrong"] = (
                result.get("valid", False) and not result.get("goal_reached", False)
            )
            results.append(result)

    # Collect all fieldnames in order
    all_keys = []
    seen = set()
    for key in _SCORE_FIELDS:
        if key not in seen:
            all_keys.append(key)
            seen.add(key)
    for r in results:
        for key in r:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    total = len(results)
    correct = sum(1 for r in results if r.get("correct"))
    valid = sum(1 for r in results if r.get("valid"))
    parse_fail = sum(1 for r in results if not r.get("parsed_moves"))

    print(f"Scored {total} rows → {output_csv}")
    print(f"  Correct       : {correct}/{total} ({100*correct/total:.1f}%)" if total else "  No rows")
    print(f"  Valid moves   : {valid}/{total}")
    print(f"  Parse failures: {parse_fail}")
    if missing:
        print(f"  WARNING: {len(missing)} response IDs not found in data CSV")

    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Evaluate model responses on non-math game CFs")
    ap.add_argument("--self-test", action="store_true", help="Validate ground-truth solutions")
    ap.add_argument("--all", action="store_true", help="Run on all known data CSVs")
    ap.add_argument("--data", help="Path to a single data CSV")
    ap.add_argument("--responses", help="Path to responses CSV (id, response[, model])")
    ap.add_argument("--output", help="Path for scored output CSV")
    args = ap.parse_args()

    if args.self_test:
        if args.all:
            total_pass = total_fail = 0
            for name, rel_path in ALL_DATA_CSVS.items():
                path = os.path.join(_ROOT, rel_path)
                if not os.path.exists(path):
                    print(f"  SKIP {name}: file not found")
                    continue
                summary = self_test(path)
                status = "OK" if summary["failed"] == 0 else "FAIL"
                print(f"  [{status}] {name}: {summary['passed']}/{summary['total']} passed")
                if summary["errors"]:
                    for e in summary["errors"][:3]:
                        print(f"         {e['id']}: {e['error']} (move {e['error_at_move']})")
                total_pass += summary["passed"]
                total_fail += summary["failed"]
            print(f"\nTotal: {total_pass} passed, {total_fail} failed")
        elif args.data:
            summary = self_test(args.data)
            status = "ALL PASS" if summary["failed"] == 0 else f"{summary['failed']} FAILED"
            print(f"{status}: {summary['passed']}/{summary['total']} ground-truth solutions valid")
            for e in summary["errors"]:
                print(f"  {e['id']}: {e['error']} (move {e['error_at_move']})")
        else:
            ap.error("--self-test requires --data <csv> or --all")
        return

    if args.responses:
        if not args.data:
            ap.error("--responses requires --data <data_csv>")
        output = args.output or args.responses.replace(".csv", "_scored.csv")
        score_file(args.data, args.responses, output)
        return

    ap.print_help()


if __name__ == "__main__":
    main()
