"""
River Crossing — Baseline
N missionary-cannibal pairs, boat capacity 2 (or 3 for N>3).
Safety: cannibals must never outnumber missionaries on either bank.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from river_crossing.utils import solve_river
from river_crossing.utils.state import make_people
from river_crossing.utils.solver import _boat_capacity

N_VALUES = [2, 3, 4, 5]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "river_baseline.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        people = sorted(make_people(n, include_neutral=False))
        capacity = _boat_capacity(n)
        initial = [people, []]
        goal = [[], people]
        solution = solve_river(n)
        if solution is None:
            print(f"  WARNING: no solution for n={n}")
            continue
        rows.append({
            "id": f"river_baseline_n{n}",
            "game": "river_crossing",
            "variant": "baseline",
            "n": n,
            "params": json.dumps({"n_pairs": n, "boat_capacity": capacity, "neutral": False}),
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
