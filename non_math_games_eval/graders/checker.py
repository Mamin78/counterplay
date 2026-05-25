"""
Validates a Checker Jumping move sequence.
Moves: list of [color, from_pos, to_pos]  (color 'R' or 'B'; positions 0-indexed).
Works for all four variants: baseline, cf1_asymmetric, cf2_jump_two, cf3_two_empty.
"""
import json


def validate(moves, row):
    """
    moves : list of [color, from_pos, to_pos]
    row   : CSV row dict
    """
    params = json.loads(row["params"])
    max_jump = params.get("jump_distance", 1)  # max consecutive opposite frogs to jump over
    board = list(json.loads(row["initial_state"]))
    goal = list(json.loads(row["goal_state"]))
    total = len(board)

    for i, move in enumerate(moves, 1):
        try:
            color = str(move[0]).upper()
            from_pos, to_pos = int(move[1]), int(move[2])
        except (ValueError, IndexError, TypeError) as e:
            return _fail(f"Malformed move {move}: {e}", i, len(moves))

        if color not in ("R", "B"):
            return _fail(f"Unknown color '{color}'", i, len(moves))
        if not (0 <= from_pos < total and 0 <= to_pos < total):
            return _fail(f"Position out of range: {from_pos}→{to_pos} (board size {total})", i, len(moves))
        if board[from_pos] != color:
            return _fail(
                f"No {color} frog at position {from_pos} (found '{board[from_pos]}')",
                i, len(moves),
            )

        dist = to_pos - from_pos
        if color == "R" and dist <= 0:
            return _fail(f"Red must move right ({from_pos}→{to_pos})", i, len(moves))
        if color == "B" and dist >= 0:
            return _fail(f"Blue must move left ({from_pos}→{to_pos})", i, len(moves))

        abs_dist = abs(dist)
        step = 1 if dist > 0 else -1
        opposite = "B" if color == "R" else "R"

        if abs_dist == 1:
            # Slide: destination must be empty
            if board[to_pos] != "_":
                return _fail(f"Slide to occupied pos {to_pos} ('{board[to_pos]}')", i, len(moves))
        elif 2 <= abs_dist <= max_jump + 1:
            # Jump: all intermediate cells must be opposite-color; destination empty
            intermediates = [from_pos + step * k for k in range(1, abs_dist)]
            for pos in intermediates:
                if board[pos] != opposite:
                    return _fail(
                        f"Intermediate pos {pos} is '{board[pos]}', expected '{opposite}'",
                        i, len(moves),
                    )
            if board[to_pos] != "_":
                return _fail(f"Jump destination {to_pos} not empty ('{board[to_pos]}')", i, len(moves))
        else:
            return _fail(
                f"Move distance {abs_dist} invalid (max allowed: {max_jump + 1})",
                i, len(moves),
            )

        board[to_pos] = color
        board[from_pos] = "_"

    goal_reached = board == goal
    return {
        "valid": True,
        "goal_reached": goal_reached,
        "correct": goal_reached,
        "move_count": len(moves),
        "error": None,
        "error_at_move": None,
        "final_board": board,
    }


def _fail(msg, move_idx, total):
    return {
        "valid": False,
        "goal_reached": False,
        "correct": False,
        "move_count": total,
        "error": msg,
        "error_at_move": move_idx,
        "final_board": None,
    }
