"""
Checker Jumping — Baseline
N red frogs on left, N blue frogs on right, 1 empty space in middle.
Frogs slide one step forward or jump over exactly 1 opposite-color frog.
Goal: swap all positions.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from checker_jumping.utils import solve_checker
from checker_jumping.utils.state import make_initial_state, make_goal_state

N_VALUES = [2, 3, 4, 5, 6]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "checker_baseline.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        initial = make_initial_state(n, n, n_empty=1)
        goal = make_goal_state(n, n, n_empty=1)
        solution = solve_checker(n, n, max_jump_distance=1, n_empty=1)
        rows.append({
            "id": f"checker_baseline_n{n}",
            "game": "checker_jumping",
            "variant": "baseline",
            "n": n,
            "params": json.dumps({"n_red": n, "n_blue": n, "n_empty": 1, "jump_distance": 1}),
            "initial_state": json.dumps(initial),
            "goal_state": json.dumps(goal),
            "solution": json.dumps(solution),
            "num_moves": len(solution),
        })
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {OUTPUT}")


if __name__ == "__main__":
    generate()
