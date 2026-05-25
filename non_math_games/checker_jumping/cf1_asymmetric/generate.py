"""
Checker Jumping — CF1: Asymmetric counts (N red vs N+k blue)
Left side has N red frogs, right side has N+k blue frogs, 1 empty space.
k ∈ {1, 3, 5}. As N increases so does the size gap.
Goal: blues end up on left, reds on right.
"""
import csv
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from checker_jumping.utils import solve_checker
from checker_jumping.utils.state import make_initial_state, make_goal_state

N_VALUES = [2, 3, 4, 5]
K_VALUES = [1, 3, 5]
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "checker_cf1_asymmetric.csv")
FIELDNAMES = ["id", "game", "variant", "n", "params",
              "initial_state", "goal_state", "solution", "num_moves"]


def generate():
    rows = []
    for n in N_VALUES:
        for k in K_VALUES:
            m = n + k  # blue count
            initial = make_initial_state(n, m, n_empty=1)
            goal = make_goal_state(n, m, n_empty=1)
            solution = solve_checker(n, m, max_jump_distance=1, n_empty=1)
            if solution is None:
                print(f"  WARNING: no solution for n={n}, k={k} (m={m})")
                continue
            rows.append({
                "id": f"checker_cf1_asymmetric_n{n}_k{k}",
                "game": "checker_jumping",
                "variant": "cf1_asymmetric",
                "n": n,
                "params": json.dumps({"n_red": n, "n_blue": m, "k": k, "n_empty": 1, "jump_distance": 1}),
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
