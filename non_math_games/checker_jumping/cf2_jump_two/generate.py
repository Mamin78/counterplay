"""
Checker Jumping — CF2: Jump over 2 frogs
A frog can jump over exactly 2 opposite-color frogs (landing 3 steps away)
in addition to the normal 1-step slide. Standard board: N vs N, 1 empty.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from checker_jumping.utils import solve_checker_jump_two
from checker_jumping.utils.state import make_initial_state, make_goal_state

N_VALUES = [2, 3, 4, 5, 6]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "checker_cf2_jump_two.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        initial = make_initial_state(n, n, n_empty=1)
        goal = make_goal_state(n, n, n_empty=1)
        solution = solve_checker_jump_two(n)
        if solution is None:
            print(f"  WARNING: no solution for n={n}")
            continue
        rows.append({
            "id": f"checker_cf2_jump_two_n{n}",
            "game": "checker_jumping",
            "variant": "cf2_jump_two",
            "n": n,
            "params": json.dumps({"n_red": n, "n_blue": n, "n_empty": 1, "jump_distance": 2}),
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
