"""Display helpers for Entropy Jugs puzzles."""


CLASSIC_RULES = (
    "  - Fill a jug from the tap (fills it to full capacity).\n"
    "  - Empty a jug (drains it completely to 0).\n"
    "  - Pour from one jug to the other (transfers water exactly, no loss)."
)

TAXED_RULES = (
    "  - Fill a jug from the tap (fills it to full capacity).\n"
    "  - Empty a jug (drains it completely to 0).\n"
    "  - Pour from one jug to the other — with a 1-unit EVAPORATION TAX:\n"
    "      Amount removed from source jug = min(Source, TargetSpace + 1)\n"
    "      Amount added to target jug     = max(0, AmountRemoved - 1)\n"
    "    Example: pouring 4 units removes 4 from source but delivers only 3 to target."
)


def puzzle_to_text(cap1, cap2, target, start, taxed=False):
    """One-line setup summary embedded in question text."""
    return (
        f"Jug A capacity: {cap1}L | Jug B capacity: {cap2}L | "
        f"Starting state: [{start[0]}, {start[1]}] | Target: {target}L in either jug"
    )
