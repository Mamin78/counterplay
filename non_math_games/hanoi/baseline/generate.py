"""
Tower of Hanoi — Baseline
3 pegs, move one disk at a time, larger disk never on smaller.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils import make_initial_state, make_goal_state, solve_hanoi

N_VALUES = [2, 3, 4, 5, 6, 7]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "hanoi_baseline.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        initial = make_initial_state(n, num_pegs=3)
        goal = make_goal_state(n, num_pegs=3)
        solution = solve_hanoi(n, src=0, dst=2, aux=1)
        rows.append({
            "id": f"hanoi_baseline_n{n}",
            "game": "hanoi",
            "variant": "baseline",
            "n": n,
            "params": json.dumps({"num_pegs": 3}),
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
