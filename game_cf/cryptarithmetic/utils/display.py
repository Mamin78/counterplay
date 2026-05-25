"""Display utilities for cryptarithmetic puzzles."""


def build_equation_string(words, coefficients):
    """
    Build a human-readable equation string.

    Examples
    --------
    ['ABC', 'DEF', 'GHI'], [+1, +1, -1]       -> 'ABC + DEF = GHI'
    ['ABC', 'DEF', 'GH', 'IJK'], [+1,+1,-1,-1] -> 'ABC + DEF - GH = IJK'
    """
    parts = [words[0]]
    # Middle words: indices 1 .. n-2 (all except the last, which is the RHS)
    for word, coeff in zip(words[1:-1], coefficients[1:-1]):
        op = '+' if coeff > 0 else '-'
        parts.append(f'{op} {word}')
    parts.append(f'= {words[-1]}')
    return ' '.join(parts)


def assignment_to_str(assignment):
    """Format an assignment as 'A=3, B=7, …' sorted by letter."""
    return ', '.join(f'{k}={v}' for k, v in sorted(assignment.items()))
