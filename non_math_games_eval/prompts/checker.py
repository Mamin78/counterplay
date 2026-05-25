"""
Builds prompts for Checker Jumping evaluation (all four variants).
"""
import json


def build(row: dict) -> str:
    params = json.loads(row["params"])
    max_jump = params.get("jump_distance", 1)
    n_empty = params.get("n_empty", 1)
    n_red = params.get("n_red", int(row["n"]))
    n_blue = params.get("n_blue", int(row["n"]))
    variant = row["variant"]

    initial = json.loads(row["initial_state"])  # e.g. ["R","R","_","B","B"]
    goal = json.loads(row["goal_state"])
    total = len(initial)

    def board_display(board):
        indexed = "  ".join(f"[{i}]={cell}" for i, cell in enumerate(board))
        return indexed

    # --- jump rule ---
    if max_jump == 1:
        jump_rule = "- A frog can JUMP: leap over exactly 1 adjacent opposite-color frog into the empty space beyond."
    else:
        jump_rule = (
            "- A frog can JUMP: leap over 1 OR 2 consecutive adjacent opposite-color frogs "
            "into the empty space immediately beyond them (both variants count as one move)."
        )

    # --- empty-space description ---
    empty_desc = f"{n_empty} empty space{'s' if n_empty > 1 else ''} in the middle"

    prompt = f"""You are solving the Checker Jumping (Frog Puzzle).

SETUP:
- The board has {total} positions numbered 0 to {total - 1} (left to right).
- {n_red} Red (R) frogs start on the LEFT. {n_blue} Blue (B) frogs start on the RIGHT.
- There {'are' if n_empty > 1 else 'is'} {empty_desc}.

RULES:
- Red frogs can only move to the RIGHT (increasing position number).
- Blue frogs can only move to the LEFT (decreasing position number).
- A frog can SLIDE: move 1 position into an immediately adjacent empty space.
{jump_rule}
- No other moves are allowed.

INITIAL BOARD:
  {board_display(initial)}
  (read left to right: positions 0 … {total - 1})

GOAL BOARD:
  {board_display(goal)}

OUTPUT FORMAT:
List every move on its own line using EXACTLY this format (no other text on move lines):
  <COLOR> <FROM> -> <TO>

where COLOR is R or B, FROM and TO are 0-indexed position numbers.

Example lines:
  R 1 -> 2
  B 4 -> 3
  R 2 -> 4

Think through the solution step by step, then output all moves."""

    return prompt
