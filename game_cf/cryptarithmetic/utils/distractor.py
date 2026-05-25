"""
Distractor generation for cryptarithmetic MCQs.

Near-miss strategy: swap the digit values of two letters.  The swap preserves
the bijection property (no digit appears twice) but almost always breaks the
equation — we verify this explicitly before accepting the distractor.
"""

from .solver import is_valid_assignment


def make_distractors(assignment, words, coefficients, base, rng, count=3):
    """
    Generate up to ``count`` distinct near-miss distractors.

    Each distractor is produced by swapping the digit values of a randomly
    chosen pair of letters.  Swaps that re-satisfy the equation or introduce a
    leading zero are rejected.

    Parameters
    ----------
    assignment : dict[str, int]  — correct letter→digit mapping
    words : list[str]
    coefficients : list[int]
    base : int
    rng : random.Random
    count : int

    Returns
    -------
    list[dict[str, int]]  — up to ``count`` invalid assignments
    """
    letters = sorted(assignment.keys())
    # All pairs of letters whose values can be swapped.
    all_pairs = [
        (a, b)
        for i, a in enumerate(letters)
        for b in letters[i + 1:]
    ]
    rng.shuffle(all_pairs)

    leading = {w[0] for w in words if len(w) > 1}
    seen = {tuple(sorted(assignment.items()))}
    distractors = []

    for a, b in all_pairs:
        if len(distractors) >= count:
            break

        new_asgn = dict(assignment)
        new_asgn[a], new_asgn[b] = new_asgn[b], new_asgn[a]

        # Reject if any leading letter would become 0.
        if any(new_asgn[ch] == 0 for ch in leading if ch in new_asgn):
            continue

        key = tuple(sorted(new_asgn.items()))
        if key in seen:
            continue

        # Accept only if this is NOT a valid solution.
        if not is_valid_assignment(new_asgn, words, coefficients, base):
            seen.add(key)
            distractors.append(new_asgn)

    return distractors
