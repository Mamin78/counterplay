"""Generic backtracking Sudoku solver with MRV heuristic."""


def solve(grid, n, valid_digits, is_valid_fn, rng=None, max_solutions=1):
    """
    Backtracking solver parameterised by constraint function.

    grid          : n×n list-of-lists, 0 = empty
    n             : grid dimension
    valid_digits  : ordered list of digits to try (no duplicates even for multiset rules)
    is_valid_fn   : callable(grid, r, c, d) -> bool
    rng           : random.Random for randomised solving; None = deterministic
    max_solutions : stop after finding this many solutions

    Returns a list of complete grids (each is a shallow-copied list-of-lists).
    """
    solutions = []

    def backtrack(g):
        if len(solutions) >= max_solutions:
            return

        # MRV: pick the empty cell with fewest valid candidates
        best_r = best_c = best_cands = None
        for r in range(n):
            for c in range(n):
                if g[r][c] != 0:
                    continue
                cands = [d for d in valid_digits if is_valid_fn(g, r, c, d)]
                if not cands:
                    return  # dead end
                if best_cands is None or len(cands) < len(best_cands):
                    best_r, best_c, best_cands = r, c, cands
                    if len(cands) == 1:
                        break
            if best_cands is not None and len(best_cands) == 1:
                break

        if best_r is None:
            # No empty cells → complete solution
            solutions.append([row[:] for row in g])
            return

        if rng:
            rng.shuffle(best_cands)

        for d in best_cands:
            if len(solutions) >= max_solutions:
                return
            g[best_r][best_c] = d
            backtrack(g)
            g[best_r][best_c] = 0

    backtrack([row[:] for row in grid])
    return solutions


def solve_one(grid, n, valid_digits, is_valid_fn, rng=None):
    s = solve(grid, n, valid_digits, is_valid_fn, rng=rng, max_solutions=1)
    return s[0] if s else None


def has_unique_solution(grid, n, valid_digits, is_valid_fn):
    return len(solve(grid, n, valid_digits, is_valid_fn, max_solutions=2)) == 1
