from . import hanoi, checker, river

PARSERS = {
    "hanoi": hanoi.parse,
    "checker_jumping": checker.parse,
    "river_crossing": river.parse,
}

def parse(game, text):
    if game not in PARSERS:
        raise ValueError(f"No parser for game '{game}'")
    return PARSERS[game](text)
