"""Game of 24 baseline: four numbers, reach 24 using each exactly once with + − × ÷."""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solvable_for_24, one_solution_expression
from utils.expr import perturbed_distractors
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'game24_baseline'
NUM_SAMPLES = 100
TARGET = 24

RULE_DESC = (
    "Solve the following Game of 24 puzzle.\n"
    "Rules:\n"
    "  - You are given four positive integers.\n"
    "  - Use each number exactly once.\n"
    "  - Combine them with +, −, ×, ÷ and parentheses.\n"
    "  - Every intermediate division must yield an exact integer.\n"
    "  - The expression must evaluate to 24."
)


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(nums):
    nums_s = ", ".join(str(n) for n in nums)
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers: {nums_s}\n"
        "Which expression — using each number exactly once — reaches 24?"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 30:
        nums = [rng.randint(1, 13) for _ in range(4)]
        key = tuple(sorted(nums))
        if key in seen:
            skips += 1
            continue
        if not solvable_for_24(nums):
            skips += 1
            continue

        correct_expr = one_solution_expression(nums, TARGET)
        if correct_expr is None:
            skips += 1
            continue

        distractors = perturbed_distractors(correct_expr, TARGET, rng, count=3)
        if len(distractors) < 3:
            skips += 1
            continue

        seen.add(key)
        correct_disp = _normalize(correct_expr)
        distractor_disp = [_normalize(d) for d in distractors]
        opts, correct = shuffle_options(correct_disp, distractor_disp, rng)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'baseline',
            'puzzle': json.dumps({'numbers': nums, 'target': TARGET}),
            'question': _make_question(nums),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({'numbers': nums, 'target': TARGET}),
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
