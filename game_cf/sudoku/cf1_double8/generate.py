"""CF1 – Double-8 Sudoku: digit set {1,2,3,4,5,6,7,8,8}, no 9.
8 must appear exactly twice per row, column, and 3×3 box.
One MCQ distractor is always the standard 1-9 solution of the same puzzle.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solve_one, has_unique_solution
from utils.generator import random_complete_grid, make_puzzle
from utils.distractor import make_distractors
from utils.io_utils import write_csv
from utils.mcq import shuffle_options
from utils.display import grid_to_text

N = 9
BOX_SIZE = 3
# Digits to try during solving; is_valid_fn allows 8 twice per unit
VALID_DIGITS = list(range(1, 9))   # [1..8]
STD_DIGITS   = list(range(1, 10))  # [1..9] for standard solver
RULE_NAME    = 'sudoku_cf1_double8'
TARGET_GIVENS = 30
NUM_SAMPLES   = 100

CF_TARGET  = sorted([1, 2, 3, 4, 5, 6, 7, 8, 8])
STD_TARGET = sorted(STD_DIGITS)

RULE_DESC = (
    "Solve the following modified Sudoku puzzle.\n"
    "Rule change: The valid digit set is {1, 2, 3, 4, 5, 6, 7, 8, 8}. "
    "The digit 9 does not exist. The digit 8 must appear exactly twice "
    "in every row, column, and 3×3 box."
)


def _std_box_cells(r, c):
    br = (r // BOX_SIZE) * BOX_SIZE
    bc = (c // BOX_SIZE) * BOX_SIZE
    return [(br + i, bc + j) for i in range(BOX_SIZE) for j in range(BOX_SIZE)]


def is_valid_cf1(grid, r, c, d):
    max_count = 2 if d == 8 else 1
    if grid[r].count(d) >= max_count:
        return False
    if sum(1 for i in range(N) if grid[i][c] == d) >= max_count:
        return False
    if sum(1 for r2, c2 in _std_box_cells(r, c) if grid[r2][c2] == d) >= max_count:
        return False
    return True


def is_complete_valid_cf1(grid):
    for r in range(N):
        if sorted(grid[r]) != CF_TARGET:
            return False
    for c in range(N):
        if sorted(grid[r][c] for r in range(N)) != CF_TARGET:
            return False
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            box = [grid[br * BOX_SIZE + i][bc * BOX_SIZE + j]
                   for i in range(BOX_SIZE) for j in range(BOX_SIZE)]
            if sorted(box) != CF_TARGET:
                return False
    return True


def is_valid_std(grid, r, c, d):
    if d in grid[r]:
        return False
    for i in range(N):
        if grid[i][c] == d:
            return False
    for r2, c2 in _std_box_cells(r, c):
        if grid[r2][c2] == d:
            return False
    return True


def _fix_givens_for_std(puzzle):
    """Remove duplicate 8-givens so standard rules can solve the puzzle."""
    p = [row[:] for row in puzzle]
    for r in range(N):
        eights = [c for c in range(N) if p[r][c] == 8]
        for c in eights[1:]:
            p[r][c] = 0
    for c in range(N):
        eights = [r for r in range(N) if p[r][c] == 8]
        for r in eights[1:]:
            p[r][c] = 0
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            eights = [(br * BOX_SIZE + i, bc * BOX_SIZE + j)
                      for i in range(BOX_SIZE) for j in range(BOX_SIZE)
                      if p[br * BOX_SIZE + i][bc * BOX_SIZE + j] == 8]
            for r2, c2 in eights[1:]:
                p[r2][c2] = 0
    return p


def _make_question(puzzle, has_std_distractor=False):
    display = grid_to_text(puzzle, N, BOX_SIZE, str)
    note = (
        "\nNote: one option is the solution obtained by applying standard Sudoku rules."
        if has_std_distractor else ""
    )
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle (. = empty cell):\n{display}\n\n"
        f"Which of the following is the correct completed solution?{note}"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen_puzzles = set()

    while len(rows) < num_samples:
        complete = random_complete_grid(N, VALID_DIGITS, is_valid_cf1, rng)
        if complete is None:
            continue

        puzzle = make_puzzle(complete, N, VALID_DIGITS, is_valid_cf1, rng,
                             target_givens=TARGET_GIVENS, check_unique=True)

        # Reduce givens so puzzle is also valid under standard rules
        puzzle_std = _fix_givens_for_std(puzzle)

        # Re-verify CF1 uniqueness with the (possibly reduced) puzzle
        if not has_unique_solution(puzzle_std, N, VALID_DIGITS, is_valid_cf1):
            puzzle_std = puzzle  # fall back to original

        puzzle_key = json.dumps(puzzle_std)
        if puzzle_key in seen_puzzles:
            continue

        # CF1 solution for this (possibly reduced) puzzle
        cf_sol = solve_one(puzzle_std, N, VALID_DIGITS, is_valid_cf1)
        if cf_sol is None:
            continue

        # Try to get a standard solution (natural wrong-rule foil)
        std_sol = solve_one(puzzle_std, N, STD_DIGITS, is_valid_std)

        distractors_json = []
        if std_sol and std_sol != cf_sol:
            distractors_json.append(json.dumps(std_sol))

        needed = 3 - len(distractors_json)
        given_mask = {(r, c) for r in range(N) for c in range(N) if puzzle_std[r][c] != 0}
        near_misses = make_distractors(cf_sol, N, is_complete_valid_cf1, rng,
                                       count=needed, given_mask=given_mask)
        distractors_json += [json.dumps(d) for d in near_misses]

        if len(distractors_json) < 3:
            continue

        has_std = std_sol is not None  # cf_sol always differs (digit-set {1..8,8} vs {1..9})
        sol_json = json.dumps(cf_sol)
        opts, correct = shuffle_options(sol_json, distractors_json[:3], rng)
        seen_puzzles.add(puzzle_key)

        num_givens = sum(1 for r in range(N) for c in range(N) if puzzle_std[r][c] != 0)
        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps(puzzle_std),
            'question': _make_question(puzzle_std, has_std_distractor=has_std),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'num_givens': num_givens,
                'grid_size': N,
                'has_standard_distractor': std_sol is not None and std_sol != cf_sol,
            }),
        })
        counter += 1

    output_path = os.path.join(output_dir, f'{RULE_NAME}.csv')
    write_csv(rows, output_path)
    print(f"Written {len(rows)} rows to {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir',
                        default=os.path.join(os.path.dirname(__file__), 'data'))
    parser.add_argument('--num-samples', type=int, default=NUM_SAMPLES)
    args = parser.parse_args()
    generate(args.seed, args.output_dir, args.num_samples)
