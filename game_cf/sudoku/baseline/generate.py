"""Standard 9×9 Sudoku baseline generator. Produces 100 MCQ items."""
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
RULE_NAME = 'sudoku_baseline'
TARGET_GIVENS = 30
NUM_SAMPLES = 100

RULE_DESC = (
    "Solve the following standard Sudoku puzzle.\n"
    "Rules: Fill the 9×9 grid so that each row, column, and 3×3 box "
    "contains each of the digits 1 through 9 exactly once."
)


def _box_cells(r, c):
    br = (r // BOX_SIZE) * BOX_SIZE
    bc = (c // BOX_SIZE) * BOX_SIZE
    return [(br + i, bc + j) for i in range(BOX_SIZE) for j in range(BOX_SIZE)]


def is_valid(grid, r, c, d):
    if d in grid[r]:
        return False
    for i in range(N):
        if grid[i][c] == d:
            return False
    for r2, c2 in _box_cells(r, c):
        if grid[r2][c2] == d:
            return False
    return True


def is_complete_valid(grid):
    target = sorted(VALID_DIGITS)
    for r in range(N):
        if sorted(grid[r]) != target:
            return False
    for c in range(N):
        if sorted(grid[r][c] for r in range(N)) != target:
            return False
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            box = [grid[br * BOX_SIZE + i][bc * BOX_SIZE + j]
                   for i in range(BOX_SIZE) for j in range(BOX_SIZE)]
            if sorted(box) != target:
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
        complete = random_complete_grid(N, VALID_DIGITS, is_valid, rng)
        if complete is None:
            continue

        puzzle = make_puzzle(complete, N, VALID_DIGITS, is_valid, rng,
                             target_givens=TARGET_GIVENS, check_unique=True)

        puzzle_key = json.dumps(puzzle)
        if puzzle_key in seen_puzzles:
            continue

        given_mask = {(r, c) for r in range(N) for c in range(N) if puzzle[r][c] != 0}
        distractors = make_distractors(complete, N, is_complete_valid, rng,
                                       count=3, given_mask=given_mask)
        if len(distractors) < 3:
            continue

        sol_json = json.dumps(complete)
        d_jsons = [json.dumps(d) for d in distractors]
        opts, correct = shuffle_options(sol_json, d_jsons, rng)
        seen_puzzles.add(puzzle_key)

        num_givens = sum(1 for r in range(N) for c in range(N) if puzzle[r][c] != 0)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'baseline',
            'puzzle': json.dumps(puzzle),
            'question': _make_question(puzzle),
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
