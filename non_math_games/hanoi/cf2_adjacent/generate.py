"""
Tower of Hanoi — CF2: Adjacent-only moves
Pegs are arranged in a line (0-1-2). Only moves between adjacent
pegs are allowed: 0↔1 and 1↔2. The direct 0↔2 move is forbidden.
Produces 3^n - 1 moves (much longer than standard).
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from hanoi.utils import make_initial_state, make_goal_state, solve_hanoi_adjacent

N_VALUES = [2, 3, 4, 5, 6, 7]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "hanoi_cf2_adjacent.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        initial = make_initial_state(n, num_pegs=3)
        goal = make_goal_state(n, num_pegs=3)
        solution = solve_hanoi_adjacent(n, src=0, dst=2)
        rows.append({
            "id": f"hanoi_cf2_adjacent_n{n}",
            "game": "hanoi",
            "variant": "cf2_adjacent",
            "n": n,
            "params": json.dumps({"num_pegs": 3, "adjacent_only": True}),
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
