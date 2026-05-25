"""
Validates a River Crossing solution.
Solution: list of passenger lists (one list per trip).
Direction alternates: trip 1 (index 0) → L→R, trip 2 → R→L, ...
Person naming follows the CSV: 'A_1', 'A_2', 'a_1', 'a_2', 'neutral'.
"""
import json


def validate(trips, row):
    """
    trips : list of lists-of-strings  (each inner list = passengers for that trip)
    row   : CSV row dict
    """
    params = json.loads(row["params"])
    boat_capacity = params.get("boat_capacity", 2)
    initial = json.loads(row["initial_state"])  # [left_bank_list, right_bank_list]
    goal = json.loads(row["goal_state"])

    left = set(initial[0])
    right = set(initial[1])
    goal_left = set(goal[0])
    goal_right = set(goal[1])

    # Validate the initial state itself
    err = _check_safety(left, "initial left bank")
    if err:
        return _fail(f"Initial state unsafe: {err}", 0, len(trips))

    for i, passengers in enumerate(trips, 1):
        passengers = [str(p) for p in passengers]
        going_right = (i % 2 == 1)  # trip 1,3,5,... go L→R

        if not passengers:
            return _fail(f"Trip {i}: empty boat", i, len(trips))
        if len(passengers) > boat_capacity:
            return _fail(
                f"Trip {i}: {len(passengers)} passengers exceeds capacity {boat_capacity}",
                i, len(trips),
            )

        departure = left if going_right else right
        arrival = right if going_right else left
        dir_label = "left" if going_right else "right"

        for p in passengers:
            if p not in departure:
                return _fail(f"Trip {i}: '{p}' not on {dir_label} bank", i, len(trips))

        for p in passengers:
            departure.discard(p)
            arrival.add(p)

        err = _check_safety(left, f"trip {i} left bank")
        if err:
            return _fail(err, i, len(trips))
        err = _check_safety(right, f"trip {i} right bank")
        if err:
            return _fail(err, i, len(trips))

    goal_reached = (left == goal_left and right == goal_right)
    return {
        "valid": True,
        "goal_reached": goal_reached,
        "correct": goal_reached,
        "move_count": len(trips),
        "error": None,
        "error_at_move": None,
    }


def _check_safety(bank, context):
    """
    Safety rule: if any agent (A_i) and any actor (a_j) are on the same bank,
    then every actor a_i on that bank must have their own agent A_i present.
    'neutral' is exempt.
    """
    agents = {p for p in bank if p.startswith("A_")}
    actors = {p for p in bank if p.startswith("a_")}

    if not agents or not actors:
        return None  # no conflict possible

    for actor in actors:
        suffix = actor[2:]  # 'a_1' → '1'
        own_agent = f"A_{suffix}"
        if own_agent not in bank:
            return f"{context}: '{actor}' unprotected (present agents: {sorted(agents)})"

    return None


def _fail(msg, trip_idx, total):
    return {
        "valid": False,
        "goal_reached": False,
        "correct": False,
        "move_count": total,
        "error": msg,
        "error_at_move": trip_idx,
    }
