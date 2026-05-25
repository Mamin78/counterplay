"""
Parses Checker Jumping move sequences from free-form model text.

Expected format asked in the prompt:
  <COLOR> <FROM> -> <TO>
  e.g. R 2 -> 3   or   B 5 -> 3

Also accepts several fallback formats.
Returns list of [color, from_pos, to_pos] where color is 'R' or 'B'.
"""
import re

_COLOR_MAP = {
    "r": "R", "red": "R",
    "b": "B", "blue": "B",
}


def parse(text: str) -> list:
    """Return list of [color, from_pos, to_pos] extracted from text."""
    moves = []

    # Primary: "R 2 -> 3" or "B 5 -> 3" (color then positions)
    primary = re.findall(
        r"\b([RBrb]|red|blue)\s+(\d+)\s*(?:->|→|to)\s*(\d+)",
        text, re.IGNORECASE,
    )
    for c, f, t in primary:
        color = _COLOR_MAP.get(c.lower())
        if color:
            moves.append([color, int(f), int(t)])

    if moves:
        return moves

    # Fallback 1: "Move red/R from 2 to 3"
    fallback = re.findall(
        r"move\s+([RBrb]|red|blue)\s+(?:frog\s+)?(?:from\s+)?(?:pos(?:ition)?\s+)?(\d+)\s+(?:to|->|→)\s+(?:pos(?:ition)?\s+)?(\d+)",
        text, re.IGNORECASE,
    )
    for c, f, t in fallback:
        color = _COLOR_MAP.get(c.lower())
        if color:
            moves.append([color, int(f), int(t)])

    if moves:
        return moves

    # Fallback 2: "[R, 2, 3]"
    json_like = re.findall(
        r"\[\s*['\"]?([RBrb]|red|blue)['\"]?\s*,\s*(\d+)\s*,\s*(\d+)\s*\]",
        text, re.IGNORECASE,
    )
    for c, f, t in json_like:
        color = _COLOR_MAP.get(c.lower())
        if color:
            moves.append([color, int(f), int(t)])

    return moves
