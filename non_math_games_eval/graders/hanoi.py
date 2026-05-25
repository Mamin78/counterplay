"""
Validates a Hanoi move sequence against variant rules.
Moves: list of [disk, src_peg, dst_peg]  (ints; pegs 0-indexed; disks 1-indexed).
Works for all three variants: baseline, cf1_four_pegs, cf2_adjacent.
"""
import json


def validate(moves, row):
    """
    moves : list of [disk, src, dst]
    row   : CSV row dict (needs 'params', 'initial_state', 'goal_state', 'variant')
    """
    params = json.loads(row["params"])
    n_pegs = params.get("num_pegs", 3)
    pegs = [list(p) for p in json.loads(row["initial_state"])]
    goal = [list(p) for p in json.loads(row["goal_state"])]
    adjacent_only = row["variant"] == "cf2_adjacent"

    for i, move in enumerate(moves, 1):
        try:
            disk, src, dst = int(move[0]), int(move[1]), int(move[2])
        except (ValueError, IndexError, TypeError) as e:
            return _fail(f"Malformed move {move}: {e}", i, len(moves))

        if not (0 <= src < n_pegs and 0 <= dst < n_pegs):
            return _fail(f"Peg index out of range: {src}→{dst}", i, len(moves))
        if src == dst:
            return _fail(f"src == dst == {src}", i, len(moves))
        if adjacent_only and abs(src - dst) != 1:
            return _fail(f"Non-adjacent move {src}→{dst} not allowed (CF2)", i, len(moves))

        if not pegs[src] or pegs[src][-1] != disk:
            top = pegs[src][-1] if pegs[src] else None
            return _fail(
                f"Disk {disk} not on top of peg {src} (top={top}, peg={pegs[src]})",
                i, len(moves),
            )

        if pegs[dst] and pegs[dst][-1] < disk:
            return _fail(
                f"Cannot place disk {disk} on smaller disk {pegs[dst][-1]} at peg {dst}",
                i, len(moves),
            )

        pegs[src].pop()
        pegs[dst].append(disk)

    goal_reached = pegs == goal
    return {
        "valid": True,
        "goal_reached": goal_reached,
        "correct": goal_reached,
        "move_count": len(moves),
        "error": None,
        "error_at_move": None,
        "final_state": pegs,
    }


def _fail(msg, move_idx, total):
    return {
        "valid": False,
        "goal_reached": False,
        "correct": False,
        "move_count": total,
        "error": msg,
        "error_at_move": move_idx,
        "final_state": None,
    }
