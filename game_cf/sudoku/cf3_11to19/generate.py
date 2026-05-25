"""CF3 – 11-to-19 Sudoku: symbols {11, 12, ..., 19} replace {1, ..., 9}.
Structurally identical to standard Sudoku; only the labels change.

Strategy: generate a standard 9×9 solution (digits 1–9), then relabel
d → d+10. The "standard solution" distractor keeps the original 1–9 labelling,
making the contrast between rule sets immediately visible in the options.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solve_one
from utils.generator import random_complete_grid, make_puzzle
from utils.distractor import make_distractors
from utils.io_utils import write_csv
from utils.mcq import shuffle_options
from utils.display import grid_to_text

N = 9
BOX_SIZE = 3
STD_DIGITS   = list(range(1, 10))   # 1-9 for underlying solver
CF_DIGITS    = list(range(11, 20))  # 11-19 for display and options
RULE_NAME    = 'sudoku_cf3_11to19'
TARGET_GIVENS = 30
NUM_SAMPLES   = 100

CF_TARGET  = sorted(CF_DIGITS)
STD_TARGET = sorted(STD_DIGITS)

RULE_DESC = (
    "Solve the following modified Sudoku puzzle.\n"
    "Rule change: Instead of the digits 1–9, the valid symbols are 11–19. "
    "Each row, column, and 3×3 box must contain each of "
    "{11, 12, 13, 14, 15, 16, 17, 18, 19} exactly once."
)


def _box_cells(r, c):
    br = (r // BOX_SIZE) * BOX_SIZE
    bc = (c // BOX_SIZE) * BOX_SIZE
    return [(br + i, bc + j) for i in range(BOX_SIZE) for j in range(BOX_SIZE)]


def _is_valid_std(grid, r, c, d):
    """Validity check on the 1-9 working grid."""
    if d in grid[r]:
        return False
    for i in range(N):
        if grid[i][c] == d:
            return False
    for r2, c2 in _box_cells(r, c):
        if grid[r2][c2] == d:
            return False
    return True


def is_complete_valid_cf3(grid):
    """Validate a complete grid whose values are in {11..19}."""
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


def _relabel(grid, offset=10):
    """Add offset to every non-zero cell value."""
    return [[v + offset if v != 0 else 0 for v in row] for row in grid]


def _digit_str(d):
    return str(d)


def _make_question(puzzle_cf):
    display = grid_to_text(puzzle_cf, N, BOX_SIZE, _digit_str)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle (. = empty cell):\n{display}\n\n"
        "Which of the following is the correct completed solution?\n"
        "Note: one option shows what the solution looks like under standard "
        "Sudoku rules (using digits 1–9 instead of 11–19)."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen_puzzles = set()

    while len(rows) < num_samples:
        # Solve in 1-9 space, then relabel
        std_complete = random_complete_grid(N, STD_DIGITS, _is_valid_std, rng)
        if std_complete is None:
            continue

        std_puzzle = make_puzzle(std_complete, N, STD_DIGITS, _is_valid_std, rng,
                                 target_givens=TARGET_GIVENS, check_unique=True)

        # Relabel to 11-19
        cf_complete = _relabel(std_complete)
        cf_puzzle   = _relabel(std_puzzle)

        # Correctness sanity-check
        if not is_complete_valid_cf3(cf_complete):
            continue

        puzzle_key = json.dumps(cf_puzzle)
        if puzzle_key in seen_puzzles:
            continue

        # Distractors: standard solution (1-9) + 2 near-misses in 11-19 space
        std_sol_json = json.dumps(std_complete)   # the 1-9 "standard" solution
        given_mask = {(r, c) for r in range(N) for c in range(N) if cf_puzzle[r][c] != 0}
        near_misses = make_distractors(cf_complete, N, is_complete_valid_cf3, rng,
                                       count=2, given_mask=given_mask)

        if len(near_misses) < 2:
            continue

        distractors_json = [std_sol_json] + [json.dumps(d) for d in near_misses]

        sol_json = json.dumps(cf_complete)
        opts, correct = shuffle_options(sol_json, distractors_json, rng)
        seen_puzzles.add(puzzle_key)

        num_givens = sum(1 for r in range(N) for c in range(N) if cf_puzzle[r][c] != 0)
        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps(cf_puzzle),
            'question': _make_question(cf_puzzle),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({'num_givens': num_givens, 'grid_size': N}),
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
