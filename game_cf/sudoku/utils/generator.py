"""Puzzle generation: random complete grids and cell-removal to create puzzles."""
import random
from .solver import solve_one, has_unique_solution


def random_complete_grid(n, valid_digits, is_valid_fn, rng):
    """Return a randomly filled complete valid grid, or None on failure."""
    empty = [[0] * n for _ in range(n)]
    return solve_one(empty, n, valid_digits, is_valid_fn, rng=rng)


def make_puzzle(complete_grid, n, valid_digits, is_valid_fn, rng,
                target_givens=30, check_unique=True):
    """
    Remove cells from a complete grid while optionally preserving unique solvability.
    Returns the puzzle grid (0 = removed cell).  The solution is complete_grid itself.
    """
    puzzle = [row[:] for row in complete_grid]
    cells = list(range(n * n))
    rng.shuffle(cells)
    given_count = n * n

    for idx in cells:
        if given_count <= target_givens:
            break
        r, c = divmod(idx, n)
        val = puzzle[r][c]
        puzzle[r][c] = 0

        if check_unique and not has_unique_solution(puzzle, n, valid_digits, is_valid_fn):
            puzzle[r][c] = val  # restore
        else:
            given_count -= 1

    return puzzle
