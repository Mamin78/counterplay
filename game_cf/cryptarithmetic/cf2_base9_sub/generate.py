"""
CF2 — Nonary Cryptarithmetics, Base-9 Subtraction (open-eval).

Equation structure: W1 - W2 = RESULT
All arithmetic is performed in Base 9.  Borrowing adds 9 (not 10) to the
current digit when the top digit is smaller than the bottom digit.

Open-eval: the model produces the letter-to-digit JSON object directly;
``correct_answer`` is the unique base-9 solution. CF invariant: the base-9
assignment must not also satisfy the equation under base-10 rules.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import is_valid_assignment
from utils.generator import generate_puzzle
from utils.display import build_equation_string
from utils.io_utils import write_csv

BASE = 9
RULE_NAME = 'cryptarithmetic_cf2_base9_sub'
NUM_SAMPLES = 100
MIN_UNIQUE_LETTERS = 6

RULE_DESC = (
    "Solve the following cryptarithmetic subtraction puzzle in Base 9 (Nonary arithmetic).\n"
    "Rules:\n"
    "  - Valid digits: {0, 1, 2, 3, 4, 5, 6, 7, 8}.  The digit 9 does not exist.\n"
    "  - Each letter represents a unique digit from this set.\n"
    "  - No multi-letter word may begin with 0.\n"
    "  - When borrowing is needed, the 'Add 9' rule applies: the current digit "
    "gains 9 (not 10) and 1 is borrowed from the column to the left.\n"
    "  - Example: to compute 3 − 6, borrow 1 from the left; 3 becomes 3 + 9 = 12, "
    "then 12 − 6 = 6."
)

# W1 must be large enough to always exceed W2 in the chosen range.
# lhs_lengths = [L_W1, L_W2], lhs_signs = [+1, -1]
_CONFIGS = [
    ([4, 2], [1, -1]),
    ([4, 2], [1, -1]),
    ([4, 3], [1, -1]),
    ([5, 3], [1, -1]),
]


def _asgn_json(asgn):
    return json.dumps({k: v for k, v in sorted(asgn.items())})


def _make_question(equation):
    return (
        f"{RULE_DESC}\n\n"
        f"Equation:  {equation}\n\n"
        "Provide the unique letter-to-digit assignment as a JSON object."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen_equations = set()

    while len(rows) < num_samples:
        lhs_lengths, lhs_signs = rng.choice(_CONFIGS)

        result = generate_puzzle(
            rng, BASE, lhs_lengths, lhs_signs,
            min_unique_letters=MIN_UNIQUE_LETTERS,
            min_result_length=2,
            max_attempts=3000,
        )
        if result is None:
            continue

        words, coefficients, assignment = result
        equation = build_equation_string(words, coefficients)

        if equation in seen_equations:
            continue

        # CF invariant: the base-9 assignment must NOT also satisfy the
        # equation in base-10 — otherwise the CF and standard answers coincide.
        if is_valid_assignment(assignment, words, coefficients, base=10):
            continue

        sol_json = _asgn_json(assignment)
        seen_equations.add(equation)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': equation,
            'question': _make_question(equation),
            'option_A': '',
            'option_B': '',
            'option_C': '',
            'option_D': '',
            'correct_option': '',
            'correct_answer': sol_json,
            'params': json.dumps({
                'base': BASE,
                'num_letters': len(assignment),
                'equation': equation,
                'eval_mode': 'open_native_base9',
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
