"""
Builds prompts for River Crossing evaluation (baseline + neutral variant).
"""
import json


def build(row: dict) -> str:
    params = json.loads(row["params"])
    n_pairs = params.get("n_pairs", int(row["n"]))
    boat_capacity = params.get("boat_capacity", 2)
    has_neutral = params.get("neutral", False)
    variant = row["variant"]

    initial = json.loads(row["initial_state"])  # [left_list, right_list]
    goal = json.loads(row["goal_state"])

    # Build person lists for the prompt
    agents = [f"A_{i}" for i in range(1, n_pairs + 1)]
    actors = [f"a_{i}" for i in range(1, n_pairs + 1)]
    pairs_desc = ", ".join(f"(A_{i}, a_{i})" for i in range(1, n_pairs + 1))

    neutral_section = ""
    if has_neutral:
        neutral_section = (
            "\n- There is also 1 NEUTRAL person (neutral). "
            "The neutral person may travel with anyone and does NOT trigger safety violations — "
            "they count as neither agent nor actor."
        )

    all_on_left = ", ".join(initial[0])
    goal_on_right = ", ".join(goal[1])

    safety_example = (
        f"  Example: if A_1 and a_2 are on a bank, a_2's own agent A_2 must also be present "
        f"(otherwise a_2 is outnumbered)."
    )

    prompt = f"""You are solving the River Crossing puzzle.

SETUP:
- There are {n_pairs} agent-actor pairs: {pairs_desc}.
- Each pair consists of one AGENT (A_i) and one ACTOR (a_i).
- Everyone starts on the LEFT bank. The goal is to move everyone to the RIGHT bank.
- Boat capacity: {boat_capacity} people per trip (minimum 1; boat cannot travel empty).{neutral_section}

SAFETY RULE:
- On any bank, if any ACTOR (a_i) is present alongside any AGENT (A_j), then EVERY actor
  on that bank must have their OWN agent present.
{safety_example}
- A bank with only agents, only actors (and/or neutral), or nobody is always safe.

TRIP DIRECTION:
- Trips alternate automatically: ODD trips go LEFT → RIGHT; EVEN trips go RIGHT → LEFT.
- Trip 1 is LEFT → RIGHT.

INITIAL STATE:
  Left bank : {all_on_left}
  Right bank: (empty)

GOAL STATE:
  Left bank : (empty)
  Right bank: {goal_on_right}

OUTPUT FORMAT:
List every trip on its own line using EXACTLY this format (no other text on trip lines):
  trip <N> : <person1>[, <person2>]

Example lines:
  trip 1 : A_1, a_1
  trip 2 : A_1
  trip 3 : A_1, A_2

Think through the solution step by step, verifying safety after each trip,
then output all trips."""

    return prompt
