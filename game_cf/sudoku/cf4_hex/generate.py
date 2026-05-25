"""CF4 – Hexadecimal Sudoku: 16×16 grid, 4×4 boxes, symbols {0,1,...,9,A,B,C,D,E,F}.
Each row, column, and 4×4 box must contain each of the 16 hex symbols exactly once.

Uniqueness checking is skipped for performance (16×16 is much harder).
We generate a complete valid grid and remove ~40 % of cells; the MCQ
options are the known solution + 3 near-miss distractors.
The "normal solution" concept does not apply here (incompatible grid size),
so all three distractors are near-misses.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.distractor import make_distractors
from utils.io_utils import write_csv
from utils.mcq import shuffle_options
from utils.display import grid_to_text

N = 16
BOX_SIZE = 4
VALID_DIGITS = list(range(0, 16))   # 0-15
RULE_NAME    = 'sudoku_cf4_hex'
TARGET_GIVENS = 100   # ~156 cells removed from 256 → ~60 % given
NUM_SAMPLES   = 100

HEX_TARGET = sorted(VALID_DIGITS)

RULE_DESC = (
    "Solve the following hexadecimal Sudoku puzzle.\n"
    "Rule change: The grid is 16×16 (instead of 9×9). The blocks are 4×4 "
    "(instead of 3×3). The valid symbols are the hexadecimal digits "
    "{0, 1, 2, 3, 4, 5, 6, 7, 8, 9, A, B, C, D, E, F}. "
    "Each row, column, and 4×4 block must contain each symbol exactly once."
)


def _make_complete_grid(rng):
    """
    Generate a random complete valid 16×16 HexSudoku via template + shuffle.

    Base template: grid[r][c] = (c + row_offset[r]) % 16
    where row_offset[r] = (r % 4) * 4 + r // 4.
    This is provably valid for all rows, columns, and 4×4 boxes.

    Randomisation: permute digit labels, shuffle rows within each band,
    shuffle columns within each stack, then shuffle bands and stacks.
    """
    BAND = BOX_SIZE  # 4

    # Build base template
    row_offset = [(r % BAND) * BAND + r // BAND for r in range(N)]
    template = [[(c + row_offset[r]) % N for c in range(N)] for r in range(N)]

    # 1. Random digit permutation  (0-15 → any bijection)
    perm = list(range(N))
    rng.shuffle(perm)
    grid = [[perm[template[r][c]] for c in range(N)] for r in range(N)]

    # 2. Shuffle rows within each band
    for band in range(N // BAND):
        rows_in_band = list(range(band * BAND, (band + 1) * BAND))
        rng.shuffle(rows_in_band)
        grid_copy = [grid[r][:] for r in range(N)]
        for i, r in enumerate(rows_in_band):
            grid[band * BAND + i] = grid_copy[r]

    # 3. Shuffle columns within each stack
    for stack in range(N // BAND):
        cols_in_stack = list(range(stack * BAND, (stack + 1) * BAND))
        rng.shuffle(cols_in_stack)
        grid_copy = [row[:] for row in grid]
        for i, c in enumerate(cols_in_stack):
            for r in range(N):
                grid[r][stack * BAND + i] = grid_copy[r][c]

    # 4. Shuffle entire bands
    bands = list(range(N // BAND))
    rng.shuffle(bands)
    grid_copy = [row[:] for row in grid]
    for i, b in enumerate(bands):
        for offset in range(BAND):
            grid[i * BAND + offset] = grid_copy[b * BAND + offset][:]

    # 5. Shuffle entire stacks
    stacks = list(range(N // BAND))
    rng.shuffle(stacks)
    grid_copy = [row[:] for row in grid]
    for i, s in enumerate(stacks):
        for r in range(N):
            for offset in range(BAND):
                grid[r][i * BAND + offset] = grid_copy[r][s * BAND + offset]

    return grid


def is_complete_valid_hex(grid):
    for r in range(N):
        if sorted(grid[r]) != HEX_TARGET:
            return False
    for c in range(N):
        if sorted(grid[r][c] for r in range(N)) != HEX_TARGET:
            return False
    for br in range(N // BOX_SIZE):
        for bc in range(N // BOX_SIZE):
            box = [grid[br * BOX_SIZE + i][bc * BOX_SIZE + j]
                   for i in range(BOX_SIZE) for j in range(BOX_SIZE)]
            if sorted(box) != HEX_TARGET:
                return False
    return True


def _hex_str(d):
    """Display digit as uppercase hex character."""
    return format(d, 'X')   # 0..9 → '0'..'9', 10..15 → 'A'..'F'


def _make_question(puzzle):
    display = grid_to_text(puzzle, N, BOX_SIZE, _hex_str)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle (. = empty cell):\n{display}\n\n"
        "Which of the following is the correct completed solution?"
    )


def _make_puzzle(complete, rng, target_givens=TARGET_GIVENS):
    """Remove random cells without uniqueness checking (too slow for 16×16).
    Empty cells are stored as None (not 0), because 0 is a valid hex digit.
    """
    puzzle = [row[:] for row in complete]
    cells = list(range(N * N))
    rng.shuffle(cells)
    given_count = N * N
    for idx in cells:
        if given_count <= target_givens:
            break
        r, c = divmod(idx, N)
        puzzle[r][c] = None
        given_count -= 1
    return puzzle


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen_puzzles = set()

    while len(rows) < num_samples:
        complete = _make_complete_grid(rng)

        # Uniqueness not checked (too expensive for 16×16);
        # MCQ correctness is preserved because distractors are near-misses.
        puzzle = _make_puzzle(complete, rng)

        puzzle_key = json.dumps(puzzle)
        if puzzle_key in seen_puzzles:
            continue

        given_mask = {(r, c) for r in range(N) for c in range(N) if puzzle[r][c] is not None}
        distractors = make_distractors(complete, N, is_complete_valid_hex, rng,
                                       count=3, given_mask=given_mask)
        if len(distractors) < 3:
            continue

        sol_json = json.dumps(complete)
        d_jsons  = [json.dumps(d) for d in distractors]
        opts, correct = shuffle_options(sol_json, d_jsons, rng)
        seen_puzzles.add(puzzle_key)

        num_givens = sum(1 for r in range(N) for c in range(N) if puzzle[r][c] is not None)
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
