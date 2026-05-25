from . import hanoi, checker, river

GRADERS = {
    "hanoi": hanoi.validate,
    "checker_jumping": checker.validate,
    "river_crossing": river.validate,
}

def grade(row, moves_or_text):
    game = row["game"]
    if game not in GRADERS:
        raise ValueError(f"No grader for game '{game}'")
    return GRADERS[game](moves_or_text, row)
