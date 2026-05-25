"""
Builds prompts for Tower of Hanoi evaluation (all three variants).
"""
import json

_PEG_LABELS = {3: ["A", "B", "C"], 4: ["A", "B", "C", "D"]}


def build(row: dict) -> str:
    params = json.loads(row["params"])
    n = int(row["n"])
    n_pegs = params.get("num_pegs", 3)
    labels = _PEG_LABELS.get(n_pegs, [str(i) for i in range(n_pegs)])
    variant = row["variant"]

    initial = json.loads(row["initial_state"])  # list of peg stacks (bottom→top)
    goal = json.loads(row["goal_state"])

    def peg_display(stacks):
        lines = []
        for i, stack in enumerate(stacks):
            contents = ", ".join(str(d) for d in stack) if stack else "(empty)"
            lines.append(f"  Peg {labels[i]}: {contents}  [bottom → top]")
        return "\n".join(lines)

    # --- variant-specific rule paragraph ---
    if variant == "cf2_adjacent":
        extra_rule = (
            "\n- ADJACENCY CONSTRAINT: The pegs are arranged in a line (A – B – C). "
            "You may only move a disk between adjacent pegs (A↔B or B↔C). "
            "A direct move between A and C is NOT allowed."
        )
    else:
        extra_rule = ""

    peg_list = ", ".join(labels)

    prompt = f"""You are solving the Tower of Hanoi puzzle.

RULES:
- There are {n_pegs} pegs labeled {peg_list}.
- There are {n} disks numbered 1 (smallest) to {n} (largest).
- Only the top disk of a peg may be moved.
- A larger disk may never be placed on top of a smaller disk.
- Move ALL disks from peg {labels[0]} to peg {labels[-1]}.{extra_rule}

INITIAL STATE:
{peg_display(initial)}

GOAL STATE:
{peg_display(goal)}

OUTPUT FORMAT:
List every move on its own line using EXACTLY this format (no other text on move lines):
  disk <N> : <SRC> -> <DST>

Example lines:
  disk 1 : A -> C
  disk 2 : A -> B
  disk 1 : C -> B

Think through the solution step by step, then output all moves."""

    return prompt
