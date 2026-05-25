"""
Baseline cryptarithmetic: standard Base-10 addition puzzles.

Equation structure: W1 + W2 = RESULT
Each option shows a letter-to-digit assignment; the correct one satisfies the
equation under standard Base-10 arithmetic.  One distractor is always the
assignment that would be correct under Base-9 rules (if one exists), making
the comparison with CF1 directly transparent.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solve
from utils.generator import generate_puzzle
from utils.distractor import make_distractors
from utils.display import build_equation_string
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

BASE = 10
RULE_NAME = 'cryptarithmetic_baseline'
NUM_SAMPLES = 100
MIN_UNIQUE_LETTERS = 6

RULE_DESC = (
    "Solve the following cryptarithmetic puzzle using standard arithmetic (Base 10).\n"
    "Rules:\n"
    "  - Valid digits: {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}.\n"
    "  - Each letter represents a unique digit.\n"
    "  - No multi-letter word may begin with 0.\n"
    "  - Addition carries when a column sum reaches 10 (standard rule).\n"
    "  - Subtraction borrows by adding 10 to the current digit (standard rule)."
)

# LHS configs: (lhs_lengths, lhs_signs)
# 4+3 and 4+4 formats give more digit positions → more cross-word letter sharing
# → higher probability of uniquely-solvable puzzles.
_CONFIGS = [
    ([4, 3], [1, 1]),
    ([4, 3], [1, 1]),
    ([4, 4], [1, 1]),
    ([3, 4], [1, 1]),
]


def _asgn_json(asgn):
    return json.dumps({k: v for k, v in sorted(asgn.items())})


def _make_question(equation):
    return (
        f"{RULE_DESC}\n\n"
        f"Equation:  {equation}\n\n"
        "Which of the following letter-to-digit assignments is the correct solution?\n"
        "Note: one option shows the solution obtained by applying Base-9 rules instead."
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
            # Keep unique-letter count ≤ 9 so a Base-9 distractor is possible.
            max_attempts=3000,
        )
        if result is None:
            continue

        words, coefficients, assignment = result
        equation = build_equation_string(words, coefficients)

        if equation in seen_equations:
            continue

        # --- Base-9 distractor ---
        base9_sols = solve(words, coefficients, base=9, max_solutions=1)
        base9_distractor = None
        if base9_sols and base9_sols[0] != assignment:
            base9_distractor = base9_sols[0]

        # --- Near-miss distractors ---
        near_misses = make_distractors(
            assignment, words, coefficients, BASE, rng, count=3
        )

        distractors = []
        if base9_distractor is not None:
            distractors.append(_asgn_json(base9_distractor))
        needed = 3 - len(distractors)
        distractors += [_asgn_json(d) for d in near_misses[:needed]]

        if len(distractors) < 3:
            continue

        sol_json = _asgn_json(assignment)
        opts, correct = shuffle_options(sol_json, distractors[:3], rng)
        seen_equations.add(equation)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'baseline',
            'puzzle': equation,
            'question': _make_question(equation),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'base': BASE,
                'num_letters': len(assignment),
                'equation': equation,
                'has_base9_distractor': base9_distractor is not None,
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
