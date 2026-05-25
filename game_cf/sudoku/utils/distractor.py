"""Near-miss distractor generation: swap two non-given cells in a row
to break column/box constraints while keeping the distractor consistent
with the puzzle's given cells.
"""


def near_miss(solution, n, is_complete_valid_fn, rng,
              given_mask=None, max_attempts=300):
    """
    Produce an invalid near-miss grid by swapping two differently-valued cells
    in the same row.  Both swapped cells must be non-given (i.e., not revealed
    in the puzzle) so the distractor doesn't contradict visible clues.

    solution     : complete valid n×n grid
    given_mask   : optional set of (r, c) that are given/fixed; swaps avoid these
    """
    if given_mask is None:
        given_mask = set()

    for _ in range(max_attempts):
        grid = [row[:] for row in solution]
        r = rng.randint(0, n - 1)

        # Columns that are NOT given in this row and have different values
        free_cols = [c for c in range(n) if (r, c) not in given_mask]
        rng.shuffle(free_cols)

        c1 = c2 = None
        for i in range(len(free_cols) - 1):
            if grid[r][free_cols[i]] != grid[r][free_cols[i + 1]]:
                c1, c2 = free_cols[i], free_cols[i + 1]
                break

        if c1 is None:
            continue

        grid[r][c1], grid[r][c2] = grid[r][c2], grid[r][c1]
        if not is_complete_valid_fn(grid):
            return grid

    return None


def make_distractors(solution, n, is_complete_valid_fn, rng,
                     count=2, given_mask=None):
    """Return `count` distinct near-miss distractor grids."""
    distractors = []
    seen = set()
    for _ in range(count * 400):
        if len(distractors) >= count:
            break
        d = near_miss(solution, n, is_complete_valid_fn, rng,
                      given_mask=given_mask)
        if d is None:
            continue
        key = tuple(d[r][c] for r in range(n) for c in range(n))
        if key not in seen:
            seen.add(key)
            distractors.append(d)
    return distractors
