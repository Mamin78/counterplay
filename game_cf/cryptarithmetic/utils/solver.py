"""
Cryptarithmetic solver using column-based backtracking with carry propagation.

The column carry approach prunes the search space aggressively: after assigning
all letters that first appear in a given column, we check whether the column sum
plus carry-in is divisible by the base.  Only valid column sums are propagated,
reducing the effective branching factor from O(base) to O(1) per column on average.

This works for any mix of addition and subtraction in any base.
"""


def _word_value(word, assignment, base):
    v = 0
    for ch in word:
        v = v * base + assignment[ch]
    return v


def solve(words, coefficients, base=10, max_solutions=2):
    """
    Find letter→digit assignments satisfying sum_i(coefficients[i] * value(words[i])) == 0.

    Parameters
    ----------
    words : list[str]
        Each string is a sequence of letter characters.
    coefficients : list[int]
        +1 for terms added on the LHS, -1 for the RHS term and any subtracted LHS terms.
    base : int
        Number base (9 for Base-9, 10 for standard).
    max_solutions : int
        Stop early once this many solutions are found (use 2 for uniqueness checks).

    Returns
    -------
    list[dict[str, int]]
        Each dict maps letter → digit value.
    """
    if not words:
        return []

    max_len = max(len(w) for w in words)

    # Build column structure: columns[c] = [(letter, coeff), ...], c=0 is rightmost column.
    columns = []
    for c in range(max_len):
        col = []
        for w, coeff in zip(words, coefficients):
            pos = len(w) - 1 - c
            if 0 <= pos < len(w):
                col.append((w[pos], coeff))
        columns.append(col)

    # Leading letters of multi-character words cannot be 0.
    leading = {w[0] for w in words if len(w) > 1}

    # For each column (right→left), record letters appearing here for the first time.
    seen = set()
    col_new = []
    for c in range(max_len):
        new = []
        for ch, _ in columns[c]:
            if ch not in seen:
                new.append(ch)
                seen.add(ch)
        col_new.append(new)

    solutions = []

    def process_column(c, carry, asgn, used):
        if len(solutions) >= max_solutions:
            return
        if c == max_len:
            if carry == 0:
                solutions.append(dict(asgn))
            return

        new_letters = col_new[c]

        def assign_new(li):
            if len(solutions) >= max_solutions:
                return
            if li == len(new_letters):
                # All new letters for this column are now assigned.
                # Column constraint: (col_sum + carry) must be divisible by base.
                col_sum = sum(coeff * asgn[ch] for ch, coeff in columns[c])
                total = col_sum + carry
                if total % base == 0:
                    process_column(c + 1, total // base, asgn, used)
                # Else: prune — this branch can never satisfy the equation.
                return

            ch = new_letters[li]
            lo = 1 if ch in leading else 0
            for d in range(lo, base):
                if d not in used:
                    asgn[ch] = d
                    used.add(d)
                    assign_new(li + 1)
                    del asgn[ch]
                    used.discard(d)

        assign_new(0)

    process_column(0, 0, {}, set())
    return solutions


def has_unique_solution(words, coefficients, base=10):
    """Return True iff exactly one valid assignment exists."""
    return len(solve(words, coefficients, base, max_solutions=2)) == 1


def is_valid_assignment(assignment, words, coefficients, base):
    """Quick check: does this specific assignment satisfy the equation?"""
    total = sum(
        c * _word_value(w, assignment, base)
        for w, c in zip(words, coefficients)
    )
    return total == 0
