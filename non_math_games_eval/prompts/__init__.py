from . import hanoi, checker, river

BUILDERS = {
    "hanoi": hanoi.build,
    "checker_jumping": checker.build,
    "river_crossing": river.build,
}

def build_prompt(row: dict) -> str:
    game = row["game"]
    if game not in BUILDERS:
        raise ValueError(f"No prompt builder for game '{game}'")
    return BUILDERS[game](row)
