"""
Cryptarithmetic puzzle generator.

Strategy: construct puzzles from a known arithmetic identity.
  1. Choose random digit values for each LHS word.
  2. Compute the RHS value deterministically.
  3. Convert all values to digit arrays.
  4. Map each unique digit to a letter (A, B, C, …), preserving the bijection.
  5. Run the solver to verify the resulting letter equation has exactly one solution.

This guarantees every returned puzzle has at least one solution; the uniqueness
check filters out the rare cases with multiple solutions.
"""

from .solver import solve


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_base_digits(value, length, base):
    """
    Convert a non-negative integer to a list of ``length`` base-B digits,
    most-significant digit first.  Returns None if it doesn't fit.
    """
    if value < 0 or (length > 0 and value >= base ** length):
        return None
    digits = []
    v = value
    for _ in range(length):
        digits.append(v % base)
        v //= base
    return digits[::-1]


def _num_digits(value, base):
    """Number of base-B digits needed to represent a positive integer."""
    if value <= 0:
        return 0
    count = 0
    v = value
    while v > 0:
        count += 1
        v //= base
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_puzzle(
    rng,
    base,
    lhs_lengths,
    lhs_signs,
    min_unique_letters=6,
    min_result_length=1,
    max_attempts=3000,
):
    """
    Generate a unique cryptarithmetic puzzle.

    The equation structure is::

        W[0] <op1> W[1] <op2> … = RESULT

    where each op is determined by lhs_signs (``+1`` → "+", ``-1`` → "−").
    The RESULT word is computed from the LHS values and appended last.

    Parameters
    ----------
    rng : random.Random
    base : int
    lhs_lengths : list[int]
        Length (number of letters) for each LHS word.
    lhs_signs : list[int]
        +1 or -1 per LHS word; the first entry must be +1.
    min_unique_letters : int
        Minimum number of distinct letters in the puzzle.
    min_result_length : int
        Minimum digit-length of the RESULT word.
    max_attempts : int

    Returns
    -------
    (words, coefficients, assignment) or None
        words       : list[str] — letter strings; last is RESULT.
        coefficients: list[int] — +1/-1 per word; last is -1 for RESULT.
        assignment  : dict[str, int] — letter → digit.
    """
    assert len(lhs_lengths) == len(lhs_signs)
    assert lhs_signs[0] == 1, "First LHS term must have sign +1"

    for _ in range(max_attempts):
        # ----------------------------------------------------------------
        # 1. Generate random digit values for LHS words.
        # ----------------------------------------------------------------
        lhs_values = []
        for length in lhs_lengths:
            lo = base ** (length - 1) if length > 1 else 0
            hi = base ** length - 1
            lhs_values.append(rng.randint(lo, hi))

        # ----------------------------------------------------------------
        # 2. Compute RESULT value.
        # ----------------------------------------------------------------
        result_val = sum(s * v for s, v in zip(lhs_signs, lhs_values))

        if result_val <= 0:
            continue

        result_len = _num_digits(result_val, base)

        if result_len < min_result_length:
            continue

        # ----------------------------------------------------------------
        # 3. Convert values to digit arrays and collect unique digits.
        # ----------------------------------------------------------------
        all_lengths = lhs_lengths + [result_len]
        all_values = lhs_values + [result_val]
        all_coefficients = list(lhs_signs) + [-1]

        digit_arrays = []
        skip = False
        for v, L in zip(all_values, all_lengths):
            arr = _to_base_digits(v, L, base)
            if arr is None:
                skip = True
                break
            digit_arrays.append(arr)
        if skip:
            continue

        # No leading zeros (should be guaranteed by lo > 0 for length > 1, but verify).
        if any(arr[0] == 0 for arr, L in zip(digit_arrays, all_lengths) if L > 1):
            continue

        unique_digits = sorted(set(d for arr in digit_arrays for d in arr))

        if len(unique_digits) < min_unique_letters:
            continue
        if len(unique_digits) > base:
            continue  # Shouldn't happen; base arithmetic guarantees this.

        # ----------------------------------------------------------------
        # 4. Build letter-word representation.
        # ----------------------------------------------------------------
        digit_to_letter = {d: chr(ord('A') + i) for i, d in enumerate(unique_digits)}
        assignment = {letter: digit for digit, letter in digit_to_letter.items()}
        words = [''.join(digit_to_letter[d] for d in arr) for arr in digit_arrays]

        # ----------------------------------------------------------------
        # 4b. Pre-check: require at least one letter shared across words.
        # Cross-word letter repetitions are the key mechanism that constrains
        # the solution space and makes unique solutions achievable.
        # Without sharing, puzzles with k < base letters almost always have
        # many valid assignments (the system is underdetermined).
        # ----------------------------------------------------------------
        all_letters_str = ''.join(words)
        if len(set(all_letters_str)) == len(all_letters_str):
            continue  # No cross-word sharing → likely non-unique, skip cheaply.

        # ----------------------------------------------------------------
        # 5. Verify exactly one solution exists.
        # ----------------------------------------------------------------
        solutions = solve(words, all_coefficients, base, max_solutions=2)
        if len(solutions) != 1:
            continue
        if solutions[0] != assignment:
            continue  # Sanity check: solver must agree with our construction.

        return words, all_coefficients, assignment

    return None
