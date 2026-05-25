"""
Tower of Hanoi — CF1: 4 pegs
Same disk constraint, but a fourth peg is available.
Uses Frame-Stewart heuristic for the solution.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from hanoi.utils import make_initial_state, make_goal_state, solve_hanoi_four_pegs

N_VALUES = [2, 3, 4, 5, 6, 7]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "hanoi_cf1_four_pegs.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        initial = make_initial_state(n, num_pegs=4)
        goal = make_goal_state(n, num_pegs=4)
        solution = solve_hanoi_four_pegs(n, src=0, dst=3, aux1=1, aux2=2)
        rows.append({
            "id": f"hanoi_cf1_four_pegs_n{n}",
            "game": "hanoi",
            "variant": "cf1_four_pegs",
            "n": n,
            "params": json.dumps({"num_pegs": 4}),
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
