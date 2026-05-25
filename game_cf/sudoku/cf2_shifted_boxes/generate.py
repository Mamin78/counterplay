"""CF2 – Shifted-Box Sudoku: toroidal box topology.
Row/column rules identical to standard. The nine 3×3 boxes are shifted
by 1 cell in both directions with wrap-around (toroidal topology).

Box (br, bc) covers rows { (br*3+1+i) % 9 for i in 0..2 }
                and cols { (bc*3+1+j) % 9 for j in 0..2 }.

Cell (r, c) belongs to box ( (r-1)%9 // 3 , (c-1)%9 // 3 ).
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
VALID_DIGITS = list(range(1, 10))
RULE_NAME    = 'sudoku_cf2_shifted_boxes'
TARGET_GIVENS = 32   # slightly more givens to help uniqueness with shifted topology
NUM_SAMPLES   = 100

STD_TARGET = sorted(VALID_DIGITS)

RULE_DESC = (
    "Solve the following modified Sudoku puzzle.\n"
    "Rule change: The row and column rules are identical to standard Sudoku "
    "(each digit 1–9 appears exactly once per row and column). However, the "
    "nine 3×3 boxes are spatially shifted: instead of starting at rows/columns "
    "0, 3, 6, each box is shifted by 1 cell in both directions with toroidal "
    "(wrap-around) topology. Concretely, box (br, bc) covers "
    "rows {(br×3+1) mod 9, (br×3+2) mod 9, (br×3+3) mod 9} and "
    "cols {(bc×3+1) mod 9, (bc×3+2) mod 9, (bc×3+3) mod 9}."
)


def _shifted_box_cells(r, c):
    br = (r - 1) % N // BOX_SIZE
    bc = (c - 1) % N // BOX_SIZE
    return [
        ((br * BOX_SIZE + 1 + i) % N, (bc * BOX_SIZE + 1 + j) % N)
        for i in range(BOX_SIZE) for j in range(BOX_SIZE)
    ]


def _std_box_cells(r, c):
    br = (r // BOX_SIZE) * BOX_SIZE
    bc = (c // BOX_SIZE) * BOX_SIZE
    return [(br + i, bc + j) for i in range(BOX_SIZE) for j in range(BOX_SIZE)]


def is_valid_cf2(grid, r, c, d):
    if d in grid[r]:
        return False
    for i in range(N):
        if grid[i][c] == d:
            return False
    for r2, c2 in _shifted_box_cells(r, c):
        if grid[r2][c2] == d:
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


def is_complete_valid_cf2(grid):
    # Check rows and columns (same as standard)
    for r in range(N):
        if sorted(grid[r]) != STD_TARGET:
            return False
    for c in range(N):
        if sorted(grid[r][c] for r in range(N)) != STD_TARGET:
            return False
    # Check shifted boxes
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            box = [
                grid[(br * BOX_SIZE + 1 + i) % N][(bc * BOX_SIZE + 1 + j) % N]
                for i in range(BOX_SIZE) for j in range(BOX_SIZE)
            ]
            if sorted(box) != STD_TARGET:
                return False
    return True


def _givens_std_box_ok(puzzle):
    """True if no standard box has a duplicate non-zero given."""
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            vals = [
                puzzle[br * BOX_SIZE + i][bc * BOX_SIZE + j]
                for i in range(BOX_SIZE) for j in range(BOX_SIZE)
                if puzzle[br * BOX_SIZE + i][bc * BOX_SIZE + j] != 0
            ]
            if len(vals) != len(set(vals)):
                return False
    return True


def _make_question(puzzle):
    display = grid_to_text(puzzle, N, BOX_SIZE, str)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle (. = empty cell):\n{display}\n\n"
        "Which of the following is the correct completed solution?"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen_puzzles = set()

    while len(rows) < num_samples:
        complete = random_complete_grid(N, VALID_DIGITS, is_valid_cf2, rng)
        if complete is None:
            continue

        puzzle = make_puzzle(complete, N, VALID_DIGITS, is_valid_cf2, rng,
                             target_givens=TARGET_GIVENS, check_unique=True)

        puzzle_key = json.dumps(puzzle)
        if puzzle_key in seen_puzzles:
            continue

        # CF2 solution
        cf_sol = solve_one(puzzle, N, VALID_DIGITS, is_valid_cf2)
        if cf_sol is None:
            continue

        # Try standard solution as a foil (only if givens are standard-box-compatible)
        std_sol = None
        if _givens_std_box_ok(puzzle):
            candidate = solve_one(puzzle, N, VALID_DIGITS, is_valid_std)
            if candidate is not None:
                # CF invariant: if the standard-rule solver yields the same grid,
                # the rule change had no observable effect for this puzzle.
                if candidate == cf_sol:
                    continue
                std_sol = candidate

        distractors_json = []
        if std_sol:
            distractors_json.append(json.dumps(std_sol))

        needed = 3 - len(distractors_json)
        given_mask = {(r, c) for r in range(N) for c in range(N) if puzzle[r][c] != 0}
        near_misses = make_distractors(cf_sol, N, is_complete_valid_cf2, rng,
                                       count=needed, given_mask=given_mask)
        distractors_json += [json.dumps(d) for d in near_misses]

        if len(distractors_json) < 3:
            continue

        sol_json = json.dumps(cf_sol)
        opts, correct = shuffle_options(sol_json, distractors_json[:3], rng)
        seen_puzzles.add(puzzle_key)

        num_givens = sum(1 for r in range(N) for c in range(N) if puzzle[r][c] != 0)
        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps(puzzle),
            'question': _make_question(puzzle),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'num_givens': num_givens,
                'grid_size': N,
                'has_standard_distractor': std_sol is not None,
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
